"""
ElectroSmart — Seed de Catálogos Iniciales
==========================================
Comando de management para poblar la base de datos con los datos de
referencia técnica requeridos para operar el sistema:

  - Normas: NEC (National Electrical Code) y RETIE (Colombia)
  - Versiones de norma activas
  - Niveles de tensión y configuraciones de fase
  - Materiales conductores (Cobre, Aluminio)
  - Tipos de aislamiento (THHN, THWN-2, XHHW)
  - Catálogo de conductores AWG calibres 14 al 2/0
  - Catálogo de breakers 1P y 2P (15A a 200A)
  - Tipos de carga eléctrica comunes
  - Unidades de medida

Uso:
    python manage.py seed_catalogs
    python manage.py seed_catalogs --clear  (limpia y recrea)
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from core.models import (
    BreakerCatalog,
    ConductorCatalog,
    InsulationType,
    LoadType,
    MaterialUnitMeasure,
    Norm,
    NormVersion,
    PhaseConfig,
    VoltageLevel,
    WireMaterial,
)


# ---------------------------------------------------------------------------
# Datos de referencia
# ---------------------------------------------------------------------------

NORMS = [
    {'code': 'NEC', 'name': 'National Electrical Code (NFPA 70)'},
    {'code': 'RETIE', 'name': 'Reglamento Técnico de Instalaciones Eléctricas — Colombia'},
    {'code': 'IEC', 'name': 'International Electrotechnical Commission'},
]

NORM_VERSIONS = [
    {'norm_code': 'NEC', 'version_name': '2020', 'effective_from': '2020-01-01', 'is_current': True},
    {'norm_code': 'NEC', 'version_name': '2023', 'effective_from': '2023-01-01', 'is_current': False},
    {'norm_code': 'RETIE', 'version_name': '2013', 'effective_from': '2013-04-22', 'is_current': True},
]

VOLTAGE_LEVELS = [
    {'voltage_numeric': 120.0, 'phase_type': 'single', 'frequency': 60.0},
    {'voltage_numeric': 208.0, 'phase_type': 'three', 'frequency': 60.0},
    {'voltage_numeric': 220.0, 'phase_type': 'single', 'frequency': 60.0},
    {'voltage_numeric': 240.0, 'phase_type': 'split', 'frequency': 60.0},
    {'voltage_numeric': 380.0, 'phase_type': 'three', 'frequency': 60.0},
    {'voltage_numeric': 440.0, 'phase_type': 'three', 'frequency': 60.0},
]

PHASE_CONFIGS = [
    {'name': '1 Fase — 2 hilos (fase + neutro)', 'active_conductors': 1, 'has_neutral': True},
    {'name': '2 Fases — 3 hilos (bifásica)', 'active_conductors': 2, 'has_neutral': True},
    {'name': '3 Fases — 3 hilos (delta)', 'active_conductors': 3, 'has_neutral': False},
    {'name': '3 Fases — 4 hilos (estrella con neutro)', 'active_conductors': 3, 'has_neutral': True},
]

WIRE_MATERIALS = [
    {'material_name': 'Cobre', 'resistivity_ohm_mm2_m': 0.01724},
    {'material_name': 'Aluminio', 'resistivity_ohm_mm2_m': 0.02830},
]

INSULATION_TYPES = [
    {'code': 'THHN', 'max_temperature_c': 90},
    {'code': 'THWN-2', 'max_temperature_c': 90},
    {'code': 'XHHW', 'max_temperature_c': 90},
    {'code': 'TW', 'max_temperature_c': 60},
    {'code': 'THW', 'max_temperature_c': 75},
]

# Catálogo NEC 2020 — Cobre THHN, Ampacidad base a 30°C (Tabla 310.16)
# (gauge_awg, cross_section_mm2, ampacity_30c)
CONDUCTOR_ENTRIES_NEC2020_CU_THHN = [
    ('14 AWG', 2.08, 20.0),
    ('12 AWG', 3.31, 25.0),
    ('10 AWG', 5.26, 35.0),
    ('8 AWG', 8.37, 50.0),
    ('6 AWG', 13.30, 65.0),
    ('4 AWG', 21.15, 85.0),
    ('3 AWG', 26.67, 100.0),
    ('2 AWG', 33.62, 115.0),
    ('1 AWG', 42.41, 130.0),
    ('1/0 AWG', 53.49, 150.0),
    ('2/0 AWG', 67.43, 175.0),
    ('3/0 AWG', 85.01, 200.0),
    ('4/0 AWG', 107.20, 230.0),
]

# Breakers NEC 2020 — 1 polo, curva C
BREAKERS_1P = [15, 20, 30, 40, 50, 60, 70, 80, 90, 100, 125, 150, 200]
# Breakers NEC 2020 — 2 polos, curva C
BREAKERS_2P = [15, 20, 30, 40, 50, 60, 70, 80, 90, 100, 125, 150, 200]
# Breakers NEC 2020 — 3 polos, curva C
BREAKERS_3P = [15, 20, 30, 40, 50, 60, 70, 80, 90, 100, 125, 150, 200]

LOAD_TYPES = [
    {'code': 'LIGHTING', 'name': 'Iluminación General', 'category': 'Iluminación', 'default_power_factor': 0.90, 'default_demand_factor': 1.00},
    {'code': 'RECEPTACLE', 'name': 'Tomacorrientes de Uso General', 'category': 'Tomacorrientes', 'default_power_factor': 0.95, 'default_demand_factor': 0.80},
    {'code': 'APPLIANCE', 'name': 'Electrodoméstico General', 'category': 'Electrodomésticos', 'default_power_factor': 0.90, 'default_demand_factor': 1.00},
    {'code': 'MOTOR', 'name': 'Motor Eléctrico', 'category': 'Motores', 'default_power_factor': 0.85, 'default_demand_factor': 1.00},
    {'code': 'AC', 'name': 'Aire Acondicionado', 'category': 'HVAC', 'default_power_factor': 0.85, 'default_demand_factor': 1.00},
    {'code': 'HEATING', 'name': 'Calefacción Eléctrica', 'category': 'Calefacción', 'default_power_factor': 1.00, 'default_demand_factor': 1.00},
    {'code': 'WATER_HEATER', 'name': 'Calentador de Agua', 'category': 'Electrodomésticos', 'default_power_factor': 1.00, 'default_demand_factor': 1.00},
    {'code': 'DRYER', 'name': 'Secadora de Ropa', 'category': 'Electrodomésticos', 'default_power_factor': 0.90, 'default_demand_factor': 1.00},
    {'code': 'WASHER', 'name': 'Lavadora', 'category': 'Electrodomésticos', 'default_power_factor': 0.85, 'default_demand_factor': 1.00},
    {'code': 'REFRIGERATOR', 'name': 'Nevera / Refrigerador', 'category': 'Electrodomésticos', 'default_power_factor': 0.90, 'default_demand_factor': 1.00},
    {'code': 'PUMP', 'name': 'Bomba de Agua', 'category': 'Motores', 'default_power_factor': 0.85, 'default_demand_factor': 1.00},
    {'code': 'EV_CHARGER', 'name': 'Cargador de Vehículo Eléctrico', 'category': 'Especial', 'default_power_factor': 0.95, 'default_demand_factor': 1.00},
]

UNIT_MEASURES = ['metro', 'unidad', 'caja', 'rollo', 'par']


# ---------------------------------------------------------------------------
# Comando
# ---------------------------------------------------------------------------

class Command(BaseCommand):
    help = 'Pobla la base de datos con catálogos técnicos iniciales de ElectroSmart.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Elimina los catálogos existentes antes de insertar los nuevos.',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write(self.style.WARNING('Limpiando catálogos existentes...'))
            BreakerCatalog.objects.all().delete()
            ConductorCatalog.objects.all().delete()
            InsulationType.objects.all().delete()
            WireMaterial.objects.all().delete()
            LoadType.objects.all().delete()
            MaterialUnitMeasure.objects.all().delete()
            PhaseConfig.objects.all().delete()
            VoltageLevel.objects.all().delete()
            NormVersion.objects.all().delete()
            Norm.objects.all().delete()

        self.stdout.write('Insertando normas...')
        norms = {}
        for data in NORMS:
            obj, _ = Norm.objects.get_or_create(code=data['code'], defaults={'name': data['name']})
            norms[data['code']] = obj

        self.stdout.write('Insertando versiones de norma...')
        norm_versions = {}
        for data in NORM_VERSIONS:
            norm = norms[data['norm_code']]
            obj, _ = NormVersion.objects.get_or_create(
                norm=norm,
                version_name=data['version_name'],
                defaults={
                    'effective_from': data['effective_from'],
                    'is_current': data['is_current'],
                }
            )
            norm_versions[f"{data['norm_code']}_{data['version_name']}"] = obj

        self.stdout.write('Insertando niveles de tensión...')
        for data in VOLTAGE_LEVELS:
            VoltageLevel.objects.get_or_create(
                voltage_numeric=data['voltage_numeric'],
                phase_type=data['phase_type'],
                defaults={'frequency': data['frequency']}
            )

        self.stdout.write('Insertando configuraciones de fase...')
        for data in PHASE_CONFIGS:
            PhaseConfig.objects.get_or_create(name=data['name'], defaults={
                'active_conductors': data['active_conductors'],
                'has_neutral': data['has_neutral'],
            })

        self.stdout.write('Insertando materiales conductores...')
        materials = {}
        for data in WIRE_MATERIALS:
            obj, _ = WireMaterial.objects.get_or_create(
                material_name=data['material_name'],
                defaults={'resistivity_ohm_mm2_m': data['resistivity_ohm_mm2_m']}
            )
            materials[data['material_name']] = obj

        self.stdout.write('Insertando tipos de aislamiento...')
        insulations = {}
        for data in INSULATION_TYPES:
            obj, _ = InsulationType.objects.get_or_create(
                code=data['code'],
                defaults={'max_temperature_c': data['max_temperature_c']}
            )
            insulations[data['code']] = obj

        self.stdout.write('Insertando catálogo de conductores NEC 2020...')
        nec2020 = norm_versions.get('NEC_2020')
        copper = materials.get('Cobre')
        thhn = insulations.get('THHN')
        if nec2020 and copper and thhn:
            for gauge, section, ampacity in CONDUCTOR_ENTRIES_NEC2020_CU_THHN:
                ConductorCatalog.objects.get_or_create(
                    norm_version=nec2020,
                    wire_material=copper,
                    insulation_type=thhn,
                    gauge_awg=gauge,
                    defaults={
                        'cross_section_mm2': section,
                        'ampacity_30c': ampacity,
                    }
                )

        self.stdout.write('Insertando catálogo de breakers NEC 2020...')
        if nec2020:
            for amps in BREAKERS_1P:
                BreakerCatalog.objects.get_or_create(
                    norm_version=nec2020, poles=1, ampacity=amps, trip_curve='C',
                    defaults={'ka_rating': 10.0}
                )
            for amps in BREAKERS_2P:
                BreakerCatalog.objects.get_or_create(
                    norm_version=nec2020, poles=2, ampacity=amps, trip_curve='C',
                    defaults={'ka_rating': 10.0}
                )
            for amps in BREAKERS_3P:
                BreakerCatalog.objects.get_or_create(
                    norm_version=nec2020, poles=3, ampacity=amps, trip_curve='C',
                    defaults={'ka_rating': 10.0}
                )

        self.stdout.write('Insertando tipos de carga...')
        for data in LOAD_TYPES:
            LoadType.objects.get_or_create(code=data['code'], defaults={
                'name': data['name'],
                'category': data['category'],
                'default_power_factor': data['default_power_factor'],
                'default_demand_factor': data['default_demand_factor'],
            })

        self.stdout.write('Insertando unidades de medida...')
        for name in UNIT_MEASURES:
            MaterialUnitMeasure.objects.get_or_create(name=name)

        self.stdout.write(self.style.SUCCESS('Catálogos iniciales cargados exitosamente.'))
