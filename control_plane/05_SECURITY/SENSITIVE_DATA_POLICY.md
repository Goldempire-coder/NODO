# SENSITIVE_DATA_POLICY.md

## Slice 14 - Intake and support sensitive data

Sensitive:
- business intake identity documents
- RIF/local media/references
- support attachments
- support messages containing personal, payment or order evidence
- Telegram IDs and phone/contact data

Rules:
- Store files via `file_assets` and private storage.
- Do not expose `storage_path`.
- Admin/support list views use masked summaries.
- Signed URLs must be short-lived and permission checked.
- Audit metadata must not copy full message bodies, documents, signed URLs or private evidence.
- Staff 20C list/detail views use masked summaries by default.
- Staff activity read model must redact support message bodies, Telegram IDs, phones, storage paths, account values, tokens and signed URLs.

Contrato de datos sensibles.

## Objetivo

Minimizar exposicion de datos personales, bancarios, comprobantes y evidencia de pago.

## Datos sensibles

- nombres completos cuando no sean necesarios
- telefonos
- cedulas/documentos
- RIF/documentos de verificacion de negocio
- correos
- cuentas Zelle
- telefonos de pago movil
- wallets USDT
- wallet publica de recepcion Base cuando no sea necesaria para el flujo de compra
- TxID/hash completos
- RPC provider URLs/API keys
- raw on-chain provider responses
- comprobantes
- payment evidence URLs
- full payment instructions
- payment account_value
- Telegram IDs internos
- storage keys
- Stripe secrets, webhook secrets, checkout session internals
- comprobantes manuales de compra de creditos
- referral abuse metadata when it can identify fraud patterns

## Reglas de exposicion

- Mostrar datos enmascarados por defecto.
- Revelar datos completos solo dentro de una orden activa y con permiso.
- Cada revelado sensible debe generar audit log cuando aplique.
- Los comprobantes viven en storage privado.
- Acceso a comprobantes por signed URL con expiracion.
- No persistir signed URLs como dato permanente.
- Admin ve solo lo necesario para resolver la tarea.
- Full payment instructions can only be returned by `GET /api/v1/orders/{id}/payment-instructions` to the remitter owner while the order is `waiting_payment` and not expired.
- `account_value` must not appear in general order detail/list, frontend bundle, logs or audit metadata.
- `tx_hash` may be stored internally for USDT reports; UI/list/audit should use masked/truncated display unless a later contract grants full reveal.
- Business order list/detail must not expose `storage_path`, tokens, secrets or full payment instructions.
- Business order detail may show full `tx_hash` only when needed for USDT verification; list, audit and logs must use masked/truncated value.
- `account_value` of the business payment method is not needed for slice 06 business operations and must not appear in business order list/detail.
- Business payment method selector responses may return `id`, method labels, limits and masked account metadata only; they must never return full `account_value`, full bank data or `storage_path`.
- Credit purchase manual proofs use private `file_assets`; API/frontend/logs/audit must never expose `storage_path`.
- Stripe checkout/session/event identifiers may be stored internally for idempotency, but secrets and raw webhook signatures must never be returned to frontend or logged.
- Base USDC tx hashes may be stored internally for idempotency and duplicate prevention; UI/list/audit/logs must use masked/truncated display unless detail access is explicitly authorized.
- On-chain provider raw responses, RPC keys, private keys, seed phrases and mnemonics must never be returned, logged or stored in audit metadata.
- Referral codes may be shown to the owning business; fraud/prevention metadata must stay internal.
- Admin console list/detail responses must mask sensitive fields by default.
- Admin user list/detail responses must mask `phone` and `telegram_id` by default.
- Full `telegram_id` in admin user endpoints is allowed only for `admin` and `super_admin`; `support` receives masked values only.
- Admin user endpoints must never return session internals, refresh token hashes, raw Authorization headers, tokens or secrets.
- Admin dispute resolution must not expose or log full payment instructions,
  `account_value`, `storage_path`, signed URLs, tokens or secrets.
- Support admin views are read-only and masked unless a later contract grants
  explicit reveal capability.
- Admin metrics/audit views must redact sensitive JSON values before returning
  data to frontend.
- Job run metadata and notification job metadata must be masked before admin
  display and must not include `storage_path`, `account_value`, full payment
  instructions, signed URLs, tokens, secrets, raw evidence or full banking data.

