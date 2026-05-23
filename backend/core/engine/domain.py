"""
ElectroSmart Platform — Motor de Cálculo Eléctrico
=================================================
Módulo: domain.py
Descripción: Define los tipos de datos, enumeraciones y dataclasses inmutables
             que constituyen el dominio técnico del motor.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class SystemType(str, Enum):
    """Tipos de sistemas de distribución eléctrica."""
    SINGLE_PHASE = "single_phase"      # Monofásico (fase + neutro)
    SPLIT_PHASE = "split_phase"        # Bifásico (dos fases + neutro)
    THREE_PHASE_WYE = "three_phase_wye" # Trifásico en estrella (con neutro)
    THREE_PHASE_DELTA = "three_phase_delta" # Trifásico en delta (sin neutro)


class ConductorMaterial(str, Enum):
    """Materiales conductores eléctricos estándar."""
    COPPER = "copper"
    ALUMINUM = "aluminum"


class InsulationType(str, Enum):
    """Tipos de aislamiento de conductores comunes."""
    THHN = "THHN"
    THWN_2 = "THWN-2"
    XHHW = "XHHW"
    TW = "TW"
    THW = "THW"


@dataclass(frozen=True)
class CircuitInput:
    """
    Datos de entrada inmutables requeridos para calcular un circuito derivado.
    Todas las medidas están normalizadas al Sistema Internacional (SI) o normas eléctricas.
    """
    system_type: SystemType
    voltage_ln: float                # Voltaje Fase-Neutro (V)
    voltage_ll: float                # Voltaje Fase-Fase (V)
    frequency: float                 # Frecuencia (Hz, ej. 60.0)
    length_m: float                  # Longitud del tramo (metros)
    power_watts: float               # Potencia activa total de la carga (W)
    power_factor: float = 0.90       # Factor de potencia (0.0 - 1.0)
    efficiency: float = 1.00         # Eficiencia del equipo (0.0 - 1.0)
    continuous_fraction: float = 0.0 # Fracción de la carga que es continua (0.0 a 1.0)
    ambient_temperature_c: float = 30.0 # Temperatura ambiente de diseño (°C)
    conductor_material: ConductorMaterial = ConductorMaterial.COPPER
    insulation_type: InsulationType = InsulationType.THHN
    terminal_temp_rating_c: float = 75.0 # Límite de temperatura del terminal de equipo (°C)
    grouping_active_conductors: int = 3 # Número de cables cargados en la misma canalización
    max_voltage_drop_pct: float = 3.0  # Límite máximo de caída de tensión (%)
    allow_next_size_up: bool = True   # Permitir la regla del breaker comercial inmediato superior
    circuit_id: Optional[str] = None  # Identificador de persistencia opcional


@dataclass(frozen=True)
class ConductorSpec:
    """Especificación técnica de un conductor seleccionado."""
    gauge_awg: str
    cross_section_mm2: float
    ampacity_base_a: float
    ampacity_corrected_a: float
    resistance_ac_ohm_km: float
    reactance_ac_ohm_km: float


@dataclass(frozen=True)
class BreakerSpec:
    """Especificación de la protección (disyuntor) seleccionada."""
    ampacity_a: float
    poles: int
    trip_curve: str = "C"
    ka_rating: float = 10.0


@dataclass(frozen=True)
class TraceEntry:
    """Entrada de auditoría inmutable que documenta una decisión del motor."""
    stage: str
    decision_rule: str
    rule_reference: str
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CircuitAlert:
    """Alerta de validación o seguridad generada en el cálculo."""
    severity: str                   # 'error', 'warning', 'info'
    code: str                       # Ej. 'AMPACITY_FAIL', 'VOLTAGE_DROP_HIGH'
    message: str
    rule_reference: str


@dataclass(frozen=True)
class CircuitResult:
    """Resultado inmutable consolidado entregado por el motor de cálculo."""
    circuit_id: Optional[str]
    design_current_a: float
    nominal_current_a: float
    corrected_ampacity_a: float
    selected_conductor: ConductorSpec
    selected_breaker: BreakerSpec
    voltage_drop_percent: float
    is_compliant: bool
    alerts: List[CircuitAlert] = field(default_factory=list)
    trace: List[TraceEntry] = field(default_factory=list)
