# 52B QA Contract

## Backend

- Listado devuelve solo summary, default 20 y maximo 50.
- Listado no contiene ledger, proof metadata, raw provider payloads ni valores
  completos de hash/wallet/direccion.
- Detalle relaciona compra y ledger por `related_credit_purchase_id`.
- Compra acreditada con ledger produce `matched`.
- Compra acreditada sin ledger produce `warning` y
  `CREDITED_WITHOUT_LEDGER` sin mutacion.
- `under_review`, `verification_failed` y `expired` producen estados claros.
- Ledger Memory/PostgreSQL pagina por `(created_at, id)` sin perdidas ni duplicados.
- Support conserva solo lectura permitida y no puede rechazar.
- `/reject` conserva reason e idempotencia para manual/on-chain en revision.

## Frontend

- Entrar a Admin no precarga compras.
- Entrar a Creditos carga solo una pagina.
- Detalle se solicita solo al pulsar `Detalle`.
- Cargar mas conserva filtro, bloquea doble carga y deduplica por id.
- Detalle tiene loading, error, estado vacio y scroll interno.
- No hay polling nuevo.
- UI no parsea cursores ni decide reconciliacion.

## Validacion requerida

- Pytest dirigido de creditos/Admin.
- PostgreSQL desechable para cursor estable y compra-ledger.
- Ruff y Compileall.
- Next production build.
- git diff --check y Secret Guard.
- Sin deploy, wallet real, fondos reales, staging ni produccion.
