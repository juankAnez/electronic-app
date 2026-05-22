"""
ElectroSmart — Core Admin Registration
=======================================
Registro de todos los modelos del dominio en el panel de administración de
Django. Se agrupan por módulo funcional para facilitar la navegación.
Se aplican configuraciones de búsqueda, filtros y columnas relevantes en
cada ModelAdmin para agilizar la gestión de datos de catálogos y proyectos.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import (
    # Módulo 1 — Identidad
    AuditLog,
    BillOfMaterials,
    BreakerCatalog,
    Budget,
    BudgetItem,
    BudgetItemMaterial,
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
    MaterialUnitMeasure,
    Norm,
    NormVersion,
    Permission,
    PhaseConfig,
    Project,
    ProjectParameter,
    Role,
    RolePermission,
    Tenant,
    User,
    UserTenantRole,
    VoltageLevel,
    WireMaterial,
    Zone,
)

# ---------------------------------------------------------------------------
# MÓDULO 1 — IDENTIDAD Y ACCESO MULTI-TENANT
# ---------------------------------------------------------------------------

@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = ['name', 'subdomain', 'is_active', 'created_at']
    list_filter = ['is_active']
    search_fields = ['name', 'subdomain']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['name']


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['email', 'first_name', 'last_name', 'is_active', 'is_staff', 'date_joined']
    list_filter = ['is_active', 'is_staff', 'is_superuser']
    search_fields = ['email', 'first_name', 'last_name']
    ordering = ['email']
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Auditoría', {'fields': ('deleted_at',)}),
    )


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ['name', 'description']
    search_fields = ['name']


@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    list_display = ['resource', 'action']
    list_filter = ['resource']
    search_fields = ['resource', 'action']
    ordering = ['resource', 'action']


@admin.register(UserTenantRole)
class UserTenantRoleAdmin(admin.ModelAdmin):
    list_display = ['user', 'tenant', 'role', 'granted_at']
    list_filter = ['tenant', 'role']
    search_fields = ['user__email', 'tenant__name']
    autocomplete_fields = ['user', 'tenant', 'role']


@admin.register(RolePermission)
class RolePermissionAdmin(admin.ModelAdmin):
    list_display = ['role', 'permission']
    list_filter = ['role']


# ---------------------------------------------------------------------------
# MÓDULO 2 — NORMAS Y CATÁLOGOS TÉCNICOS
# ---------------------------------------------------------------------------

@admin.register(Norm)
class NormAdmin(admin.ModelAdmin):
    list_display = ['code', 'name']
    search_fields = ['code', 'name']


@admin.register(NormVersion)
class NormVersionAdmin(admin.ModelAdmin):
    list_display = ['norm', 'version_name', 'effective_from', 'effective_to', 'is_current']
    list_filter = ['norm', 'is_current']
    search_fields = ['norm__code', 'version_name']


@admin.register(VoltageLevel)
class VoltageLevelAdmin(admin.ModelAdmin):
    list_display = ['voltage_numeric', 'phase_type', 'frequency']
    list_filter = ['phase_type', 'frequency']
    ordering = ['voltage_numeric']


@admin.register(PhaseConfig)
class PhaseConfigAdmin(admin.ModelAdmin):
    list_display = ['name', 'active_conductors', 'has_neutral']


@admin.register(WireMaterial)
class WireMaterialAdmin(admin.ModelAdmin):
    list_display = ['material_name', 'resistivity_ohm_mm2_m']


@admin.register(InsulationType)
class InsulationTypeAdmin(admin.ModelAdmin):
    list_display = ['code', 'max_temperature_c']


@admin.register(ConductorCatalog)
class ConductorCatalogAdmin(admin.ModelAdmin):
    list_display = ['gauge_awg', 'wire_material', 'insulation_type', 'cross_section_mm2', 'ampacity_30c', 'norm_version']
    list_filter = ['norm_version', 'wire_material', 'insulation_type']
    search_fields = ['gauge_awg']
    ordering = ['-ampacity_30c']


@admin.register(BreakerCatalog)
class BreakerCatalogAdmin(admin.ModelAdmin):
    list_display = ['ampacity', 'poles', 'trip_curve', 'ka_rating', 'norm_version']
    list_filter = ['norm_version', 'poles', 'trip_curve']
    ordering = ['poles', 'ampacity']


@admin.register(LoadType)
class LoadTypeAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'category', 'default_power_factor', 'default_demand_factor']
    list_filter = ['category']
    search_fields = ['code', 'name']


@admin.register(MaterialUnitMeasure)
class MaterialUnitMeasureAdmin(admin.ModelAdmin):
    list_display = ['name']


@admin.register(MaterialCatalog)
class MaterialCatalogAdmin(admin.ModelAdmin):
    list_display = ['sku', 'name', 'unit_measure', 'unit_price']
    search_fields = ['sku', 'name']
    list_filter = ['unit_measure']


# ---------------------------------------------------------------------------
# MÓDULO 3 — ESTRUCTURA ELÉCTRICA DEL PROYECTO
# ---------------------------------------------------------------------------

class ProjectParameterInline(admin.StackedInline):
    model = ProjectParameter
    can_delete = False
    verbose_name_plural = 'Parámetros Técnicos'


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ['name', 'tenant', 'user', 'status', 'norm_version', 'created_at']
    list_filter = ['status', 'tenant', 'norm_version']
    search_fields = ['name', 'tenant__name', 'user__email']
    readonly_fields = ['created_at', 'updated_at']
    inlines = [ProjectParameterInline]
    ordering = ['-created_at']


@admin.register(Zone)
class ZoneAdmin(admin.ModelAdmin):
    list_display = ['name', 'project', 'sort_order']
    list_filter = ['project']
    search_fields = ['name', 'project__name']


class CircuitInline(admin.TabularInline):
    model = Circuit
    extra = 0
    fields = ['circuit_number', 'length_meters', 'is_three_phase', 'phase_assignment']


@admin.register(ElectricalPanel)
class ElectricalPanelAdmin(admin.ModelAdmin):
    list_display = ['name', 'project', 'zone', 'main_breaker_ampacity', 'is_subpanel']
    list_filter = ['project', 'is_subpanel']
    search_fields = ['name', 'project__name']
    inlines = [CircuitInline]


class LoadInline(admin.TabularInline):
    model = Load
    extra = 0
    fields = ['name', 'load_type', 'quantity', 'power_watts', 'voltage_v', 'power_factor', 'is_continuous']


@admin.register(Circuit)
class CircuitAdmin(admin.ModelAdmin):
    list_display = ['circuit_number', 'panel', 'length_meters', 'phase_assignment', 'is_three_phase']
    list_filter = ['panel__project', 'phase_assignment', 'is_three_phase']
    inlines = [LoadInline]
    ordering = ['panel', 'circuit_number']


@admin.register(Load)
class LoadAdmin(admin.ModelAdmin):
    list_display = ['name', 'circuit', 'load_type', 'quantity', 'power_watts', 'voltage_v', 'power_factor', 'is_continuous']
    list_filter = ['load_type', 'is_continuous']
    search_fields = ['name', 'circuit__panel__project__name']


# ---------------------------------------------------------------------------
# MÓDULO 4 — MOTOR DE CÁLCULO E HISTORIAL
# ---------------------------------------------------------------------------

@admin.register(CircuitCalculation)
class CircuitCalculationAdmin(admin.ModelAdmin):
    list_display = ['circuit', 'calculation_version', 'total_load_amps', 'voltage_drop_percent', 'is_compliant', 'calculation_date']
    list_filter = ['is_compliant']
    search_fields = ['circuit__panel__project__name']
    readonly_fields = ['calculation_date']


class CalculationAlertInline(admin.TabularInline):
    model = CalculationAlert
    extra = 0
    fields = ['alert_type', 'severity', 'message']
    readonly_fields = ['alert_type', 'severity', 'message']


@admin.register(CalculationHistory)
class CalculationHistoryAdmin(admin.ModelAdmin):
    list_display = ['circuit', 'calculation_version', 'total_load_amps', 'is_compliant', 'created_at', 'created_by']
    list_filter = ['is_compliant']
    search_fields = ['circuit__panel__project__name']
    readonly_fields = ['created_at']
    inlines = [CalculationAlertInline]
    ordering = ['-created_at']


@admin.register(CalculationAlert)
class CalculationAlertAdmin(admin.ModelAdmin):
    list_display = ['alert_type', 'severity', 'calculation_history', 'message']
    list_filter = ['severity', 'alert_type']


# ---------------------------------------------------------------------------
# MÓDULO 5 — MATERIALES Y PRESUPUESTACIÓN
# ---------------------------------------------------------------------------

class BudgetItemInline(admin.TabularInline):
    model = BudgetItem
    extra = 0
    fields = ['name', 'sort_order']


@admin.register(BillOfMaterials)
class BillOfMaterialsAdmin(admin.ModelAdmin):
    list_display = ['project', 'material', 'quantity', 'unit_price', 'circuit']
    list_filter = ['project']
    search_fields = ['project__name', 'material__name']


@admin.register(Budget)
class BudgetAdmin(admin.ModelAdmin):
    list_display = ['project', 'version', 'subtotal', 'tax_percent', 'created_at']
    list_filter = ['project']
    readonly_fields = ['created_at']
    inlines = [BudgetItemInline]
    ordering = ['-created_at']


@admin.register(BudgetItem)
class BudgetItemAdmin(admin.ModelAdmin):
    list_display = ['budget', 'name', 'sort_order']
    list_filter = ['budget__project']


@admin.register(BudgetItemMaterial)
class BudgetItemMaterialAdmin(admin.ModelAdmin):
    list_display = ['budget_item', 'bill_of_materials']


# ---------------------------------------------------------------------------
# MÓDULO 6 — DOCUMENTOS Y AUDITORÍA
# ---------------------------------------------------------------------------

@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ['file_name', 'project', 'document_type', 'generated_at']
    list_filter = ['document_type', 'project']
    readonly_fields = ['generated_at']
    ordering = ['-generated_at']


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['table_name', 'record_id', 'action', 'changed_by', 'changed_at']
    list_filter = ['action', 'table_name']
    search_fields = ['table_name', 'changed_by__email']
    readonly_fields = ['tenant', 'table_name', 'record_id', 'action', 'old_data', 'new_data', 'changed_by', 'changed_at']
    ordering = ['-changed_at']

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
