# Security Contract

## Autoridad y privacidad

- Backend y PostgreSQL son autoridad para tiempo, ownership, estados, holds,
  restricciones y publicacion. Frontend solo refleja capabilities.
- El cliente nunca envia `business_id` como autoridad. Se deriva de la orden.
- El cliente tampoco recibe si el reporte creo hold; ese dato es interno.
- El negocio nunca recibe rating, estrellas, cliente, orden origen, ticket,
  causa de pausa ni motivo del reporte.
- No se crean mensajes de chat, attention items ni Telegram para el negocio por
  rating, reporte o hold.
- Audit y notification metadata no contienen cuerpos privados, telefonos,
  bancos, wallets, capturas, datos de pago, signed URLs, `storage_path`, tokens
  ni secretos.

## Guard compartido de publicacion

42D2 implementa la politica backend para la pausa temporal. 42F1 extiende la
misma politica con el hold operativo:

```txt
evaluate_ad_publication_access(
  business,
  has_active_operational_hold,
  database_now
)
```

Debe exigir:

```txt
business activo y aprobado
AND no bloqueado por Admin
AND no suspendido o restringido
AND no hold operativo activo
AND database_now >= ad_publication_paused_until
AND capacidad, creditos y limites vigentes permiten publicar
```

La misma autoridad protege crear, publicar, reactivar y republicar anuncios,
filtrar marketplace y crear una orden directa contra un anuncio existente. La
prevalidacion de UI o marketplace nunca autoriza una mutacion.

42D2 revalida cada hit de marketplace contra la fuente durable. Una respuesta
publica cacheada nunca autoriza crear orden y la transaccion final consulta la
restriccion durable. 42F1 conserva esta propiedad al iniciar o liberar holds.

El bloqueo Admin domina aunque la pausa venza. La pausa y el hold no cambian el
estado durable de anuncios existentes.

## Reporte y hold

- No existe entrada desde chat.
- Un ticket generico, texto libre o negocio escrito por el cliente no crea hold.
- El hold solo nace del endpoint estructurado, una orden propia reportable y una
  pausa que siga activa con frontera estricta `database_now < paused_until`.
- El cliente no puede liberar el hold y cerrar su ticket no lo libera.
- La liberacion exige actor Admin/Super Admin activo, reason, idempotencia y
  audit. La delegacion Support queda fuera de 42F1 hasta ampliar el constraint
  durable de permisos y aplicar scope contra el ticket asociado.
- Concurrencia debe dejar un solo reporte/hold por orden y ticket.

## Copy neutral

Pausa temporal:

```txt
Publicacion temporalmente no disponible. Podras intentar nuevamente en unos minutos.
```

Hold/revision:

```txt
Publicacion temporalmente no disponible mientras se revisa la operacion.
```

Quedan prohibidos `te reportaron`, `rating bajo`, `reclamo del cliente`,
`investigacion por calificacion`, `castigo`, `sancion automatica`, `protegido`,
`garantizado` y `seguro` como explicacion publica de esta restriccion.

## Eventos internos futuros

- `business_publication_pause_started`;
- `structured_operation_report_created`;
- `business_publication_hold_started`;
- `business_publication_hold_released`;
- `admin_telegram_alert_queued`;
- `admin_telegram_alert_failed`.

Los eventos registran IDs, actor, timestamp y resultado minimo; no guardan rating,
estrellas, mensaje privado ni datos completos de pago.
