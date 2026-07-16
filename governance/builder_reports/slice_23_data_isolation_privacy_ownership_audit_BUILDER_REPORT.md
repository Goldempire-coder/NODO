# BUILDER REPORT - slice_23_data_isolation_privacy_ownership_audit

## Estado final

DATA ISOLATION VERIFIED WITH LIMITS

No deploy. No READY_FOR_REAL_USE.

## Resumen

Se audito aislamiento de datos en superficies cliente, negocio, admin/staff, soporte, chat/disputas, creditos, storage privado, cache y serializers/presenters. Se encontro y corrigio un hallazgo real de aislamiento en soporte de negocio: un `business_owner` con `business_access_link` revocado podia leer un ticket de soporte de negocio por ID directo porque la visibilidad aceptaba `ticket.requester_user_id == user.id` antes de revalidar el access link activo.

## DATA_EXPOSURE_CRITICAL_FINDING contenido

- Recurso afectado: tickets de soporte con `scope=business_general` u otros tickets asociados a `business_id`.
- Endpoint afectado antes del fix: `GET /api/v1/support/tickets/{id}`; por extension, mensajes y adjuntos de ese ticket si el shortcut de visibilidad aplicaba.
- Datos expuestos: subject, mensajes, estado y metadatos seguros del ticket de soporte de negocio.
- Rol afectado: `business_owner` que abrio el ticket y luego perdio acceso por `business_access_link.status = revoked/suspended/blocked`.
- Causa raiz: `SupportService._ticket_visible_to_user` validaba primero `ticket.requester_user_id == user.id` y solo despues revisaba reglas de negocio; por eso el creador del ticket mantenia visibilidad aunque el link de negocio ya no estuviera activo.
- Reproduccion antes del fix: `test_business_support_ticket_detail_messages_and_attachments_require_active_access_link` fallo con `assert 200 == 404`.
- Contencion/fix: la regla de negocio ahora se evalua antes del shortcut de requester. Si el usuario es `business_owner` y el ticket tiene `business_id`, se llama a `_active_business_for_user`, que usa `evaluate_business_access`; si falla, el ticket no es visible.
- Prueba de correccion: la misma prueba pasa y exige 404 en detail, message y attachment cuando el access link esta revocado.

## Inventario de datos auditado

- Publico: marketplace ads activos, metodos display seguros, labels publicos.
- Privado cliente: perfil, telefono, ordenes propias, payment reports, chat, evidencia de pago.
- Privado negocio: business profile, payment methods internos, anuncios, ordenes entrantes, credit wallet/ledger/purchases, support tickets.
- Financiero: credit wallets, credit ledger, purchases, Base USDC tx metadata, payment instructions snapshots.
- Evidencia privada: business verification, payment evidence, credit proofs, message/support attachments, business intake documents.
- Administrativo: users, roles/status, business access links, staff profiles/permissions, audit logs, admin read models.
- Soporte: support tickets, support messages, support attachments, assignment/status events.
- Secreto: JWT secrets, bot tokens, DB/Redis URLs, service role keys, RPC keys. No deben salir a frontend/evidence sin redaccion.

## Validaciones de ownership revisadas

- Business access: `require_active_business_access` y `evaluate_business_access` cubren negocio aprobado + user active + link active.
- Orders business ops: usa `_approved_business_for_owner`, que delega en `require_active_business_access`.
- Ads business ops: usa `require_active_business_access`.
- Credits business ops: usa `_owner_business`, que delega en `require_active_business_access`.
- Chat/disputes: revalidan acceso de negocio con `evaluate_business_access`.
- Support: corregido para revalidar access link antes de permitir tickets de negocio.
- Staff/admin support: `require_staff_permission` mantiene enforcement backend.
- Storage: signed URLs pasan por endpoints con RBAC/ownership; `storage_path` queda interno.

## Archivos modificados

- `apps/api/app/modules/support/service.py`
- `apps/api/tests/test_support_ticket_center.py`
- `governance/builder_reports/slice_23_data_isolation_privacy_ownership_audit_BUILDER_REPORT.md`
- `evidence/slice_runs/slice_23_data_isolation_privacy_ownership_audit_evidence.md`
- `evidence/slice_runs/slice_23_data_isolation_privacy_ownership_audit_test_results.json`

## Tests agregados

- `test_business_support_ticket_detail_messages_and_attachments_require_active_access_link`

Este test cubre:

- business owner abre ticket de negocio.
- se revoca `business_access_link`.
- detail por ID directo devuelve 404.
- crear mensaje devuelve 404.
- subir adjunto devuelve 404.

## Validaciones ejecutadas

- `python -m pytest apps\api\tests\test_support_ticket_center.py::test_business_support_ticket_detail_messages_and_attachments_require_active_access_link -q --tb=short`
  - Antes del fix: FAILED, `200 != 404`.
  - Despues del fix: `1 passed, 1 warning`.
- `python -m pytest apps\api\tests\test_support_ticket_center.py -q --tb=short`
  - `7 passed, 1 warning`.
- `python -m pytest apps\api\tests\test_business_access_control.py apps\api\tests\test_internal_staff_roles.py -q --tb=short`
  - `10 passed, 1 warning`.
- `python -m pytest apps\api\tests\test_chat_disputes.py apps\api\tests\test_business_order_ops.py apps\api\tests\test_credits_referrals.py -q --tb=short`
  - `28 passed, 1 warning`.
- `python -m pytest apps\api\tests\test_admin_users_business_control.py apps\api\tests\test_api_input_validation_hardening.py -q --tb=short`
  - `11 passed, 1 warning`.
- `python -m pytest apps\api\tests -q`
  - `210 passed, 1 warning`.
- `python -m ruff check apps\api scripts`
  - `All checks passed!`
- `python -m compileall apps\api apps\web\src scripts`
  - OK.
- `corepack pnpm --filter @nodo/web build`
  - OK.

## Scans

- Frontend source/build scan for `storage_path`, `account_value`, DB/Redis/JWT/BOT tokens, private keys and seed phrases: no hits.
- Backend module/shared scan found only internal storage persistence, storage adapter implementation, masking/redaction helpers, and token type constants. No response exposure was found in the reviewed presenters.
- Governance/evidence scan contains historical commands and redacted values (`[REDACTED]`), not live secrets.

## Riesgos pendientes

- Esta auditoria fue local/estatica + pytest. No reemplaza DAST adversarial contra staging real ni pruebas multi-tab/browser con usuarios reales.
- No se hizo deploy ni validacion en servicios reales.
- La suite cubre muchos escenarios negativos, pero no todos los endpoints con fuzzing exhaustivo por combinatoria.

## Plan de respuesta ante exposicion similar

1. Preservar request id, actor id, recurso y evidencia del response.
2. Bloquear la ruta afectada o endurecer ownership check centralizado.
3. Agregar prueba negativa que falle antes del fix.
4. Corregir con error seguro 404/403 segun contrato.
5. Revisar audit logs para alcance temporal y actores.
6. Notificar owner con recurso, roles afectados y contencion.

## Confirmaciones

- No hice deploy.
- No declare READY_FOR_REAL_USE.
- No cambie reglas de negocio fuera de scope.
- No relaje seguridad.
- No toque migraciones.
- No toque frontend de producto.
