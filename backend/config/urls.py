"""
ElectroSmart — URL Configuration
==================================
Configuración de rutas de la API REST con DefaultRouter de DRF.

Estructura de URLs:
    /api/v1/   — Todos los endpoints de la plataforma.
    /admin/    — Panel de administración de Django.
    /api/v1/schema/   — Esquema OpenAPI (cuando se integre drf-spectacular).
"""

from django.contrib import admin
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from core.views import (
    BillOfMaterialsViewSet,
    BreakerCatalogViewSet,
    BudgetItemViewSet,
    BudgetViewSet,
    CalculationHistoryViewSet,
    CircuitViewSet,
    ConductorCatalogViewSet,
    DocumentViewSet,
    ElectricalPanelViewSet,
    LoadTypeViewSet,
    LoadViewSet,
    MaterialCatalogViewSet,
    NormVersionViewSet,
    NormViewSet,
    PhaseConfigViewSet,
    ProjectViewSet,
    VoltageLevelViewSet,
    ZoneViewSet,
)

# ---------------------------------------------------------------------------
# Router DRF — registra automáticamente las rutas CRUD de cada ViewSet
# ---------------------------------------------------------------------------

router = DefaultRouter()

# Catálogos técnicos (solo lectura)
router.register(r'norms', NormViewSet, basename='norm')
router.register(r'norm-versions', NormVersionViewSet, basename='norm-version')
router.register(r'voltage-levels', VoltageLevelViewSet, basename='voltage-level')
router.register(r'phase-configs', PhaseConfigViewSet, basename='phase-config')
router.register(r'conductors', ConductorCatalogViewSet, basename='conductor')
router.register(r'breakers', BreakerCatalogViewSet, basename='breaker')
router.register(r'load-types', LoadTypeViewSet, basename='load-type')
router.register(r'materials', MaterialCatalogViewSet, basename='material')

# Proyectos y estructura eléctrica
router.register(r'projects', ProjectViewSet, basename='project')
router.register(r'zones', ZoneViewSet, basename='zone')
router.register(r'panels', ElectricalPanelViewSet, basename='panel')
router.register(r'circuits', CircuitViewSet, basename='circuit')
router.register(r'loads', LoadViewSet, basename='load')

# Cálculos
router.register(r'calculation-history', CalculationHistoryViewSet, basename='calculation-history')

# Presupuesto y materiales
router.register(r'bill-of-materials', BillOfMaterialsViewSet, basename='bill-of-materials')
router.register(r'budgets', BudgetViewSet, basename='budget')
router.register(r'budget-items', BudgetItemViewSet, basename='budget-item')

# Documentos
router.register(r'documents', DocumentViewSet, basename='document')

# ---------------------------------------------------------------------------
# URL patterns principales
# ---------------------------------------------------------------------------

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/', include(router.urls)),
]
