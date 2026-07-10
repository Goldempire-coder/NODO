# Architecture Review - Credits Memory Referrals Split

Status: PASSED_AFTER_REFACTOR

## Scope

Separacion quirurgica de referrals in-memory para alinear el repositorio de memoria con la separacion ya aplicada en Postgres.

No se cambiaron reglas de negocio, endpoints, payloads, frontend, migraciones, contratos, storage, servicios reales ni deploy.

## Archivos modificados

- `apps/api/app/modules/credits/memory_referrals.py`
- `apps/api/app/modules/credits/memory_repository.py`

## Cambio realizado

- Se creo `InMemoryReferralStore`.
- `InMemoryCreditRepository` conserva la interfaz publica y delega:
  - `get_or_create_referral_code`
  - `apply_referral_code`
  - `list_referral_events_for_business`
  - `_grant_referral_bonus_if_eligible`
- El store recibe callbacks para acceder a business repository, ledger values y credit wallet sin acoplarse al repositorio completo.
- Se corrigio un import muerto detectado por Ruff antes de cerrar el corte.

## Medicion despues del corte

- `memory_repository.py`: 181 lineas
- `memory_referrals.py`: 97 lineas
- `memory_purchases.py`: 151 lineas

Referencia de mejora:

- `memory_repository.py` estaba en 234 lineas antes de separar referrals.
- `memory_repository.py` estaba en 298 lineas antes de iniciar la limpieza de memoria.

## Validacion ejecutada

- `$env:PYTHONPATH='apps/api'; python -m pytest apps\api\tests\test_credits_referrals.py -q`
  - Resultado: `7 passed, 1 warning`
- `python -m ruff check apps\api\app\modules\credits apps\api\tests\test_credits_referrals.py`
  - Resultado: `All checks passed`
- `$env:PYTHONPATH='apps/api'; python -m pytest apps\api\tests -q`
  - Resultado: `133 passed, 1 warning`
- `python -m ruff check apps\api scripts`
  - Resultado: `All checks passed`
- `python -m compileall apps\api scripts`
  - Resultado: OK
- `corepack pnpm --filter @nodo/web build`
  - Resultado: OK

## Riesgo residual

`memory_repository.py` queda como orquestador in-memory de wallet/ledger y delega compras/referrals.

Siguiente corte recomendado: evaluar si `_credit_wallet` y helpers directos de wallet deben moverse a `memory_wallet.py`. No conviene forzar ese corte sin revisar primero si reduce complejidad real o solo crea archivos pequenos sin beneficio.
