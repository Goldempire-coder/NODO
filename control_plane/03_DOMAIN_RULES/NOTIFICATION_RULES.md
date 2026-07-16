# NOTIFICATION_RULES.md

## Slice 14 - Intake and support notifications

- Business intake submitted notifica a admin/support queue.
- Business intake accepted/rejected puede notificar al solicitante sin prometer aprobacion previa.
- Support ticket created/message/assigned/escalated/resolved/closed puede notificar a participantes autorizados.
- Support attachment uploaded/viewed no envia documento ni signed URL por notificacion; como maximo notifica metadata segura al participante autorizado.
- Notificaciones no deben incluir documentos completos, storage paths, signed URLs persistidas, tokens, secretos ni datos bancarios completos.

Canal principal: Telegram Bot.

Todas las notificaciones deben ser idempotentes por orden, tipo y ventana de tiempo para evitar spam.

## Eventos base

- order_created -> negocio
- payment_reported -> negocio
- payment_confirmed -> remitente
- payment_rejected -> remitente
- delivered -> remitente
- order_completed -> ambos
- order_cancelled -> ambos segun contexto
- order_expiring -> remitente
- credits_low -> negocio
- dispute_opened -> admin
- dispute_resolved -> partes
- credit_purchase_approved -> negocio
- onchain_credit_purchase_credited -> negocio
- manual_credit_payment_rejected -> negocio
- referral_bonus_granted -> negocio
- founder_access_expired -> negocio

## Timers de orden

### waiting_payment

- Al crear orden: mostrar timer de 30 minutos.
- Antes de expirar: recordar al remitente.
- Extension: permitir 15 minutos una sola vez.
- Al cancelar por tiempo: notificar que la orden expiro y que no se cobraron creditos al negocio.

### payment_reported

- Al reportar pago: notificar al negocio inmediatamente.
- A las 2 horas sin respuesta: recordar al negocio.
- A las 2 horas: alertar admin/support si negocio es nuevo o de riesgo.
- A las 6 horas sin respuesta: abrir disputa y notificar a remitente, negocio y admin.
- Slice 05 no construye jobs masivos de recordatorio/escalamiento.
- Slice 05 puede dejar el estado listo para notificacion posterior; los jobs masivos pertenecen a `slice_10_jobs_notifications`.
- Payloads de notificacion no deben incluir instrucciones completas, `account_value`, `storage_path`, tokens ni secretos.

### slice_07_chat_disputes

- `message_created` may notify the other party when enabled by future notification workers.
- `message_attachment_uploaded` may notify the other party only with metadata.
- `dispute_opened` notifies admin/support queue and both parties.
- `dispute_resolved` belongs to `slice_09_admin_console`, not slice 07 build.
- Notification payloads must not include full payment instructions, `account_value`, signed URLs, `storage_path`, tokens or secrets.

### slice_09_admin_console

- `dispute_resolved` may notify both parties after admin resolution.
- `dispute_marked_in_review` may notify both parties that admin review continues.
- `admin_viewed_metrics`, `admin_viewed_audit_logs` and dashboard reads do not notify users.
- Dispute resolution notifications must not promise refunds, escrow, guaranteed recovery, guaranteed delivery or that NODO holds funds.
- Payloads must not include full payment instructions, `account_value`, signed URLs, `storage_path`, tokens or secrets.

### slice_08_credits_referrals

- `credit_purchase_approved` puede notificar al negocio que los creditos publicitarios fueron acreditados.
- `onchain_credit_purchase_credited` puede notificar al negocio que una compra Base USDC fue acreditada despues de verifier y ledger exact-once.
- `manual_credit_payment_rejected` puede notificar rechazo con reason seguro/enmascarado.
- `referral_bonus_granted` puede notificar bonus acreditado sin exponer datos del negocio referido.
- `founder_access_expired` puede notificar que nuevas publicaciones requieren creditos disponibles.
- Stripe webhook notifications must be idempotent and must not include Stripe secrets, raw webhook payloads or signed URLs.
- Manual proof notifications must not include `storage_path` or signed URLs.
- Base USDC on-chain notifications may report safe status changes only: purchase created, tx detected, confirmations pending, credited, under review, rejected or expired.
- Bot/admin notification for on-chain credit purchases is informational only; it cannot approve, reject or credit.
- On-chain notification payloads must not include RPC keys, raw provider responses, private keys, seed phrases, full tx hashes in broad channels, `storage_path`, `account_value` or promises of recovery.
- Payloads de creditos/referrals no deben prometer fondos, escrow, garantia de entrega ni recuperacion de pagos.

### payment_rejected

