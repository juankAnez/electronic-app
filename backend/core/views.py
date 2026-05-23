"""
ElectroSmart — Core Views (ViewSets DRF)
=========================================
Todos los ViewSets siguen el patrón de responsabilidad única:
  - Los catálogos técnicos son de solo lectura (ReadOnlyModelViewSet).
  - Los recursos de negocio aplican filtrado por tenant del request.
  - La creación de proyectos asigna automáticamente el usuario autenticado.
  - Los endpoints de cálculo serán el punto de entrada al motor en la Sesión 5.

Convenciones de URL (registradas en urls.py con DefaultRouter):
  GET  /api/v1/norms/                   Lista de normas
  GET  /api/v1/norm-versions/           Versiones de normas
  GET  /api/v1/conductors/              Catálogo de conductores
  GET  /api/v1/breakers/                Catálogo de breakers
  GET  /api/v1/load-types/              Tipos de carga
  GET  /api/v1/materials/               Catálogo de materiales

  CRUD /api/v1/projects/                Proyectos
  CRUD /api/v1/zones/                   Zonas
  CRUD /api/v1/panels/                  Tableros eléctricos
  CRUD /api/v1/circuits/                Circuitos
  CRUD /api/v1/loads/                   Cargas
  GET  /api/v1/calculation-history/     Historial de cálculos
  CRUD /api/v1/bill-of-materials/       Lista de materiales
  CRUD /api/v1/budgets/                 Presupuestos
  GET  /api/v1/documents/               Documentos generados
"""

import logging

from django.shortcuts import get_object_or_404
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

logger = logging.getLogger(__name__)

from .models import (
    BillOfMaterials,
    BreakerCatalog,
    Budget,
    BudgetItem,
    CalculationHistory,
    Circuit,
    ConductorCatalog,
    Document,
    ElectricalPanel,
    Load,
    LoadType,
    MaterialCatalog,
    Norm,
    NormVersion,
    PhaseConfig,
    Project,
    VoltageLevel,
    Zone,
)
from .serializers import (
    BillOfMaterialsSerializer,
    BreakerCatalogSerializer,
    BudgetItemSerializer,
    BudgetSerializer,
    CalculationHistorySerializer,
    CircuitSerializer,
    CircuitWriteSerializer,
    ConductorCatalogSerializer,
    DocumentSerializer,
    ElectricalPanelSerializer,
    ElectricalPanelWriteSerializer,
    LoadSerializer,
    LoadTypeSerializer,
    MaterialCatalogSerializer,
    NormSerializer,
    NormVersionSerializer,
    PhaseConfigSerializer,
    ProjectDetailSerializer,
    ProjectListSerializer,
    ProjectWriteSerializer,
    VoltageLevelSerializer,
    ZoneSerializer,
)


# ---------------------------------------------------------------------------
# MIXINS Y PERMISOS BASE
# ---------------------------------------------------------------------------

class TenantFilterMixin:
    """
    Mixin que filtra los QuerySets de negocio por el tenant activo del usuario.

    En la fase actual sin autenticación JWT completa, se usa AllowAny para
    desarrollo. En Sesión 6 se reemplazará por IsAuthenticated con middleware
    de inyección de tenant.
    """

    permission_classes = [AllowAny]  # Temporal — cambiar a IsAuthenticated en Sesión 6

    def get_tenant_queryset(self, queryset):
        """Filtra por tenant_id si viene en los headers de la request."""
        tenant_id = self.request.headers.get('X-Tenant-ID')
        if tenant_id:
            return queryset.filter(tenant_id=tenant_id)
        return queryset


# ---------------------------------------------------------------------------
# MÓDULO 2 — CATÁLOGOS TÉCNICOS (solo lectura)
# ---------------------------------------------------------------------------

class NormViewSet(viewsets.ReadOnlyModelViewSet):
    """Lista de normas eléctricas disponibles en el sistema."""

    queryset = Norm.objects.all()
    serializer_class = NormSerializer
    permission_classes = [AllowAny]


