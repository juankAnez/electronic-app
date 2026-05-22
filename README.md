# ElectroSmart Platform

ElectroSmart es una plataforma web inteligente de software como servicio (SaaS) diseñada para agilizar y optimizar el diseño, cálculo matemático y documentación de instalaciones eléctricas. El sistema permite realizar cálculos normativos con precisión de ingeniería, estructurar cargas por tableros y circuitos, validar caídas de tensión y balance de fases, y generar la documentación técnica y diagramas unifilares requeridos en proyectos residenciales y comerciales.

## Estructura del Repositorio

El repositorio se organiza bajo la siguiente estructura de directorios:

```
electronic-app/
├── backend/          # Servidor de API y lógica de negocio (Django)
│   ├── config/       # Configuración global del proyecto Django
│   ├── venv/         # Entorno virtual de Python (ignorado por Git)
│   ├── .env.example  # Plantilla de variables de entorno locales
│   └── requirements.txt
├── documentacion/    # Especificaciones, requerimientos y diseño del sistema
└── README.md
```

## Arquitectura del Proyecto

* **Backend:** Django 5.x y Django REST Framework (DRF), estructurado con soporte para bases de datos PostgreSQL.
* **Frontend:** React (planificado para la siguiente fase de desarrollo).

---

## Configuración y Ejecución del Backend

Para levantar el servidor de desarrollo local del backend, siga estos pasos:

### Requisitos Previos

* Python 3.10 o superior instalado en el sistema.
* PostgreSQL configurado localmente o acceso a un servidor de base de datos Postgres.

### Pasos de Instalación

1. **Navegar al directorio del backend:**
   ```bash
   cd backend
   ```

2. **Crear y activar el entorno virtual:**
   * En Windows:
     ```bash
     python -m venv venv
     .\venv\Scripts\activate
     ```
   * En macOS / Linux:
     ```bash
     python3 -m venv venv
     source venv/bin/activate
     ```

3. **Instalar dependencias:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configurar variables de entorno:**
   * Copie el archivo `.env.example` y nombre la copia como `.env`.
   * Complete las credenciales de conexión de su base de datos PostgreSQL local en el archivo `.env`.

### Verificación y Ejecución

* **Comprobar la configuración del sistema:**
  ```bash
  python manage.py check
  ```
  Debería obtener un mensaje indicando que no se han detectado problemas.

* **Ejecutar servidor de desarrollo:**
  ```bash
  python manage.py runserver
  ```
  El servidor estará disponible en la dirección local `http://127.0.0.1:8000/`.

---

## Documentación de Referencia

Para obtener detalles adicionales sobre el alcance, justificación y el diseño técnico del sistema, consulte los archivos dentro de la carpeta `documentacion/`:

* `Especificacion_Requerimientos.txt`: Resumen ejecutivo, alcance del MVP y requerimientos funcionales.
* `Diseno_Tecnico_y_Arquitectura.txt`: Diseño detallado del esquema de datos para la base de datos PostgreSQL y recomendaciones de visualización interactiva.
