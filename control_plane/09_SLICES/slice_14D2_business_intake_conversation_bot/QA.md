# QA.md

Tests requeridos:
- `BUSINESS_INTAKE_BOT_TOKEN` configurado y usado solo backend.
- Secret de bot cliente falla en webhook de intake.
- Secret de bot intake falla en webhook cliente.
- `/start` en bot intake crea/recupera draft y no crea negocio.
- Codigo de referencia requerido antes del WhatsApp.
- Numero de WhatsApp requerido antes de documentos.
- Input invalido en WhatsApp/documentos responde webhook `200 OK` con mensaje correctivo; no debe dejar a Telegram reintentando.
- Cada paso persiste parcialmente.
- Flujo completo termina `submitted`.
- Confirmacion final usa copy canonico.
- Update duplicado no duplica solicitud, audit, documento ni notificacion.
- `photo` valida se descarga y guarda privado.
- `document` PDF valido se descarga y guarda privado.
- Video/audio/MIME invalido falla con `BOT_UPLOAD_INVALID`.
- Archivo mayor a 5 MB falla.
- Respuestas no exponen `storage_path`.
- Bot no crea `businesses`, no cambia roles y no crea `business_access_links`.
- Bot no crea anuncios ni acredita creditos.
- Admin/super_admin puede borrar una solicitud mal hecha con reason e idempotencia.
- Borrar solicitud oculta documentos de intake y preserva `audit_logs`.
- Scan frontend/build sin `BUSINESS_INTAKE_BOT_TOKEN`, `BOT_TOKEN`, `storage_path` ni claims prohibidos.
