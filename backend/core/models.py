"""
ElectroSmart Platform — Core Application Models
================================================
Este módulo define todos los modelos de dominio del sistema ElectroSmart.

Organización por módulos:
    1. Identidad y acceso multi-tenant
    2. Normas y catálogos técnicos (globales, versionados por norma)
    3. Estructura eléctrica del proyecto
    4. Motor de cálculo e historial
    5. Materiales y presupuestación
    6. Documentos y auditoría
"""

import uuid

from django.contrib.auth.models import AbstractUser
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


# ---------------------------------------------------------------------------
# MIXIN GENÉRICO DE TIMESTAMPS
# ---------------------------------------------------------------------------

class TimestampMixin(models.Model):
    """Campos de auditoría de tiempo comunes a entidades de negocio."""

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True, db_index=True)

    class Meta:
        abstract = True


# ===========================================================================
# MÓDULO 1 — IDENTIDAD Y ACCESO MULTI-TENANT
# ===========================================================================

class Tenant(TimestampMixin):
    """
    Organización suscriptora al SaaS.

    Cada tenant es una empresa o equipo de trabajo independiente. Un mismo
    usuario puede pertenecer a múltiples tenants con roles diferenciados.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=150)
    subdomain = models.CharField(max_length=63, unique=True)
    settings = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Tenant'
        verbose_name_plural = 'Tenants'

    def __str__(self):
        return self.name


class User(AbstractUser, TimestampMixin):
    """
    Usuario global de la plataforma.

    Extiende AbstractUser de Django manteniendo el sistema de autenticación
    nativo (tokens de sesión, hashing de contraseñas). La relación con
    tenants se gestiona mediante UserTenantRole, permitiendo multi-tenencia.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Los campos username, email, password, first_name, last_name
    # son heredados de AbstractUser. Se elimina la fecha de borrado
    # de TimestampMixin y se usa deleted_at explícito.

    class Meta:
        ordering = ['email']
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'

    def __str__(self):
        return self.email


class Role(models.Model):
    """Catálogo de roles del sistema (admin, engineer, client)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Rol'
        verbose_name_plural = 'Roles'

    def __str__(self):
        return self.name


class Permission(models.Model):
    """Permisos granulares por recurso y acción."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    resource = models.CharField(max_length=100)
    action = models.CharField(max_length=50)

    class Meta:
        unique_together = [('resource', 'action')]
        ordering = ['resource', 'action']
        verbose_name = 'Permiso'
        verbose_name_plural = 'Permisos'

    def __str__(self):
        return f'{self.resource}:{self.action}'


class UserTenantRole(models.Model):
    """
    Relación N:M entre usuarios, tenants y roles.

    Permite que un mismo usuario tenga diferentes niveles de acceso
    en cada tenant al que pertenece.
    """

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tenant_roles')
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='user_roles')
    role = models.ForeignKey(Role, on_delete=models.RESTRICT, related_name='assignments')
    granted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [('user', 'tenant', 'role')]
        verbose_name = 'Rol de Usuario en Tenant'
        verbose_name_plural = 'Roles de Usuarios en Tenants'

    def __str__(self):
        return f'{self.user.email} @ {self.tenant.name} [{self.role.name}]'


class RolePermission(models.Model):
    """Asignación de permisos a roles."""

    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name='permissions')
    permission = models.ForeignKey(Permission, on_delete=models.CASCADE, related_name='roles')

    class Meta:
        unique_together = [('role', 'permission')]
        verbose_name = 'Permiso de Rol'
        verbose_name_plural = 'Permisos de Roles'


# ===========================================================================
# MÓDULO 2 — NORMAS Y CATÁLOGOS TÉCNICOS GLOBALES
# ===========================================================================

class Norm(models.Model):
    """Norma eléctrica base (NEC, IEC, RETIE)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=150)

    class Meta:
        ordering = ['code']
        verbose_name = 'Norma'
        verbose_name_plural = 'Normas'

    def __str__(self):
        return f'{self.code} — {self.name}'


class NormVersion(models.Model):
    """
    Versión concreta de una norma eléctrica.

    Los proyectos y catálogos técnicos referencian una versión específica
    para garantizar la reproducibilidad de cálculos sin importar futuras
    actualizaciones normativas.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    norm = models.ForeignKey(Norm, on_delete=models.RESTRICT, related_name='versions')
    version_name = models.CharField(max_length=50)
    effective_from = models.DateField()
    effective_to = models.DateField(null=True, blank=True)
    is_current = models.BooleanField(default=False)

    class Meta:
        unique_together = [('norm', 'version_name')]
        ordering = ['norm', '-effective_from']
        verbose_name = 'Versión de Norma'
        verbose_name_plural = 'Versiones de Normas'

    def __str__(self):
        return f'{self.norm.code} {self.version_name}'


