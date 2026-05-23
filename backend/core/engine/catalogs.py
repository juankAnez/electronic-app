"""
ElectroSmart Platform — Motor de Cálculo Eléctrico
=================================================
Módulo: catalogs.py
Descripción: Provee las tablas técnicas maestras y funciones de búsqueda (lookup)
             para ampacidades, factores de corrección y disyuntores comerciales.
"""

from typing import Dict, List, Tuple
from core.engine.domain import ConductorMaterial, InsulationType


# ---------------------------------------------------------------------------
# 1. CATALOGO DE CONDUCTORES (NEC Tabla 310.16 + Tabla 9 para Impedancias)
# ---------------------------------------------------------------------------
# Diccionario indexado por material -> calibre -> datos del calibre
# Datos del calibre:
#   - cross_section_mm2
#   - ampacities: diccionario por temperatura [60, 75, 90]
#   - resistance_ac_ohm_km: resistencia AC a 75°C en ducto de PVC
#   - reactance_ac_ohm_km: reactancia inductiva a 60Hz en ducto de PVC

CONDUCTOR_CATALOG: Dict[ConductorMaterial, Dict[str, Dict[str, any]]] = {
    ConductorMaterial.COPPER: {
        "14 AWG": {
            "cross_section_mm2": 2.08,
            "ampacities": {60: 15.0, 75: 20.0, 90: 25.0},
            "resistance_ac_ohm_km": 10.17,
            "reactance_ac_ohm_km": 0.180
        },
        "12 AWG": {
            "cross_section_mm2": 3.31,
            "ampacities": {60: 20.0, 75: 25.0, 90: 30.0},
            "resistance_ac_ohm_km": 6.56,
            "reactance_ac_ohm_km": 0.177
        },
        "10 AWG": {
            "cross_section_mm2": 5.26,
            "ampacities": {60: 30.0, 75: 35.0, 90: 40.0},
            "resistance_ac_ohm_km": 3.94,
            "reactance_ac_ohm_km": 0.164
        },
        "8 AWG": {
            "cross_section_mm2": 8.37,
            "ampacities": {60: 40.0, 75: 50.0, 90: 55.0},
            "resistance_ac_ohm_km": 2.56,
            "reactance_ac_ohm_km": 0.171
        },
        "6 AWG": {
            "cross_section_mm2": 13.30,
            "ampacities": {60: 55.0, 75: 65.0, 90: 75.0},
            "resistance_ac_ohm_km": 1.61,
            "reactance_ac_ohm_km": 0.167
        },
        "4 AWG": {
            "cross_section_mm2": 21.15,
            "ampacities": {60: 70.0, 75: 85.0, 90: 95.0},
            "resistance_ac_ohm_km": 1.02,
            "reactance_ac_ohm_km": 0.157
        },
        "3 AWG": {
            "cross_section_mm2": 26.67,
            "ampacities": {60: 85.0, 75: 100.0, 90: 115.0},
            "resistance_ac_ohm_km": 0.81,
            "reactance_ac_ohm_km": 0.154
        },
        "2 AWG": {
            "cross_section_mm2": 33.62,
            "ampacities": {60: 95.0, 75: 115.0, 90: 130.0},
            "resistance_ac_ohm_km": 0.64,
            "reactance_ac_ohm_km": 0.148
        },
        "1 AWG": {
            "cross_section_mm2": 42.41,
            "ampacities": {60: 110.0, 75: 130.0, 90: 145.0},
            "resistance_ac_ohm_km": 0.51,
            "reactance_ac_ohm_km": 0.151
        },
        "1/0 AWG": {
            "cross_section_mm2": 53.49,
            "ampacities": {60: 125.0, 75: 150.0, 90: 170.0},
            "resistance_ac_ohm_km": 0.40,
            "reactance_ac_ohm_km": 0.144
        },
        "2/0 AWG": {
            "cross_section_mm2": 67.43,
            "ampacities": {60: 145.0, 75: 175.0, 90: 195.0},
            "resistance_ac_ohm_km": 0.32,
            "reactance_ac_ohm_km": 0.141
        },
        "3/0 AWG": {
            "cross_section_mm2": 85.01,
            "ampacities": {60: 165.0, 75: 200.0, 90: 225.0},
            "resistance_ac_ohm_km": 0.25,
            "reactance_ac_ohm_km": 0.138
        },
        "4/0 AWG": {
            "cross_section_mm2": 107.20,
            "ampacities": {60: 195.0, 75: 230.0, 90: 260.0},
            "resistance_ac_ohm_km": 0.20,
            "reactance_ac_ohm_km": 0.135
        }
    },
    ConductorMaterial.ALUMINUM: {
        "12 AWG": {
            "cross_section_mm2": 3.31,
            "ampacities": {60: 15.0, 75: 20.0, 90: 25.0},
            "resistance_ac_ohm_km": 10.82,
            "reactance_ac_ohm_km": 0.177
        },
        "10 AWG": {
            "cross_section_mm2": 5.26,
            "ampacities": {60: 25.0, 75: 30.0, 90: 35.0},
            "resistance_ac_ohm_km": 6.56,
            "reactance_ac_ohm_km": 0.164
        },
        "8 AWG": {
            "cross_section_mm2": 8.37,
            "ampacities": {60: 35.0, 75: 40.0, 90: 45.0},
            "resistance_ac_ohm_km": 4.26,
            "reactance_ac_ohm_km": 0.171
        },
        "6 AWG": {
            "cross_section_mm2": 13.30,
            "ampacities": {60: 40.0, 75: 50.0, 90: 60.0},
            "resistance_ac_ohm_km": 2.66,
            "reactance_ac_ohm_km": 0.167
        },
        "4 AWG": {
            "cross_section_mm2": 21.15,
            "ampacities": {60: 55.0, 75: 65.0, 90: 75.0},
            "resistance_ac_ohm_km": 1.67,
            "reactance_ac_ohm_km": 0.157
        },
        "3 AWG": {
            "cross_section_mm2": 26.67,
            "ampacities": {60: 65.0, 75: 75.0, 90: 85.0},
            "resistance_ac_ohm_km": 1.33,
            "reactance_ac_ohm_km": 0.154
        },
        "2 AWG": {
            "cross_section_mm2": 33.62,
            "ampacities": {60: 75.0, 75: 90.0, 90: 100.0},
            "resistance_ac_ohm_km": 1.05,
            "reactance_ac_ohm_km": 0.148
        },
        "1 AWG": {
            "cross_section_mm2": 42.41,
            "ampacities": {60: 85.0, 75: 100.0, 90: 115.0},
            "resistance_ac_ohm_km": 0.83,
            "reactance_ac_ohm_km": 0.151
        },
        "1/0 AWG": {
            "cross_section_mm2": 53.49,
            "ampacities": {60: 100.0, 75: 120.0, 90: 135.0},
            "resistance_ac_ohm_km": 0.66,
            "reactance_ac_ohm_km": 0.144
        },
        "2/0 AWG": {
            "cross_section_mm2": 67.43,
            "ampacities": {60: 115.0, 75: 135.0, 90: 150.0},
            "resistance_ac_ohm_km": 0.52,
            "reactance_ac_ohm_km": 0.141
        },
        "3/0 AWG": {
            "cross_section_mm2": 85.01,
            "ampacities": {60: 130.0, 75: 155.0, 90: 175.0},
            "resistance_ac_ohm_km": 0.41,
            "reactance_ac_ohm_km": 0.138
        },
        "4/0 AWG": {
            "cross_section_mm2": 107.20,
            "ampacities": {60: 150.0, 75: 180.0, 90: 205.0},
            "resistance_ac_ohm_km": 0.33,
            "reactance_ac_ohm_km": 0.135
        }
    }
}


