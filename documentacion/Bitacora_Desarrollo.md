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
| Estructura de repositorio | COMPLETADO |
| Configuración de entorno backend | COMPLETADO |
| Diseño y selección de base de datos | COMPLETADO |
| Modelos Django ORM (core) | COMPLETADO |
| API REST (serializers + viewsets) | COMPLETADO |
| Motor de cálculo eléctrico | PENDIENTE |
| Frontend React | PENDIENTE |
| Pruebas y QA | PENDIENTE |

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

## PRÓXIMAS SESIONES PLANIFICADAS

### Sesión 5 — Motor de cálculo eléctrico
- Crear módulo `core/engine/` con el motor de cálculo puro (sin Django, sin base de datos).
- Implementar las fórmulas:
  - Corriente de diseño: I = P / (V · FP) para cargas monofásicas.
  - Corriente de diseño trifásica: I = P / (√3 · V · FP).
  - Factor de demanda y corrección por carga continua (125%).
  - Selección de calibre de conductor por ampacidad con corrección por temperatura y agrupamiento.
  - Selección de breaker: Breaker >= 1.25 · I_diseño para cargas continuas.
  - Caída de tensión: ΔV% = (2 · ρ · L · I) / (S · V) · 100 (para sistemas monofásicos).
- Crear endpoint `POST /api/v1/projects/{id}/calculate/` que dispara el motor.

### Sesión 6 — Autenticación JWT y multi-tenant
- Instalar `djangorestframework-simplejwt`.
- Implementar endpoints de login/refresh/logout.
- Crear middleware de contexto de tenant para inyectar `tenant_id` en cada request.

### Sesión 7 — Frontend React (inicio)
- Inicializar proyecto con Vite + React + TypeScript.
- Instalar dependencias de UI: Tailwind CSS, shadcn/ui, React Flow, React PDF.
- Crear estructura de carpetas y rutas principales.

---

> Este documento se actualiza al finalizar cada sesión de desarrollo.