class NormVersionViewSet(viewsets.ReadOnlyModelViewSet):
    """Versiones de normas con filtrado por norma base."""

    queryset = NormVersion.objects.select_related('norm').all()
    serializer_class = NormVersionSerializer
    permission_classes = [AllowAny]
    filter_backends = [filters.SearchFilter]
    search_fields = ['norm__code', 'version_name']

    def get_queryset(self):
        qs = super().get_queryset()
        norm_id = self.request.query_params.get('norm')
        if norm_id:
            qs = qs.filter(norm_id=norm_id)
        is_current = self.request.query_params.get('is_current')
        if is_current is not None:
            qs = qs.filter(is_current=(is_current.lower() == 'true'))
        return qs


class VoltageLevelViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = VoltageLevel.objects.all()
    serializer_class = VoltageLevelSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        qs = super().get_queryset()
        phase_type = self.request.query_params.get('phase_type')
        if phase_type:
            qs = qs.filter(phase_type=phase_type)
        return qs


class PhaseConfigViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = PhaseConfig.objects.all()
    serializer_class = PhaseConfigSerializer
    permission_classes = [AllowAny]


class ConductorCatalogViewSet(viewsets.ReadOnlyModelViewSet):
    """Catálogo de conductores con filtrado por norma y material."""

    queryset = ConductorCatalog.objects.select_related(
        'norm_version__norm', 'wire_material', 'insulation_type'
    ).all()
    serializer_class = ConductorCatalogSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        qs = super().get_queryset()
        norm_version_id = self.request.query_params.get('norm_version')
        if norm_version_id:
            qs = qs.filter(norm_version_id=norm_version_id)
        material = self.request.query_params.get('material')
        if material:
            qs = qs.filter(wire_material__material_name__icontains=material)
        min_ampacity = self.request.query_params.get('min_ampacity')
        if min_ampacity:
            qs = qs.filter(ampacity_30c__gte=min_ampacity)
        return qs.order_by('ampacity_30c')


class BreakerCatalogViewSet(viewsets.ReadOnlyModelViewSet):
    """Catálogo de breakers con filtrado por polos y amperaje mínimo."""

    queryset = BreakerCatalog.objects.select_related('norm_version__norm').all()
    serializer_class = BreakerCatalogSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        qs = super().get_queryset()
        norm_version_id = self.request.query_params.get('norm_version')
        if norm_version_id:
            qs = qs.filter(norm_version_id=norm_version_id)
        poles = self.request.query_params.get('poles')
        if poles:
            qs = qs.filter(poles=poles)
        min_ampacity = self.request.query_params.get('min_ampacity')
        if min_ampacity:
            qs = qs.filter(ampacity__gte=min_ampacity)
        return qs.order_by('poles', 'ampacity')


class LoadTypeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = LoadType.objects.all()
    serializer_class = LoadTypeSerializer
    permission_classes = [AllowAny]
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'category', 'code']

    def get_queryset(self):
        qs = super().get_queryset()
        category = self.request.query_params.get('category')
        if category:
            qs = qs.filter(category__icontains=category)
        return qs


class MaterialCatalogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = MaterialCatalog.objects.select_related('unit_measure').all()
    serializer_class = MaterialCatalogSerializer
    permission_classes = [AllowAny]
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'sku']


# ---------------------------------------------------------------------------
# MÓDULO 3 — PROYECTOS Y ESTRUCTURA ELÉCTRICA
# ---------------------------------------------------------------------------