- Al rechazar reporte: notificar al remitente que el negocio no reconocio el pago reportado.
- No prometer devolucion, garantia ni recuperacion.
- Explicar que el caso queda con trazabilidad para correccion, soporte o disputa futura.
- Payloads de notificacion no deben incluir instrucciones completas, `account_value`, `storage_path`, tokens ni secretos.

### payment_confirmed

- Al confirmar pago recibido: notificar al remitente que el negocio debe enviar pago movil.
- A los 30 minutos sin entrega: recordar al negocio.
- A las 2 horas sin entrega: abrir disputa y notificar a partes/admin.

### delivered

- Al marcar entregado: notificar al remitente.
- A las 12 horas: recordar que puede abrir disputa si no recibio.
- A las 23 horas: ultimo aviso antes del cierre automatico.
- A las 24 horas sin disputa: auto-completar y notificar a ambos.

Mensaje obligatorio en delivered:

```txt
El negocio marco el pago movil como enviado. Si tu receptor no recibio, abre disputa antes de que la orden cierre automaticamente.
```

## Anti-spam

- No reenviar el mismo recordatorio mas de una vez por ventana.
- Respetar rate limits de Telegram.
- Registrar notificaciones enviadas.
- Si Telegram falla, reintentar con backoff.

## Slice 10 notification jobs

Tabla canonica: `notification_jobs`.

Columnas canonicas:

- `notification_type`
- `recipient_user_id`
- `recipient_role`
- `order_id`
- `business_id`
- `dispute_id`
- `status`
- `scheduled_for`
- `attempts`
- `max_attempts`
- `dedupe_key`
- `metadata_json`

`notification_jobs.event_type` y `telegram_chat_id` son legacy/no validos para
nuevas migraciones de slice 10.

Tipos canonicos:

| notification_type | destinatario | cuando se programa | copy base seguro |
| --- | --- | --- | --- |
| order_payment_deadline_warning | remitente | antes de vencer `waiting_payment` | Tu orden esta por vencer. Reporta el pago antes del limite si ya pagaste. |
| order_cancelled_payment_not_reported | remitente y negocio | `waiting_payment` vencida | La orden expiro porque el pago no fue reportado a tiempo. |
| order_business_response_warning | negocio | 2h despues de `payment_reported` sin respuesta | Hay una orden con pago reportado pendiente de revisar. |
| order_disputed_business_no_payment_confirmation | remitente, negocio, admin/support | 6h despues de `payment_reported` sin respuesta | La orden paso a disputa por falta de respuesta del negocio. |
| order_delivery_warning | negocio | 30 min despues de `payment_confirmed` sin entrega | Confirma el envio del pago movil antes del limite. |
| order_disputed_business_confirmed_payment_but_not_delivered | remitente, negocio, admin/support | 2h despues de `payment_confirmed` sin entrega | La orden paso a disputa porque el pago movil no fue marcado como enviado a tiempo. |
| delivered_reminder_immediate | remitente | al pasar a `delivered` | El negocio marco el pago movil como enviado. Si tu receptor no recibio, abre disputa antes de que la orden cierre automaticamente. |
| delivered_reminder_12h | remitente | 12h despues de `delivered` | Si el receptor no recibio el pago movil, abre disputa antes del cierre automatico. |
| delivered_reminder_23h | remitente | 23h despues de `delivered` | Ultimo aviso antes del cierre automatico de la orden. |
| order_auto_completed_after_24h | remitente y negocio | 24h despues de `delivered` sin disputa | La orden se cerro automaticamente porque no se abrio disputa dentro del plazo. |
| ad_expired | negocio | anuncio vence por edad | Tu anuncio cumplio 7 dias, se archivo y el credito fue consumido. |
| founder_access_expired | negocio | `founder_expires_at <= now` | Tu periodo fundador expiro; nuevas publicaciones requieren creditos disponibles. |

Reglas:

- Canal principal: Telegram Bot.
- `status = pending` cuando se programa.
- `status = sent` solo despues de envio exitoso.
- `status = failed` cuando agota reintentos o falla de forma permanente.
- `status = skipped` cuando el recurso cambio de estado o dedupe indica envio previo.
- `status = cancelled` cuando la notificacion ya no aplica por cambio de estado.
- `dedupe_key` debe ser unico por recurso, notification_type y ventana.
- No incluir instrucciones completas, `account_value`, `storage_path`, signed
  URLs, evidencia privada, tokens, secretos ni datos bancarios completos.
- No prometer escrow, fondos protegidos, garantia de entrega, recuperacion de
  fondos ni que NODO recibe/retiene/transfiere dinero.
