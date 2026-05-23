"""
ElectroSmart Platform — Motor de Cálculo Eléctrico
=================================================
Módulo: calculators.py
Descripción: Contiene funciones matemáticas puras para calcular corrientes,
             caídas de tensión y factores combinados del sistema eléctrico.
"""

import math
from core.engine.domain import SystemType


def calculate_nominal_current(
    power_w: float,
    voltage_ln: float,
    voltage_ll: float,
    system_type: SystemType,
    power_factor: float,
    efficiency: float = 1.0
) -> float:
    """
    Calcula la corriente nominal (I_base) en amperios del sistema.
    Lanza ZeroDivisionError si el voltaje, factor de potencia o eficiencia es cero.
    """
    if power_factor <= 0 or efficiency <= 0:
        raise ValueError("El factor de potencia y la eficiencia deben ser mayores que cero.")
    
    denominator_coeff = power_factor * efficiency

    if system_type == SystemType.SINGLE_PHASE:
        if voltage_ln <= 0:
            raise ValueError("El voltaje Fase-Neutro debe ser mayor que cero para sistemas monofásicos.")
        return power_w / (voltage_ln * denominator_coeff)
        
    elif system_type == SystemType.SPLIT_PHASE:
        if voltage_ll <= 0:
            raise ValueError("El voltaje Fase-Fase debe ser mayor que cero para sistemas bifásicos.")
        return power_w / (voltage_ll * denominator_coeff)
        
    elif system_type in (SystemType.THREE_PHASE_WYE, SystemType.THREE_PHASE_DELTA):
        if voltage_ll <= 0:
            raise ValueError("El voltaje Fase-Fase debe ser mayor que cero para sistemas trifásicos.")
        sqrt_3 = math.sqrt(3.0)
        return power_w / (sqrt_3 * voltage_ll * denominator_coeff)
        
    else:
        raise ValueError(f"Tipo de sistema desconocido: {system_type}")


def calculate_design_current(nominal_current: float, continuous_fraction: float) -> float:
    """
    Calcula la corriente de diseño aplicando el factor del 125% únicamente
    a la fracción de la carga continua, según NEC 210.19(A)(1).
    
    I_diseño = I_no_continua + 1.25 * I_continua
             = I_nominal * (1 - fraction) + 1.25 * I_nominal * fraction
             = I_nominal * (1 + 0.25 * fraction)
    """
    if not (0.0 <= continuous_fraction <= 1.0):
        raise ValueError("La fracción continua debe estar entre 0.0 y 1.0.")
    return nominal_current * (1.0 + 0.25 * continuous_fraction)


def calculate_voltage_drop(
    nominal_current: float,
    length_m: float,
    resistance_ac_ohm_km: float,
    reactance_ac_ohm_km: float,
    power_factor: float,
    system_type: SystemType
) -> float:
    """
    Calcula la caída de tensión absoluta (V) utilizando el método exacto
    de impedancia considerando la resistencia y reactancia inductiva del conductor:
    
    Z = R * cos(theta) + X * sin(theta)
    Donde:
      - theta es el ángulo de fase (cos(theta) = factor de potencia)
      - R y X están en Ohm/km, la longitud en metros se divide por 1000 para pasar a km.
    
    Línea de cálculo:
      Monofásico/Bifásico: dV = 2 * L * I * Z / 1000
      Trifásico:           dV = sqrt(3) * L * I * Z / 1000
    """
    cos_theta = power_factor
    sin_theta = math.sqrt(max(0.0, 1.0 - cos_theta ** 2))
    
    # Impedancia unitaria en Ohm/km
    impedance_ohm_km = (resistance_ac_ohm_km * cos_theta) + (reactance_ac_ohm_km * sin_theta)
    
    # Convertir longitud a kilómetros
    length_km = length_m / 1000.0
    
    if system_type in (SystemType.SINGLE_PHASE, SystemType.SPLIT_PHASE):
        # Retorno por el conductor neutro o segunda fase activo (factor 2)
        return 2.0 * length_km * nominal_current * impedance_ohm_km
    elif system_type in (SystemType.THREE_PHASE_WYE, SystemType.THREE_PHASE_DELTA):
        # Factor raíz de 3 para sistemas trifásicos balanceados
        sqrt_3 = math.sqrt(3.0)
        return sqrt_3 * length_km * nominal_current * impedance_ohm_km
    else:
        raise ValueError(f"Tipo de sistema desconocido para caída de tensión: {system_type}")


def calculate_voltage_drop_percent(
    voltage_drop_v: float,
    voltage_ln: float,
    voltage_ll: float,
    system_type: SystemType
) -> float:
    """
    Convierte la caída de tensión absoluta a porcentaje.
    Para sistemas monofásicos (fase-neutro) se divide respecto a voltage_ln.
    Para bifásicos/trifásicos se divide respecto a voltage_ll.
    """
    if system_type == SystemType.SINGLE_PHASE:
        if voltage_ln <= 0:
            raise ValueError("Voltaje Fase-Neutro inválido.")
        return (voltage_drop_v / voltage_ln) * 100.0
    else:
        if voltage_ll <= 0:
            raise ValueError("Voltaje Fase-Fase inválido.")
        return (voltage_drop_v / voltage_ll) * 100.0