class ProjectViewSet(TenantFilterMixin, viewsets.ModelViewSet):
    """
    CRUD completo de proyectos eléctricos.

    - GET    /api/v1/projects/          Lista paginada de proyectos del tenant.
    - POST   /api/v1/projects/          Crea proyecto + parámetros técnicos.
    - GET    /api/v1/projects/{id}/     Detalle completo con zonas, tableros y circuitos.
    - PATCH  /api/v1/projects/{id}/     Actualización parcial.
    - DELETE /api/v1/projects/{id}/     Soft delete (cambia status a 'archived').
    """

    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at', 'status']
    ordering = ['-created_at']

    def get_queryset(self):
        qs = Project.objects.select_related(
            'tenant', 'user', 'norm_version__norm',
            'voltage_level', 'phase_config', 'parameters',
        ).filter(deleted_at__isnull=True)
        return self.get_tenant_queryset(qs)

    def get_serializer_class(self):
        if self.action == 'list':
            return ProjectListSerializer
        if self.action in ('create', 'update', 'partial_update'):
            return ProjectWriteSerializer
        return ProjectDetailSerializer

    def perform_create(self, serializer):
        # En Sesión 6 se asignará desde request.user cuando haya JWT
        serializer.save()

    def destroy(self, request, *args, **kwargs):
        """Soft delete: archiva el proyecto en lugar de eliminarlo."""
        project = self.get_object()
        from django.utils import timezone
        project.deleted_at = timezone.now()
        project.status = 'archived'
        project.save(update_fields=['deleted_at', 'status', 'updated_at'])
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['get'], url_path='summary')
    def summary(self, request, pk=None):
        """
        Resumen técnico del proyecto: totales de carga por tablero,
        estado de cumplimiento y conteo de alertas.
        """
        project = self.get_object()
        panels = project.panels.prefetch_related('circuits__calculation', 'circuits__loads').all()

        panel_data = []
        for panel in panels:
            total_circuits = panel.circuits.count()
            compliant = panel.circuits.filter(calculation__is_compliant=True).count()
            non_compliant = panel.circuits.filter(calculation__is_compliant=False).count()
            pending = total_circuits - compliant - non_compliant
            panel_data.append({
                'panel_id': str(panel.id),
                'panel_name': panel.name,
                'total_circuits': total_circuits,
                'compliant': compliant,
                'non_compliant': non_compliant,
                'pending_calculation': pending,
            })

        return Response({
            'project_id': str(project.id),
            'project_name': project.name,
            'status': project.status,
            'panels': panel_data,
        })

    @action(detail=True, methods=['post'], url_path='calculate')
    def calculate(self, request, pk=None):
        """
        Ejecuta el motor de cálculo eléctrico sobre todos los circuitos del proyecto.
        Persiste los resultados de cálculo, alertas, históricos y recalcula la BOM.
        """
        from .services import ElectricalEngineService
        project = self.get_object()
        user = request.user if request.user and request.user.is_authenticated else None

        try:
            results = ElectricalEngineService.calculate_project(project.id, user)
            return Response(results, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error calculating project {project.id}: {str(e)}", exc_info=True)
            return Response(
                {"error": f"Fallo al calcular el proyecto: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )


class ZoneViewSet(TenantFilterMixin, viewsets.ModelViewSet):
    queryset = Zone.objects.select_related('project').all()
    serializer_class = ZoneSerializer

    def get_queryset(self):
        qs = Zone.objects.select_related('project').filter(project__deleted_at__isnull=True)
        project_id = self.request.query_params.get('project')
        if project_id:
            qs = qs.filter(project_id=project_id)
        return qs


class ElectricalPanelViewSet(TenantFilterMixin, viewsets.ModelViewSet):
    """Tableros eléctricos con soporte de subtableros jerárquicos."""

    def get_queryset(self):
        qs = ElectricalPanel.objects.select_related('project', 'zone', 'parent_panel').filter(
            project__deleted_at__isnull=True
        )
        project_id = self.request.query_params.get('project')
        if project_id:
            qs = qs.filter(project_id=project_id)
        return qs

    def get_serializer_class(self):
        if self.action in ('list', 'retrieve'):
            return ElectricalPanelSerializer
        return ElectricalPanelWriteSerializer


class CircuitViewSet(TenantFilterMixin, viewsets.ModelViewSet):
    """Circuitos ramales con cargas y resultado de cálculo activo."""

    def get_queryset(self):
        qs = Circuit.objects.select_related(
            'panel__project', 'calculation'
        ).prefetch_related('loads').filter(
            panel__project__deleted_at__isnull=True
        )
        panel_id = self.request.query_params.get('panel')
        if panel_id:
            qs = qs.filter(panel_id=panel_id)
        project_id = self.request.query_params.get('project')
        if project_id:
            qs = qs.filter(panel__project_id=project_id)
        return qs

    def get_serializer_class(self):
        if self.action in ('list', 'retrieve'):
            return CircuitSerializer
        return CircuitWriteSerializer


class LoadViewSet(TenantFilterMixin, viewsets.ModelViewSet):
    """Cargas eléctricas con validación de potencia y factor de potencia."""

    serializer_class = LoadSerializer

    def get_queryset(self):
        qs = Load.objects.select_related(
            'circuit__panel__project', 'load_type'
        ).filter(circuit__panel__project__deleted_at__isnull=True)
        circuit_id = self.request.query_params.get('circuit')
        if circuit_id:
            qs = qs.filter(circuit_id=circuit_id)
        return qs


# ---------------------------------------------------------------------------
# MÓDULO 4 — HISTORIAL DE CÁLCULOS
# ---------------------------------------------------------------------------

class CalculationHistoryViewSet(TenantFilterMixin, viewsets.ReadOnlyModelViewSet):
    """
    Historial inmutable de cálculos por circuito.
    Solo lectura — los cálculos se crean únicamente mediante el endpoint
    /api/v1/circuits/{id}/calculate/ (disponible en Sesión 5).
    """

    serializer_class = CalculationHistorySerializer

    def get_queryset(self):
        qs = CalculationHistory.objects.select_related(
            'circuit__panel__project', 'created_by'
        ).prefetch_related('alerts').filter(
            circuit__panel__project__deleted_at__isnull=True
        ).order_by('-created_at')

        circuit_id = self.request.query_params.get('circuit')
        if circuit_id:
            qs = qs.filter(circuit_id=circuit_id)
        project_id = self.request.query_params.get('project')
        if project_id:
            qs = qs.filter(circuit__panel__project_id=project_id)
        return qs


# ---------------------------------------------------------------------------
# MÓDULO 5 — PRESUPUESTO Y MATERIALES
# ---------------------------------------------------------------------------

class BillOfMaterialsViewSet(TenantFilterMixin, viewsets.ModelViewSet):
    """
    Lista de materiales con precios congelados al momento de presupuestar.
    El precio unitario debe ingresarse explícitamente para garantizar
    la integridad histórica de la cotización.
    """

    serializer_class = BillOfMaterialsSerializer

    def get_queryset(self):
        qs = BillOfMaterials.objects.select_related(
            'project', 'material__unit_measure', 'circuit'
        ).filter(project__deleted_at__isnull=True)
        project_id = self.request.query_params.get('project')
        if project_id:
            qs = qs.filter(project_id=project_id)
        return qs


class BudgetViewSet(TenantFilterMixin, viewsets.ModelViewSet):
    """
    Presupuestos del proyecto con versionado automático.
    Cada nuevo presupuesto incrementa la versión automáticamente.
    """

    serializer_class = BudgetSerializer

    def get_queryset(self):
        qs = Budget.objects.select_related('project').prefetch_related('items').filter(
            project__deleted_at__isnull=True
        ).order_by('-created_at')
        project_id = self.request.query_params.get('project')
        if project_id:
            qs = qs.filter(project_id=project_id)
        return qs


class BudgetItemViewSet(TenantFilterMixin, viewsets.ModelViewSet):
    serializer_class = BudgetItemSerializer

    def get_queryset(self):
        qs = BudgetItem.objects.select_related('budget__project').filter(
            budget__project__deleted_at__isnull=True
        )
        budget_id = self.request.query_params.get('budget')
        if budget_id:
            qs = qs.filter(budget_id=budget_id)
        return qs


# ---------------------------------------------------------------------------
# MÓDULO 6 — DOCUMENTOS
# ---------------------------------------------------------------------------

class DocumentViewSet(TenantFilterMixin, viewsets.ReadOnlyModelViewSet):
    """Documentos generados por el sistema (solo lectura desde API)."""

    serializer_class = DocumentSerializer

    def get_queryset(self):
        qs = Document.objects.select_related('project').filter(
            project__deleted_at__isnull=True
        ).order_by('-generated_at')
        project_id = self.request.query_params.get('project')
        if project_id:
            qs = qs.filter(project_id=project_id)
        return qs
