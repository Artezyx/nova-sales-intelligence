# NOVA Sales Intelligence

**CRM experimental con scoring explicable, asistencia de conocimiento y automatización con supervisión humana.**

Proyecto independiente de portafolio. Implementación original en Python, FastAPI, SQLAlchemy, scikit-learn y JavaScript nativo. No requiere claves externas, React, Node para ejecutar la interfaz, ni un servicio de IA de pago. Los datos y el entrenamiento de demostración son sintéticos. No se presenta como un producto comercial ni como un modelo de ventas validado.

## Estado de verificación

- Backend + ML: 32 pruebas aprobadas localmente con SQLite; ver `docs/test-results.txt` (cobertura de líneas, no garantía de seguridad).
- JavaScript: sintaxis comprobada con Node.
- Browser: dos pruebas E2E escritas. Intentos locales bloqueados por la política de navegación de Chromium; **no aprobaron**. Ver `docs/browser-results.txt`.
- PostgreSQL y Docker: configuración incluida, no ejecutada localmente.
- GitHub Actions: configurado, no ejecutado en GitHub.
- Integraciones Salesforce, HubSpot, Odoo, Atlas y Synapse: no implementadas en NOVA. Se puede integrar en una siguiente fase mediante sus APIs documentadas; actualmente es autónomo.

## Ejecutar en Windows (PowerShell)

Requiere Python 3.13. Desde esta carpeta:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
$env:NOVA_SECRET = (.\.venv\Scripts\python -c "import secrets; print(secrets.token_urlsafe(48))")
.\.venv\Scripts\python -m app.provision --org "Demo NOVA" --email "manager@nova.example" --demo
.\.venv\Scripts\python -m uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000
```

El aprovisionamiento solicita una contraseña de 12–128 caracteres. Inicia sesión con ella. No se incluyen contraseñas predeterminadas. Conserva el secreto de desarrollo de forma segura si necesitas mantener sesiones tras reinicios; no lo subas al repositorio. Para Linux/macOS usa `python3.13 -m venv .venv`, `.venv/bin/python` y `export NOVA_SECRET=$(...)`.

- Interfaz: http://127.0.0.1:8000
- API OpenAPI: http://127.0.0.1:8000/docs
- Salud: http://127.0.0.1:8000/health

El archivo SQLite `nova.db` se crea localmente. Puedes agregar otro usuario del mismo grupo con `--org "Demo NOVA" --email "analyst@nova.example" --role analyst`. El aprovisionamiento es administrativo, no hay registro público. Usa datos ficticios de demostración, no información personal real.

## Flujo de demostración

1. Inicia sesión con el responsable de Demo NOVA. El dashboard muestra indicadores y el rendimiento sintético del modelo.
2. Abre Prospectos, crea un registro o revisa los cinco ejemplos; puedes editar los atributos. El índice se calcula al consultar el registro.
3. Pulsa Explicar para ver los aportes de seis características al logit del modelo.
4. Pulsa Sugerir en un prospecto activo con permiso de contacto. La recomendación determinista aparece en Revisiones. Repetir la solicitud para la misma revisión no crea otra.
5. Aprueba como responsable; se crea una tarea interna. El analista no puede aprobar. Rechazar no crea tarea. Editar el prospecto invalida las recomendaciones pendientes; retirar el permiso cancela tareas abiertas.
6. Completa la tarea, consulta el asistente sobre objeciones de precio o seguimiento, y revisa Auditoría. No se envían mensajes.

## API y arquitectura

| Método | Ruta | Finalidad |
|---|---|---|
| POST | `/api/login` | JWT de 60 minutos |
| GET | `/api/me` | Identidad, organización, rol |
| GET/POST | `/api/leads` | Lista paginada y alta |
| PUT | `/api/leads/{id}` | Actualización con control de revisión |
| GET | `/api/dashboard` | Indicadores organizacionales |
| GET | `/api/model` | Métricas y versión del modelo |
| POST | `/api/leads/{id}/recommend` | Generar propuesta idempotente |
| GET | `/api/reviews` | Consultar propuestas |
| POST | `/api/reviews/{id}/decision` | Aprobación/rechazo de responsable |
| GET/PATCH | `/api/tasks`, `/api/tasks/{id}` | Consultar/actualizar tareas |
| POST | `/api/assistant` | Recuperar guía local y contexto opcional |
| GET | `/api/audit` | Registro para responsable |

Interfaz JS → FastAPI (JWT/RBAC) → SQLAlchemy → SQLite/PostgreSQL. Scoring y recuperación local se ejecutan en el proceso de API. No existen llamadas a modelos generativos remotos. Revisa `docs/ARCHITECTURE.md` y `docs/MODEL_CARD.md`.

## Ejecutar pruebas

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q tests/test_api.py tests/test_intelligence.py --cov=app --cov-report=term
python -m playwright install chromium
python -m pytest -q tests/test_browser.py
```

Opcional: define `CHROMIUM_PATH` para utilizar un Chromium instalado. Las pruebas usan bases de datos temporales independientes. `NOVA_SCREENSHOT` permite guardar una captura del dashboard durante la prueba E2E. El pipeline incluido ejecuta API y browser en trabajos distintos.

## Docker/PostgreSQL (configuración pendiente de prueba)

Crea `.env` con `NOVA_SECRET`, `POSTGRES_PASSWORD` y `NOVA_DATABASE_URL=postgresql+psycopg://nova:CONTRASENA@db:5432/nova` (utiliza una contraseña URL-safe o codificada correctamente). Luego:

```bash
docker compose up -d --build db
docker compose run --rm app python -m app.provision --org 'Demo NOVA' --email manager@nova.example --demo
docker compose up -d app
```

No uses contraseñas de ejemplo en producción. El esquema se crea con SQLAlchemy `create_all`; una aplicación real requiere migraciones versionadas, backups, control de concurrencia, gestión de secretos, TLS, rate limiting y pruebas con PostgreSQL. El puerto se publica únicamente en localhost.

## Alcance y limitaciones

Consulta `docs/AUDIT.md` para una valoración de competitividad y pendientes. No hay afirmaciones sobre empresas, usuarios reales, tasas de conversión o reducción comercial. El código es un proyecto técnico demostrativo, no experiencia laboral.
