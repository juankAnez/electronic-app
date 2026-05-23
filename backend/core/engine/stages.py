"""
ElectroSmart Platform — Motor de Cálculo Eléctrico
=================================================
Módulo: stages.py
Descripción: Implementa las etapas individuales del pipeline de ejecución
             utilizando un contexto inmutable y paso de estado limpio.
"""

from dataclasses import dataclass, field, replace
import math
from typing import List, Optional

from core.engine.domain import (
    BreakerSpec,
    CircuitAlert,
    CircuitInput,
    CircuitResult,
    ConductorSpec,
    SystemType,
    TraceEntry,
)
from core.engine.catalogs import (
    CONDUCTOR_CATALOG,
    get_available_gauges,
    get_breaker_commercial_sizes,
    get_grouping_factor,
    get_insulation_temperature,
    get_temperature_factor,
)
from core.engine.calculators import (
    calculate_design_current,
    calculate_nominal_current,
    calculate_voltage_drop,
    calculate_voltage_drop_percent,
)


@dataclass(frozen=True)
class CalculationContext:
    """Contexto de ejecución inmutable que viaja a través del pipeline."""
    input_data: CircuitInput
    nominal_current_a: float = 0.0
    design_current_a: float = 0.0
    temperature_factor: float = 1.0
    grouping_factor: float = 1.0
    selected_conductor: Optional[ConductorSpec] = None
    selected_breaker: Optional[BreakerSpec] = None
    voltage_drop_v: float = 0.0
    voltage_drop_percent: float = 0.0
    is_compliant: bool = True
    alerts: List[CircuitAlert] = field(default_factory=list)
    trace: List[TraceEntry] = field(default_factory=list)


class NormalizationStage:
    """Paso 1: Normaliza y valida valores iniciales de entrada."""
    
    def execute(self, ctx: CalculationContext) -> CalculationContext:
        inp = ctx.input_data
        
        # Validar consistencia básica de parámetros
        alerts = list(ctx.alerts)
        trace = list(ctx.trace)
        
        if inp.power_watts <= 0:
            alerts.append(CircuitAlert(
                severity="error",
                code="INVALID_POWER",
                message="La potencia del circuito debe ser mayor a cero.",
                rule_reference="General"
            ))
            
        if inp.voltage_ln <= 0 and inp.voltage_ll <= 0:
            alerts.append(CircuitAlert(
                severity="error",
                code="INVALID_VOLTAGE",
                message="Debe especificar al menos un voltaje nominal válido.",
                rule_reference="General"
            ))
            
        trace.append(TraceEntry(
            stage="Normalization",
            decision_rule="Validación de datos de entrada",
            rule_reference="NEC Art. 110",
            details={
                "power_watts": inp.power_watts,
                "voltage_ln": inp.voltage_ln,
                "voltage_ll": inp.voltage_ll,
                "length_m": inp.length_m
            }
        ))
        
        return replace(ctx, alerts=alerts, trace=trace)


class CurrentCalculationStage:
    """Paso 2: Calcula la corriente nominal y de diseño aplicando factores de continuidad."""
    
    def execute(self, ctx: CalculationContext) -> CalculationContext:
        if any(a.severity == "error" for a in ctx.alerts):
            return ctx
            
        inp = ctx.input_data
        trace = list(ctx.trace)
        
        # 1. Corriente nominal base
        nominal_current = calculate_nominal_current(
            power_w=inp.power_watts,
            voltage_ln=inp.voltage_ln,
            voltage_ll=inp.voltage_ll,
            system_type=inp.system_type,
            power_factor=inp.power_factor,
            efficiency=inp.efficiency
        )
        
        # 2. Corriente de diseño (continuidad)
        design_current = calculate_design_current(
            nominal_current=nominal_current,
            continuous_fraction=inp.continuous_fraction
        )
        
        trace.append(TraceEntry(
            stage="CurrentCalculation",
            decision_rule="Cálculo de corriente nominal y de diseño (125% continua)",
            rule_reference="NEC 210.19(A)(1)",
            details={
                "nominal_current_a": round(nominal_current, 3),
                "design_current_a": round(design_current, 3),
                "continuous_fraction": inp.continuous_fraction
            }
        ))
        
        return replace(
            ctx,
            nominal_current_a=nominal_current,
            design_current_a=design_current,
            trace=trace
        )


