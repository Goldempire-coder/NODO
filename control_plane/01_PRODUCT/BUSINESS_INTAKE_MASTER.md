# BUSINESS_INTAKE_MASTER.md

Contrato de captacion de negocios referidos/interesados.

## Slice 14D2 - bot conversacional separado

Decision canonica:
- El Bot Registro Negocios usa un bot Telegram separado del bot cliente.
- El secreto/token backend para este bot es `BUSINESS_INTAKE_BOT_TOKEN`.
- El bot cliente no procesa intake de negocios.
- El bot de negocios no abre Mini App Cliente ni Mini App Negocio como autorizacion; solo puede informar que la solicitud fue recibida o, cuando admin/backend lo decidan en otra fase, mostrar un boton seguro.
- El bot no crea negocio activo, no cambia `users.role`, no crea `business_access_links`, no publica anuncios y no acredita creditos.

Secuencia conversacional canonica:
1. `start`
2. `awaiting_contact`
3. `awaiting_business_name`
4. `awaiting_responsible_name`
5. `awaiting_city`
6. `awaiting_business_phone`
7. `awaiting_operation`
8. `awaiting_banks`
9. `awaiting_methods`
10. `awaiting_min_amount`
11. `awaiting_max_amount`
12. `awaiting_schedule`
13. `awaiting_references`
14. `awaiting_documents`
15. `submitted`

Persistencia:
- Cada respuesta valida se guarda inmediatamente en `business_intake_requests`.
- `status = draft` durante el flujo.
- Al completar el paso final, `status = submitted`.
- `accepted` y `rejected` son exclusivamente decisiones admin.
- Repetir un `update_id` no duplica solicitud, documento, audit ni notificacion.

Mensajes:
- La copia debe ser clara, sobria y no tecnica.
- Confirmacion final canonica: "Solicitud recibida. Revisaremos tu informacion y te avisaremos el siguiente paso."
- Prohibido prometer aprobacion, acceso al negocio, publicacion de anuncios, creditos o fondos garantizados.

## Objetivo

El Bot Registro Negocios recopila informacion y documentos para crear una solicitud revisable por admin. La solicitud no activa un negocio ni permite publicar anuncios.

## Datos solicitados

- nombre del negocio
- responsable
- ciudad
- telefono de contacto Telegram compartido
- telefono del negocio
- operacion: `buy_usd`, `sell_usd`, `both`
- bancos
- metodos: `zelle`, `usdt_trc20`, futuros solo si contrato los aprueba
- rango minimo/maximo
- horario de atencion
- referencias/redes
- documentos/referencias:
  - cedula/pasaporte
  - RIF si aplica
  - foto del local si aplica
  - redes sociales o referencias

## Flujo

1. Bot muestra bienvenida.
2. Solicita compartir contacto.
3. Valida que el contacto compartido pertenece al mismo `telegram_user_id`.
4. Guia el formulario.
5. Recibe adjuntos privados.
6. Crea o actualiza `business_intake_requests.status = submitted`.
6. Responde: "Solicitud recibida. Revisaremos tu informacion y te avisaremos el siguiente paso."
7. Notifica al panel admin.
8. Admin revisa, acepta o rechaza.
9. Si acepta, admin puede crear/agregar negocio desde solicitud y asociar Telegram ID.

## Reglas

- Bot no crea `businesses` directamente.
- Bot no cambia `users.role` a `business_owner`.
- Bot no publica anuncios.
- Bot no promete aprobacion.
- Bot no acepta video en MVP; video/local media en movimiento queda post-MVP.
- `contact_phone` es el telefono compartido por Telegram y debe validarse contra `contact.user_id == telegram_user_id`.
- `business_phone` es el telefono operativo declarado por el negocio y no reemplaza el contacto Telegram.
- Cada update de Telegram se procesa idempotentemente por `telegram_chat_id + last_update_id`.
- Admin debe registrar reason para aceptar/rechazar.
- Crear negocio desde intake debe auditar `business_created_from_intake`.
- Asociar Telegram/persona/negocio debe crear `business_access_links` y auditar `business_access_linked`.
- `business_telegram_linked` queda como alias legacy/no canonico para nuevas implementaciones.

## Estados

Ver `business_intake.status` en `ENUMS_AND_STATUS_MASTER.md`.

## Datos sensibles

Documentos y referencias usan storage privado mediante `file_assets.resource_type = business_intake`.

`storage_path`, documentos completos, telefono completo y datos de identidad no se exponen en frontend publico ni logs.
