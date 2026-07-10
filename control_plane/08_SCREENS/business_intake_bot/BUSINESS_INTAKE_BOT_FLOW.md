# BUSINESS_INTAKE_BOT_FLOW.md

## Owner

Bot Registro Negocios.

## Flujo

Bot:
- Este flujo pertenece al Bot Registro Negocios separado, configurado con `BUSINESS_INTAKE_BOT_TOKEN`.
- No pertenece al bot cliente configurado con `BOT_TOKEN`.
- No abre Mini App Cliente ni autoriza Mini App Negocio.

1. Bienvenida para negocio referido.
2. Pedir codigo de referencia.
3. Pedir numero de WhatsApp de contacto.
4. Adjuntar documentos/referencias:
   - cedula/pasaporte
   - RIF si aplica
   - foto del local si aplica
   - redes o referencias
5. Confirmacion cuando el solicitante escriba `finalizar`: "Solicitud recibida. Revisaremos tu informacion y te avisaremos el siguiente paso."

## Pasos y copy canonico 14D2

| last_step | Entrada esperada | Copy/prompt |
| --- | --- | --- |
| `start` | `/start` o boton Start | "Bienvenido a NODO Registro Negocios. Para comenzar, escribe tu codigo de referencia." |
| `awaiting_referral_code` | texto | "Para comenzar, escribe tu codigo de referencia." |
| `awaiting_whatsapp_phone` | telefono WhatsApp | "Ahora escribe tu numero de WhatsApp para poder contactarte sobre la solicitud." |
| `awaiting_documents` | photo/document o finalizar | "Puedes adjuntar cedula/pasaporte, RIF, foto del local o referencias. Aceptamos imagenes y PDF de hasta 5 MB. Cuando termines, envia 'finalizar'." |
| `submitted` | ninguno | "Solicitud recibida. Revisaremos tu informacion y te avisaremos el siguiente paso." |

Reglas:
- Cada respuesta valida se guarda antes de avanzar al siguiente paso.
- Si una respuesta no pasa validacion, el bot mantiene el mismo `last_step`, responde `200 OK` al webhook y pide corregir por Telegram.
- La copia debe ser sobria y no debe prometer aprobacion, acceso, anuncios ni creditos.
- Mensajes muy largos o fuera del paso actual son errores recuperables del usuario; no deben causar retry de Telegram.

## Archivos MVP

- Permitidos: `image/jpeg`, `image/png`, `image/webp`, `application/pdf`.
- Maximo: 5 MB.
- Storage: privado.
- `file_assets.resource_type = business_intake`.
- `file_assets.file_type = intake_document`.
- Video queda post-MVP y debe rechazarse con `BOT_UPLOAD_INVALID`.
- El bot acepta `photo` y `document` de Telegram, descarga el archivo con `getFile` usando `BUSINESS_INTAKE_BOT_TOKEN` y guarda el binario en storage privado.
- `file_id` y `file_unique_id` solo se guardan como metadata privada para deduplicacion; no son URLs publicas.

## Estado conversacional

- Estados activos MVP: `draft`, `submitted`, `accepted`, `rejected`.
- El bot persiste `last_step`, `last_update_id`, `telegram_user_id` y `telegram_chat_id`.
- Cada `update_id` de Telegram es idempotente por chat; repetirlo no duplica solicitud, documento ni notificacion.
- `last_step` debe usar solo los valores de la tabla de pasos canonica 14D2.

## No hace

- No crea negocio activo automaticamente.
- No publica anuncios.
- No da acceso al marketplace de negocios.
- No promete aprobacion.
