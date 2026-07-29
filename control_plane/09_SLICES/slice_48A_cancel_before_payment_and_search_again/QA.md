# Slice 48A QA

Estado: READY_FOR_VALIDATOR_REVIEW

## Backend

- Cliente cancela una orden propia `waiting_payment`.
- Motivo fuera del allowlist responde `VALIDATION_ERROR`.
- Instrucciones reveladas requieren confirmacion de no envio.
- `payment_reported` no permite cancelacion libre.
- Replay no duplica state event, liberacion ni notificacion.
- Capacidad se libera una sola vez.
- Anuncio vigente vuelve a `active`.
- Expiracion automatica mantiene su contrato.

## Frontend

- CTA visible: `Cancelar y buscar otro negocio`.
- La confirmacion advierte que solo debe usarse si no se envio el pago.
- Se elige un motivo allowlist.
- Solo el CTA de cancelacion queda ocupado.
- En exito se conserva el monto de la orden.
- La cache local se vacia antes de buscar.
- La nueva busqueda no muestra resultados viejos.
- Un error conserva la orden y permite reintentar.

## Admin Y Privacidad

- El detalle muestra `Cancelada antes de reportar pago.`
- La ausencia de reporte sigue visible.
- La notificacion al negocio no contiene datos privados.

## Comandos

```powershell
python -m pytest apps/api/tests/test_order_creation.py -k "slice_48a or cancel" -q --tb=short
python -m pytest apps/api/tests/test_jobs_notifications.py -k "slice_48a or slice_36a" -q --tb=short
python -m pytest apps/api/tests/test_auth_lifecycle_static.py -k "slice_48a" -q --tb=short
python -m pytest apps/api/tests/test_business_capacity_matching.py apps/api/tests/test_order_creation.py apps/api/tests/test_jobs_notifications.py -q --tb=short
python -m pytest apps/api/tests -q
python -m ruff check apps/api scripts
python -m compileall apps/api apps/web/src scripts
pnpm --filter @nodo/web build
git diff --check
```
