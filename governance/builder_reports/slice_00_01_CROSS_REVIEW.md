# CROSS_REVIEW - slice_00_foundation + slice_01_auth_telegram

Estado final: BLOCKED_BY_SECURITY_GAP

Fecha: 2026-07-03

## Alcance

Revision cruzada de la base acumulada:

- `slice_00_foundation`
- `slice_01_auth_telegram`

No se construyeron nuevas features. No se modifico codigo de producto.

## Archivos revisados

Contratos de datos:

- `control_plane/04_DATA/DATA_MODEL_MASTER.md`
- `control_plane/04_DATA/DATABASE_CONSTRAINTS.md`
- `control_plane/04_DATA/ENUMS_AND_STATUS_MASTER.md`
- `control_plane/04_DATA/INDEXES.md`
- `control_plane/09_SLICES/slice_00_foundation/DATA_CONTRACT.md`
- `control_plane/09_SLICES/slice_01_auth_telegram/DATA_CONTRACT.md`

Contratos API/seguridad:

- `control_plane/05_SECURITY/AUTH_TELEGRAM.md`
- `control_plane/05_SECURITY/RBAC_PERMISSION_MATRIX.md`
- `control_plane/05_SECURITY/SECURITY_CONTRACT_INDEX.md`
- `control_plane/05_SECURITY/SECRETS_POLICY.md`
- `control_plane/05_SECURITY/SENSITIVE_DATA_POLICY.md`
- `control_plane/05_SECURITY/RATE_LIMIT_POLICY.md`
- `control_plane/05_SECURITY/AUDIT_LOG_POLICY.md`
- `control_plane/06_API_CONTRACTS/API_OVERVIEW.md`
- `control_plane/06_API_CONTRACTS/AUTH_API.md`
- `control_plane/06_API_CONTRACTS/USERS_API.md`
- `control_plane/06_API_CONTRACTS/ERROR_CONTRACT.md`
- `control_plane/09_SLICES/slice_01_auth_telegram/SECURITY_CONTRACT.md`

Contratos UI:

- `control_plane/07_UI_UX/TELEGRAM_MINI_APP_RULES.md`
- `control_plane/07_UI_UX/MOTION_AND_INTERACTION.md`
- `control_plane/07_UI_UX/DESIGN_TOKENS.md`
- `control_plane/08_SCREENS/remitter/R-01_WELCOME_ENTRY.md`
- `control_plane/08_SCREENS/remitter/R-13_PROFILE.md`
- `control_plane/09_SLICES/slice_01_auth_telegram/UI_CONTRACT.md`

Implementacion/evidencia:

- `database/migrations/0001_slice_00_foundation.up.sql`
- `database/migrations/0002_slice_01_auth_telegram.up.sql`
- `apps/api/app/main.py`
- `apps/api/app/routes/health.py`
- `apps/api/app/routes/auth.py`
- `apps/api/app/routes/users.py`
- `apps/api/app/auth/telegram.py`
- `apps/api/app/auth/jwt.py`
- `apps/api/app/auth/dependencies.py`
- `apps/api/app/modules/users/repository.py`
- `apps/api/app/modules/users/service.py`
- `apps/api/app/repositories/database.py`
- `apps/api/app/repositories/redis.py`
- `apps/api/app/shared/rate_limit/in_memory.py`
- `apps/web/src/app/page.tsx`
- `apps/web/src/app/globals.css`
- `apps/web/src/app/layout.tsx`
- `apps/api/tests/test_foundation_http.py`
- `apps/api/tests/test_auth_telegram.py`
- `scripts/run_slice_00_tests.py`
- `scripts/run_slice_01_tests.py`
- `governance/builder_reports/slice_00_foundation_BUILDER_REPORT.md`
- `governance/builder_reports/slice_01_auth_telegram_BUILDER_REPORT.md`
- `evidence/slice_runs/slice_00_foundation_evidence.md`
- `evidence/slice_runs/slice_01_auth_telegram_evidence.md`
- `evidence/slice_runs/slice_00_foundation_test_results.json`
- `evidence/slice_runs/slice_01_auth_telegram_test_results.json`

## Pruebas ejecutadas

```powershell
corepack pnpm --filter @nodo/web build
```

Resultado: passed. Next.js compilo correctamente la ruta `/`.

```powershell
python scripts\run_slice_00_tests.py
```

Resultado: 6 passed, 0 failed.

```powershell
python scripts\run_slice_01_tests.py
```

Resultado: 6 passed, 0 failed.

```powershell
$env:PYTHONPATH='apps/api'; python -m pytest apps\api\tests -q
```

Resultado: 13 passed, 1 warning.

Warning: `StarletteDeprecationWarning` de `fastapi.testclient` por el stack instalado.

```powershell
python -m ruff check apps\api scripts
```

Resultado: All checks passed.

```powershell
python -m compileall apps/api scripts
```

Resultado: passed.

