# RATING_REPUTATION_MASTER.md

Estado: `OFFICIAL_SLICE_42C_PUBLIC_SNAPSHOT`

## Autoridad

Este documento gobierna la reputacion visible de negocios. Cuando exista drift,
se deben alinear `DATA_MODEL_MASTER.md`, `ENUMS_AND_STATUS_MASTER.md`, los
contratos API y las pantallas a estas reglas antes de construir UI.

## Separacion obligatoria

- `trust_level` controla limites y capacidad interna. No es reputacion publica.
- `reputation_tier` resume reputacion calculada internamente: `new`, `active`,
  `reliable`, `elite`. Solo su copia de snapshot puede publicarse.
- `risk_level` es una senal interna de seguridad. Nunca se expone en DTOs
  publicos, marketplace ni mensajes para clientes.
- El negocio no puede editar rating, metricas agregadas ni `reputation_tier`.
- Admin puede ver datos internos y operar controles existentes, pero no puede
  crear, alterar ni falsificar estrellas.

## Rating MVP

- Una orden `completed` admite como maximo un rating del cliente propietario.
- El rating tiene solo `stars` entero entre 1 y 5.
- No existen comentarios, resenas textuales, titulo ni cuerpo libre en MVP.
- El backend valida ownership, estado de la orden, disputa cerrada, duplicados e
  idempotencia.
- Slice 42B implementa `POST /api/v1/orders/{order_id}/rating` y una UI minima
  de 1 a 5 estrellas en la Mini App Cliente.
- Rating y agregados de reputacion se guardan en una sola operacion segura.
- `completion_reason = manual_confirmed` y
  `completion_reason = auto_completed_after_24h` habilitan rating bajo las
  mismas reglas, siempre que no exista disputa `open|in_review`.
- `completion_reason = admin_resolved` puede habilitar rating solo cuando la
  disputa asociada esta cerrada/resuelta y el contrato de rating lo permite.
- Completion no crea rating automaticamente; el cliente conserva la accion
  explicita de 1 a 5 estrellas.

## Metricas canonicas

- `rating_avg`: promedio de estrellas validas, con dos decimales; `null` sin
  ratings. Es un agregado interno y no forma parte de DTOs publicos o del
  negocio.
- `ratings_count`: cantidad exacta de ratings validos. El valor vivo es interno;
  solo la copia durable publicada puede formar parte del DTO publico.
- `completed_orders_count`: ordenes completadas correctamente.
- `business_failure_orders_count`: resultados atribuibles al negocio que
  cuentan contra success rate.
- `success_rate`: porcentaje calculado por backend:

```txt
completed_orders_count
----------------------------------------------- * 100
completed_orders_count + business_failure_orders_count
```

- Si el denominador es cero, `success_rate = null`; el frontend no sustituye ni
  calcula el valor.
- `average_delivery_seconds`: promedio backend desde
  `payment_confirmed_at` hasta `delivered_at`, solo con timestamps validos y no
  negativos. El DTO puede presentarlo como minutos, pero la conversion sigue
  siendo backend.

## Resultados atribuibles

Cuentan contra el negocio:

- disputa resuelta contra el negocio;
- cancelacion posterior a `payment_reported` causada por incumplimiento del
  negocio;
- entrega vencida atribuible al negocio cuando ese outcome exista en el
  contrato de orden.

No cuentan contra el negocio:

- cliente abandona antes de pagar;
- orden expira sin reporte de pago;
- error externo documentado como no atribuible.

La clasificacion se deriva de ordenes, eventos y disputas canonicas. No se
infieren fallos por texto libre ni desde frontend.

## Tiers y badges

Los tiers se evalúan de mayor a menor y todos los minimos del tier deben
cumplirse:

| Tier | Etiqueta | Completadas | Ratings | Rating | Success rate |
|---|---|---:|---:|---:|---:|
| `elite` | Elite | 100 | 30 | 4.50 | 97% |
| `reliable` | Reputacion alta | 25 | 10 | 4.20 | 95% |
| `active` | Activo | 5 | 3 | 4.00 | 90% |
| `new` | Nuevo | base | 0 | n/a | n/a |

`new` es el tier base y se conserva hasta cumplir todos los minimos de
`active`; superar cuatro ordenes por si solo no promueve al negocio.

`Pausado/Offline` y `No disponible` son estados de disponibilidad, no valores
de `reputation_tier`:

- si `is_accepting_orders = false`, la superficie puede mostrar
  `Pausado/Offline`;
- si backend/admin oculta el negocio por riesgo, la superficie solo muestra
  `No disponible temporalmente` o responde el error seguro vigente;
- una disputa abierta nunca expone publicamente `under_review` ni la causa de
  riesgo.

## Exposicion por audiencia

Publico/cliente:

- id y nombre del negocio;
- verificacion publica;
- `publication_status = withheld_pending_snapshot` y etiqueta
  `Reputacion aun no publicada` mientras haya menos de cinco ratings elegibles;
- con snapshot durable: `publication_status = published_snapshot`, promedio,
  cantidad y `published_at` copiados en lote, nunca valores vivos;
- prohibido cualquier rating asociado a una orden o cliente.
- Prohibidos: `trust_level`, `risk_level`, contadores antifraude, causas de
  disputa y senales internas.

Negocio propio autenticado:

- la misma proyeccion de snapshot publico, sin estrellas por orden;
- su capacidad/`trust_level` cuando el contrato propio lo requiera;
- no puede mutar campos derivados ni recibir detalles internos de riesgo.

Admin autorizado:

- agregados exactos de reputacion y campos internos necesarios, incluidos
  `trust_level`, `risk_level`, fallos atribuibles y disputas perdidas;
- la vista admin no es autoridad para editar ratings y este slice no expone
  ratings individuales a Admin ni Support.

## Privacidad e inferencia

- El rating individual solo vuelve al cliente que lo creo y en el estado de su
  propia orden.
- No se crea mensaje de chat, attention item ni notificacion Telegram por un
  rating.
- Publicar tier, promedio o conteo inmediatamente permitiria atribuir un cambio
  a una calificacion reciente. Esos valores vivos quedan internos.
- `business_public_reputation_snapshots` conserva la copia publica durable. El
  worker singleton existente publica como maximo una vez cada 24 horas, solo
  desde cinco ratings elegibles y cuando el calculo fuente tiene al menos 24
  horas. La existencia del runner no demuestra que un scheduler externo este
  activo en staging o produccion.
- El marketplace tampoco puede revelar cambios vivos mediante posicion. Slice
  42C mantiene todos los sorts publicos por tasa y fecha del anuncio; confianza,
  velocidad y metricas reputacionales, vivas o de snapshot, no participan en
  ranking ni desempates.

## Integridad y reconstruccion

- `ratings` es la fuente de estrellas por orden.
- Ordenes, eventos y disputas son la fuente de resultados operativos.
- Los campos agregados de `businesses` son read-models reconstruibles.
- `business_public_reputation_snapshots` es la unica fuente de reputacion para
  marketplace y perfil del negocio.
- `reputation_calculated_at = null` indica que el agregado aun no fue
  recalculado por un proceso contratado.
- Slice 42A no hace backfill ni activa recalculo automatico; eso requiere un
  slice posterior con pruebas de idempotencia y reconciliacion.
