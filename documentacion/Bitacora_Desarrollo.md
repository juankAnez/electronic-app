# BITÁCORA DE DESARROLLO — ELECTROSMART PLATFORM
================================================================================
Proyecto: ElectroSmart Platform (EDP)
Repositorio: https://github.com/[usuario]/sistema-electrico
Stack: Django 5.x · Django REST Framework · PostgreSQL · React
================================================================================

---

## ESTADO GENERAL DEL PROYECTO

| Módulo | Estado |
|---|---|
| Estructura de repositorio | ✅ COMPLETADO |
| Configuración de entorno backend | ✅ COMPLETADO |
| Diseño y selección de base de datos | ✅ COMPLETADO |
| Modelos Django ORM (core) | ✅ COMPLETADO |
| API REST (serializers + viewsets) | ✅ COMPLETADO |
| Motor de cálculo eléctrico (pipeline NEC) | ✅ COMPLETADO |
| Pruebas unitarias del motor (11 tests) | ✅ COMPLETADO |
| Pruebas de integración Django + API (1 test E2E) | ✅ COMPLETADO |
| Autenticación JWT y multi-tenant | ⏳ PENDIENTE (Sesión 6) |
| Frontend React | ⏳ PENDIENTE (Sesión 7) |

---

## SESIÓN 1 — Configuración Inicial del Proyecto
Fecha: 2026-05-22

### Lo que se realizó

**1. Inicialización del repositorio**
- Se clonó el repositorio base.
- Se creó el archivo `.gitignore` en la raíz del repositorio.
- Se estableció la estructura de directorios:
  ```
  electronic-app/
  ├── backend/           <- Proyecto Django
  ├── frontend/          <- React (fase futura)
  ├── documentacion/     <- Documentos técnicos
  └── README.md
  ```

**2. Configuración del entorno virtual Python**
- Se creó el entorno virtual `backend/venv`.
- Se instalaron las dependencias del backend:
  - `Django>=5.0`
  - `djangorestframework>=3.14.0`
  - `django-cors-headers>=4.3.0`
  - `psycopg2-binary>=2.9.9`
  - `python-dotenv>=1.0.1`

**3. Creación del proyecto Django**
- Se ejecutó `django-admin startproject config` dentro de `backend/`.
- Se configuró `config/settings.py` con:
  - Carga de variables de entorno desde `.env` mediante `python-dotenv`.
  - Conexión a PostgreSQL con fallback a SQLite.
  - Integración de `djangorestframework` y `django-cors-headers`.
  - Variables de entorno para SECRET_KEY, ALLOWED_HOSTS y CORS.

**4. Diseño y selección de base de datos**
- Se analizaron dos propuestas de diseño (`diseñodb1.txt` y `diseñodb2.txt`).
- Se seleccionó el **Diseño 2** como base, justificado por:
  - Arquitectura multi-tenant con usuarios globales y tabla pivote `user_tenant_roles`.
  - Separación de datos físicos del circuito vs. resultados de cálculo.
  - Trazabilidad completa mediante `calculation_history` con snapshots JSONB.
  - Precios congelados en el presupuesto para integridad de cotizaciones.
- Se aplicaron las siguientes mejoras al diseño:
  - Campo `phase_assignment` en `circuits` para balanceo trifásico.
  - Campos `voltage_v` y `power_factor` en `loads` para cálculo de corriente I=P/(V·FP).
  - DDL completo de `breaker_catalog` con curvas de disparo y capacidad de corte.
- Documento consolidado generado en: `diseño_db_final.txt`.

---

## SESIÓN 2 — Implementación de Modelos Django ORM
Fecha: 2026-05-22

### Lo que se realizó

**1. Creación de la aplicación Django `core`**
- La app `core` centraliza todos los modelos de dominio del sistema.
- Registrada en `INSTALLED_APPS` y configurado `AUTH_USER_MODEL = 'core.User'`.

**2. Implementación de `core/models.py`**

Los modelos se organizaron en 6 módulos siguiendo el diseño final de base de datos:

| Módulo | Modelos implementados |
|---|---|
| Identidad y acceso | `Tenant`, `User`, `Role`, `Permission`, `UserTenantRole`, `RolePermission` |
| Normas y catálogos | `Norm`, `NormVersion`, `VoltageLevel`, `PhaseConfig`, `WireMaterial`, `InsulationType`, `ConductorCatalog`, `BreakerCatalog`, `LoadType`, `MaterialUnitMeasure`, `MaterialCatalog` |
| Estructura eléctrica | `Project`, `ProjectParameter`, `Zone`, `ElectricalPanel`, `Circuit`, `Load` |
| Cálculos | `CircuitCalculation`, `CalculationHistory`, `CalculationAlert` |
| Presupuesto | `BillOfMaterials`, `Budget`, `BudgetItem`, `BudgetItemMaterial` |
| Documentos y auditoría | `Document`, `AuditLog` |

