# Slice 48B QA

Estado: 48B2_IMPLEMENTED_LOCALLY_WITHOUT_DURABLE_MESSAGE_UNREAD

## Pruebas De Mapeo Requeridas

Builder debe entregar evidencia de:

- Evento de orden nueva para negocio: existe o falta.
- Evento de pago reportado para negocio: existe o falta.
- Evento de mensaje cliente -> negocio: existe o falta.
- Evento de mensaje negocio -> cliente: existe o falta.
- Evento de respuesta soporte -> participante: existe o falta.
- Badge global en Mini App Negocio: existe o falta.
- Badge global en Mini App Cliente: existe o falta.
- Deep link de Telegram abre la pantalla correcta.
- Si Telegram falla, Admin puede verlo.
- Si la app esta visible, los contadores se actualizan sin refrescar manual.
- Si la app esta oculta, se pausa o reduce el polling.
- Ningun payload de notificacion contiene cuerpos privados.

## Pruebas Para Implementacion Posterior

Cuando el Owner apruebe construir:

- Negocio recibe Telegram por orden nueva y abre detalle correcto.
- Negocio recibe badge por mensaje de cliente sin estar dentro del chat.
- Cliente recibe badge por mensaje de negocio sin estar dentro del chat.
- Participante recibe aviso por respuesta de soporte.
- Abrir orden/chat/ticket limpia solo el contador correspondiente.
- Replay idempotente no duplica contador.
- App oculta no sigue generando polling agresivo.
- App visible refresca un endpoint liviano, no varias listas completas.
- Notificacion no muestra cuerpos, bancos, wallets, archivos ni URLs privadas.
- Build web pasa.
- Suite dirigida backend pasa.
- Smoke manual en Telegram staging pasa.

## Regresiones 48B1

- Cliente -> Negocio crea un solo `order_message_created_business`.
- Negocio -> Cliente crea un solo `order_message_created_client`.
- Replay conserva un solo job por mensaje y recipient.
- Mensaje con adjunto no filtra body, attachment ID, `file_asset_id`,
  `storage_path` ni signed URL.
- Respuesta Admin/Soporte `participants` crea un solo
  `support_message_created_participant`.
- Respuesta del participante mantiene la notificacion Admin existente y no
  crea un Telegram hacia si mismo.
- Sender reclama los tres tipos nuevos.
- Deep links de ambas superficies abren chat/ticket exacto.
- Migracion 0037 es reversible y no fue ejecutada.

## Regresiones 48B2

- Negocio muestra badge por orden accionable y ticket `waiting_user`.
- Cliente muestra badge por orden accionable y ticket `waiting_user`.
- Abrir un recurso reconoce solo ese pendiente durante la sesion.
- Un cambio posterior de estado vuelve a presentar el pendiente.
- El aviso interno solo contiene copy generico y ruta local al recurso.
- Un fallo temporal conserva el ultimo contador valido y marca `Sin actualizar`.
- El scheduler corre cada 30 segundos, se pausa oculto y evita solapamientos.
- No hay polling independiente por badge ni descarga de listas completas desde
  el frontend.
- El endpoint combinado filtra por ownership y superficie antes del limite.
- Una orden antigua actualizada recientemente aparece entre las primeras 50.
- Memory y Postgres ordenan awareness por `updated_at DESC, id DESC`.
- Una apertura fallida conserva el pendiente; solo una apertura exitosa lo
  reconoce durante la sesion.
- `truncated.orders` y `truncated.support` muestran `50+`, no un total exacto.
- No se afirma unread durable de mensajes de chat.

## Comandos Esperados

```powershell
python -m pytest apps/api/tests/test_jobs_notifications.py apps/api/tests/test_order_creation.py apps/api/tests/test_support_ticket_center.py -q --tb=short
python -m pytest apps/api/tests/test_auth_lifecycle_static.py -q --tb=short
python -m ruff check apps/api scripts
python -m compileall apps/api apps/web/src scripts
pnpm --filter @nodo/web build
git diff --check
```

## Evidencia Minima Del Mapeo

- Tabla evento -> productor -> receptor -> canal -> UI -> estado.
- Lista de brechas con severidad.
- Plan de implementacion dividido en mini tareas.
- Archivos probables a tocar.
- Riesgos de costo, privacidad y duplicados.
- Confirmacion de no haber modificado runtime durante el mapeo.
