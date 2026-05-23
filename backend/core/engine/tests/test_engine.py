"""
ElectroSmart Platform — Pruebas Unitarias del Motor de Cálculo
============================================================
Archivo: tests/test_engine.py
Descripción: Suite de pruebas unitarias puras en Python para verificar la
             rigurosidad, precisión e inmutabilidad del motor de cálculo.
"""

import unittest

from core.engine.domain import (
    CircuitInput,
    ConductorMaterial,
    InsulationType,
    SystemType,
)
from core.engine.pipeline import ElectricalEngineRunner


class TestElectricalEngine(unittest.TestCase):
    """Pruebas unitarias para validar las reglas del motor eléctrico."""

    def test_current_calculations_single_phase(self):
        """Prueba cálculo de corrientes nominales y de diseño monofásicas."""
        inp = CircuitInput(
            system_type=SystemType.SINGLE_PHASE,
            voltage_ln=120.0,
            voltage_ll=240.0,
            frequency=60.0,
            length_m=10.0,
            power_watts=1800.0,  # 1800W / 120V = 15A nominal
            power_factor=1.00,
            efficiency=1.00,
            continuous_fraction=1.00,  # 100% carga continua -> 1.25 factor
            conductor_material=ConductorMaterial.COPPER,
            insulation_type=InsulationType.THHN,
            terminal_temp_rating_c=75.0,
            grouping_active_conductors=3,
            max_voltage_drop_pct=3.0
        )
        
        result = ElectricalEngineRunner.calculate_circuit(inp)
        self.assertEqual(result.nominal_current_a, 15.0)
        self.assertEqual(result.design_current_a, 18.75)  # 15A * 1.25

    def test_current_calculations_three_phase(self):
        """Prueba cálculo de corrientes trifásicas balanceadas."""
        inp = CircuitInput(
            system_type=SystemType.THREE_PHASE_WYE,
            voltage_ln=120.0,
            voltage_ll=208.0,
            frequency=60.0,
            length_m=15.0,
            power_watts=10000.0,  # 10kW
            power_factor=0.90,
            efficiency=0.95,
            continuous_fraction=0.00,
            conductor_material=ConductorMaterial.COPPER,
            insulation_type=InsulationType.THHN
        )
        
        result = ElectricalEngineRunner.calculate_circuit(inp)
        # I = 10000 / (sqrt(3) * 208 * 0.90 * 0.95)
        # I = 10000 / (1.73205 * 208 * 0.855) = 10000 / 308.04 = 32.46 A
        self.assertAlmostEqual(result.nominal_current_a, 32.461, places=2)

    def test_terminal_limit_nec_110_14(self):
        """Prueba la limitación por temperatura de terminales a 75°C."""
        # Un circuito con 20A de diseño requiere un cable de 12 AWG
        # (Cobre base a 90°C = 30A, pero limitado a 75°C = 25A)
        inp = CircuitInput(
            system_type=SystemType.SINGLE_PHASE,
            voltage_ln=120.0,
            voltage_ll=240.0,
            frequency=60.0,
            length_m=10.0,
            power_watts=2400.0,  # 20A nominal
            power_factor=1.00,
            efficiency=1.00,
            continuous_fraction=0.00,
            conductor_material=ConductorMaterial.COPPER,
            insulation_type=InsulationType.THHN,
            terminal_temp_rating_c=75.0
        )
        
        result = ElectricalEngineRunner.calculate_circuit(inp)
        self.assertTrue(result.is_compliant)
        self.assertEqual(result.selected_conductor.gauge_awg, "12 AWG")
        self.assertEqual(result.selected_breaker.ampacity_a, 20.0)

    def test_iterative_resize_by_voltage_drop(self):
        """Prueba el redimensionamiento iterativo automático cuando la caída de tensión supera el límite."""
        # Un circuito largo (60 metros) con una carga de 16A nominal.
        # Si se usara calibre estándar por ampacidad, se elegiría 12 AWG (ampacidad 25A).
        # Pero a 60 metros, un cable de 12 AWG tendría una caída de tensión excesiva (> 3%).
        # El motor debe seleccionar un calibre mayor (ej. 10 AWG o 8 AWG) de forma iterativa.
        inp = CircuitInput(
            system_type=SystemType.SINGLE_PHASE,
            voltage_ln=120.0,
            voltage_ll=240.0,
            frequency=60.0,
            length_m=60.0,  # 60 metros (distancia larga)
            power_watts=1920.0,  # 16 A
            power_factor=1.00,
            efficiency=1.00,
            continuous_fraction=0.00,
            conductor_material=ConductorMaterial.COPPER,
            insulation_type=InsulationType.THHN,
            terminal_temp_rating_c=75.0,
            max_voltage_drop_pct=3.0  # Límite estricto 3%
        )
        
        result = ElectricalEngineRunner.calculate_circuit(inp)
        self.assertTrue(result.is_compliant)
        # Debe haber aumentado el calibre del cable a por lo menos 10 AWG o superior para mantener la caída < 3%
        self.assertIn(result.selected_conductor.gauge_awg, ["10 AWG", "8 AWG", "6 AWG"])
        self.assertLessEqual(result.voltage_drop_percent, 3.0)

    def test_next_size_up_rule(self):
        """Prueba que se aplique la regla next-size-up del breaker cuando corresponda."""
        # Supongamos una corriente de diseño de 23A.
        # Un cable 12 AWG tiene ampacidad corregida (y limitada por terminales de 75°C) de 25A.
        # No hay breaker comercial de 25A para este circuito en algunos mercados (o supongamos que el diseño exige 30A).
        # Si permitimos next-size-up, y la ampacidad es 25A, un breaker de 30A se puede autorizar bajo NEC 240.4(B)
        # si allow_next_size_up es True.
        inp = CircuitInput(
            system_type=SystemType.SINGLE_PHASE,
            voltage_ln=120.0,
            voltage_ll=240.0,
            frequency=60.0,
            length_m=10.0,
            power_watts=2640.0,  # 22A nominal
            power_factor=1.00,
            efficiency=1.00,
            continuous_fraction=0.00,
            conductor_material=ConductorMaterial.COPPER,
            insulation_type=InsulationType.THHN,
            terminal_temp_rating_c=75.0,
            allow_next_size_up=True
        )
        
        result = ElectricalEngineRunner.calculate_circuit(inp)
        self.assertTrue(result.is_compliant)
        # Breaker comercial para 22A es 25A. La ampacidad del cable 12 AWG es 25A.
        # Breaker 25A <= Ampacidad 25A. Esto cumple sin necesidad de Next-Size-Up.
        self.assertEqual(result.selected_breaker.ampacity_a, 25.0)

    def test_trace_auditing(self):
        """Prueba que el resultado contenga entradas detalladas de auditoría para la IA."""
        inp = CircuitInput(
            system_type=SystemType.SINGLE_PHASE,
            voltage_ln=120.0,
            voltage_ll=240.0,
            frequency=60.0,
            length_m=15.0,
            power_watts=1200.0,
            power_factor=0.90,
            continuous_fraction=0.50,
            conductor_material=ConductorMaterial.COPPER,
            insulation_type=InsulationType.THHN
        )
        
        result = ElectricalEngineRunner.calculate_circuit(inp)
        self.assertTrue(len(result.trace) > 0)
        # Verificar que la traza contenga referencias normativas claras
        stages_traced = [entry.stage for entry in result.trace]
        self.assertIn("Normalization", stages_traced)
        self.assertIn("CurrentCalculation", stages_traced)
        self.assertIn("ConductorSelection", stages_traced)

    def test_invalid_inputs_power(self):
        """Prueba cómo reacciona el motor ante una potencia inválida (cero o negativa)."""
        inp = CircuitInput(
            system_type=SystemType.SINGLE_PHASE,
            voltage_ln=120.0,
            voltage_ll=240.0,
            frequency=60.0,
            length_m=10.0,
            power_watts=0.0,  # Potencia inválida!
            power_factor=1.00,
            efficiency=1.00
        )
        result = ElectricalEngineRunner.calculate_circuit(inp)
        self.assertFalse(result.is_compliant)
        alerts_codes = [a.code for a in result.alerts]
        self.assertIn("INVALID_POWER", alerts_codes)

    def test_invalid_inputs_voltage(self):
        """Prueba cómo reacciona el motor ante un voltaje inválido (cero o negativo)."""
        inp = CircuitInput(
            system_type=SystemType.SINGLE_PHASE,
            voltage_ln=0.0,  # Voltaje inválido!
            voltage_ll=0.0,  # Voltaje inválido!
            frequency=60.0,
            length_m=10.0,
            power_watts=1200.0,
            power_factor=1.00,
            efficiency=1.00
        )
        result = ElectricalEngineRunner.calculate_circuit(inp)
        self.assertFalse(result.is_compliant)
        alerts_codes = [a.code for a in result.alerts]
        self.assertIn("INVALID_VOLTAGE", alerts_codes)

    def test_extreme_temperature_failure(self):
        """Prueba cómo reacciona el motor ante temperaturas extremadamente altas (ej. 85°C) que reducen la ampacidad del cable a cero."""
        inp = CircuitInput(
            system_type=SystemType.SINGLE_PHASE,
            voltage_ln=120.0,
            voltage_ll=240.0,
            frequency=60.0,
            length_m=10.0,
            power_watts=1200.0,
            power_factor=1.00,
            efficiency=1.00,
            ambient_temperature_c=85.0,  # Temperatura extrema!
            conductor_material=ConductorMaterial.COPPER,
            insulation_type=InsulationType.THHN
        )
        result = ElectricalEngineRunner.calculate_circuit(inp)
        self.assertFalse(result.is_compliant)
        alerts_codes = [a.code for a in result.alerts]
        self.assertIn("CONDUCTOR_NOT_FOUND", alerts_codes)

    def test_extreme_load_ampacity_failure(self):
        """Prueba cómo reacciona el motor ante una carga de potencia gigante que excede la capacidad de conductores o breakers estándar."""
        inp = CircuitInput(
            system_type=SystemType.SINGLE_PHASE,
            voltage_ln=120.0,
            voltage_ll=240.0,
            frequency=60.0,
            length_m=10.0,
            power_watts=60000.0,  # 60 kW a 120V = 500 A! Supera el catálogo (max 260A de cable 4/0 y max 200A de breaker)
            power_factor=1.00,
            efficiency=1.00,
            conductor_material=ConductorMaterial.COPPER,
            insulation_type=InsulationType.THHN
        )
        result = ElectricalEngineRunner.calculate_circuit(inp)
        self.assertFalse(result.is_compliant)
        alerts_codes = [a.code for a in result.alerts]
        self.assertTrue("CONDUCTOR_NOT_FOUND" in alerts_codes or "BREAKER_NOT_FOUND" in alerts_codes or "OVERCURRENT_PROTECTION_FAIL" in alerts_codes)

    def test_voltage_drop_limit_warning(self):
        """Prueba que un circuito extremadamente largo (ej. 800m) conserve el calibre máximo pero arroje una alerta de advertencia en lugar de caerse por completo."""
        inp = CircuitInput(
            system_type=SystemType.SINGLE_PHASE,
            voltage_ln=120.0,
            voltage_ll=240.0,
            frequency=60.0,
            length_m=800.0,  # Distancia ridículamente larga!
            power_watts=4800.0,  # 40 A nominales
            power_factor=1.00,
            efficiency=1.00,
            conductor_material=ConductorMaterial.COPPER,
            insulation_type=InsulationType.THHN,
            max_voltage_drop_pct=3.0
        )
        result = ElectricalEngineRunner.calculate_circuit(inp)
        # El motor debería haber subido al calibre máximo de cobre (4/0 AWG)
        self.assertEqual(result.selected_conductor.gauge_awg, "4/0 AWG")
        # Pero dado que la distancia es insalvable, debe haber una alerta warning de caída de tensión excedida
        self.assertTrue(len(result.alerts) > 0)
        alerts_codes = [a.code for a in result.alerts]
        self.assertIn("VOLTAGE_DROP_EXCEEDED", alerts_codes)


if __name__ == "__main__":
    unittest.main()