class VoltageLevel(models.Model):
    """Tensión nominal de servicio con tipo de acometida y frecuencia."""

    PHASE_TYPE_CHOICES = [
        ('single', 'Monofásica'),
        ('split', 'Bifásica'),
        ('three', 'Trifásica'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    voltage_numeric = models.DecimalField(max_digits=6, decimal_places=1)
    phase_type = models.CharField(max_length=10, choices=PHASE_TYPE_CHOICES)
    frequency = models.DecimalField(max_digits=4, decimal_places=1, default=60.0)

    class Meta:
        unique_together = [('voltage_numeric', 'phase_type', 'frequency')]
        ordering = ['voltage_numeric']
        verbose_name = 'Nivel de Tensión'
        verbose_name_plural = 'Niveles de Tensión'

    def __str__(self):
        return f'{self.voltage_numeric}V {self.get_phase_type_display()} {self.frequency}Hz'


class PhaseConfig(models.Model):
    """Configuración de conductores activos y neutro para el sistema."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    active_conductors = models.PositiveSmallIntegerField()
    has_neutral = models.BooleanField(default=True)

    class Meta:
        ordering = ['active_conductors', 'name']
        verbose_name = 'Configuración de Fase'
        verbose_name_plural = 'Configuraciones de Fase'

    def __str__(self):
        return self.name


class WireMaterial(models.Model):
    """Material conductor con resistividad."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    material_name = models.CharField(max_length=50, unique=True)
    resistivity_ohm_mm2_m = models.DecimalField(max_digits=10, decimal_places=8)

    class Meta:
        ordering = ['material_name']
        verbose_name = 'Material Conductor'
        verbose_name_plural = 'Materiales Conductores'

    def __str__(self):
        return self.material_name


class InsulationType(models.Model):
    """Tipo de aislamiento del conductor y su temperatura máxima operativa."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=20, unique=True)
    max_temperature_c = models.PositiveSmallIntegerField()

    class Meta:
        ordering = ['code']
        verbose_name = 'Tipo de Aislamiento'
        verbose_name_plural = 'Tipos de Aislamiento'

    def __str__(self):
        return f'{self.code} ({self.max_temperature_c}°C)'


class ConductorCatalog(models.Model):
    """
    Catálogo técnico de conductores eléctricos por norma.

    Cada registro especifica la ampacidad base de un conductor definido
    por su calibre, material y tipo de aislamiento, bajo una versión de norma.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    norm_version = models.ForeignKey(NormVersion, on_delete=models.RESTRICT, related_name='conductors')
    wire_material = models.ForeignKey(WireMaterial, on_delete=models.RESTRICT, related_name='catalog_entries')
    insulation_type = models.ForeignKey(InsulationType, on_delete=models.RESTRICT, related_name='catalog_entries')
    gauge_awg = models.CharField(max_length=10)
    cross_section_mm2 = models.DecimalField(max_digits=8, decimal_places=2)
    ampacity_30c = models.DecimalField(max_digits=6, decimal_places=1)

    class Meta:
        ordering = ['norm_version', '-ampacity_30c']
        verbose_name = 'Catálogo de Conductores'
        verbose_name_plural = 'Catálogos de Conductores'

    def __str__(self):
        return (
            f'{self.gauge_awg} AWG '
            f'{self.wire_material.material_name} '
            f'{self.insulation_type.code} — '
            f'{self.ampacity_30c}A'
        )


class BreakerCatalog(models.Model):
    """
    Catálogo de interruptores termomagnéticos (breakers).

    La curva de disparo define el comportamiento ante sobrecargas y
    cortocircuitos. La capacidad de corte (kA) establece la corriente
    máxima de cortocircuito que puede interrumpir de forma segura.
    """

    TRIP_CURVE_CHOICES = [
        ('B', 'B — Baja retención (iluminación)'),
        ('C', 'C — Retención estándar (cargas generales)'),
        ('D', 'D — Alta retención (motores con alto arranque)'),
        ('K', 'K — Uso industrial'),
        ('Z', 'Z — Equipos electrónicos sensibles'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    norm_version = models.ForeignKey(NormVersion, on_delete=models.RESTRICT, related_name='breakers')
    poles = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(3)]
    )
    ampacity = models.DecimalField(max_digits=6, decimal_places=1)
    trip_curve = models.CharField(max_length=1, choices=TRIP_CURVE_CHOICES, blank=True)
    ka_rating = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)

    class Meta:
        ordering = ['norm_version', 'poles', 'ampacity']
        verbose_name = 'Catálogo de Breakers'
        verbose_name_plural = 'Catálogos de Breakers'

    def __str__(self):
        return f'{self.poles}P {self.ampacity}A {self.trip_curve}'


class LoadType(models.Model):
    """
    Catálogo de tipos de carga eléctrica.

    Define factores estándar para facilitar el ingreso rápido de cargas
    sin que el usuario necesite conocer los valores de fábrica.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=30, unique=True)
    name = models.CharField(max_length=100)
    category = models.CharField(max_length=50, blank=True)
    default_power_factor = models.DecimalField(
        max_digits=3, decimal_places=2, default=0.90,
        validators=[MinValueValidator(0.01), MaxValueValidator(1.00)]
    )
    default_demand_factor = models.DecimalField(
        max_digits=3, decimal_places=2, default=1.00,
        validators=[MinValueValidator(0.01), MaxValueValidator(1.00)]
    )

    class Meta:
        ordering = ['category', 'name']
        verbose_name = 'Tipo de Carga'
        verbose_name_plural = 'Tipos de Carga'

    def __str__(self):
        return f'{self.code} — {self.name}'


class MaterialUnitMeasure(models.Model):
    """Unidades de medida para materiales (metro, unidad, caja)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=30, unique=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Unidad de Medida'
        verbose_name_plural = 'Unidades de Medida'

    def __str__(self):
        return self.name


class MaterialCatalog(models.Model):
    """Catálogo general de materiales físicos para presupuestación."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sku = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=200)
    unit_measure = models.ForeignKey(
        MaterialUnitMeasure, on_delete=models.RESTRICT, related_name='materials'
    )
    unit_price = models.DecimalField(max_digits=12, decimal_places=4)

    class Meta:
        ordering = ['name']
        verbose_name = 'Material'
        verbose_name_plural = 'Materiales'

    def __str__(self):
        return f'{self.sku} — {self.name}'


# ===========================================================================
# MÓDULO 3 — ESTRUCTURA ELÉCTRICA DEL PROYECTO
# ===========================================================================

class Project(TimestampMixin):
    """
    Proyecto eléctrico central del sistema.

    Cada proyecto pertenece a un tenant y congela la versión de norma
    al momento de su configuración para garantizar reproducibilidad de cálculos.
    """

    STATUS_CHOICES = [
        ('draft', 'Borrador'),
        ('active', 'Activo'),
        ('calculated', 'Calculado'),
        ('budgeted', 'Presupuestado'),
        ('archived', 'Archivado'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='projects')
    user = models.ForeignKey(User, on_delete=models.RESTRICT, related_name='projects')
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    norm_version = models.ForeignKey(NormVersion, on_delete=models.RESTRICT, related_name='projects')
    voltage_level = models.ForeignKey(VoltageLevel, on_delete=models.RESTRICT, related_name='projects')
    phase_config = models.ForeignKey(PhaseConfig, on_delete=models.RESTRICT, related_name='projects')
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='draft')

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Proyecto'
        verbose_name_plural = 'Proyectos'

    def __str__(self):
        return f'{self.name} [{self.tenant.name}]'


class ProjectParameter(models.Model):
    """
    Parámetros técnicos y ambientales del proyecto (relación 1:1).

    Separado de Project para mantener la entidad principal limpia
    y facilitar extensiones futuras sin alterar el núcleo del proyecto.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.OneToOneField(Project, on_delete=models.CASCADE, related_name='parameters')
    ambient_temp_c = models.DecimalField(max_digits=4, decimal_places=1, default=30.0)
    altitude_m = models.DecimalField(max_digits=6, decimal_places=1, default=0.0)
    max_voltage_drop_pct = models.DecimalField(max_digits=3, decimal_places=1, default=3.0)
    safety_factor = models.DecimalField(max_digits=3, decimal_places=2, default=1.25)

    class Meta:
        verbose_name = 'Parámetros del Proyecto'
        verbose_name_plural = 'Parámetros de Proyectos'

    def __str__(self):
        return f'Parámetros de {self.project.name}'


class Zone(models.Model):
    """
    Zona o área física del proyecto.

    Permite organizar los tableros por áreas lógicas (ej. Planta Alta,
    Área de Producción) sin que esto afecte los cálculos eléctricos.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='zones')
    name = models.CharField(max_length=100)
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        unique_together = [('project', 'name')]
        ordering = ['project', 'sort_order', 'name']
        verbose_name = 'Zona'
        verbose_name_plural = 'Zonas'

    def __str__(self):
        return f'{self.project.name} / {self.name}'


class ElectricalPanel(models.Model):
    """
    Tablero de distribución eléctrica.

    Soporta jerarquía de tablero principal y subtableros mediante
    la autorreferencia a parent_panel.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='panels')
    zone = models.ForeignKey(Zone, on_delete=models.SET_NULL, null=True, blank=True, related_name='panels')
    parent_panel = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True, related_name='sub_panels'
    )
    name = models.CharField(max_length=100)
    location = models.CharField(max_length=200, blank=True)
    main_breaker_ampacity = models.DecimalField(max_digits=6, decimal_places=1, null=True, blank=True)
    is_subpanel = models.BooleanField(default=False)

    class Meta:
        ordering = ['project', 'name']
        verbose_name = 'Tablero Eléctrico'
        verbose_name_plural = 'Tableros Eléctricos'

    def __str__(self):
        return f'{self.name} ({self.project.name})'