```powershell
rg -n "BOT_TOKEN|JWT_SECRET|JWT_REFRESH_SECRET|DATABASE_URL|REDIS_URL|SUPABASE_SERVICE_ROLE_KEY|123456:test-bot-token|test-access-secret|test-refresh-secret" apps/web/src apps/web/.next apps/web/package.json apps/web/next.config.mjs
```

Resultado: sin matches.

## Verificacion de migraciones acumuladas

OK:

- `users`, `audit_logs`, `job_runs` y `app_metadata` existen en `0001_slice_00_foundation.up.sql`.
- `sessions` existe en `0002_slice_01_auth_telegram.up.sql`.
- `users.telegram_id` es unique parcial cuando no es null.
- `users.role` permite `remitter`, `business_owner`, `admin`, `support`, `super_admin`.
- `users.role` no persiste `business`.
- `users.role` no persiste `guest`.
- `audit_logs` usa `resource_type/resource_id`, no `entity_type/entity_id`.
- `audit_logs.request_id` es obligatorio.
- `audit_logs` tiene triggers append-only.
- `sessions.refresh_token_hash` es unique not null.
- `sessions.status` valida `active`, `revoked`, `expired`.
- `sessions.revoked_at` es obligatorio cuando `status = revoked`.
- Indices requeridos para users, audit_logs, job_runs, app_metadata y sessions existen.

Conflicto operativo:

- La migracion `sessions` existe, pero el runtime de auth no escribe en PostgreSQL/Supabase. `apps/api/app/main.py` instancia `InMemoryUserRepository` y `InMemoryRateLimiter`, por lo que `users`, `sessions` y audit events de auth no quedan persistidos en las tablas contratadas.

## Verificacion de endpoints acumulados

OK:

- `GET /api/v1/health` existe en `apps/api/app/routes/health.py`.
- `GET /api/v1/ready` existe en `apps/api/app/routes/health.py`.
- `GET /api/v1/version` existe en `apps/api/app/routes/health.py`.
- `POST /api/v1/auth/telegram` existe en `apps/api/app/routes/auth.py`.
- `POST /api/v1/auth/refresh` existe en `apps/api/app/routes/auth.py`.
- `POST /api/v1/auth/logout` existe en `apps/api/app/routes/auth.py`.
- `GET /api/v1/users/me` existe en `apps/api/app/routes/users.py`.
- `apps/api/app/main.py` registra auth y users con prefijo `/api/v1`.

Observacion:

- Foundation mantiene tambien rutas health sin prefijo mediante `app.include_router(health_router)`. Esto no rompe el contrato acumulado porque las rutas canonicas `/api/v1/*` tambien existen.

## Prohibiciones

OK:

- No hay endpoint implementado `/auth/telegram-login`.
- No hay `session_revocations` implementado.
- No hay `entity_type/entity_id` en migraciones nuevas; solo aparecen en assertions de tests.
- No hay `business` como rol persistente en migraciones.
- No hay `guest` como rol persistente en migraciones.
- No se detectaron secretos backend en `apps/web/src`, `apps/web/.next`, `apps/web/package.json` ni `apps/web/next.config.mjs`.
- `public_user_payload` no expone `telegram_id`.
- Los tests verifican que raw `initData`, access token, refresh token y secretos de prueba no queden en audit/repository text.

## Seguridad

OK:

- `apps/api/app/auth/telegram.py` valida `initData` en backend.
- La firma Telegram usa HMAC y `hmac.compare_digest`.
- `initData` expirado devuelve `TELEGRAM_INIT_DATA_EXPIRED`.
- Hash invalido devuelve `TELEGRAM_INIT_DATA_INVALID`.
- Access token JWT incluye `exp` y usa TTL configurable, default 900 segundos.
- Refresh token se genera opaco con `secrets.token_urlsafe`.
- Refresh token se hashea antes de guardarse en el repositorio.
- Refresh rota `refresh_token_hash`.
- Logout marca session como `revoked` en el repositorio.
- Usuario `blocked` no puede login, refresh ni usar dependency autenticada.
- Audit events declarados/escritos: `user_created`, `user_login`, `user_logout`, `session_refreshed`, `auth_failed`.
- Error contract usa `{ error: { code, message, details }, request_id }` y no expone stack traces en respuestas.

Bloqueos:

1. `BLOCKED_BY_SECURITY_GAP`: sesiones/auth/audit no son durables.

   Evidencia:

   - `apps/api/app/main.py` usa `InMemoryUserRepository`.
   - `apps/api/app/modules/users/repository.py` guarda users y sessions en diccionarios.
   - `apps/api/app/modules/users/service.py` crea session con `create_session(...)`, pero esa operacion queda en memoria.
   - `apps/api/app/shared/audit/audit_service.py` guarda audit events en lista en memoria.
   - `apps/api/app/repositories/database.py` solo verifica conectividad; no hay repository SQL para users/sessions/audit.

   Impacto:

   - `refresh_token_hash` no queda persistido en la tabla `sessions`.
   - `revoked_at`, `last_used_at` y rotacion de refresh no sobreviven restart.
   - `user_created`, `user_login`, `user_logout`, `session_refreshed`, `auth_failed` no quedan en `audit_logs`.
   - Logout/revocacion no es durable.
   - La base acumulada no cumple completamente `AUTH_API.md`, `DATA_CONTRACT.md`, `AUDIT_LOG_POLICY.md` ni `SESSIONS` de `DATABASE_CONSTRAINTS.md`.

