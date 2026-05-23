"""
ElectroSmart Platform — Pruebas de Integración Django
===================================================
Archivo: core/tests.py
Descripción: Valida de extremo a extremo la integración del motor de cálculo
             eléctrico puro de Python con los modelos Django y la API REST.
"""

from decimal import Decimal
import json
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from core.models import (
    BreakerCatalog,
    Budget,
    BillOfMaterials,
    CalculationHistory,
    CalculationAlert,
    Circuit,
    CircuitCalculation,
    ConductorCatalog,
    ElectricalPanel,
    InsulationType,
    Load,
    LoadType,
    MaterialUnitMeasure,
    Norm,
    NormVersion,
    PhaseConfig,
    Project,
    ProjectParameter,
    Tenant,
    VoltageLevel,
    WireMaterial,
)

User = get_user_model()


class TestElectricalEngineIntegration(APITestCase):
    """Pruebas de integración de Django para el motor de cálculo y API REST."""

    def setUp(self):
        # 1. Crear Tenant y Usuario Administrador
        self.tenant = Tenant.objects.create(
            name="Test Engineering Tenant",
            subdomain="test-tenant"
        )
        self.user = User.objects.create_superuser(
            username="admin_test",
            email="admin@test.com",
            password="testpassword"
        )
        self.client.force_authenticate(user=self.user)

        # 2. Crear Catálogos Técnicos Básicos
        self.norm = Norm.objects.create(code="NEC", name="National Electrical Code")
        self.norm_version = NormVersion.objects.create(
            norm=self.norm,
            version_name="2020",
            effective_from="2020-01-01",
            is_current=True
        )
        
        self.voltage_level = VoltageLevel.objects.create(
            voltage_numeric=Decimal("120.0"),
            phase_type="single",
            frequency=Decimal("60.0")
        )
        
        self.phase_config = PhaseConfig.objects.create(
            name="1 Fase — 2 hilos (fase + neutro)",
            active_conductors=1,
            has_neutral=True
        )
        
        self.wire_material = WireMaterial.objects.create(
            material_name="Cobre",
            resistivity_ohm_mm2_m=Decimal("0.01724")
        )
        
        self.insulation_type = InsulationType.objects.create(
            code="THHN",
            max_temperature_c=90
        )

        # 3. Registrar calibres en ConductorCatalog
        self.conductor_14 = ConductorCatalog.objects.create(
            norm_version=self.norm_version,
            wire_material=self.wire_material,
            insulation_type=self.insulation_type,
            gauge_awg="14 AWG",
            cross_section_mm2=Decimal("2.08"),
            ampacity_30c=Decimal("20.0")
        )
        self.conductor_12 = ConductorCatalog.objects.create(
            norm_version=self.norm_version,
            wire_material=self.wire_material,
            insulation_type=self.insulation_type,
            gauge_awg="12 AWG",
            cross_section_mm2=Decimal("3.31"),
            ampacity_30c=Decimal("25.0")
        )

        # 4. Registrar breakers comerciales
        self.breaker_15 = BreakerCatalog.objects.create(
            norm_version=self.norm_version,
            poles=1,
            ampacity=Decimal("15.0"),
            trip_curve="C",
            ka_rating=Decimal("10.0")
        )
        self.breaker_20 = BreakerCatalog.objects.create(
            norm_version=self.norm_version,
            poles=1,
            ampacity=Decimal("20.0"),
            trip_curve="C",
            ka_rating=Decimal("10.0")
        )

        # 5. Registrar tipo de carga
        self.load_type = LoadType.objects.create(
            code="LIGHTING",
            name="Iluminación",
            default_power_factor=Decimal("0.90"),
            default_demand_factor=Decimal("1.00")
        )
        
        # 6. Registrar unidades de medida
        self.unit_meter = MaterialUnitMeasure.objects.create(name="metro")
        self.unit_qty = MaterialUnitMeasure.objects.create(name="unidad")

        # 7. Crear un Proyecto de prueba
        self.project = Project.objects.create(
            tenant=self.tenant,
            user=self.user,
            name="Edificio Residencial Alfa",
            norm_version=self.norm_version,
            voltage_level=self.voltage_level,
            phase_config=self.phase_config,
            status="draft"
        )
        
        self.project_params = ProjectParameter.objects.create(
            project=self.project,
            ambient_temp_c=Decimal("30.0"),
            altitude_m=Decimal("0.0"),
            max_voltage_drop_pct=Decimal("3.0"),
            safety_factor=Decimal("1.25")
        )

        # 8. Crear Tablero Eléctrico y Circuito derivado
        self.panel = ElectricalPanel.objects.create(
            project=self.project,
            name="Tablero Principal TD-1",
            location="Sótano Técnico"
        )
        
        self.circuit = Circuit.objects.create(
            panel=self.panel,
            circuit_number=1,
            length_meters=Decimal("15.0"),
            is_three_phase=False,
            phase_assignment="A"
        )

        # 9. Conectar carga al circuito (ej. 1200W, 120V -> 10A nominales)
        self.load = Load.objects.create(
            circuit=self.circuit,
            load_type=self.load_type,
            name="Luces Lobby",
            quantity=1,
            power_watts=Decimal("1200.0"),
            voltage_v=Decimal("120.0"),
            power_factor=Decimal("0.90"),
            is_continuous=True  # 1.25 factor -> 12.5A corriente de diseño
        )

    def test_calculate_project_endpoint(self):
        """Prueba de extremo a extremo que el endpoint de cálculo ejecuta el motor y persiste los resultados."""
        url = reverse("project-calculate", args=[self.project.id])
        
        # Enviar petición POST para calcular el proyecto
        response = self.client.post(url, HTTP_X_TENANT_ID=str(self.tenant.id))
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data
        
        # Validar estructura de respuesta
        self.assertEqual(data["project_name"], "Edificio Residencial Alfa")
        self.assertEqual(data["circuits_calculated"], 1)
        self.assertTrue(data["is_compliant"])
        
        circuit_res = data["circuits"][0]
        self.assertEqual(circuit_res["circuit_number"], 1)
        self.assertEqual(circuit_res["nominal_current_a"], 11.111)  # 1200 / (120 * 0.90) = 11.11 A
        # Corriente de diseño = 11.111 * 1.25 = 13.88 A -> requiere breaker 15A y cable 14 AWG (ampacidad base 20A)
        self.assertEqual(circuit_res["selected_conductor"], "14 AWG")
        self.assertEqual(circuit_res["selected_breaker"], "1P 15.0A")
        
        # 1. Validar que se guardó en CircuitCalculation
        calc = CircuitCalculation.objects.get(circuit=self.circuit)
        self.assertEqual(calc.conductor.gauge_awg, "14 AWG")
        self.assertEqual(calc.breaker.ampacity, Decimal("15.0"))
        self.assertTrue(calc.is_compliant)
        
        # Verificar existencia de la traza de auditoría JSON
        self.assertIn("trace", calc.parameters_snapshot)
        self.assertTrue(len(calc.parameters_snapshot["trace"]) > 0)
        
        # 2. Validar que se creó historial CalculationHistory
        hist = CalculationHistory.objects.filter(circuit=self.circuit).first()
        self.assertIsNotNone(hist)
        self.assertEqual(hist.calculation_version, 1)
        
        # 3. Validar que se actualizó el listado de materiales (BOM)
        # Debe contener cable (metros) y un breaker disyuntor
        bom_items = BillOfMaterials.objects.filter(project=self.project, circuit=self.circuit)
        self.assertEqual(bom_items.count(), 2)
        
        # 4. Validar que se creó y actualizó el presupuesto Budget
        budget = Budget.objects.get(project=self.project, version=1)
        self.assertTrue(budget.subtotal > 0)