class Circuit(models.Model):
    """
    Circuito ramal derivado de un tablero.

    La asignación de fase (phase_assignment) es fundamental para que el motor
    de cálculo realice el balance de fases en instalaciones trifásicas.
    """

    PHASE_ASSIGNMENT_CHOICES = [
        ('A', 'Fase A'),
        ('B', 'Fase B'),
        ('C', 'Fase C'),
        ('AB', 'Fase A-B (bifásico)'),
        ('BC', 'Fase B-C (bifásico)'),
        ('CA', 'Fase C-A (bifásico)'),
        ('ABC', 'Tres fases'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    panel = models.ForeignKey(ElectricalPanel, on_delete=models.CASCADE, related_name='circuits')
    circuit_number = models.PositiveSmallIntegerField()
    length_meters = models.DecimalField(max_digits=8, decimal_places=2)
    is_three_phase = models.BooleanField(default=False)
    phase_assignment = models.CharField(
        max_length=3, choices=PHASE_ASSIGNMENT_CHOICES, blank=True
    )

    class Meta:
        unique_together = [('panel', 'circuit_number')]
        ordering = ['panel', 'circuit_number']
        verbose_name = 'Circuito'
        verbose_name_plural = 'Circuitos'

    def __str__(self):
        return f'Circuito {self.circuit_number} — {self.panel.name}'


class Load(models.Model):
    """
    Carga eléctrica conectada a un circuito.

    Los campos voltage_v y power_factor permiten al motor de cálculo
    determinar la corriente real de cada carga mediante la fórmula:

        Monofásica: I = (P · quantity) / (V · FP)
        Trifásica:  I = (P · quantity) / (√3 · V · FP)

    is_continuous indica si la carga opera durante 3 horas o más
    de forma continua, lo que requiere un incremento del 125% sobre la
    corriente de diseño según NEC.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    circuit = models.ForeignKey(Circuit, on_delete=models.CASCADE, related_name='loads')
    load_type = models.ForeignKey(LoadType, on_delete=models.RESTRICT, related_name='loads')
    name = models.CharField(max_length=150)
    quantity = models.PositiveSmallIntegerField(default=1)
    power_watts = models.DecimalField(max_digits=10, decimal_places=2)
    voltage_v = models.DecimalField(max_digits=5, decimal_places=1, default=120.0)
    power_factor = models.DecimalField(
        max_digits=3, decimal_places=2, default=0.90,
        validators=[MinValueValidator(0.01), MaxValueValidator(1.00)]
    )
    is_continuous = models.BooleanField(default=False)

    class Meta:
        ordering = ['circuit', 'name']
        verbose_name = 'Carga'
        verbose_name_plural = 'Cargas'

    def __str__(self):
        return f'{self.name} ({self.power_watts}W × {self.quantity})'


# ===========================================================================
# MÓDULO 4 — MOTOR DE CÁLCULO E HISTORIAL
# ===========================================================================

class CircuitCalculation(models.Model):
    """
    Resultado activo del último cálculo ejecutado sobre un circuito.

    Mantiene una única fila por circuito (relación OneToOne) con el
    resultado más reciente. El historial completo se almacena en
    CalculationHistory.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    circuit = models.OneToOneField(Circuit, on_delete=models.CASCADE, related_name='calculation')
    calculation_version = models.PositiveIntegerField(default=1)
    total_load_amps = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    demand_load_amps = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    conductor = models.ForeignKey(
        ConductorCatalog, on_delete=models.SET_NULL, null=True, blank=True, related_name='active_calculations'
    )
    breaker = models.ForeignKey(
        BreakerCatalog, on_delete=models.SET_NULL, null=True, blank=True, related_name='active_calculations'
    )
    voltage_drop_percent = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    is_compliant = models.BooleanField(null=True, blank=True)
    parameters_snapshot = models.JSONField(null=True, blank=True)
    calculation_date = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Cálculo de Circuito'
        verbose_name_plural = 'Cálculos de Circuitos'

    def __str__(self):
        status = 'OK' if self.is_compliant else 'NO CUMPLE'
        return f'{self.circuit} — v{self.calculation_version} [{status}]'


class CalculationHistory(models.Model):
    """
    Snapshot inmutable de cada versión de cálculo por circuito.

    full_input_snapshot almacena el estado completo de las cargas,
    longitudes y factores ambientales en el momento de calcular, de modo
    que el cálculo pueda reproducirse en el futuro aunque los datos cambien.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    circuit = models.ForeignKey(Circuit, on_delete=models.CASCADE, related_name='calculation_history')
    calculation_version = models.PositiveIntegerField()
    total_load_amps = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    demand_load_amps = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    conductor_catalog_id = models.UUIDField(null=True, blank=True)
    breaker_catalog_id = models.UUIDField(null=True, blank=True)
    voltage_drop_percent = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    is_compliant = models.BooleanField(null=True, blank=True)
    full_input_snapshot = models.JSONField(null=True, blank=True)
    full_output_snapshot = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name='calculation_history'
    )

    class Meta:
        ordering = ['circuit', '-calculation_version']
        verbose_name = 'Historial de Cálculo'
        verbose_name_plural = 'Históricos de Cálculo'

    def __str__(self):
        return f'{self.circuit} — Versión {self.calculation_version}'


class CalculationAlert(models.Model):
    """
    Alerta normativa generada durante un cálculo.

    Implementa el sistema visual de semáforo: severity=error (rojo)
    y severity=warning (amarillo) para orientar al usuario sobre
    incumplimientos de norma en lenguaje comprensible.
    """

    ALERT_TYPE_CHOICES = [
        ('overcurrent', 'Sobrecorriente'),
        ('voltage_drop', 'Caída de Tensión'),
        ('short_circuit', 'Cortocircuito'),
        ('temperature', 'Temperatura'),
    ]
    SEVERITY_CHOICES = [
        ('warning', 'Advertencia'),
        ('error', 'Error'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    calculation_history = models.ForeignKey(
        CalculationHistory, on_delete=models.CASCADE, related_name='alerts'
    )
    alert_type = models.CharField(max_length=20, choices=ALERT_TYPE_CHOICES)
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES)
    message = models.TextField()
    details = models.JSONField(null=True, blank=True)

    class Meta:
        ordering = ['severity', 'alert_type']
        verbose_name = 'Alerta de Cálculo'
        verbose_name_plural = 'Alertas de Cálculo'

    def __str__(self):
        return f'[{self.severity.upper()}] {self.alert_type} — {self.message[:60]}'


# ===========================================================================
# MÓDULO 5 — MATERIALES Y PRESUPUESTACIÓN
# ===========================================================================

class BillOfMaterials(models.Model):
    """
    Lista de materiales cuantificados por proyecto.

    El campo unit_price congela el precio del catálogo en el momento de
    la presupuestación. Esto garantiza que presupuestos ya aprobados no
    se alteren si el catálogo de materiales se actualiza posteriormente.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='bill_of_materials')
    material = models.ForeignKey(MaterialCatalog, on_delete=models.RESTRICT, related_name='bom_entries')
    circuit = models.ForeignKey(
        Circuit, on_delete=models.SET_NULL, null=True, blank=True, related_name='bom_entries'
    )
    quantity = models.DecimalField(max_digits=12, decimal_places=4)
    unit_price = models.DecimalField(max_digits=12, decimal_places=4)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['project', 'material__name']
        verbose_name = 'Lista de Materiales'
        verbose_name_plural = 'Listas de Materiales'

    @property
    def total_price(self):
        return self.quantity * self.unit_price

    def __str__(self):
        return f'{self.material.name} × {self.quantity}'


class Budget(models.Model):
    """
    Presupuesto del proyecto con soporte de versionado.

    Cada vez que se revisa o actualiza un presupuesto se crea una nueva
    versión, permitiendo el historial de cotizaciones enviadas al cliente.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='budgets')
    version = models.PositiveSmallIntegerField(default=1)
    subtotal = models.DecimalField(max_digits=14, decimal_places=4, default=0)
    tax_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [('project', 'version')]
        ordering = ['project', '-version']
        verbose_name = 'Presupuesto'
        verbose_name_plural = 'Presupuestos'

    @property
    def total(self):
        return self.subtotal * (1 + self.tax_percent / 100)

    def __str__(self):
        return f'Presupuesto v{self.version} — {self.project.name}'


class BudgetItem(models.Model):
    """Partida organizativa dentro de un presupuesto."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    budget = models.ForeignKey(Budget, on_delete=models.CASCADE, related_name='items')
    name = models.CharField(max_length=150)
    sort_order = models.PositiveSmallIntegerField(default=0)
    materials = models.ManyToManyField(
        BillOfMaterials,
        through='BudgetItemMaterial',
        related_name='budget_items'
    )

    class Meta:
        ordering = ['budget', 'sort_order', 'name']
        verbose_name = 'Partida de Presupuesto'
        verbose_name_plural = 'Partidas de Presupuesto'

    def __str__(self):
        return f'{self.budget} / {self.name}'


class BudgetItemMaterial(models.Model):
    """Tabla intermedia entre partidas de presupuesto y materiales del BOM."""

    budget_item = models.ForeignKey(BudgetItem, on_delete=models.CASCADE)
    bill_of_materials = models.ForeignKey(BillOfMaterials, on_delete=models.CASCADE)

    class Meta:
        unique_together = [('budget_item', 'bill_of_materials')]
        verbose_name = 'Material en Partida'
        verbose_name_plural = 'Materiales en Partidas'


# ===========================================================================
# MÓDULO 6 — DOCUMENTOS Y AUDITORÍA
# ===========================================================================

class Document(models.Model):
    """
    Documento oficial generado para el proyecto.

    Almacena la referencia a los archivos exportados (PDF de memoria de
    cálculo, Excel de presupuesto, SVG de diagrama unifilar).
    """

    DOCUMENT_TYPE_CHOICES = [
        ('pdf_memory', 'Memoria de Cálculo PDF'),
        ('xlsx_budget', 'Presupuesto Excel'),
        ('svg_diagram', 'Diagrama Unifilar SVG'),
        ('pdf_full', 'Informe Completo PDF'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='documents')
    calculation_version = models.PositiveIntegerField(null=True, blank=True)
    document_type = models.CharField(max_length=20, choices=DOCUMENT_TYPE_CHOICES)
    file_name = models.CharField(max_length=255)
    storage_url = models.TextField()
    generated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-generated_at']
        verbose_name = 'Documento'
        verbose_name_plural = 'Documentos'

    def __str__(self):
        return f'{self.file_name} ({self.get_document_type_display()})'


class AuditLog(models.Model):
    """
    Bitácora de cambios sobre tablas críticas del sistema.

    Se registra quién realizó cada operación, sobre qué registro y cuáles
    fueron los datos antes y después del cambio, para cumplir con
    requerimientos de trazabilidad de proyectos de ingeniería.
    """

    ACTION_CHOICES = [
        ('INSERT', 'Inserción'),
        ('UPDATE', 'Actualización'),
        ('DELETE', 'Eliminación'),
        ('SOFT_DELETE', 'Eliminación lógica'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        Tenant, on_delete=models.SET_NULL, null=True, blank=True, related_name='audit_logs'
    )
    table_name = models.CharField(max_length=100)
    record_id = models.UUIDField()
    action = models.CharField(max_length=15, choices=ACTION_CHOICES)
    old_data = models.JSONField(null=True, blank=True)
    new_data = models.JSONField(null=True, blank=True)
    changed_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name='audit_logs'
    )
    changed_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-changed_at']
        verbose_name = 'Registro de Auditoría'
        verbose_name_plural = 'Registros de Auditoría'

    def __str__(self):
        return f'[{self.action}] {self.table_name} / {self.record_id} — {self.changed_at}'
