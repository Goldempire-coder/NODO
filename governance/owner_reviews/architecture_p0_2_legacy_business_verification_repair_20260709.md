# Architecture P0.2 Repair - Legacy Business Verification Endpoints Disabled

## Estado

PASSED_AFTER_FIX

## Problema reparado

Despues de cerrar `POST /api/v1/businesses`, quedaban endpoints legacy de verificacion/edicion de negocio que podian operar sin el gate canonico de Mini App Negocio:

- `PUT /api/v1/businesses/{id}`
- `POST /api/v1/businesses/{id}/verification-documents`
- `POST /api/v1/businesses/{id}/submit-verification`

Estos endpoints pertenecen al flujo historico de self-onboarding de negocio. La arquitectura actual exige Bot Registro Negocios + Admin Web + `business_access_links` + `GET /api/v1/surface/session`.

## Decision aplicada

Los endpoints legacy quedan bloqueados en runtime real.

Solo pueden ejecutarse como fixture interno de pruebas:

```txt
APP_ENV=test
X-NODO-Test-Fixture: business_create
```

Esto evita que una app, usuario o integracion externa use esos endpoints para mutar/verificar negocio fuera del flujo gobernado.

## Archivos modificados

- `apps/api/app/modules/businesses/routes.py`
- `apps/api/tests/test_business_verification.py`
- `scripts/local_smoke.py`
- `control_plane/06_API_CONTRACTS/BUSINESSES_API.md`
- `control_plane/09_SLICES/slice_02_business_verification/API_CONTRACT.md`

## Evidencia de codigo

- `apps/api/app/modules/businesses/routes.py:35` define el gate interno de fixture.
- `apps/api/app/modules/businesses/routes.py:40` devuelve `BUSINESS_SELF_ONBOARDING_DISABLED`.
- `apps/api/app/modules/businesses/routes.py:95` bloquea `PUT /businesses/{id}` sin fixture.
- `apps/api/app/modules/businesses/routes.py:112` bloquea upload de documentos sin fixture.
- `apps/api/app/modules/businesses/routes.py:134` bloquea submit-verification sin fixture.
- `apps/api/tests/test_business_verification.py:177` prueba que los tres endpoints legacy responden 403 sin fixture.

## Validacion ejecutada

```txt
$env:PYTHONPATH='apps/api'; python -m pytest apps\api\tests\test_business_verification.py -q
11 passed, 1 warning

$env:PYTHONPATH='apps/api'; python -m pytest apps\api\tests -q
133 passed, 1 warning

python -m ruff check apps\api scripts
All checks passed

python -m compileall apps\api scripts
OK

corepack pnpm --filter @nodo/web build
OK
```

## Alcance no tocado

- No cambie reglas de creditos.
- No cambie lifecycle de ordenes.
- No cambie chat/disputas.
- No cambie Mini App Cliente.
- No cambie Mini App Negocio.
- No cambie Admin Web.
- No hice deploy.
- No declare `READY_FOR_REAL_USE`.

## Siguiente punto recomendado

P0.3: separar o retirar del frontend compilado los modelos/pantallas legacy de verificacion de negocio que todavia contienen llamadas a esos endpoints, para que el codigo muerto no vuelva a confundirse con superficie activa.
