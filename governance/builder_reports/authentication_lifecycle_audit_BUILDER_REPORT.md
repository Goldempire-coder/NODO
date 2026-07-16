# AUTHENTICATION LIFECYCLE AUDIT REPORT - NODO

## Estado final

AUTHENTICATION READY WITH LIMITS

No se declara READY_FOR_REAL_USE.

## Flujo real auditado

### Mini App Cliente

- Obtiene `initData` desde Telegram WebApp.
- Envía `POST /api/v1/auth/telegram`.
- Backend valida HMAC y expiración de Telegram initData.
- Backend emite JWT corto y refresh token opaco.
- Frontend guarda sesión en `sessionStorage` con scope `telegram`.
- APIs protegidas usan `Authorization: Bearer`.
- Si una llamada recibe 401, el frontend intenta `POST /api/v1/auth/refresh` una sola vez y reintenta.
- Si refresh falla, limpia sesión local.

### Mini App Negocio

- Usa el mismo login Telegram base.
- Entra por `?surface=business`, pero ese query param no autoriza.
- Debe validar `GET /api/v1/surface/session` con `X-NODO-Surface: business_mini_app`.
- Backend valida user active, role `business_owner`, business approved y `business_access_links.status = active`.
- Deniega por user/business/link suspended, revoked o blocked.

### Admin Web

- No importa Telegram SDK ni `useTelegramAuth`.
- Valida sesión contra backend con `GET /api/v1/users/me` y `X-NODO-Surface: admin_web`.
- Backend RBAC sigue siendo autoridad.
- Ahora puede usar payload de sesión con refresh si backend lo emite; el modo legacy de JWT pegado sigue sin refresh.
- Límite residual: falta un flujo admin first-party completo con sesión web endurecida/HttpOnly-cookie o equivalente.

### Bots Telegram

- Webhooks y tokens son separados por propósito.
- No emiten sesión de usuario.
- No autorizan negocio.
- Bot Registro Negocios captura intake; Admin/backend deciden.

## Problemas encontrados

1. Frontend no declaraba ni conservaba `refresh_token`.
   - Riesgo: access token expirado rompía UX y obligaba reauth completa.
   - Fix: `AuthResponse` incluye `refresh_token`; `useTelegramAuth` persiste sesión scoped.

2. `apiRequest` no tenía refresh centralizado.
   - Riesgo: 401 simultáneos podían generar fallos en cascada o logout prematuro.
   - Fix: helper de sesión con una sola promesa de refresh concurrente por superficie.

3. Rotación de refresh token no era atómica frente a replay/race.
   - Riesgo: dos refresh simultáneos con el mismo token podían emitir sesiones inconsistentes.
   - Fix: `rotate_session_if_current` compara el hash actual en la escritura y rechaza stale refresh.

4. Admin Web sigue sin auth web completa.
   - Riesgo: operación admin depende de sesión emitida fuera del panel y almacenamiento browser.
   - Estado: mitigado parcialmente con revalidación backend y refresh opcional; no es una solución final de producción.

## Cambios realizados

- Backend:
  - Rotación atómica de refresh en repositorio in-memory y Postgres.
  - `AuthService.refresh` rechaza refresh stale como `SESSION_EXPIRED`.
  - Tests nuevos para expiración, refresh, claims actualizados y replay/race.

- Frontend:
  - Nuevo gestor scoped de sesión en `apps/web/src/api/session.ts`.
  - `apiRequest` refresca una vez en 401 y reintenta.
  - Mini Apps guardan refresh token tras auth Telegram.
  - Admin Web puede validar payload de sesión con refresh y no arrastra Telegram runtime.

## Escenarios probados

- Access token expirado falla con `SESSION_EXPIRED`.
- Refresh token válido renueva access token y permite continuar.
- Refresh viejo/replay queda rechazado.
- Refresh usa rol/status actuales del usuario.
- Usuario dormant/restricted admin no puede refrescar/operar.
- Usuario bloqueado no puede login.
- Business Mini App usa `surface/session`.
- Admin Web no importa Telegram runtime.
- Tokens reales no aparecen en evidence/build por scan regex.

## Validación ejecutada

- `$env:PYTHONPATH='apps/api'; python -m pytest apps\api\tests -q`
  - Resultado: 200 passed, 1 warning.
- `python -m ruff check apps\api scripts`
  - Resultado: All checks passed.
- `python -m compileall apps\api apps\web\src scripts`
  - Resultado: OK.
- `corepack pnpm --filter @nodo/web build`
  - Resultado: OK.
- Scan frontend source/build:
  - Secret/storage/account/claims pattern: 0 hits.
- Scan token-value evidence/build:
  - JWT/access/refresh value regex: 0 hits.
- Scan Admin Web Telegram runtime:
  - 0 hits.

## Riesgos pendientes

- Admin Web todavía necesita un contrato/build futuro de login administrativo first-party y sesión web endurecida. La sesión pegada/manual no debe considerarse experiencia final de producción.
- Refresh token se guarda en `sessionStorage`, no en cookie HttpOnly. Esto evita persistencia larga en `localStorage`, pero sigue siendo accesible a JS si hubiera XSS.
- No se ejecutó browser E2E multi-tab real; se cubrió con pruebas backend y static assertions frontend.

## Recomendaciones para producción

- Crear slice de Admin Web Auth propio con sesión web segura, idealmente cookie HttpOnly/SameSite o mecanismo equivalente gobernado.
- Agregar E2E Playwright para refresh concurrente, multi-tab, offline/online y logout visual.
- Considerar revocación server-side de access token por `jti` para cierres inmediatos tras logout si el riesgo operativo lo exige.
