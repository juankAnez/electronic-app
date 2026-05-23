"""
ElectroSmart Platform — Core Application Services
=================================================
Este módulo provee la capa de servicios (ElectricalEngineService) para integrar el
motor de cálculo eléctrico puro de Python con los modelos de la base de datos
Django ORM.
"""

from decimal import Decimal
import logging
from django.db import transaction
from django.shortcuts import get_object_or_404
from core.models import (
    Project,
    Circuit,
    CircuitCalculation,
    CalculationHistory,
    CalculationAlert,
    ConductorCatalog,
    BreakerCatalog,
    BillOfMaterials,
    Budget,
    MaterialCatalog,
    MaterialUnitMeasure,
)
from core.engine.domain import (
    CircuitInput,
    SystemType,
    ConductorMaterial,
    InsulationType,
)
from core.engine.pipeline import ElectricalEngineRunner

logger = logging.getLogger(__name__)


class ElectricalEngineService:
    """
    Servicio de integración para ejecutar cálculos sobre proyectos
    y persistir los resultados en la base de datos de Django.
    """

    @classmethod
    def calculate_project(cls, project_id, user) -> dict:
        """
        Ejecuta los cálculos eléctricos de todos los circuitos y tableros
        de un proyecto de forma transaccional.
        """
        project = get_object_or_404(Project, id=project_id)
        params = getattr(project, "parameters", None)
        
        # Parámetros ambientales y de diseño
        ambient_temp = float(params.ambient_temp_c) if params else 30.0
        max_vd_pct = float(params.max_voltage_drop_pct) if params else 3.0
        
        # Resolver tensiones nominales basadas en el nivel de tensión del proyecto
        voltage_val = float(project.voltage_level.voltage_numeric)
        phase_type = project.voltage_level.phase_type # single, split, three
        
        if phase_type == "three":
            voltage_ll = voltage_val
            voltage_ln = voltage_ll / 1.73205
        elif phase_type == "split":
            voltage_ll = voltage_val
            voltage_ln = voltage_ll / 2.0
        else: # single
            voltage_ln = voltage_val
            voltage_ll = voltage_val

        results = []
        
        # Ejecutar los cálculos de cada circuito
        with transaction.atomic():
            panels = project.panels.all()
            for panel in panels:
                circuits = panel.circuits.all()
                for circuit in circuits:
                    res = cls._calculate_single_circuit(
                        circuit=circuit,
                        project=project,
                        ambient_temp=ambient_temp,
                        max_vd_pct=max_vd_pct,
                        voltage_ln=voltage_ln,
                        voltage_ll=voltage_ll,
                        user=user
                    )
                    results.append(res)
            
            # Recalcular el presupuesto total del proyecto
            cls._update_project_budget(project)
            
            # Actualizar el estado del proyecto
            project.status = "calculated"
            project.save()
            
        return {
            "project_id": str(project.id),
            "project_name": project.name,
            "circuits_calculated": len(results),
            "is_compliant": all(r.get("is_compliant", False) for r in results if "error" not in r),
            "circuits": results
        }

    @classmethod
    def _calculate_single_circuit(
        cls,
        circuit: Circuit,
        project: Project,
        ambient_temp: float,
        max_vd_pct: float,
        voltage_ln: float,
        voltage_ll: float,
        user
    ) -> dict:
        """
        Calcula un único circuito derivado e interactúa con el ORM para guardar resultados.
        """
        loads = circuit.loads.all()
        
        # Si no hay cargas, no calculamos el circuito
        if not loads.exists():
            return {
                "circuit_id": str(circuit.id),
                "circuit_number": circuit.circuit_number,
                "is_compliant": False,
                "error": "El circuito no tiene cargas registradas."
            }
            
        # Calcular potencia total, factor de potencia promedio ponderado y fracción continua
        total_w = 0.0
        continuous_w = 0.0
        weighted_pf_sum = 0.0
        
        for load in loads:
            w = float(load.power_watts) * float(load.quantity)
            total_w += w
            if load.is_continuous:
                continuous_w += w
            weighted_pf_sum += float(load.power_factor) * w
            
        power_factor = (weighted_pf_sum / total_w) if total_w > 0 else 0.90
        continuous_fraction = (continuous_w / total_w) if total_w > 0 else 0.0
        
        # Mapear material y aislamiento por defecto a nivel de base de datos
        material = ConductorMaterial.COPPER
        insulation = InsulationType.THHN
        
        # Mapear el tipo de sistema del circuito
        if circuit.is_three_phase:
            if project.phase_config.has_neutral:
                system_type = SystemType.THREE_PHASE_WYE
            else:
                system_type = SystemType.THREE_PHASE_DELTA
        else:
            if circuit.phase_assignment in ("AB", "BC", "CA"):
                system_type = SystemType.SPLIT_PHASE
            else:
                system_type = SystemType.SINGLE_PHASE
                
        # Construir objeto input_data para el motor puro
        inp = CircuitInput(
            system_type=system_type,
            voltage_ln=voltage_ln,
            voltage_ll=voltage_ll,
            frequency=float(project.voltage_level.frequency),
            length_m=float(circuit.length_meters),
            power_watts=total_w,
            power_factor=power_factor,
            efficiency=1.00,
            continuous_fraction=continuous_fraction,
            ambient_temperature_c=ambient_temp,
            conductor_material=material,
            insulation_type=insulation,
            terminal_temp_rating_c=75.0, 
            grouping_active_conductors=3, 
            max_voltage_drop_pct=max_vd_pct,
            allow_next_size_up=True,
            circuit_id=str(circuit.id)
        )
        
        # 1. Ejecutar el motor puro de cálculo
        engine_result = ElectricalEngineRunner.calculate_circuit(inp)
        
        # 2. Buscar especificaciones del catálogo en la base de datos para mapear llaves foráneas (FKs)
        norm_ver = project.norm_version
        
        conductor_db = None
        if engine_result.selected_conductor:
            conductor_db = ConductorCatalog.objects.filter(
                norm_version=norm_ver,
                gauge_awg=engine_result.selected_conductor.gauge_awg,
                wire_material__material_name__iexact="Cobre" if material == ConductorMaterial.COPPER else "Aluminio",
                insulation_type__code__iexact=insulation.value
            ).first()
            
        breaker_db = None
        if engine_result.selected_breaker:
            breaker_db = BreakerCatalog.objects.filter(
                norm_version=norm_ver,
                ampacity=Decimal(str(engine_result.selected_breaker.ampacity_a)),
                poles=engine_result.selected_breaker.poles
            ).first()
            
        # 3. Guardar el resultado activo en CircuitCalculation
        calc_active, created = CircuitCalculation.objects.get_or_create(
            circuit=circuit,
            defaults={"calculation_version": 1}
        )
        
        if not created:
            calc_active.calculation_version += 1
            
        calc_active.total_load_amps = Decimal(str(engine_result.nominal_current_a))
        calc_active.demand_load_amps = Decimal(str(engine_result.design_current_a))
        calc_active.conductor = conductor_db
        calc_active.breaker = breaker_db
        calc_active.voltage_drop_percent = Decimal(str(engine_result.voltage_drop_percent))
        calc_active.is_compliant = engine_result.is_compliant
        
        # Serializar snapshot detallado de la traza para auditoría futura y el asistente de IA
        serialized_trace = []
        for entry in engine_result.trace:
            serialized_trace.append({
                "stage": entry.stage,
                "decision_rule": entry.decision_rule,
                "rule_reference": entry.rule_reference,
                "details": entry.details
            })
            
        calc_active.parameters_snapshot = {
            "inputs": {
                "power_watts": total_w,
                "power_factor": power_factor,
                "continuous_fraction": continuous_fraction,
                "ambient_temperature_c": ambient_temp,
                "length_m": float(circuit.length_meters),
                "system_type": system_type.value
            },
            "outputs": {
                "conductor_gauge": engine_result.selected_conductor.gauge_awg if engine_result.selected_conductor else None,
                "breaker_ampacity": engine_result.selected_breaker.ampacity_a if engine_result.selected_breaker else None,
                "voltage_drop_percent": engine_result.voltage_drop_percent
            },
            "trace": serialized_trace
        }
        calc_active.save()
        
        # 4. Guardar snapshot histórico inmutable en CalculationHistory
        hist = CalculationHistory.objects.create(
            circuit=circuit,
            calculation_version=calc_active.calculation_version,
            total_load_amps=calc_active.total_load_amps,
            demand_load_amps=calc_active.demand_load_amps,
            conductor_catalog_id=conductor_db.id if conductor_db else None,
            breaker_catalog_id=breaker_db.id if breaker_db else None,
            voltage_drop_percent=calc_active.voltage_drop_percent,
            is_compliant=calc_active.is_compliant,
            full_input_snapshot=calc_active.parameters_snapshot["inputs"],
            full_output_snapshot={
                "outputs": calc_active.parameters_snapshot["outputs"],
                "trace": serialized_trace
            },
            created_by=user if user and user.is_authenticated else None
        )
        
        # 5. Guardar alertas en la base de datos
        for alert in engine_result.alerts:
            severity_db = "error" if alert.severity == "error" else "warning"
            
            alert_type_db = "overcurrent"
            if alert.code in ("VOLTAGE_DROP_HIGH", "VOLTAGE_DROP_EXCEEDED"):
                alert_type_db = "voltage_drop"
            elif alert.code == "TEMPERATURE_FAIL":
                alert_type_db = "temperature"
                
            CalculationAlert.objects.create(
                calculation_history=hist,
                alert_type=alert_type_db,
                severity=severity_db,
                message=alert.message,
                details={"code": alert.code, "rule_reference": alert.rule_reference}
            )
            
        # 6. Actualizar o crear items en la Lista de Materiales (BOM) del circuito
        cls._update_circuit_bom(circuit, project, engine_result, conductor_db, breaker_db)
        
        return {
            "circuit_id": str(circuit.id),
            "circuit_number": circuit.circuit_number,
            "nominal_current_a": engine_result.nominal_current_a,
            "design_current_a": engine_result.design_current_a,
            "selected_conductor": engine_result.selected_conductor.gauge_awg if engine_result.selected_conductor else None,
            "selected_breaker": f"{engine_result.selected_breaker.poles}P {engine_result.selected_breaker.ampacity_a}A" if engine_result.selected_breaker else None,
            "voltage_drop_percent": engine_result.voltage_drop_percent,
            "is_compliant": engine_result.is_compliant,
            "alerts_count": len(engine_result.alerts)
        }

    @classmethod
    def _update_circuit_bom(cls, circuit: Circuit, project: Project, engine_result, conductor_db, breaker_db):
        """
        Genera/actualiza las entradas en el listado de materiales (BOM) para el circuito calculado.
        """
        # Eliminar entradas previas asociadas a este circuito específico para recalcular limpiamente
        BillOfMaterials.objects.filter(project=project, circuit=circuit).delete()
        
        unit_measure = MaterialUnitMeasure.objects.filter(name="metro").first()
        if not unit_measure:
            unit_measure = MaterialUnitMeasure.objects.first()
            
        # 1. Agregar conductor (cables)
        if conductor_db and engine_result.selected_conductor:
            sku_cable = f"CABLE-CU-THHN-{engine_result.selected_conductor.gauge_awg.replace(' ', '')}"
            material_cable, _ = MaterialCatalog.objects.get_or_create(
                sku=sku_cable,
                defaults={
                    "name": f"Cable de Cobre THHN {engine_result.selected_conductor.gauge_awg}",
                    "unit_measure": unit_measure,
                    "unit_price": Decimal("2.50")
                }
            )
            
            wires_count = 2 
            if circuit.is_three_phase:
                wires_count = 4 
            elif circuit.phase_assignment in ("AB", "BC", "CA"):
                wires_count = 3 
                
            # Agregar desperdicio del 10%
            quantity_meters = float(circuit.length_meters) * wires_count * 1.10
            
            BillOfMaterials.objects.create(
                project=project,
                material=material_cable,
                circuit=circuit,
                quantity=Decimal(str(round(quantity_meters, 2))),
                unit_price=material_cable.unit_price,
                notes=f"Conductor principal ramal para circuito {circuit.circuit_number}. Incluye 10% desperdicio."
            )
            
        # 2. Agregar protección (breaker)
        if breaker_db and engine_result.selected_breaker:
            sku_breaker = f"BREAKER-{engine_result.selected_breaker.poles}P-{int(engine_result.selected_breaker.ampacity_a)}A"
            unit_measure_u = MaterialUnitMeasure.objects.filter(name="unidad").first() or unit_measure
            material_breaker, _ = MaterialCatalog.objects.get_or_create(
                sku=sku_breaker,
                defaults={
                    "name": f"Disyuntor Termomagnético {engine_result.selected_breaker.poles} Polos {int(engine_result.selected_breaker.ampacity_a)}A Curva C",
                    "unit_measure": unit_measure_u,
                    "unit_price": Decimal("15.00") * engine_result.selected_breaker.poles
                }
            )
            
            BillOfMaterials.objects.create(
                project=project,
                material=material_breaker,
                circuit=circuit,
                quantity=Decimal("1.00"),
                unit_price=material_breaker.unit_price,
                notes=f"Protección termo-magnética del circuito {circuit.circuit_number} en tablero {circuit.panel.name}."
            )

    @classmethod
    def _update_project_budget(cls, project: Project):
        """
        Recalcula el presupuesto monetario del proyecto basándose en los elementos
        acumulados en BillOfMaterials.
        """
        boms = BillOfMaterials.objects.filter(project=project)
        subtotal = sum(item.quantity * item.unit_price for item in boms)
        
        budget, created = Budget.objects.get_or_create(
            project=project,
            version=1,
            defaults={"tax_percent": Decimal("19.00")}
        )
        
        budget.subtotal = Decimal(str(subtotal))
        budget.save()
