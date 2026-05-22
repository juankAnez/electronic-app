"""
ElectroSmart — Core Serializers
=================================
Serializers de Django REST Framework para la capa API.

Organización:
    - Catálogos (solo lectura): normas, conductores, breakers, tipos de carga.
    - Proyectos y estructura eléctrica: CRUD completo con validaciones de negocio.
    - Cálculos: escritura controlada únicamente mediante el motor de cálculo.
    - Presupuestos y documentos: CRUD con reglas de congelamiento de precios.
"""

from rest_framework import serializers

from .models import (
    BillOfMaterials,
    BreakerCatalog,
    Budget,
    BudgetItem,
    CalculationAlert,
    CalculationHistory,
    Circuit,
    CircuitCalculation,
    ConductorCatalog,
    Document,
    ElectricalPanel,
    InsulationType,
    Load,
    LoadType,
    MaterialCatalog,
    Norm,
    NormVersion,
    PhaseConfig,
    Project,
    ProjectParameter,
    Role,
    Tenant,
    User,
    UserTenantRole,
    VoltageLevel,
    WireMaterial,
    Zone,
)


# ---------------------------------------------------------------------------
# MÓDULO 1 — IDENTIDAD Y TENANTS
# ---------------------------------------------------------------------------

class TenantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tenant
        fields = ['id', 'name', 'subdomain', 'is_active', 'created_at']
        read_only_fields = ['id', 'created_at']


class UserPublicSerializer(serializers.ModelSerializer):
    """Serializer ligero para mostrar datos básicos del usuario en relaciones."""

    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'email', 'full_name']
        read_only_fields = ['id']

    def get_full_name(self, obj):
        return obj.get_full_name() or obj.email


class UserTenantRoleSerializer(serializers.ModelSerializer):
    user = UserPublicSerializer(read_only=True)
    role_name = serializers.CharField(source='role.name', read_only=True)

    class Meta:
        model = UserTenantRole
        fields = ['user', 'tenant', 'role', 'role_name', 'granted_at']
        read_only_fields = ['granted_at']


# ---------------------------------------------------------------------------
# MÓDULO 2 — CATÁLOGOS TÉCNICOS (solo lectura desde la API)
# ---------------------------------------------------------------------------

class NormSerializer(serializers.ModelSerializer):
    class Meta:
        model = Norm
        fields = ['id', 'code', 'name']


class NormVersionSerializer(serializers.ModelSerializer):
    norm_code = serializers.CharField(source='norm.code', read_only=True)
    norm_name = serializers.CharField(source='norm.name', read_only=True)

    class Meta:
        model = NormVersion
        fields = ['id', 'norm', 'norm_code', 'norm_name', 'version_name', 'effective_from', 'effective_to', 'is_current']


class VoltageLevelSerializer(serializers.ModelSerializer):
    phase_type_display = serializers.CharField(source='get_phase_type_display', read_only=True)

    class Meta:
        model = VoltageLevel
        fields = ['id', 'voltage_numeric', 'phase_type', 'phase_type_display', 'frequency']


class PhaseConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = PhaseConfig
        fields = ['id', 'name', 'active_conductors', 'has_neutral']


class WireMaterialSerializer(serializers.ModelSerializer):
    class Meta:
        model = WireMaterial
        fields = ['id', 'material_name', 'resistivity_ohm_mm2_m']


class InsulationTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = InsulationType
        fields = ['id', 'code', 'max_temperature_c']


class ConductorCatalogSerializer(serializers.ModelSerializer):
    norm_version_label = serializers.CharField(source='norm_version.__str__', read_only=True)
    material = serializers.CharField(source='wire_material.material_name', read_only=True)
    insulation = serializers.CharField(source='insulation_type.code', read_only=True)

    class Meta:
        model = ConductorCatalog
        fields = [
            'id', 'norm_version', 'norm_version_label',
            'material', 'insulation',
            'gauge_awg', 'cross_section_mm2', 'ampacity_30c',
        ]