**3. Decisiones de diseño aplicadas en los modelos**
- Todas las PKs son `UUIDField(default=uuid.uuid4, editable=False)`.
- Se usa `DecimalField` para todos los valores eléctricos y monetarios (sin punto flotante).
- El modelo `User` extiende `AbstractUser` de Django para mantener compatibilidad con el sistema de autenticación nativo.
- Se definieron `Meta.ordering` y `Meta.verbose_name` en cada modelo para administración clara.
- Se aplicaron `CheckConstraints` y `UniqueConstraints` directamente en el ORM donde el DDL lo requería.

**4. Generación y aplicación de migraciones**
- Se ejecutó `python manage.py makemigrations core`.
- Se ejecutó `python manage.py migrate`.

---

## SESIÓN 3 — Admin de Django, Datos Semilla y Superusuarios
Fecha: 2026-05-22

### Lo que se realizó

**1. Registro en el panel de administración (`core/admin.py`)**
- Se registraron todos los modelos del dominio de negocio.
- Configuración de búsquedas, filtros y visualizaciones amigables para el operador.
- Seguridad: El modelo `AuditLog` se configuró como de solo lectura por diseño.

**2. Creación del comando de inicialización de datos (`seed_catalogs.py`)**
- Se creó un comando de Django Management (`python manage.py seed_catalogs`) para poblar la base de datos con los catálogos técnicos maestros:
  - Normas: NEC 2020 y RETIE 2013.
  - Catálogo de conductores de Cobre (calibres 14 AWG a 2/0 AWG en aislamiento THHN/THWN).
  - Breakers termo-magnéticos comerciales (capacidades de 15A a 100A, 1 y 2 polos).
  - Tipos de carga base: iluminación general, tomacorrientes de uso general, motores.
- El comando se ejecutó y pobló la base de datos PostgreSQL exitosamente.

**3. Creación de Superusuarios**
- Se crearon los primeros superusuarios administradores (`admin` y `janiez`) para gestionar el sistema desde `/admin`.

---

## SESIÓN 4 — API REST con Django REST Framework (DRF)
Fecha: 2026-05-22

### Lo que se realizó

**1. Serializadores de API (`core/serializers.py`)**
- Serializadores de solo lectura para catálogos maestros.
- CRUD completo para proyectos (`Project`) con creación anidada de parámetros técnicos.
- Serializadores para zonas, tableros, circuitos y cargas, incluyendo validación semántica.

**2. Vistas y Controladores de API (`core/views.py`)**
- ViewSets robustos con herencia de un mixin de filtrado automático por inquilino (`TenantFilterMixin`).
- Filtros por parámetros query e implementaciones optimizadas con `select_related` y `prefetch_related`.
- Acción personalizada `/summary` en proyectos para retornar métricas rápidas.

**3. Enrutamiento (`config/urls.py`)**
- Configuración del enrutamiento de la API utilizando `DefaultRouter` de DRF bajo el prefijo `/api/v1/`.

---

## SESIÓN 5 — Motor de Cálculo Eléctrico NEC
Fecha: 2026-05-23

### Lo que se realizó

#### 1. Arquitectura del motor (`core/engine/`)

Se implementó el motor de cálculo en Python puro, completamente desacoplado de Django y de la base de datos. El motor sigue el patrón **Pipeline + Immutable Context** con 8 etapas secuenciales:

```
CircuitInput (frozen dataclass)
     ↓
ElectricalEngineRunner (orquestador)
     ↓
1. NormalizationStage        → Valida parámetros de entrada
2. CurrentCalculationStage   → Calcula I_nominal e I_diseño (+25% continua)
3. CorrectionFactorsStage    → Factores de temperatura y agrupamiento
4. ConductorSelectionStage   → Selecciona calibre AWG mínimo por ampacidad
5. VoltageDropStage          → Calcula ΔV absoluta y porcentual
6. IterativeResizeStage      → Sube calibre si ΔV supera el límite configurado
7. BreakerSelectionStage     → Selecciona protección comercial
8. FinalValidationStage      → Consolida cumplimiento y genera alertas semáforo
     ↓
CircuitResult (frozen dataclass)
```

**Archivos creados:**

