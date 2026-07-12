# slice_29A_cross_surface_functional_smoke - evidence

Estado: READY_FOR_OWNER_REVIEW

## Resultado

`scripts/local_surface_cross_smoke.py` fue ampliado y ejecutado correctamente.

Archivo principal de salida:

- `evidence/slice_runs/local_surface_cross_smoke_29A.json`

## Cobertura funcional

El smoke local recorrió:

- Cliente: términos, perfil, marketplace, orden, instrucciones, evidencia, reporte de pago, chat y soporte.
- Negocio: acceso por surface/session, anuncio, orden entrante, chat, confirmación de pago, ticket de soporte y compra Base USDC pendiente.
- Admin: dashboard, detalle de orden, audit logs, staff invite y soporte.
- Staff/soporte: permisos granulares, lista de tickets, asignación, respuesta, resolución y cierre.
- Bot negocio intake: start, contact, document, submit, admin list/detail.

## Checks sensibles

- `storage_path` no aparece en respuestas verificadas.
- `account_value` completo no aparece en detalle admin de orden.
- Compra Base USDC queda en `pending_payment`, sin acreditar créditos sin verificación on-chain.

## Validaciones ejecutadas

- `python scripts\local_surface_cross_smoke.py --output evidence\slice_runs\local_surface_cross_smoke_29A.json`: PASS
- `python -m ruff check scripts\local_surface_cross_smoke.py`: OK
- `python -m compileall scripts\local_surface_cross_smoke.py`: OK
- `python -m pytest apps\api\tests\test_support_ticket_center.py apps\api\tests\test_internal_staff_roles.py apps\api\tests\test_credits_referrals.py apps\api\tests\test_order_creation.py -q --tb=short`: `44 passed, 1 warning`

## Límites

No se corrió contra staging real ni UI visual. No hubo deploy. No se declaró `READY_FOR_REAL_USE`.