class BreakerCatalogSerializer(serializers.ModelSerializer):
    norm_version_label = serializers.CharField(source='norm_version.__str__', read_only=True)
    trip_curve_display = serializers.CharField(source='get_trip_curve_display', read_only=True)

    class Meta:
        model = BreakerCatalog
        fields = [
            'id', 'norm_version', 'norm_version_label',
            'poles', 'ampacity', 'trip_curve', 'trip_curve_display', 'ka_rating',
        ]


class LoadTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = LoadType
        fields = [
            'id', 'code', 'name', 'category',
            'default_power_factor', 'default_demand_factor',
        ]


class MaterialCatalogSerializer(serializers.ModelSerializer):
    unit_measure_name = serializers.CharField(source='unit_measure.name', read_only=True)

    class Meta:
        model = MaterialCatalog
        fields = ['id', 'sku', 'name', 'unit_measure', 'unit_measure_name', 'unit_price']


# ---------------------------------------------------------------------------
# MÓDULO 3 — ESTRUCTURA ELÉCTRICA DEL PROYECTO
# ---------------------------------------------------------------------------

class LoadSerializer(serializers.ModelSerializer):
    load_type_name = serializers.CharField(source='load_type.name', read_only=True)

    class Meta:
        model = Load
        fields = [
            'id', 'circuit',
            'load_type', 'load_type_name',
            'name', 'quantity',
            'power_watts', 'voltage_v', 'power_factor',
            'is_continuous',
        ]
        read_only_fields = ['id']

    def validate_power_watts(self, value):
        if value <= 0:
            raise serializers.ValidationError('La potencia debe ser mayor a cero.')
        return value

    def validate_quantity(self, value):
        if value < 1:
            raise serializers.ValidationError('La cantidad mínima es 1.')
        return value


class LoadSummarySerializer(serializers.ModelSerializer):
    """Serializer compacto para listados anidados dentro del circuito."""

    load_type_name = serializers.CharField(source='load_type.name', read_only=True)

    class Meta:
        model = Load
        fields = ['id', 'name', 'load_type_name', 'quantity', 'power_watts', 'voltage_v', 'power_factor', 'is_continuous']


class CircuitCalculationSummarySerializer(serializers.ModelSerializer):
    """Resultado activo del cálculo para mostrar junto al circuito."""

    conductor_label = serializers.SerializerMethodField()
    breaker_label = serializers.SerializerMethodField()
    compliance_badge = serializers.SerializerMethodField()

    class Meta:
        model = CircuitCalculation
        fields = [
            'calculation_version',
            'total_load_amps', 'demand_load_amps',
            'conductor_label', 'breaker_label',
            'voltage_drop_percent',
            'is_compliant', 'compliance_badge',
            'calculation_date',
        ]

    def get_conductor_label(self, obj):
        if obj.conductor:
            return f'{obj.conductor.gauge_awg} {obj.conductor.wire_material.material_name} {obj.conductor.insulation_type.code}'
        return None

    def get_breaker_label(self, obj):
        if obj.breaker:
            return f'{obj.breaker.poles}P {obj.breaker.ampacity}A {obj.breaker.trip_curve}'
        return None

    def get_compliance_badge(self, obj):
        if obj.is_compliant is None:
            return 'pending'
        return 'ok' if obj.is_compliant else 'error'


class CircuitSerializer(serializers.ModelSerializer):
    loads = LoadSummarySerializer(many=True, read_only=True)
    calculation = CircuitCalculationSummarySerializer(read_only=True)
    phase_assignment_display = serializers.CharField(source='get_phase_assignment_display', read_only=True)

    class Meta:
        model = Circuit
        fields = [
            'id', 'panel', 'circuit_number',
            'length_meters', 'is_three_phase',
            'phase_assignment', 'phase_assignment_display',
            'loads', 'calculation',
        ]
        read_only_fields = ['id']

    def validate_circuit_number(self, value):
        if value < 1:
            raise serializers.ValidationError('El número de circuito debe ser positivo.')
        return value

    def validate_length_meters(self, value):
        if value <= 0:
            raise serializers.ValidationError('La longitud del tramo debe ser mayor a cero.')
        return value


