# VISUAL SMOKE REPORT - Business Mini App

## Estado

`PASSED_AFTER_VISUAL_SMOKE_FIX`

Se ejecuto smoke visual local de la Mini App Negocio con Telegram Mini App simulado, auth mockeado, `surface=session` mockeado y endpoints de negocio mockeados.

## Bug encontrado y corregido

Durante el primer intento, el detalle de orden rompio la UI porque `formatOrderMethodLine` esperaba strings y el order detail puede entregar snapshots/objetos.

Correccion aplicada:

- `apps/web/src/constants/paymentLabels.ts` ahora acepta string u objeto/snapshot.
- Se elimino mojibake de labels como `Pago Movil`.
- `BusinessChatScreen` ya no muestra IDs internos de orden como `ord_001`.
- Referidos humaniza `active` como `Activo`.

## Capturas generadas

Carpeta:

`output/playwright/business-smoke/`

Capturas finales:

- `01-dashboard.png`
- `02-ads.png`
- `03-create-ad.png`
- `04-methods.png`
- `05-orders.png`
- `06-order-detail.png`
- `07-chat.png`
- `08-credits.png`
- `09-movements.png`
- `10-referrals.png`

Resumen JSON:

- `output/playwright/business-smoke/business-smoke-summary.json`

## Resultado del smoke

- Screenshots: `10`
- Console errors: `[]`
- Forbidden hits: `[]`

Terminos buscados en render:

- `B-08`, `B-09`, `B-10`, `B-11`, `B-12`, `B-13`, `B-15`, `B-16`, `B-17`
- `Ledger`
- `Referrals`
- `webhook firmado`
- `Checkout:`
- `payment_reported`
- `ord_001`
- `Estado: active`

Resultado: sin hits.

## Validacion tecnica final

- `corepack pnpm --filter @nodo/web build`: PASS
- `$env:PYTHONPATH='apps/api'; python -m pytest apps\api\tests -q`: PASS, `110 passed, 1 warning`
- `python -m ruff check apps\api scripts`: PASS
- `python -m compileall apps scripts`: PASS

## Veredicto

La Mini App Negocio ya tiene:

- superficie separada,
- gate por `surface/session`,
- pantallas capturables en smoke visual,
- copy sin IDs internos,
- sin leaks privados detectados en scans,
- formatter robusto para snapshots de metodos.

No es `READY_FOR_REAL_USE`; sigue pendiente smoke contra Telegram real, backend real, datos reales y deploy final.
