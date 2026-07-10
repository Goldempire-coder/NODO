# BUILDER_REPORT - slice_01_auth_telegram

Estado final: READY_FOR_OWNER_REVIEW

## Resumen

Se construyo solo `slice_01_auth_telegram` sobre la base aceptada de `slice_00_foundation`.

No se declara `READY_FOR_REAL_USE`.

Riesgo residual heredado y mantenido:

- Falta ejecutar migraciones contra PostgreSQL/Supabase real.
- Falta readiness success contra Redis real.

## Archivos creados/modificados

Backend:

- `.env.example:11` agrega `BOT_TOKEN`.
- `.env.example:12` agrega `JWT_SECRET`.
- `.env.example:13` agrega `JWT_REFRESH_SECRET`.
- `.env.example:14` agrega max age de initData.
- `.env.example:15` agrega TTL de access token.
- `.env.example:16` agrega TTL de refresh token.
- `.env.example:17` agrega limite auth por ventana.
- `.env.example:18` agrega ventana rate limit.
- `apps/api/app/core/config.py:39` agrega settings auth opcionales.
- `apps/api/app/core/config.py:84` carga secretos auth solo desde backend env.
- `apps/api/app/core/errors.py:8` agrega errores auth Telegram.
- `apps/api/app/main.py:37` habilita POST en CORS.
- `apps/api/app/main.py:41` registra router auth bajo `/api/v1`.
- `apps/api/app/main.py:42` registra router users bajo `/api/v1`.
- `apps/api/app/auth/telegram.py:22` valida `initData` Telegram.
- `apps/api/app/auth/telegram.py:34` compara hash con `hmac.compare_digest`.
- `apps/api/app/auth/jwt.py:28` crea JWT access token corto.
- `apps/api/app/auth/jwt.py:67` crea refresh token opaco.
- `apps/api/app/auth/jwt.py:71` hashea refresh token.
- `apps/api/app/auth/dependencies.py:10` implementa dependency auth Bearer.
- `apps/api/app/modules/users/service.py:21` crea payload publico sin `telegram_id`.
- `apps/api/app/modules/users/service.py:46` aplica rate limit auth.
- `apps/api/app/modules/users/service.py:54` implementa login Telegram.
- `apps/api/app/modules/users/service.py:65` audita `auth_failed`.
- `apps/api/app/modules/users/service.py:113` audita `user_created`.
- `apps/api/app/modules/users/service.py:121` audita `user_login`.
- `apps/api/app/modules/users/service.py:136` implementa refresh.
- `apps/api/app/modules/users/service.py:159` audita `session_refreshed`.
- `apps/api/app/modules/users/service.py:173` implementa logout.
- `apps/api/app/modules/users/service.py:180` audita `user_logout`.
- `apps/api/app/modules/users/repository.py:89` rota session refresh hash.
- `apps/api/app/modules/users/repository.py:99` revoca session.
- `apps/api/app/routes/auth.py:26` expone `POST /api/v1/auth/telegram`.
- `apps/api/app/routes/auth.py:38` expone `POST /api/v1/auth/refresh`.
- `apps/api/app/routes/auth.py:45` expone `POST /api/v1/auth/logout`.
- `apps/api/app/routes/users.py:16` expone `GET /api/v1/users/me`.
- `apps/api/app/shared/audit/events.py:7` declara eventos auth.

Datos/migraciones:

- `database/migrations/0002_slice_01_auth_telegram.up.sql:1` crea `sessions`.
- `database/migrations/0002_slice_01_auth_telegram.up.sql:4` define `refresh_token_hash` unico.
- `database/migrations/0002_slice_01_auth_telegram.up.sql:14` define `sessions_status_check`.
- `database/migrations/0002_slice_01_auth_telegram.up.sql:15` exige `revoked_at` cuando status es `revoked`.
- `database/migrations/0002_slice_01_auth_telegram.up.sql:24` agrega index `(user_id, status, created_at desc)`.
- `database/migrations/0002_slice_01_auth_telegram.up.sql:27` agrega index parcial `access_token_jti`.
- `database/migrations/0002_slice_01_auth_telegram.up.sql:31` agrega index `expires_at`.
- `database/migrations/0002_slice_01_auth_telegram.down.sql:1` rollback de `sessions`.

Frontend:

- `apps/web/package.json:4` actualiza version a `0.0.0-slice-01`.
- `apps/web/src/app/layout.tsx:2` carga estilos de Telegram UI.
- `apps/web/src/app/page.tsx:4` usa Telegram UI kit.
- `apps/web/src/app/page.tsx:69` importa dinamicamente Telegram SDK.
- `apps/web/src/app/page.tsx:72` enlaza `themeParams` a CSS vars.
- `apps/web/src/app/page.tsx:76` obtiene `initData` con SDK.
- `apps/web/src/app/page.tsx:84` define `AnimatedLogo`.
- `apps/web/src/app/page.tsx:163` muestra `session loading`.
- `apps/web/src/app/page.tsx:181` muestra authenticated state.
- `apps/web/src/app/globals.css:108` anima logo en 1100ms.
- `apps/web/src/app/globals.css:129` respeta reduced motion.

Tests/evidencia:

