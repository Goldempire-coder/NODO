# slice_29A_cross_surface_functional_smoke - BUILDER_REPORT

Estado final: READY_FOR_OWNER_REVIEW

## Resumen

Se amplió el smoke funcional local para probar en un solo recorrido las superficies principales de NODO:

- Cliente Mini App backend.
- Negocio Mini App backend.
- Admin Web backend.
- Business intake bot.
- Soporte cliente/negocio/admin.
- Staff interno delegado.
- Compra de créditos Base USDC en estado `pending_payment`.

No se tocó producto de backend, frontend, migraciones, infraestructura ni deploy. El cambio fue solo en tooling local de verificación.

## Archivo modificado

- `scripts/local_surface_cross_smoke.py`

## Qué cubre ahora el smoke

1. Login Telegram simulado para admin, negocio, cliente y soporte.
2. Admin como `super_admin` crea staff `support_lead` con permisos granulares.
3. Cliente acepta términos, guarda perfil y consulta `me`.
4. Business intake bot crea solicitud, recibe contacto, adjunto y submit.
5. Admin lista y abre detalle de intake.
6. Negocio aprobado accede por `/api/v1/surface/session`.
7. Negocio crea anuncio con créditos.
8. Cliente busca marketplace y crea orden.
9. Cliente consulta instrucciones, sube evidencia y reporta pago.
10. Negocio ve orden, chatea y confirma pago.
11. Cliente y negocio intercambian mensajes.
12. Cliente crea ticket de soporte ligado a orden.
13. Negocio crea ticket de soporte ligado a anuncio.
14. Soporte/admin listan, asignan, responden, resuelven y cierran ticket.
15. Soporte no muta orden ni dominio al resolver.
16. Negocio inicia compra de créditos Base USDC sin verificación on-chain real.
17. Negocio no puede acceder a lista admin de credit purchases.
18. Admin dashboard, detalle de orden y audit logs cargan.
19. Scan de respuesta confirma que no aparece `storage_path` ni `account_value`.

## Evidencia

- `evidence/slice_runs/local_surface_cross_smoke_29A.json`

Resultado principal:

- `status`: `PASS`
- `business.confirm_status`: `payment_confirmed`
- `support.closed_status`: `closed`
- `base_usdc_credits.status`: `pending_payment`
- `sensitive_scan.storage_path_in_responses`: `false`
- `sensitive_scan.full_account_in_admin_order`: `false`

## Validaciones

- `python scripts\local_surface_cross_smoke.py --output evidence\slice_runs\local_surface_cross_smoke_29A.json`: PASS
- `python -m ruff check scripts\local_surface_cross_smoke.py`: OK
- `python -m compileall scripts\local_surface_cross_smoke.py`: OK
- `python -m pytest apps\api\tests\test_support_ticket_center.py apps\api\tests\test_internal_staff_roles.py apps\api\tests\test_credits_referrals.py apps\api\tests\test_order_creation.py -q --tb=short`: `44 passed, 1 warning`

## Límites

Este smoke es local/in-memory. No prueba:

- Telegram real.
- Navegador real.
- Cloudflare Pages.
- Railway staging real.
- Supabase Storage real.
- Base mainnet RPC real.
- Watcher on-chain acreditando créditos.
- UI visual end-to-end.

## Decisión

El flujo funcional base entre cliente, negocio, admin, soporte/staff y créditos Base USDC queda verificado localmente. El siguiente paso recomendado es llevar este mismo tipo de smoke a staging real con guardrails y cleanup, o abrir UI local/staging para revisar experiencia visual por superficie.

No se declaró `READY_FOR_REAL_USE`.
