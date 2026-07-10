# Architecture Review - Credits Memory Wallet Split

Status: PASSED_AFTER_REFACTOR

## Scope

Separacion quirurgica de wallet/ledger in-memory para que `memory_repository.py` deje de concentrar logica de wallet, compras y referrals.

No se cambiaron reglas de negocio, endpoints, payloads, frontend, migraciones, contratos, storage, servicios reales ni deploy.

## Archivos modificados

- `apps/api/app/modules/credits/memory_wallet.py`
- `apps/api/app/modules/credits/memory_repository.py`

## Cambio realizado

- Se creo `InMemoryCreditWalletStore`.
- `InMemoryCreditRepository` conserva su interfaz publica y delega:
  - `ensure_wallet`
  - `get_wallet`
  - `list_ledger`
  - `adjust_wallet`
- La logica interna de acreditar/debitar wallet y crear ledger paso a `InMemoryCreditWalletStore.credit_wallet`.
- La busqueda de ledger de purchase paso a `InMemoryCreditWalletStore.ledger_for_purchase`.
- `InMemoryCreditRepository` ahora queda como fachada/orquestador de stores in-memory:
  - wallet
  - purchases
  - referrals

## Medicion despues del corte

- `memory_repository.py`: 113 lineas
- `memory_wallet.py`: 94 lineas
- `memory_purchases.py`: 151 lineas
- `memory_referrals.py`: 97 lineas

Referencia de mejora:

- `memory_repository.py` estaba en 181 lineas antes de separar wallet.
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

## Observacion

Intentos iniciales de ejecutar archivos `test_credits.py`, `test_credits_admin.py` y `test_credits_manual_payments.py` fallaron porque esos archivos no existen en este repo. Se corrigio la validacion usando el archivo real `test_credits_referrals.py` y luego el suite completo.

## Resultado arquitectonico

El repositorio in-memory de creditos ya no es Frankenstein. Quedo separado por responsabilidad:

- `memory_repository.py`: fachada de repositorio.
- `memory_wallet.py`: wallet y ledger in-memory.
- `memory_purchases.py`: compras de creditos in-memory.
- `memory_referrals.py`: codigos/eventos/bonus de referral in-memory.

## Riesgo residual

El proximo candidato de lectura es `credits/service.py` porque sigue en 345 lineas. Ya tiene serializers separados, pero puede contener handlers de caso de uso que valga la pena dividir. No debe tocarse sin leer primero rutas, dependencias y tests.