# ---------------------------------------------------------------------------
# 2. FACTORES DE CORRECCION POR TEMPERATURA AMBIENTE (NEC 310.15(B)(1))
# ---------------------------------------------------------------------------
# Rangos de temperatura y sus multiplicadores por columna de temperatura [60C, 75C, 90C]
# Formato: (temp_min, temp_max, [f60, f75, f90])

TEMPERATURE_CORRECTION_TABLE: List[Tuple[float, float, List[float]]] = [
    (-99.0, 10.0, [1.29, 1.20, 1.15]),
    (10.1, 15.0, [1.22, 1.15, 1.12]),
    (15.1, 20.0, [1.15, 1.11, 1.08]),
    (20.1, 25.0, [1.08, 1.05, 1.04]),
    (25.1, 30.0, [1.00, 1.00, 1.00]),
    (30.1, 35.0, [0.91, 0.94, 0.96]),
    (35.1, 40.0, [0.82, 0.88, 0.91]),
    (40.1, 45.0, [0.71, 0.82, 0.87]),
    (45.1, 50.0, [0.58, 0.75, 0.82]),
    (50.1, 55.0, [0.41, 0.67, 0.76]),
    (55.1, 60.0, [0.00, 0.58, 0.71]),
    (60.1, 70.0, [0.00, 0.33, 0.58]),
    (70.1, 80.0, [0.00, 0.00, 0.41]),
    (80.1, 999.0, [0.00, 0.00, 0.00])
]