class CircuitWriteSerializer(serializers.ModelSerializer):
    """Serializer de escritura para circuitos sin cargas anidadas."""

    class Meta:
        model = Circuit
        fields = [
            'id', 'panel', 'circuit_number',
            'length_meters', 'is_three_phase', 'phase_assignment',
        ]
        read_only_fields = ['id']


class ElectricalPanelSerializer(serializers.ModelSerializer):
    circuits = CircuitSerializer(many=True, read_only=True)
    zone_name = serializers.CharField(source='zone.name', read_only=True, default=None)

    class Meta:
        model = ElectricalPanel
        fields = [
            'id', 'project', 'zone', 'zone_name',
            'parent_panel', 'name', 'location',
            'main_breaker_ampacity', 'is_subpanel',
            'circuits',
        ]
        read_only_fields = ['id']


class ElectricalPanelWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = ElectricalPanel
        fields = [
            'id', 'project', 'zone', 'parent_panel',
            'name', 'location', 'main_breaker_ampacity', 'is_subpanel',
        ]
        read_only_fields = ['id']


class ZoneSerializer(serializers.ModelSerializer):
    panels = ElectricalPanelWriteSerializer(many=True, read_only=True)

    class Meta:
        model = Zone
        fields = ['id', 'project', 'name', 'sort_order', 'panels']
        read_only_fields = ['id']


class ProjectParameterSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectParameter
        fields = [
            'id', 'project',
            'ambient_temp_c', 'altitude_m',
            'max_voltage_drop_pct', 'safety_factor',
        ]
        read_only_fields = ['id', 'project']