| Archivo | Propósito |
|---|---|
| `core/engine/domain.py` | Tipos puros: enums `SystemType`, `ConductorMaterial`, `InsulationType`; dataclasses `CircuitInput`, `CircuitResult`, `ConductorSpec`, `BreakerSpec`, `CircuitAlert`, `TraceEntry` |
| `core/engine/calculators.py` | Funciones matemáticas puras: `calculate_nominal_current()`, `calculate_design_current()`, `calculate_voltage_drop()`, `calculate_voltage_drop_percent()` |
| `core/engine/catalogs.py` | Tablas NEC: catálogo de conductores cobre/aluminio (NEC 310.16), factores de temperatura (NEC 310.15(B)(1)), factores de agrupamiento (NEC 310.15(C)(1)), breakers comerciales (NEC 240.6) |
| `core/engine/stages.py` | Implementación de las 8 etapas del pipeline |
| `core/engine/pipeline.py` | Clase `ElectricalEngineRunner` — orquestador de las etapas |

#### 2. Fórmulas eléctricas implementadas (según NEC)

| Cálculo | Fórmula | Referencia |
|---|---|---|
| I monofásica | `P / (V_ln × FP × η)` | NEC 220.14 |
| I trifásica | `P / (√3 × V_ll × FP × η)` | NEC 220.14 |
| I diseño (carga continua) | `I_nom × (1 + 0.25 × fracción_continua)` | NEC 210.19(A)(1) |
| Caída de tensión monofásica | `2 × L_km × I × (R·cosθ + X·sinθ)` | NEC Nota 210.19(A) |
| Caída de tensión trifásica | `√3 × L_km × I × (R·cosθ + X·sinθ)` | NEC Nota 210.19(A) |
| Caída porcentual | `(ΔV / V_referencia) × 100` | NEC Nota 210.19(A) |

> **Precisión**: Se usa el método de impedancia compleja `Z = R·cosθ + X·sinθ` (no el método simplificado `2RL`), con valores reales de resistencia AC y reactancia inductiva por km tomados de la Tabla 9 del NEC.

#### 3. Reglas normativas implementadas

| Regla NEC | Descripción | Implementación |
|---|---|---|
| NEC 110.14(C) | Límite de temperatura de terminales de equipos | `min(ampacidad_corregida, ampacidad_columna_75°C)` |
| NEC 210.19(A)(1) | Factor 125% para cargas continuas | `I_diseño = I_nom × (1 + 0.25 × fracción)` |
| NEC 240.4(B) | Regla next-size-up para breaker | `allow_next_size_up=True` con verificación < 800A |
| NEC 240.6(A) | Tamaños comerciales de breakers estándar | Lista: 15, 20, 25...200A |
| NEC 310.15(B)(1) | Corrección por temperatura ambiente | Tabla completa de -99°C a 80°C |
| NEC 310.15(C)(1) | Factor de reducción por agrupamiento | Tabla de 3 hasta 41+ conductores |

#### 4. Integración con Django ORM (`core/services.py`)

Se creó `ElectricalEngineService` que orquesta:
1. Carga de todos los circuitos del proyecto con sus cargas.
2. Construcción del objeto `CircuitInput` a partir de los datos ORM.
3. Ejecución del motor puro `ElectricalEngineRunner.calculate_circuit()`.
4. Mapeo de resultados a registros `ConductorCatalog` / `BreakerCatalog` via FK.
5. Persistencia atómica (transacción) de:
   - `CircuitCalculation` — resultado activo más reciente.
   - `CalculationHistory` — snapshot inmutable para auditoría y reproducibilidad.
   - `CalculationAlert` — alertas clasificadas (error/warning) por tipo normativo.
   - `BillOfMaterials` — entradas recalculadas con cable (metros + 10% desperdicio) y breaker (unidades).
   - `Budget` — presupuesto total del proyecto recalculado con subtotal sumado desde el BOM.
6. Actualización del `project.status` → `"calculated"`.

#### 5. Endpoint de cálculo (`core/views.py`)

```
POST /api/v1/projects/{project_id}/calculate/
Header: X-Tenant-ID: {tenant_uuid}
```
- Dispara `ElectricalEngineService.calculate_project()`.
- Respuesta JSON con resultados por circuito, corrientes, conductor, breaker, ΔV% y compliance.
- Manejo de errores con `HTTP 400` y mensaje descriptivo si falla el motor.

#### 6. Snapshot de auditoría por circuito

