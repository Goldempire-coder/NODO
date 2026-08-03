# NODO CONTROL PLANE

Paquete gobernado para construir NODO por slices con Cursor/Codex/Builder.

Estado: READY_FOR_BUILDER_DOCS v0.3
Fecha: 2026-07-03

Regla principal: ningun builder construye features sin contrato aprobado, evidencia de lectura y reporte de lineas tocadas.

## Producto objetivo

NODO es un directorio tecnologico para conectar remitentes con negocios registrados. NODO organiza perfiles, metodos publicados, reputacion, ordenes, chat, evidencias, creditos publicitarios y auditoria. NODO no recibe, retiene, transfiere ni garantiza fondos de usuarios; el pago y la entrega son responsabilidad entre remitente y negocio.

El producto se construye para uso masivo desde el inicio, no como demo. Capacidad minima de diseno: 200 negocios, 10,000 clientes y 2,000 ordenes activas/concurrentes bajo limites de riesgo, colas, locks, idempotencia y monitoreo.

## Stack aprobado

- Frontend: Next.js, TypeScript, Tailwind, Telegram Mini App SDK/UI.
- Backend: FastAPI, Python, servicios modulares, workers separados.
- Base de datos: PostgreSQL/Supabase con pooling, migraciones y RLS/claims donde aplique.
- Cache/colas/locks: Redis.
- Bot: Telegram webhook, no polling en produccion.
- Pagos de creditos: Stripe automatico como principal; Zelle y USDT TRC20 manual con revision admin.
- Deploy/staging aprobado: Cloudflare Pages para frontend, Railway para backend/workers, Supabase Pro para PostgreSQL, Upstash Redis para locks/rate limits/jobs y Cloudflare R2 o Supabase Storage para storage privado. Vercel queda legacy/no recomendado para NODO por costo de escala.

## Orden obligatorio de lectura

1. 00_GOVERNANCE/SOURCE_OF_TRUTH.md
2. 00_GOVERNANCE/PROJECT_STATUS.md
3. 00_GOVERNANCE/DECISION_LOG.md
4. 00_GOVERNANCE/BUILDER_RULES.md
5. 00_GOVERNANCE/CODE_ARCHITECTURE_MASTER.md
6. 01_PRODUCT/SPEC_MASTER.md
7. 02_TRUST_AND_DISCLAIMERS/REQUIRED_SCREEN_DISCLAIMERS.md
8. 03_DOMAIN_RULES/ORDER_LIFECYCLE_MASTER.md
9. 03_DOMAIN_RULES/CREDITS_AND_BILLING_MASTER.md
10. 04_DATA/DATA_MODEL_MASTER.md
11. 04_DATA/ENUMS_AND_STATUS_MASTER.md
12. 04_DATA/DATABASE_CONSTRAINTS.md
13. 05_SECURITY/RBAC_PERMISSION_MATRIX.md
14. 05_SECURITY/SECURITY_CONTRACT_INDEX.md
15. 05_SECURITY/SECURITY_MASTER.md
16. 06_API_CONTRACTS/API_OVERVIEW.md
17. 07_UI_UX/UI_UX_MASTER.md
18. 07_UI_UX/TELEGRAM_MINI_APP_RULES.md
19. 07_UI_UX/MOTION_AND_INTERACTION.md
20. 07_UI_UX/DESIGN_TOKENS.md
21. 07_UI_UX/VISUAL_REFERENCE.md
22. 07_UI_UX/SCREEN_LAYOUT_MASTER.md
23. 09_SLICES/SLICE_EXECUTION_MATRIX.md
24. 09_SLICES/SLICE_CONTRACTS_MASTER.md
25. El slice asignado en 09_SLICES/
26. Las pantallas afectadas en 08_SCREENS/
27. 10_QA/DEPLOY_READINESS_GATE.md
28. 10_QA/SECURITY_TESTS.md
29. 11_OPERATIONS/DEPLOYMENT_PLAN.md
30. 11_OPERATIONS/ENVIRONMENT_VARIABLES.md
31. 11_OPERATIONS/REAL_SERVICES_STAGING_SETUP.md
32. 11_OPERATIONS/MONITORING_ALERTS.md

## Regla de construccion

Cada slice debe entregar:

- migraciones y modelos
- repositorios separados
- servicios de dominio
- state machines
- endpoints
- permisos RBAC
- audit events
- jobs si aplica
- UI segun pantalla
- errores definidos
- tests de contrato, seguridad y flujo
- BUILDER_REPORT con archivos, lineas y evidencia

Si falta un contrato, el builder debe detenerse y reportar `BLOCKED_BY_MISSING_CONTRACT`. Si encuentra contradiccion entre documentos, debe detenerse y reportar `BLOCKED_BY_CONTRACT_CONFLICT`.