class CorrectionFactorsStage:
    """Paso 3: Determina factores de corrección por temperatura ambiente y agrupamiento."""
    
    def execute(self, ctx: CalculationContext) -> CalculationContext:
        if any(a.severity == "error" for a in ctx.alerts):
            return ctx
            
        inp = ctx.input_data
        trace = list(ctx.trace)
        
        # Obtener temperatura límite de aislamiento
        insulation_temp = get_insulation_temperature(inp.insulation_type)
        
        # Factor de temperatura
        f_temp = get_temperature_factor(inp.ambient_temperature_c, insulation_temp)
        
        # Factor de agrupamiento
        f_group = get_grouping_factor(inp.grouping_active_conductors)
        
        trace.append(TraceEntry(
            stage="CorrectionFactors",
            decision_rule="Obtención de factores de reducción",
            rule_reference="NEC Tablas 310.15(B)(1) y 310.15(C)(1)",
            details={
                "ambient_temperature_c": inp.ambient_temperature_c,
                "insulation_type": inp.insulation_type.value,
                "insulation_temp_c": insulation_temp,
                "temperature_factor": f_temp,
                "grouping_conductors": inp.grouping_active_conductors,
                "grouping_factor": f_group
            }
        ))
        
        return replace(
            ctx,
            temperature_factor=f_temp,
            grouping_factor=f_group,
            trace=trace
        )


class ConductorSelectionStage:
    """Paso 4: Selecciona el menor calibre de conductor que satisface ampacidad y terminales."""
    
    def execute(self, ctx: CalculationContext) -> CalculationContext:
        if any(a.severity == "error" for a in ctx.alerts):
            return ctx
            
        inp = ctx.input_data
        trace = list(ctx.trace)
        alerts = list(ctx.alerts)
        
        available_gauges = get_available_gauges(inp.conductor_material)
        selected_spec = None
        
        # Buscar el menor calibre que cumpla
        for gauge in available_gauges:
            specs = CONDUCTOR_CATALOG[inp.conductor_material][gauge]
            ampacity_base = specs["ampacities"][get_insulation_temperature(inp.insulation_type)]
            
            # Ampacidad corregida por factores ambientales
            ampacity_corrected = ampacity_base * ctx.temperature_factor * ctx.grouping_factor
            
            # Limitación por terminales de equipos (NEC 110.14(C))
            # No podemos superar la ampacidad de la columna de temperatura del terminal (normalmente 75°C)
            terminal_temp = int(inp.terminal_temp_rating_c)
            ampacity_terminal = specs["ampacities"].get(terminal_temp, specs["ampacities"][75])
            
            # Ampacidad efectiva real
            ampacity_effective = min(ampacity_corrected, ampacity_terminal)
            
            # Validaciones:
            # 1. La ampacidad efectiva debe ser >= corriente nominal del circuito (cargas sin factor 1.25)
            cond_effective = (ampacity_effective >= ctx.nominal_current_a)
            
            # 2. La ampacidad del terminal (antes de correcciones) debe ser >= corriente de diseño
            #    (100% no continuas + 125% continuas) para coordinar térmicamente
            cond_terminal = (ampacity_terminal >= ctx.design_current_a)
            
            if cond_effective and cond_terminal:
                selected_spec = ConductorSpec(
                    gauge_awg=gauge,
                    cross_section_mm2=specs["cross_section_mm2"],
                    ampacity_base_a=ampacity_base,
                    ampacity_corrected_a=round(ampacity_effective, 2),
                    resistance_ac_ohm_km=specs["resistance_ac_ohm_km"],
                    reactance_ac_ohm_km=specs["reactance_ac_ohm_km"]
                )
                break
                
        if not selected_spec:
            alerts.append(CircuitAlert(
                severity="error",
                code="CONDUCTOR_NOT_FOUND",
                message="No se encontró ningún calibre de conductor que cumpla con los requisitos de ampacidad y terminales.",
                rule_reference="NEC 310.16 / 110.14(C)"
            ))
            return replace(ctx, alerts=alerts)
            
        trace.append(TraceEntry(
            stage="ConductorSelection",
            decision_rule="Selección de conductor por ampacidad base y efectiva",
            rule_reference="NEC 310.16 y 110.14(C)",
            details={
                "gauge_awg": selected_spec.gauge_awg,
                "cross_section_mm2": selected_spec.cross_section_mm2,
                "ampacity_base_a": float(selected_spec.ampacity_base_a),
                "ampacity_effective_a": float(selected_spec.ampacity_corrected_a),
                "terminal_rating_limit_a": float(ampacity_terminal),
                "nominal_current_a": round(ctx.nominal_current_a, 2),
                "design_current_a": round(ctx.design_current_a, 2)
            }
        ))
        
        return replace(ctx, selected_conductor=selected_spec, trace=trace)


