# SECURITY_CONTRACT.md

## Requisitos

- Backend RBAC obligatorio.
- Frontend no decide permisos.
- Ownership estricto por business_id.
- Stripe webhook requiere firma valida.
- Stripe secrets solo en backend runtime.
- No secrets Stripe en frontend, repo, logs ni respuestas.
- Webhook idempotente.
- Admin approve/reject/adjust requiere reason.
- Wallet no puede quedar negativa.
- Ledger append-only.
- Comprobantes manuales usan storage privado.
- `storage_path` nunca aparece en API/frontend/logs/audit.
- Rate limit en checkout, manual payment, referrals, admin approve/reject/adjust y webhook.

## Permisos

business_owner:

- ver wallet/ledger propio
- iniciar Stripe checkout propio
- crear pago manual propio
- ver referrals propios
- ver su codigo y resumen; el codigo recibido se captura en Business Intake

admin/super_admin:

- listar credit purchases
- aprobar/rechazar pagos manuales
- ajustar creditos con reason

support:

- read-only si endpoint admin lo expone
- no approve/reject/adjust

## Datos sensibles

- Manual proof no es publico.
- Manual payment reference/tx hash se muestra masked fuera de revision autorizada.
- Signed URL corta solo para admin/super_admin autorizado.
- Audit/logs no guardan comprobante completo, secrets, signed URLs ni storage keys.

Si falta algun control, detener con `BLOCKED_BY_SECURITY_GAP`.