- `apps/api/tests/test_auth_telegram.py:88` test initData valido.
- `apps/api/tests/test_auth_telegram.py:107` test hash invalido.
- `apps/api/tests/test_auth_telegram.py:117` test initData expirado.
- `apps/api/tests/test_auth_telegram.py:126` test usuario existente.
- `apps/api/tests/test_auth_telegram.py:142` test usuario bloqueado.
- `apps/api/tests/test_auth_telegram.py:155` test refresh rotation.
- `apps/api/tests/test_auth_telegram.py:179` test logout revoca.
- `apps/api/tests/test_auth_telegram.py:195` test `/users/me`.
- `apps/api/tests/test_auth_telegram.py:209` test no initData/tokens/secretos persistidos.
- `apps/api/tests/test_auth_telegram.py:232` test rate limit.
- `scripts/run_slice_01_tests.py:39` valida contrato de migracion.
- `scripts/run_slice_01_tests.py:67` valida rutas canonicas.
- `scripts/run_slice_01_tests.py:78` valida seguridad backend estatica.
- `scripts/run_slice_01_tests.py:96` valida audit events.
- `scripts/run_slice_01_tests.py:105` valida UI/motion.
- `scripts/run_slice_01_tests.py:121` valida secretos fuera del frontend.
- `evidence/slice_runs/slice_01_auth_telegram_test_results.json`
- `evidence/slice_runs/slice_01_auth_telegram_evidence.md`

## Contratos cumplidos

- Endpoint canonico `POST /api/v1/auth/telegram`.
- Endpoint canonico `POST /api/v1/auth/refresh`.
- Endpoint canonico `POST /api/v1/auth/logout`.
- Endpoint canonico `GET /api/v1/users/me`.
- No se uso `/auth/telegram-login`.
- Validacion backend de firma/hash Telegram con `BOT_TOKEN`.
- Rechazo de hash invalido.
- Rechazo de initData expirado.
- `telegram_id` no se expone en payload publico.
- No se guarda raw `initData`.
- Access token JWT corto.
- Refresh token opaco.
- Solo `refresh_token_hash` persistido.
- Refresh rota token.
- Logout revoca sesion.
- Usuario `blocked` no opera.
- Rate limit basico para auth.
- Audit events: `user_created`, `user_login`, `user_logout`, `session_refreshed`, `auth_failed`.
- `sessions` usa columnas e indices del contrato.
- UI minima `R-01_WELCOME_ENTRY` para entry/session state.
- UI usa Telegram SDK y Telegram UI kit.
- UI respeta `themeParams`.
- UI incluye `AnimatedLogo`.
- Motion de logo en 1100ms, sin loop infinito.
- Reduced motion implementado.

## Dependencias instaladas

No se instalaron dependencias nuevas durante `slice_01_auth_telegram`.

Dependencias existentes reutilizadas:

- `@telegram-apps/sdk`: registrado en `apps/web/package.json`; instalado actual `3.11.8`.
- `@telegram-apps/telegram-ui`: registrado en `apps/web/package.json`; instalado actual `2.1.13`.
- `Next.js`: registrado en `apps/web/package.json`; build uso `15.5.20`.
- FastAPI/pytest/httpx/ruff: registrados en `apps/api/requirements.txt`.

## Comandos ejecutados

```powershell
python -m compileall apps/api scripts
```

Resultado: passed.

```powershell
python scripts\run_slice_01_tests.py
```

Resultado: 6 passed, 0 failed.

```powershell
python scripts\run_slice_00_tests.py
```

Resultado: 6 passed, 0 failed.

```powershell
python -m ruff check apps\api scripts
```

Resultado: All checks passed.

```powershell
python -m pytest apps\api\tests -q
```

Resultado inicial: failed por `ModuleNotFoundError: No module named 'app'` sin `PYTHONPATH`.

```powershell
$env:PYTHONPATH='apps/api'; python -m pytest apps\api\tests -q
```

Resultado: 13 passed, 1 warning.

```powershell
corepack pnpm --filter @nodo/web build
```

Resultado: build passed.

```powershell
rg -n "BOT_TOKEN|JWT_SECRET|JWT_REFRESH_SECRET|DATABASE_URL|REDIS_URL|SUPABASE_SERVICE_ROLE_KEY|123456:test-bot-token|test-access-secret|test-refresh-secret" apps/web/.next
```

Resultado: sin matches.

## Tests no ejecutados y razon

- Migracion real contra PostgreSQL/Supabase: no ejecutada porque no hay credenciales/servicio real disponible en este contexto. Riesgo heredado aceptado por owner y mantenido.
- Readiness success contra Redis real: no ejecutado porque no hay Redis real disponible en este contexto. Riesgo heredado aceptado por owner y mantenido.
- Flujo visual dentro de cliente Telegram real: no ejecutado porque no hay sesion/cliente Telegram real ni BOT_TOKEN productivo. Se cubrio build frontend y path backend con initData firmado de prueba.

## Riesgos residuales

- La implementacion de repositorio de usuarios/sesiones es in-memory para este slice; la migracion `sessions` queda lista, pero persistencia real requiere conectar la capa repository a PostgreSQL/Supabase en un slice/hardening posterior.
- El rate limit es in-memory; suficiente para foundation/auth local, no distribuido.
- Hay warning de Starlette/TestClient por deprecacion del stack instalado; no bloquea los tests actuales.
- Tailwind reporta warning de utilities no detectadas porque la UI tecnica usa CSS local; no bloquea build.
- Se mantiene riesgo heredado de migraciones reales y Redis real.

## Que NO toque

- No construi business verification.
- No construi marketplace.
- No construi ordenes.
- No construi pagos.
- No construi creditos.
- No construi admin completo.
- No cambie reglas de negocio.
- No cambie estados/enums.
- No cambie disclaimers.
- No expuse Telegram ID como identificador publico.
- No guarde raw initData.
- No guarde refresh token plano.
- No use `session_revocations`.
- No use `READY_FOR_REAL_USE`.

## Estado final

READY_FOR_OWNER_REVIEW