class VoltageDropStage:
    """Paso 5: Calcula la caída de tensión absoluta y porcentual del circuito."""
    
    def execute(self, ctx: CalculationContext) -> CalculationContext:
        if any(a.severity == "error" for a in ctx.alerts) or not ctx.selected_conductor:
            return ctx
            
        inp = ctx.input_data
        cond = ctx.selected_conductor
        trace = list(ctx.trace)
        
        # Calcular caída de tensión absoluta (V) usando corriente nominal (I_base)
        voltage_drop = calculate_voltage_drop(
            nominal_current=ctx.nominal_current_a,
            length_m=inp.length_m,
            resistance_ac_ohm_km=cond.resistance_ac_ohm_km,
            reactance_ac_ohm_km=cond.reactance_ac_ohm_km,
            power_factor=inp.power_factor,
            system_type=inp.system_type
        )
        
        # Porcentaje de caída de tensión
        vd_pct = calculate_voltage_drop_percent(
            voltage_drop_v=voltage_drop,
            voltage_ln=inp.voltage_ln,
            voltage_ll=inp.voltage_ll,
            system_type=inp.system_type
        )
        
        trace.append(TraceEntry(
            stage="VoltageDropCalculation",
            decision_rule="Cálculo de caída de tensión por tramo",
            rule_reference="NEC Nota Informativa 210.19(A)",
            details={
                "voltage_drop_v": round(voltage_drop, 3),
                "voltage_drop_percent": round(vd_pct, 3),
                "conductor_resistance_ohm_km": cond.resistance_ac_ohm_km,
                "conductor_reactance_ohm_km": cond.reactance_ac_ohm_km,
                "circuit_length_m": inp.length_m
            }
        ))
        
        return replace(
            ctx,
            voltage_drop_v=voltage_drop,
            voltage_drop_percent=vd_pct,
            trace=trace
        )


