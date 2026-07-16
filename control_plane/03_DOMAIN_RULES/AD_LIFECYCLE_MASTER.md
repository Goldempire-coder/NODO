# AD_LIFECYCLE_MASTER.md

Un anuncio es una publicacion de negocio con metodo de pago, metodo de entrega, rango de monto, tasa y vida util.

## Estados

- draft
- active
- in_order
- archived
- expired
- paused
- suspended

## Vida del anuncio

- Duracion: 7 dias desde activacion.
- Creditos bloqueados al publicar:
  - $20-$100 = 1 credito
  - $100-$500 = 2 creditos
  - $500-$2,000 = 3 creditos
  - Mas de $2,000 = no disponible en MVP o revision manual
- Si no se vende dentro de 7 dias, se archiva y consume el credito bloqueado.
- Si expira mientras tiene orden activa, la orden sigue; el anuncio no acepta nuevas ordenes.
- Reactivar un anuncio pausado no cobra credito extra porque mantiene el hold original.
- Republicar un anuncio archivado o vencido crea una nueva publicacion de 7 dias y requiere creditos disponibles antes de activarla.
- Crear anuncio desde Mini App Negocio requiere seleccionar un metodo aprobado desde backend; el usuario no escribe `payment_method_id` manualmente.
- La gestion permitida de metodos propios del negocio requiere PIN operativo desbloqueado y backend ownership. Admin mantiene control sobre aprobacion, suspension, bloqueo y limites de capacidad.
- Crear, editar, pausar, reactivar, archivar o republicar anuncios desde Mini App Negocio requiere PIN operativo configurado y desbloqueado.
- Crear, editar, reactivar o republicar debe respetar la capacidad actual del negocio:
  - `amount_min_usd >= business.min_order_amount_usd`
  - `amount_max_usd <= business.max_order_amount_usd`
  - la exposicion abierta total (`active` + `in_order`) no puede superar `business.daily_limit_usd`.
  - si no cumple, responder `AD_LIMIT_NOT_ALLOWED`.
- Si se supera `business.daily_limit_usd`, responder `BUSINESS_DAILY_LIMIT_EXCEEDED`.
- Si admin baja la capacidad, anuncios fuera del rango actual no deben seguir ofreciendose en marketplace.

## Click, orden y hold

- Click / abrir detalle no cambia estado y no consume creditos.
- Crear orden cambia `active -> in_order`.
- En MVP, 1 anuncio solo puede tener 1 orden activa.
- Cuando pasa a `in_order`, el anuncio sale totalmente del catalogo.
- Crear orden no consume creditos adicionales; solo bloquea disponibilidad operativa del anuncio.
- Si el remitente no reporta pago dentro del timer de orden, la orden expira y el anuncio/disponibilidad vuelve a `active` si aun no vencio.
- Si el remitente reporta pago, el anuncio queda comprometido hasta confirmacion, rechazo, disputa o resolucion.
- Si el negocio confirma pago recibido, se consumen los creditos bloqueados del anuncio y el anuncio pasa a `archived`.
- Si la orden expira o se cancela antes de pago confirmado y el anuncio aun no vencio, vuelve a `active` y mantiene el credito bloqueado.
- Si el negocio rechaza un reporte de pago, el anuncio permanece `in_order` y los creditos siguen bloqueados hasta resolucion/cancelacion/disputa futura.
- Si una disputa se resuelve en slice 09 con resolucion terminal, el anuncio queda `archived` y no vuelve al marketplace.
- Si una disputa queda `keep_under_review`, el anuncio conserva el estado derivado del origen de disputa: `in_order` para origen `payment_reported/payment_rejected` y `archived` para origen `payment_confirmed/delivered`.
- Si el anuncio expira sin pago confirmado, se consume el credito bloqueado y pasa a `archived`.
- El negocio no pierde creditos adicionales por curiosos que abren el anuncio o abandonan ordenes sin pago reportado.

## Transiciones

- `draft -> active`: negocio publica anuncio y se bloquean creditos segun rango.
- `active -> in_order`: remitente crea orden y se bloquea disponibilidad temporal.
- `in_order -> active`: orden expira/cancela sin pago reportado y el anuncio no vencio; el credito sigue bloqueado para esa publicacion.
- `in_order -> archived`: negocio confirma pago recibido; el anuncio ya cumplio su funcion de publicacion y no vuelve al marketplace.
- `active -> archived`: se cumplen 7 dias sin venta confirmada y se consume el credito bloqueado.
- `paused -> archived`: se cumplen 7 dias aunque el anuncio este pausado y se consume el credito bloqueado.
- `active -> paused`: negocio pausa anuncio.
- `paused -> active`: negocio reactiva si no expiro y mantiene reglas de credito/riesgo.
- `archived -> active`: prohibido sobre el mismo registro. El negocio puede republicar como una nueva publicacion si tiene creditos disponibles.
- `any -> suspended`: admin suspende por riesgo.

## Pausa no extiende vida

- `ad.expires_at` no cambia cuando el negocio pausa el anuncio.
- Pausar no congela el reloj de 7 dias.
- Si llega `expires_at` mientras esta pausado, `ad.status = archived` y el credito se consume.
- Esto evita que un negocio pause/reactive para mantener anuncios vivos eternamente sin renovar.

## Expiracion pasiva en slice 03

Hasta que `slice_10_jobs_notifications` implemente worker masivo, `slice_03_ads_marketplace` debe aplicar expiracion pasiva/materializada:

- Search excluye anuncios con `expires_at <= now()` aunque su estado persistido aun sea `active` o `paused`.
- Detail puede responder `AD_NOT_AVAILABLE` o mostrar `effective_status = expired` antes de materializar.
- Cualquier mutacion sobre anuncio vencido debe materializar `status = archived` antes de responder.
- La materializacion genera audit event `ad_expired`.
- Si el anuncio vencido no tiene pago confirmado y mantiene hold de creditos, el credit service consume el hold con ledger `expire` y audita `credits_consumed`.
- El worker masivo de expiracion queda para `slice_10_jobs_notifications`.

## Reglas anti-curiosos

- Limitar ordenes abiertas por remitente.
- Aplicar cooldown si un remitente crea y abandona muchas ordenes.
- Expirar ordenes rapidamente si no hay reporte de pago.
- No cobrar creditos adicionales al negocio por clicks o abandonos sin pago.
- Admin puede revisar abuso si un usuario bloquea anuncios repetidamente.

## Regla simple

```txt
Publicar anuncio = bloquea creditos
Cliente no paga antes de 7 dias = anuncio vuelve activo y mantiene creditos bloqueados
Anuncio llega a 7 dias sin venta = consume creditos y se archiva
Negocio confirma pago recibido = consume creditos y archiva anuncio
Negocio rechaza reporte de pago = mantiene anuncio in_order y creditos bloqueados
Resolucion admin terminal de disputa = archiva anuncio
```
