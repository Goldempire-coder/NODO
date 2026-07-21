# RATING_REPUTATION_MASTER.md

Estado: `OFFICIAL_SLICE_42A_FOUNDATION`

## Autoridad

Este documento gobierna la reputacion visible de negocios. Cuando exista drift,
se deben alinear `DATA_MODEL_MASTER.md`, `ENUMS_AND_STATUS_MASTER.md`, los
contratos API y las pantallas a estas reglas antes de construir UI.

## Separacion obligatoria

- `trust_level` controla limites y capacidad interna. No es reputacion publica.
- `reputation_tier` resume reputacion visible: `new`, `active`, `reliable`,
  `elite`.
- `risk_level` es una senal interna de seguridad. Nunca se expone en DTOs
  publicos, marketplace ni mensajes para clientes.
- El negocio no puede editar rating, metricas agregadas ni `reputation_tier`.
- Admin puede ver datos internos y operar controles existentes, pero no puede
  crear, alterar ni falsificar estrellas.

## Rating MVP

- Una orden `completed` admite como maximo un rating del cliente propietario.
- El rating tiene solo `stars` entero entre 1 y 5.
- No existen comentarios, resenas textuales, titulo ni cuerpo libre en MVP.
- El backend valida ownership, estado de la orden e idempotencia en el slice que
  implemente la escritura.
- Slice 42A crea contrato y persistencia base; no crea endpoint ni pantalla de
  rating.

## Metricas canonicas

- `rating_avg`: promedio de estrellas validas, con dos decimales; `null` sin
  ratings.
- `ratings_count`: cantidad de ratings validos.
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
| `reliable` | Confiable | 25 | 10 | 4.20 | 95% |
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
- `reputation_tier`, etiqueta, `rating_avg`, `ratings_count`,
  `completed_orders_count`, `success_rate`, `average_delivery_seconds`.
- Prohibidos: `trust_level`, `risk_level`, contadores antifraude, causas de
  disputa y senales internas.

Negocio propio autenticado:

- sus metricas de reputacion;
- su capacidad/`trust_level` cuando el contrato propio lo requiera;
- no puede mutar campos derivados ni recibir detalles internos de riesgo.

Admin autorizado:

- metricas de reputacion y campos internos necesarios, incluidos
  `trust_level`, `risk_level`, fallos atribuibles y disputas perdidas;
- la vista admin no es autoridad para editar ratings.

## Integridad y reconstruccion

- `ratings` es la fuente de estrellas por orden.
- Ordenes, eventos y disputas son la fuente de resultados operativos.
- Los campos agregados de `businesses` son read-models reconstruibles.
- `reputation_calculated_at = null` indica que el agregado aun no fue
  recalculado por un proceso contratado.
- Slice 42A no hace backfill ni activa recalculo automatico; eso requiere un
  slice posterior con pruebas de idempotencia y reconciliacion.