class IterativeResizeStage:
    """Paso 6: Si la caída de tensión supera el límite, incrementa iterativamente el calibre."""
    
    def execute(self, ctx: CalculationContext) -> CalculationContext:
        if any(a.severity == "error" for a in ctx.alerts) or not ctx.selected_conductor:
            return ctx
            
        inp = ctx.input_data
        trace = list(ctx.trace)
        alerts = list(ctx.alerts)
        
        # Límite configurado
        limit_pct = inp.max_voltage_drop_pct
        
        # Si ya cumple con el calibre seleccionado, no iteramos
        if ctx.voltage_drop_percent <= limit_pct:
            return ctx
            
        available_gauges = get_available_gauges(inp.conductor_material)
        current_gauge = ctx.selected_conductor.gauge_awg
        
        # Buscar el índice del calibre actual
        try:
            start_idx = available_gauges.index(current_gauge)
        except ValueError:
            return ctx
            
        resized_spec = None
        final_vd_pct = ctx.voltage_drop_percent
        final_vd_v = ctx.voltage_drop_v
        
        # Iterar subiendo calibre
        for i in range(start_idx + 1, len(available_gauges)):
            gauge = available_gauges[i]
            specs = CONDUCTOR_CATALOG[inp.conductor_material][gauge]
            
            # Recalcular caída de tensión para este calibre
            vd_v = calculate_voltage_drop(
                nominal_current=ctx.nominal_current_a,
                length_m=inp.length_m,
                resistance_ac_ohm_km=specs["resistance_ac_ohm_km"],
                reactance_ac_ohm_km=specs["reactance_ac_ohm_km"],
                power_factor=inp.power_factor,
                system_type=inp.system_type
            )
            vd_pct = calculate_voltage_drop_percent(
                voltage_drop_v=vd_v,
                voltage_ln=inp.voltage_ln,
                voltage_ll=inp.voltage_ll,
                system_type=inp.system_type
            )
            
            # Si logramos que esté por debajo del límite, seleccionamos y paramos
            if vd_pct <= limit_pct:
                ampacity_base = specs["ampacities"][get_insulation_temperature(inp.insulation_type)]
                ampacity_corrected = ampacity_base * ctx.temperature_factor * ctx.grouping_factor
                terminal_temp = int(inp.terminal_temp_rating_c)
                ampacity_terminal = specs["ampacities"].get(terminal_temp, specs["ampacities"][75])
                
                resized_spec = ConductorSpec(
                    gauge_awg=gauge,
                    cross_section_mm2=specs["cross_section_mm2"],
                    ampacity_base_a=ampacity_base,
                    ampacity_corrected_a=round(min(ampacity_corrected, ampacity_terminal), 2),
                    resistance_ac_ohm_km=specs["resistance_ac_ohm_km"],
                    reactance_ac_ohm_km=specs["reactance_ac_ohm_km"]
                )
                final_vd_pct = vd_pct
                final_vd_v = vd_v
                break
                
        if resized_spec:
            trace.append(TraceEntry(
                stage="IterativeResize",
                decision_rule="Redimensionamiento automático del conductor por caída de tensión",
                rule_reference="NEC Nota Informativa 210.19(A) [Eficiencia]",
                details={
                    "original_gauge_awg": current_gauge,
                    "new_gauge_awg": resized_spec.gauge_awg,
                    "original_vd_percent": round(ctx.voltage_drop_percent, 2),
                    "new_vd_percent": round(final_vd_pct, 2),
                    "max_limit_percent": limit_pct
                }
            ))
            return replace(
                ctx,
                selected_conductor=resized_spec,
                voltage_drop_v=final_vd_v,
                voltage_drop_percent=final_vd_pct,
                trace=trace
            )
        else:
            # Si recorrimos todos los calibres y ninguno cumple la caída de tensión,
            # seleccionamos el calibre máximo disponible del catálogo para mitigar la caída de tensión
            # lo más posible, y reportamos la advertencia.
            max_gauge = available_gauges[-1]
            max_specs = CONDUCTOR_CATALOG[inp.conductor_material][max_gauge]
            ampacity_base = max_specs["ampacities"][get_insulation_temperature(inp.insulation_type)]
            ampacity_corrected = ampacity_base * ctx.temperature_factor * ctx.grouping_factor
            terminal_temp = int(inp.terminal_temp_rating_c)
            ampacity_terminal = max_specs["ampacities"].get(terminal_temp, max_specs["ampacities"][75])
            
            max_conductor = ConductorSpec(
                gauge_awg=max_gauge,
                cross_section_mm2=max_specs["cross_section_mm2"],
                ampacity_base_a=ampacity_base,
                ampacity_corrected_a=round(min(ampacity_corrected, ampacity_terminal), 2),
                resistance_ac_ohm_km=max_specs["resistance_ac_ohm_km"],
                reactance_ac_ohm_km=max_specs["reactance_ac_ohm_km"]
            )
            
            # Recalcular caída de tensión con el calibre máximo
            max_vd_v = calculate_voltage_drop(
                nominal_current=ctx.nominal_current_a,
                length_m=inp.length_m,
                resistance_ac_ohm_km=max_conductor.resistance_ac_ohm_km,
                reactance_ac_ohm_km=max_conductor.reactance_ac_ohm_km,
                power_factor=inp.power_factor,
                system_type=inp.system_type
            )
            max_vd_pct = calculate_voltage_drop_percent(
                voltage_drop_v=max_vd_v,
                voltage_ln=inp.voltage_ln,
                voltage_ll=inp.voltage_ll,
                system_type=inp.system_type
            )
            
            alerts.append(CircuitAlert(
                severity="warning",
                code="VOLTAGE_DROP_EXCEEDED",
                message=f"La caída de tensión del circuito ({round(max_vd_pct, 2)}%) supera el límite del {limit_pct}%, incluso utilizando el mayor calibre disponible ({max_gauge}).",
                rule_reference="NEC 210.19(A)"
            ))
            
            trace.append(TraceEntry(
                stage="IterativeResize",
                decision_rule="Fallo de caída de tensión - calibre máximo forzado",
                rule_reference="NEC 210.19(A)",
                details={
                    "original_gauge_awg": current_gauge,
                    "forced_max_gauge_awg": max_gauge,
                    "max_gauge_vd_percent": round(max_vd_pct, 2),
                    "max_limit_percent": limit_pct
                }
            ))
            
            return replace(
                ctx,
                selected_conductor=max_conductor,
                voltage_drop_v=max_vd_v,
                voltage_drop_percent=max_vd_pct,
                alerts=alerts,
                trace=trace
            )


