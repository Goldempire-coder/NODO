# AUTHENTICATION_LIFECYCLE_AUDIT_OWNER_AUDIT

Fecha: 2026-07-11
Estado: PASSED_AFTER_OWNER_AUDIT_FIX_WITH_LIMITS
Decision: AUTHENTICATION READY WITH LIMITS

## Alcance auditado

Se reviso el resultado del builder para el ciclo de vida de autenticacion:

- Mini App Cliente: Telegram initData -> auth backend -> access token + refresh token -> refresh automatico.
- Mini App Negocio: auth Telegram + gate backend por `/api/v1/surface/session` y `X-NODO-Surface: business_mini_app`.
- Admin Web: superficie separada sin Telegram SDK, con validacion de sesion contra `/api/v1/users/me` y `X-NODO-Surface: admin_web`.
- Backend auth: refresh, logout, session rotation y tests de ciclo de vida.

No se revisaron flujos visuales E2E reales en navegador, multi-tab real, offline real, deploy ni staging real.

## Hallazgos corregidos

### AUTH-P1-001 - Admin Web no podia recuperar una sesion con access token expirado y refresh token valido

Impacto:

- El builder reporto que Admin Web podia aceptar un payload con refresh token.
- En la practica, el formulario validaba `/api/v1/users/me` antes de guardar provisionalmente el refresh token.
- Si el access token venia expirado, `apiRequest` no tenia refresh token disponible y la sesion fallaba aunque fuera renovable.
- Si el refresh ocurria durante la validacion, existia riesgo de reescribir la sesion final con el access token viejo.

Fix:

- `apps/web/src/screens/auth/AdminWebEntryPage.tsx`
- Si el payload trae `refreshToken`, se guarda una sesion provisional antes de validar.
- Luego de `/users/me`, se lee la sesion validada desde storage para conservar el access token renovado.
- El workspace admin recibe `validatedSession.accessToken`.

Validacion:

- `apps/api/tests/test_auth_lifecycle_static.py` comprueba el flujo esperado en Admin Web.
- `python -m pytest apps\api\tests\test_auth_telegram.py apps\api\tests\test_auth_lifecycle_static.py -q --tb=short` -> `20 passed, 1 warning`.

### AUTH-P1-002 - Logout dependia de un access token valido para revocar la sesion backend

Impacto:

- Si el access token expiraba pero el refresh token seguia vivo, el frontend podia limpiar estado local, pero `/auth/logout` fallaba por auth antes de revocar la sesion backend.
- Eso dejaba el refresh token activo hasta expiracion natural.

Fix:

- `apps/api/app/routes/auth.py`
- `apps/api/app/modules/users/service.py`
- `/api/v1/auth/logout` ahora revoca por refresh token, sin depender de `require_current_user`.
- Si encuentra la sesion, carga el usuario asociado para auditar; si no lo encuentra, responde idempotentemente `logged_out: true`.

Validacion:

- `apps/api/tests/test_auth_telegram.py::test_logout_revokes_refresh_session_even_when_access_token_expired`
- El test fuerza `ACCESS_TOKEN_TTL_SECONDS=1`, espera expiracion, ejecuta logout y confirma que el refresh posterior falla con `SESSION_EXPIRED`.

## Validaciones ejecutadas

```text
python -m pytest apps\api\tests\test_auth_telegram.py apps\api\tests\test_auth_lifecycle_static.py -q --tb=short
20 passed, 1 warning

python -m pytest apps\api\tests -q --tb=short
201 passed, 1 warning

python -m ruff check apps\api scripts
All checks passed!

python -m compileall apps\api apps\web\src scripts
OK

corepack pnpm --filter @nodo/web build
OK
Route /: 1.52 kB, First Load JS 104 kB
```

Scans:

```text
Frontend source/build secret scan:
FRONTEND_SECRET_SCAN_CLEAN

Admin Web Telegram runtime scan:
ADMIN_WEB_TELEGRAM_SCAN_CLEAN

Auth evidence JWT value scan:
AUTH_EVIDENCE_JWT_VALUE_SCAN_CLEAN

Business Mini App surface gate scan:
apps/web/src/api/surface.ts usa /api/v1/surface/session con X-NODO-Surface: business_mini_app
apps/web/src/hooks/business-mini-app/useBusinessAccessModel.ts usa getBusinessSurfaceSession
```

Los matches de `refresh_token`, `access_token`, `storage_path`, `account_value` y nombres de secretos dentro de `authentication_lifecycle_audit_evidence.md` / `test_results.json` corresponden a comandos de scan escritos como evidencia, no a valores secretos reales.

## Riesgos residuales

- Admin Web sigue con autenticacion minima/manual. Para produccion plena necesita flujo admin first-party robusto, no solo pegar token o payload.
- El refresh token del frontend vive en `sessionStorage`; mejora el ciclo de sesion en staging, pero no es la postura ideal para Admin Web productivo. La postura final recomendada es cookie HttpOnly/SameSite/Secure para Admin Web.
- No se ejecuto E2E real de navegador para multiples pestanas, offline, segundo plano durante horas ni reapertura al dia siguiente.
- No se hizo deploy ni staging real.
- La cache corta de usuario autenticado puede mantener cambios de status/rol por una ventana breve segun TTL existente; no se modifico en esta auditoria.

## Veredicto

AUTHENTICATION READY WITH LIMITS.

El builder no quedo aprobado "porque paso tests"; quedo aprobado despues de corregir dos problemas reales de ciclo de vida y repetir validaciones. El sistema es mejor para staging y pruebas reales, pero Admin Web aun no debe considerarse autenticacion final de produccion.