class ProjectListSerializer(serializers.ModelSerializer):
    """Serializer compacto para listados de proyectos."""

    norm_version_label = serializers.CharField(source='norm_version.__str__', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    created_by = serializers.CharField(source='user.email', read_only=True)

    class Meta:
        model = Project
        fields = [
            'id', 'name', 'status', 'status_display',
            'norm_version_label', 'created_by', 'created_at',
        ]


class ProjectDetailSerializer(serializers.ModelSerializer):
    """Serializer completo para el detalle de un proyecto."""

    norm_version_label = serializers.CharField(source='norm_version.__str__', read_only=True)
    voltage_level_label = serializers.CharField(source='voltage_level.__str__', read_only=True)
    phase_config_label = serializers.CharField(source='phase_config.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    parameters = ProjectParameterSerializer(read_only=True)
    zones = ZoneSerializer(many=True, read_only=True)
    panels = ElectricalPanelWriteSerializer(many=True, read_only=True)

    class Meta:
        model = Project
        fields = [
            'id', 'tenant', 'user',
            'name', 'description',
            'norm_version', 'norm_version_label',
            'voltage_level', 'voltage_level_label',
            'phase_config', 'phase_config_label',
            'status', 'status_display',
            'parameters', 'zones', 'panels',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']


class ProjectWriteSerializer(serializers.ModelSerializer):
    """Serializer de escritura: crea proyecto y sus parámetros técnicos."""

    parameters = ProjectParameterSerializer(required=False)

    class Meta:
        model = Project
        fields = [
            'id', 'tenant', 'name', 'description',
            'norm_version', 'voltage_level', 'phase_config',
            'status', 'parameters',
        ]
        read_only_fields = ['id']

    def create(self, validated_data):
        parameters_data = validated_data.pop('parameters', {})
        # El usuario se asigna desde el request en el ViewSet
        project = Project.objects.create(**validated_data)
        ProjectParameter.objects.create(project=project, **parameters_data)
        return project

    def update(self, instance, validated_data):
        parameters_data = validated_data.pop('parameters', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if parameters_data is not None:
            params = instance.parameters
            for attr, value in parameters_data.items():
                setattr(params, attr, value)
            params.save()
        return instance


# ---------------------------------------------------------------------------
# MÓDULO 4 — CÁLCULOS E HISTORIAL
# ---------------------------------------------------------------------------

class CalculationAlertSerializer(serializers.ModelSerializer):
    severity_display = serializers.CharField(source='get_severity_display', read_only=True)
    alert_type_display = serializers.CharField(source='get_alert_type_display', read_only=True)

    class Meta:
        model = CalculationAlert
        fields = ['id', 'alert_type', 'alert_type_display', 'severity', 'severity_display', 'message', 'details']


class CalculationHistorySerializer(serializers.ModelSerializer):
    alerts = CalculationAlertSerializer(many=True, read_only=True)
    created_by_email = serializers.CharField(source='created_by.email', read_only=True, default=None)

    class Meta:
        model = CalculationHistory
        fields = [
            'id', 'circuit', 'calculation_version',
            'total_load_amps', 'demand_load_amps',
            'voltage_drop_percent', 'is_compliant',
            'full_input_snapshot', 'full_output_snapshot',
            'created_at', 'created_by_email',
            'alerts',
        ]


# ---------------------------------------------------------------------------
# MÓDULO 5 — PRESUPUESTO Y MATERIALES
# ---------------------------------------------------------------------------

class BillOfMaterialsSerializer(serializers.ModelSerializer):
    material_name = serializers.CharField(source='material.name', read_only=True)
    material_sku = serializers.CharField(source='material.sku', read_only=True)
    unit_measure = serializers.CharField(source='material.unit_measure.name', read_only=True)
    total_price = serializers.DecimalField(max_digits=14, decimal_places=4, read_only=True)

    class Meta:
        model = BillOfMaterials
        fields = [
            'id', 'project', 'material', 'material_name', 'material_sku',
            'circuit', 'quantity', 'unit_price', 'unit_measure',
            'total_price', 'notes',
        ]
        read_only_fields = ['id', 'total_price']

    def validate_quantity(self, value):
        if value <= 0:
            raise serializers.ValidationError('La cantidad debe ser mayor a cero.')
        return value

    def validate_unit_price(self, value):
        if value < 0:
            raise serializers.ValidationError('El precio unitario no puede ser negativo.')
        return value


class BudgetItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = BudgetItem
        fields = ['id', 'budget', 'name', 'sort_order']
        read_only_fields = ['id']


class BudgetSerializer(serializers.ModelSerializer):
    items = BudgetItemSerializer(many=True, read_only=True)
    total = serializers.DecimalField(max_digits=14, decimal_places=4, read_only=True)

    class Meta:
        model = Budget
        fields = [
            'id', 'project', 'version',
            'subtotal', 'tax_percent', 'total',
            'created_at', 'items',
        ]
        read_only_fields = ['id', 'version', 'total', 'created_at']

    def create(self, validated_data):
        # Autoincrementar la versión del presupuesto para el proyecto
        project = validated_data['project']
        last_version = Budget.objects.filter(project=project).order_by('-version').values_list('version', flat=True).first()
        validated_data['version'] = (last_version or 0) + 1
        return super().create(validated_data)


# ---------------------------------------------------------------------------
# MÓDULO 6 — DOCUMENTOS
# ---------------------------------------------------------------------------

class DocumentSerializer(serializers.ModelSerializer):
    document_type_display = serializers.CharField(source='get_document_type_display', read_only=True)

    class Meta:
        model = Document
        fields = [
            'id', 'project', 'calculation_version',
            'document_type', 'document_type_display',
            'file_name', 'storage_url', 'generated_at',
        ]
        read_only_fields = ['id', 'generated_at']
