# QA.md

Required QA for `slice_06_business_order_ops`.

## Backend/API

- business list solo propias.
- business detail solo propia.
- business no ve orden ajena.
- confirm-payment desde `payment_reported` OK.
- confirm-payment desde estado invalido falla.
- confirm-payment consume creditos exactamente una vez.
- confirm-payment crea ledger `consume`.
- confirm-payment marca `payment_reports.status = accepted`.
- confirm-payment archiva anuncio con `ad.status = archived`.
- confirm-payment setea `payment_confirmed_at` y delivery deadlines.
- confirm-payment no marca delivered/completed.
- confirm-payment idempotente no doble consume.
- confirm-payment misma key payload distinto falla.
- reject-payment-report desde `payment_reported` OK.
- reject requiere reason.
- reject marca `orders.status = payment_rejected`.
- reject marca `payment_reports.status = rejected`.
- reject no consume creditos.
- reject mantiene creditos bloqueados.
- reject mantiene `ad.status = in_order`.
- mark-delivered desde `payment_confirmed` OK.
- mark-delivered desde estado invalido falla.
- mark-delivered setea `delivered_at` y auto-complete timers.
- mark-delivered no completa orden.
- no chat/dispute endpoints construidos.
- errores seguros sin stack traces, SQL, secretos, `storage_path`, `account_value` ni instrucciones completas.
- audit events.
- state events.

## Gates

- frontend build.
- runners 00-06.
- backend pytest acumulado.
- ruff.
- compileall.
- frontend secret/private scan.
- Builder report con comandos ejecutados y tests no ejecutados con razon.