## Enmascaramiento minimo

```txt
email: ca***@domain.com
phone: +58*******123
wallet: TAbc...9Xz
tx_hash: 0xabc...789
account/payment_ref: mostrar ultimos 4 cuando aplique
```

## Chat y campos libres

- Sanitizar contenido mostrado.
- Evitar HTML crudo.
- Bloquear links o patrones prohibidos si violan reglas de evasion.
- No permitir scripts ni markup ejecutable.
- `messages.body`, adjuntos de chat y disputas no deben exponer instrucciones
  completas de Pago Movil.
- Excepcion controlada: una UI de chat puede renderizar un
  `chat-style secure receiver payload` obtenido del recurso estructurado
  dedicado de Slice 50B. Ese payload no es mensaje libre, no aparece en
  `messages.body` y solo se revela a los dos participantes con ownership,
  estado y audit validados.
- Chat y disputas no deben exponer `account_value`.
- Adjuntos de chat usan storage privado mediante `file_assets`.
- `storage_path` nunca aparece en respuestas de mensajes, disputas, frontend, logs o audit metadata.
- Las respuestas de slice 07 devuelven metadata de adjunto; signed URL de lectura completa requiere contrato futuro explicito.
- Admin/support no reciben el payload completo desde detail/list, mensajes,
  busqueda o evidencia amplia. Un reveal futuro requiere endpoint explicito,
  RBAC, motivo y audit sin valores.

## Uploads/evidencias

- Validar tipo de archivo.
- Validar tamano maximo.
- Escanear metadata cuando aplique.
- Guardar en bucket privado.
- Servir con signed URL corta.
- Para `message_attachment`, MIME permitido: `image/jpeg`, `image/png`, `image/webp`, `application/pdf`.
- Para `message_attachment`, maximo 5 MB.
- Para `credit_purchase_proof`, MIME permitido: `image/jpeg`, `image/png`, `image/webp`, `application/pdf`.
- Para `credit_purchase_proof`, maximo 5 MB.
- `credit_purchase_proof` solo puede leerse mediante metadata publica o signed URL corta autorizada para admin/super_admin review.
- Para `support_attachment`, MIME permitido: `image/jpeg`, `image/png`, `image/webp`, `application/pdf`.
- Para `support_attachment`, maximo 5 MB.
- Los adjuntos de soporte usan `file_assets.resource_type = support_ticket|support_message` y `file_type = support_attachment`.
- Las APIs de soporte devuelven metadata segura; signed URL de lectura requiere RBAC, expira rapidamente y no se persiste.
- Audit/logs de soporte no copian cuerpos completos de mensajes, signed URLs, `storage_path`, evidencia privada ni datos bancarios completos.

## Verificacion de negocio

- Documentos de verificacion de negocio viven en storage privado y se referencian desde `file_assets`.
- `storage_path` nunca se expone en frontend ni audit logs.
- Admin/super_admin puede abrir documento completo solo mediante signed URL corta y con audit event.
- Support ve metadata/enmascarado por defecto y no aprueba/rechaza.
- Datos de RIF, telefono, direccion y documentos deben mostrarse enmascarados salvo permiso admin explicito.

## Tests obligatorios

- usuario no autorizado no puede ver evidencia.
- negocio no puede ver orden ajena.
- remitente no puede ver datos de otro remitente.
- signed URL expira.
- campos libres no ejecutan XSS.
- logs no contienen datos bancarios completos.
- documento de verificacion de negocio no es publico.
- admin document view genera audit event.

## Bloqueo

Si una pantalla/API expone datos sensibles sin permiso, Builder debe reportar:

```txt
BLOCKED_BY_SECURITY_GAP
```
## Observability sensitive data - slice 24

Observability events, breadcrumbs, structured logs and diagnostic exports must never include:

- Authorization/Cookie headers;
- access or refresh tokens;
- Telegram initData completo;
- bot tokens;
- JWT secrets;
- service role keys;
- private keys, seed phrases or mnemonics;
- `account_value`;
- `storage_path`;
- signed URLs;
- full tx hash;
- full phone unless a future contract explicitly allows reveal;
- documents;
- full chat/ticket messages;
- full payment instructions.

Allowed diagnostic fields are route templates, status, duration, safe error code, screen/action names, app/build version and masked identifiers.