Cada `CircuitCalculation.parameters_snapshot` guarda un JSON completo con:
```json
{
  "inputs": { "power_watts", "power_factor", "length_m", "system_type", ... },
  "outputs": { "conductor_gauge", "breaker_ampacity", "voltage_drop_percent" },
  "trace": [
    { "stage": "CurrentCalculation", "rule_reference": "NEC 210.19(A)(1)", "details": {...} },
    ...
  ]
}
```
Este snapshot garantiza la **reproducibilidad total** del cálculo histórico.

#### 7. Archivos de pruebas API

- `backend/pruebas_api.http` — Pruebas REST Client básicas (VS Code), 15 endpoints documentados.
- `backend/pruebas_completo_backend.http` — Flujo completo end-to-end.
- `backend/bruno-collection/` — Colección Bruno exportada.

---

## SESIÓN 5 — QA: Resultados de Pruebas
Fecha: 2026-05-23

### Pruebas Unitarias del Motor (Python puro, sin Django)
**Archivo:** `core/engine/tests/test_engine.py`
**Resultado: ✅ 11/11 PASSED — 0.001s**

| Test | Descripción | Resultado |
|---|---|---|
| `test_current_calculations_single_phase` | I_nom=15A, I_diseño=18.75A (1800W/120V, 100% continua) | ✅ OK |
| `test_current_calculations_three_phase` | I_nom≈32.46A (10kW trifásico, FP=0.90, η=0.95) | ✅ OK |
| `test_terminal_limit_nec_110_14` | Cable 12 AWG limitado a columna 75°C, breaker 20A | ✅ OK |
| `test_iterative_resize_by_voltage_drop` | 60m → sube de 12AWG a 10AWG para cumplir ΔV < 3% | ✅ OK |
| `test_next_size_up_rule` | 22A → breaker 25A (sin necesitar next-size-up) | ✅ OK |
| `test_trace_auditing` | Traza con stages Normalization, CurrentCalculation, ConductorSelection | ✅ OK |
| `test_invalid_inputs_power` | Potencia=0 → alerta INVALID_POWER, is_compliant=False | ✅ OK |
| `test_invalid_inputs_voltage` | Voltaje=0 → alerta INVALID_VOLTAGE, is_compliant=False | ✅ OK |
| `test_extreme_temperature_failure` | T=85°C THHN → factor=0.00 → CONDUCTOR_NOT_FOUND | ✅ OK |
| `test_extreme_load_ampacity_failure` | 60kW@120V=500A supera todo el catálogo → error | ✅ OK |
| `test_voltage_drop_limit_warning` | 800m → selecciona 4/0AWG + warning VOLTAGE_DROP_EXCEEDED | ✅ OK |

### Prueba de Integración Django E2E
**Archivo:** `core/tests.py`
**Resultado: ✅ 1/1 PASSED — 0.582s**

| Test | Descripción | Resultado |
|---|---|---|
| `test_calculate_project_endpoint` | POST `/projects/{id}/calculate/` — valida motor, ORM, BOM y Budget | ✅ OK |

**Detalles del test E2E:**
- Carga: 1200W @ 120V, FP=0.90, continua → I_nom=11.111A, I_diseño=13.89A
- Conductor seleccionado: **14 AWG** (ampacidad 20A > 13.89A diseño) ✅
- Breaker seleccionado: **1P 15A** (15A ≥ 13.89A diseño, ≤ 20A ampacidad cable) ✅
- BOM generado: 2 ítems (cable metros + breaker unidad) ✅
- Presupuesto: subtotal > 0 ✅
- Historial: 1 entrada en `CalculationHistory` versión 1 ✅
- Traza JSON guardada en `parameters_snapshot` ✅

---

## PRÓXIMAS SESIONES PLANIFICADAS

### Sesión 6 — Autenticación JWT y Multi-Tenant
- Instalar `djangorestframework-simplejwt`.
- Implementar endpoints de login/refresh/logout.
- Crear middleware de contexto de tenant para inyectar `tenant_id` en cada request.
- Reemplazar `AllowAny` por `IsAuthenticated` en todos los ViewSets.
- Eliminar el filtrado manual por header `X-Tenant-ID` y usar el tenant del JWT.

### Sesión 7 — Frontend React (inicio)
- Inicializar proyecto con Vite + React + TypeScript.
- Instalar dependencias de UI: Tailwind CSS, shadcn/ui, React Flow, React PDF.
- Crear estructura de carpetas y rutas principales.
- Conectar con API REST del backend.

### Sesión 8 — Generación de Documentos PDF
- Implementar generación de memorias de cálculo en PDF.
- Implementar exportación de BOM y presupuesto en PDF/Excel.

---

> Este documento se actualiza al finalizar cada sesión de desarrollo.
> Última actualización: 2026-05-23 — Sesión 5 completada ✅