class BreakerSelectionStage:
    """Paso 7: Selecciona la protección (breaker) comercial adecuada y valida coordinación."""
    
    def execute(self, ctx: CalculationContext) -> CalculationContext:
        if any(a.severity == "error" for a in ctx.alerts) or not ctx.selected_conductor:
            return ctx
            
        inp = ctx.input_data
        cond = ctx.selected_conductor
        trace = list(ctx.trace)
        alerts = list(ctx.alerts)
        
        # 1. Buscar polos del breaker según el sistema
        poles = 1
        if inp.system_type == SystemType.SPLIT_PHASE:
            poles = 2
        elif inp.system_type in (SystemType.THREE_PHASE_WYE, SystemType.THREE_PHASE_DELTA):
            poles = 3
            
        # 2. Encontrar el breaker comercial adecuado
        #    Regla: Breaker nominal >= Corriente de diseño del circuito (I_diseño)
        commercial_sizes = get_breaker_commercial_sizes()
        selected_amps = None
        
        for size in commercial_sizes:
            if size >= ctx.design_current_a:
                selected_amps = size
                break
                
        if not selected_amps:
            alerts.append(CircuitAlert(
                severity="error",
                code="BREAKER_NOT_FOUND",
                message=f"No se encontró un breaker comercial estándar para la corriente de diseño de {round(ctx.design_current_a, 2)} A.",
                rule_reference="NEC 240.6"
            ))
            return replace(ctx, alerts=alerts)
            
        # 3. Validar coordinación con el conductor
        #    Regla estándar: Breaker nominal <= Ampacidad efectiva del cable.
        #    Regla Next-Size-Up (NEC 240.4(B)): Si la ampacidad corregida está entre tamaños comerciales de breaker,
        #    se permite usar el breaker inmediatamente superior, siempre que la ampacidad no exceda 800A.
        is_coordinated = (selected_amps <= cond.ampacity_corrected_a)
        
        if not is_coordinated and inp.allow_next_size_up and cond.ampacity_corrected_a < 800.0:
            # Buscar el tamaño comercial estándar inmediatamente superior a la ampacidad efectiva del cable
            next_size_up_allowed = None
            for size in commercial_sizes:
                if size > cond.ampacity_corrected_a:
                    next_size_up_allowed = size
                    break
            
            # Si el breaker elegido es precisamente el next-size-up, se considera coordinado
            if next_size_up_allowed and selected_amps == next_size_up_allowed:
                is_coordinated = True
                trace.append(TraceEntry(
                    stage="BreakerSelection",
                    decision_rule="Aplicación de regla disyuntor superior comercial (Next-Size-Up)",
                    rule_reference="NEC 240.4(B)",
                    details={
                        "conductor_ampacity_effective_a": cond.ampacity_corrected_a,
                        "breaker_selected_a": selected_amps,
                        "reason": "Permitido por no exceder 800A y ser el tamaño comercial inmediatamente superior."
                    }
                ))
                
        if not is_coordinated:
            # Si no hay coordinación, tenemos un mismatch de seguridad.
            # Agregamos una alerta crítica de sobrecorriente.
            alerts.append(CircuitAlert(
                severity="error",
                code="OVERCURRENT_PROTECTION_FAIL",
                message=f"La capacidad del breaker seleccionado ({selected_amps} A) es superior a la capacidad permitida del cable ({cond.ampacity_corrected_a} A). Peligro de sobrecarga.",
                rule_reference="NEC 240.4"
            ))
            return replace(ctx, alerts=alerts)
            
        selected_breaker = BreakerSpec(
            ampacity_a=selected_amps,
            poles=poles,
            ka_rating=10.0  # Capacidad comercial básica por defecto
        )
        
        trace.append(TraceEntry(
            stage="BreakerSelection",
            decision_rule="Selección final de protección eléctrica",
            rule_reference="NEC 240.4 / 240.6",
            details={
                "breaker_ampacity_a": selected_breaker.ampacity_a,
                "breaker_poles": selected_breaker.poles,
                "design_current_a": round(ctx.design_current_a, 2),
                "conductor_ampacity_effective_a": cond.ampacity_corrected_a
            }
        ))
        
        return replace(ctx, selected_breaker=selected_breaker, trace=trace)


