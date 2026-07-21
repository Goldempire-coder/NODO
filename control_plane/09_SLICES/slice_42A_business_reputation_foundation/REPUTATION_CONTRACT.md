# REPUTATION_CONTRACT.md

## Fuente de verdad

- `ratings`: estrellas por orden, sin texto libre.
- `orders`, `order_state_events`, `disputes` y `dispute_events`: outcomes
  operativos atribuibles o no atribuibles.
- `businesses`: agregados reconstruibles para lectura eficiente.

## Formula de success rate

```txt
success_rate = completed / (completed + attributable_business_failures) * 100
```

Sin denominator, el valor es `null`. Redondeo backend a dos decimales.

## Reglas de tier

| Tier | Completed | Ratings | Rating avg | Success rate |
|---|---:|---:|---:|---:|
| `elite` | 100 | 30 | 4.50 | 97.00 |
| `reliable` | 25 | 10 | 4.20 | 95.00 |
| `active` | 5 | 3 | 4.00 | 90.00 |
| `new` | tier base | 0 | n/a | n/a |

Se evalua de mayor a menor. Si no se cumplen todos los minimos de `active`, el
tier permanece `new`.

## Contratos por audiencia

### Cliente/marketplace

Permitido:

- `business.id`
- `business.business_name`
- `business.verification_status`
- `business.reputation.tier`
- `business.reputation.label`
- `business.reputation.rating_avg`
- `business.reputation.ratings_count`
- `business.reputation.completed_orders_count`
- `business.reputation.success_rate`
- `business.reputation.average_delivery_seconds`

Por compatibilidad v1, `business.rating_avg` y
`business.completed_orders_count` pueden coexistir como aliases publicos hasta
un slice futuro de deprecacion. No son campos internos.

Prohibido:

- `trust_level`
- `risk_level`
- `business_failure_orders_count`
- `lost_disputes_count`
- causas internas, notas admin o senales antifraude

### Negocio propio

Puede leer su reputacion y capacidad contratada. No puede escribir campos
derivados, ratings ni tier. `risk_level` no forma parte del DTO propio nuevo.

### Admin autorizado

Puede leer reputacion y datos internos necesarios para decisiones operativas.
No existe operacion para editar estrellas, promedios, success rate o tier.

## Disponibilidad

- `Pausado/Offline` deriva de `is_accepting_orders = false`.
- `No disponible temporalmente` deriva de elegibilidad backend.
- Ninguna respuesta publica revela `under_review` o el motivo de riesgo.

## Slice boundary

Este slice no crea endpoints de rating, jobs de recomputacion, backfill, UI de
rating, dashboard de reputacion ni ranking nuevo. Esos cambios requieren slices
posteriores y evidencia propia.
