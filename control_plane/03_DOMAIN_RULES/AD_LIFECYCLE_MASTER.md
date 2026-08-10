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
  - solo puede existir un anuncio `active` Zelle y un anuncio `active` USDT por negocio;
  - la suma de `amount_max_usd` de todos los anuncios `active|in_order`, incluido
    el que se crea, edita, reactiva o republica, no puede superar
    `declared_available_capacity_usd`;
  - si no cumple, responder `AD_LIMIT_NOT_ALLOWED`.
- Un negocio puede tener como maximo dos anuncios `active`: uno Zelle y uno
  USDT. Dos anuncios `active` del mismo metodo estan prohibidos aunque sus
  rangos no se solapen.
- Publicar, editar, reactivar o republicar un anuncio no reserva capacidad y no
  consume `business.daily_limit_usd`. El limite diario se revalida cuando un
  cliente confirma la seleccion y el backend crea la orden.
- Zelle y USDT comparten la misma capacidad declarada y el mismo limite diario;
  no existen cupos diarios separados por metodo.
- Un anuncio `in_order` ya no es una publicacion activa. Su orden conserva la
  reserva de capacidad y el efecto diario definido por el contrato de ordenes.
  Conserva el cupo de su metodo y su `amount_max_usd` dentro de la envolvente
  declarada para que una cancelacion o expiracion pueda reactivarlo sin superar
  la disponibilidad ni terminar con dos anuncios `active` Zelle o dos USDT.
  Esta envolvente no consume `daily_limit_usd`; la reserva real de la orden
  sigue siendo la autoridad operativa.
- No se puede bajar `declared_available_capacity_usd` por debajo de la suma de
  `amount_max_usd` de los anuncios `active|in_order`; primero deben pausarse,
  ajustarse o terminar la orden aplicable.
- Si datos historicos o una carrera dejan un anuncio fuera de la capacidad
  vigente, marketplace debe excluirlo y las mutaciones deben fallar cerrado.

## Reconciliacion B0.1

Quedan sustituidas y prohibidas como regla vigente:

- validar solo solapamiento de rangos para permitir varios anuncios `active` del
  mismo metodo;
- sumar anuncios `active` o `in_order` para descontar `daily_limit_usd` al
  publicar;
- asignar limites diarios separados a Zelle y USDT;
- tratar un anuncio publicado como si ya fuera una operacion real.

El codigo de error legacy `AD_OVERLAP_NOT_ALLOWED` puede conservarse por
compatibilidad, pero no sustituye la regla mas estricta de un anuncio `active`
por metodo.

## Click, orden y hold

- Click / abrir detalle no cambia estado y no consume creditos.
- Crear orden cambia `active -> in_order`.
- En MVP, 1 anuncio solo puede tener 1 orden activa.
- Cuando pasa a `in_order`, el anuncio sale totalmente del catalogo.
- Crear orden no consume creditos adicionales; solo bloquea disponibilidad operativa del anuncio.
- Si el remitente no reporta pago dentro del timer de orden, la orden expira y el anuncio/disponibilidad vuelve a `active` si aun no vencio.
- Si el remitente reporta pago, el anuncio queda comprometido hasta confirmacion o resolucion de disputa.
- Si el negocio confirma pago recibido, se consumen los creditos bloqueados del anuncio y el anuncio pasa a `archived`.
- Si la orden expira o se cancela antes de pago confirmado y el anuncio aun no vencio, vuelve a `active` y mantiene el credito bloqueado.
- Si el negocio reporta un problema con el pago, la orden pasa a disputa y el
  anuncio permanece `in_order` con los creditos bloqueados hasta resolucion.
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
Negocio reporta problema con pago = abre disputa y mantiene anuncio in_order y creditos bloqueados
Resolucion admin terminal de disputa = archiva anuncio
```