2. `BLOCKED_BY_SECURITY_GAP`: rate limit auth es in-memory, no Redis.

   Evidencia:

   - `apps/api/app/main.py` usa `InMemoryRateLimiter`.
   - `apps/api/app/shared/rate_limit/in_memory.py` implementa contadores en proceso.
   - `RATE_LIMIT_POLICY.md` exige usar Redis para contadores.

   Impacto:

   - El limite se pierde en restart.
   - No protege despliegues multi-proceso/multi-instancia.
   - No cumple plenamente el contrato de rate limit backend para auth.

3. `BLOCKED_BY_SECURITY_GAP`: enforcement RBAC/status para refresh no cubre todos los estados del contrato.

   Evidencia:

   - `RBAC_PERMISSION_MATRIX.md` permite refresh para remitter/business_owner solo con `user active/restricted`; admin/super_admin/support requieren `user active`.
   - `apps/api/app/modules/users/service.py` solo bloquea `user.status == "blocked"`.
   - `apps/api/app/auth/dependencies.py` solo bloquea `user.status == "blocked"`.

   Impacto:

   - Un usuario `dormant` podria refrescar si existe en repository.
   - Un admin/support restricted podria operar si el estado llega a existir.
   - El contrato de RBAC queda parcialmente aplicado.

## UI/Auth

OK:

- No hay landing comercial.
- La pantalla es una entry tecnica de auth/session state.
- Usa `@telegram-apps/sdk` para obtener `initData`.
- Usa `@telegram-apps/telegram-ui` para AppRoot, Button, Spinner y tipografia.
- Carga estilos de Telegram UI.
- Respeta `themeParams` via SDK y fallback a `window.Telegram.WebApp.themeParams`.
- Existe `AnimatedLogo`.
- Motion del logo dura 1100ms, dentro de 900ms-1400ms.
- No hay loop infinito declarado.
- Existe `prefers-reduced-motion`.
- Estados visibles: loading, error/retry, session expired, authenticated.

Observaciones:

- `R-13_PROFILE` solo queda cubierto por `GET /api/v1/users/me` y estado authenticated minimo; no se construyo pantalla `/profile`, lo cual es correcto para no expandir alcance.
- No se verifico visualmente dentro de cliente Telegram real; solo build Next y lectura de contrato/implementacion.

## Evidencia requerida

Existe:

- `governance/builder_reports/slice_00_foundation_BUILDER_REPORT.md`
- `governance/builder_reports/slice_01_auth_telegram_BUILDER_REPORT.md`
- `evidence/slice_runs/slice_00_foundation_evidence.md`
- `evidence/slice_runs/slice_01_auth_telegram_evidence.md`
- `evidence/slice_runs/slice_00_foundation_test_results.json`
- `evidence/slice_runs/slice_01_auth_telegram_test_results.json`

No hay `BLOCKED_BY_MISSING_EVIDENCE`.

## Riesgos residuales

Riesgos heredados aceptados temporalmente por owner:

- Falta ejecutar migraciones contra PostgreSQL/Supabase real.
- Falta readiness success contra Redis real.

Riesgos detectados en esta revision:

- Los tests actuales pasan, pero no verifican persistencia SQL real para auth/session/audit.
- Los tests actuales pasan, pero no verifican rate limit Redis.
- Los tests actuales no cubren usuario `dormant` ni diferencias de estado por rol para refresh/RBAC.
- `X-Request-Id` ausente se convierte en `request_id_unavailable`; `API_OVERVIEW.md` pide generarlo si no llega. No lo marco como bloqueo principal, pero debe corregirse antes de endurecer auditoria/API.

## Hay que corregir antes de slice 02

Si `slice_02_business_verification` va a depender de identidad, ownership, sesiones y audit logs durables, si: hay que corregir antes de avanzar.

Correcciones requeridas:

- Reemplazar `InMemoryUserRepository` por repository DB-backed para `users` y `sessions`, o introducir una capa repository que use PostgreSQL/Supabase en runtime normal y deje in-memory solo para tests.
- Persistir audit events auth en `audit_logs` con `resource_type/resource_id` y `request_id`.
- Implementar rate limit auth con Redis o documentar un contrato temporal aprobado por owner que permita in-memory solo en local/test.
- Endurecer status/RBAC de refresh/auth dependency para respetar `RBAC_PERMISSION_MATRIX.md`.
- Agregar tests que fallen si auth/session/audit no usan persistencia contratada.

## Estado final

BLOCKED_BY_SECURITY_GAP