class FinalValidationStage:
    """Paso 8: Consolida el cumplimiento del circuito y genera alertas operativas."""
    
    def execute(self, ctx: CalculationContext) -> CalculationContext:
        trace = list(ctx.trace)
        alerts = list(ctx.alerts)
        
        # Determinar si el circuito cumple todos los requisitos
        has_errors = any(a.severity == "error" for a in alerts)
        is_compliant = not has_errors
        
        # Alertas preventivas adicionales (Warnings e Infos)
        if is_compliant:
            # Alerta preventiva de caída de tensión cercana al límite
            limit_pct = ctx.input_data.max_voltage_drop_pct
            if ctx.voltage_drop_percent > (limit_pct * 0.85):
                alerts.append(CircuitAlert(
                    severity="warning",
                    code="VOLTAGE_DROP_CLOSE_TO_LIMIT",
                    message=f"La caída de tensión del circuito ({round(ctx.voltage_drop_percent, 2)}%) está muy cerca del límite máximo permitido ({limit_pct}%).",
                    rule_reference="NEC Nota Informativa 210.19(A)"
                ))
                
            # Alerta preventiva sobre agrupamiento alto
            if ctx.input_data.grouping_active_conductors > 3:
                alerts.append(CircuitAlert(
                    severity="info",
                    code="GROUPING_DERATING_APPLIED",
                    message=f"Se aplicó un factor de reducción del agrupamiento del {int((1 - ctx.grouping_factor)*100)}% por llevar {ctx.input_data.grouping_active_conductors} conductores en canalización.",
                    rule_reference="NEC 310.15(C)(1)"
                ))
        
        trace.append(TraceEntry(
            stage="FinalValidation",
            decision_rule="Consolidación del cumplimiento normativo del circuito",
            rule_reference="General",
            details={
                "is_compliant": is_compliant,
                "total_alerts": len(alerts)
            }
        ))
        
        return replace(ctx, is_compliant=is_compliant, alerts=alerts, trace=trace)