# ---------------------------------------------------------------------------
# 3. FACTORES DE AJUSTE POR AGRUPAMIENTO DE CABLES (NEC Tabla 310.15(C)(1))
# ---------------------------------------------------------------------------
# Rangos de cables cargados y factor aplicable
# Formato: (min_conductors, max_conductors, factor)

GROUPING_CORRECTION_TABLE: List[Tuple[int, int, float]] = [
    (0, 3, 1.00),
    (4, 6, 0.80),
    (7, 9, 0.70),
    (10, 20, 0.50),
    (21, 30, 0.45),
    (31, 40, 0.40),
    (41, 999, 0.35)
]


# ---------------------------------------------------------------------------
# 4. CAPACIDADES DE PROTECCIONES COMERCIALES (BREAKERS)
# ---------------------------------------------------------------------------
STANDARD_BREAKERS: List[float] = [
    15.0, 20.0, 25.0, 30.0, 35.0, 40.0, 45.0, 50.0, 60.0, 70.0, 80.0, 90.0,
    100.0, 110.0, 125.0, 150.0, 175.0, 200.0
]


# ---------------------------------------------------------------------------
# 5. FUNCIONES DE BUSQUEDA EN CATALOGOS
# ---------------------------------------------------------------------------

def get_temperature_factor(temp_c: float, insulation_rating_c: int) -> float:
    """
    Obtiene el factor de corrección por temperatura según el aislamiento del conductor.
    """
    col_idx = {60: 0, 75: 1, 90: 2}.get(insulation_rating_c, 2)
    for t_min, t_max, factors in TEMPERATURE_CORRECTION_TABLE:
        if t_min <= temp_c <= t_max:
            return factors[col_idx]
    return 0.0


def get_grouping_factor(num_conductors: int) -> float:
    """
    Obtiene el factor de reducción por agrupamiento según la cantidad de conductores activos.
    """
    for c_min, c_max, factor in GROUPING_CORRECTION_TABLE:
        if c_min <= num_conductors <= c_max:
            return factor
    return 0.35


def get_insulation_temperature(insulation: InsulationType) -> int:
    """
    Obtiene la temperatura límite de operación del aislamiento base.
    """
    return {
        InsulationType.TW: 60,
        InsulationType.THW: 75,
        InsulationType.THHN: 90,
        InsulationType.THWN_2: 90,
        InsulationType.XHHW: 90
    }.get(insulation, 90)


def get_available_gauges(material: ConductorMaterial) -> List[str]:
    """
    Devuelve todos los calibres AWG disponibles ordenados por sección transversal de menor a mayor.
    """
    gauges = list(CONDUCTOR_CATALOG[material].keys())
    # Ordenar calibres de manera inteligente: 14, 12, 10, 8, 6, 4, 3, 2, 1, 1/0, 2/0, 3/0, 4/0
    def gauge_key(g: str) -> float:
        clean = g.replace(" AWG", "")
        if "/" in clean:
            # Calibres grandes: 1/0, 2/0, etc.
            val = float(clean.split("/")[0])
            return 100.0 + val
        else:
            # Calibres numéricos: 14, 12... de mayor número es menor calibre físico
            return -float(clean)

    return sorted(gauges, key=gauge_key)


def get_breaker_commercial_sizes() -> List[float]:
    """
    Retorna la lista de capacidades comerciales de disyuntores.
    """
    return STANDARD_BREAKERS
