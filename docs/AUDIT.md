# Auditoría técnica honesta

| Área | Resultado |
|---|---|
| API REST, validaciones y persistencia SQLite | Probadas localmente |
| ML supervisado y explicabilidad | Probados localmente; datos sintéticos |
| Aislamiento multiempresa, JWT, permisos | Casos funcionales aprobados; no pentest |
| Flujo revisión → tarea, deduplicación, consentimiento | Casos secuenciales aprobados |
| UI web | Implementada; sintaxis JS aprobada; E2E bloqueado |
| PostgreSQL/Docker | Configurados, no ejecutados |
| GitHub Actions | Configurado, no ejecutado |
| IA generativa, integraciones reales, escalabilidad | No implementadas o no verificadas |

## Prioridad de correcciones y ampliaciones
1. Ejecutar ambos jobs de CI; resolver errores reales del navegador. Probar PostgreSQL y Docker con migraciones Alembic y pruebas de concurrencia (incluida revocación de consentimiento concurrente).
2. Añadir límites de autenticación/solicitudes, revocación de sesiones, gestión de claves, políticas de retención y auditoría externa. Revisar OWASP y dependencias. El logout solo descarta el token del navegador; no invalida un token copiado antes de expirar.
3. Integrar con una cuenta CRM sandbox autorizada vía OAuth, definir contrato de datos y eventos para Atlas/Synapse y probar el flujo real. No hay conectores ahora.
4. Validar ML con datos reales autorizados, baseline simple, evaluación temporal y calibración. Añadir registro de experimentos y modelado de drift.
5. Pruebas de carga, métricas operativas, backups, recuperación, accesibilidad y despliegue reproducible. La búsqueda y agregación tienen límites documentados.

## Competitividad
- Junior Python/API: buen proyecto de demostración del backend; pendiente UI.
- Mid-level Python/CRM: potencial si se aprueban todos los pipelines y se demuestra integración real, seguridad y concurrencia.
- Senior AI/CRM o arquitecto: insuficiente actualmente. Un modelo sintético, cinco guías, ausencia de proveedores reales y falta de validación operativa no acreditan ese nivel.

No se ha realizado una prueba de penetración, auditoría independiente, ni validación empresarial. Los resultados de las pruebas no acreditan experiencia profesional.
