# DOMAIN_CONTRACT.md

## Conceptos

### Limite diario operativo

`daily_limit_usd` es el maximo de USD que un negocio puede tener comprometido durante un dia operativo.

Default actual:

```txt
daily_limit_usd = 1000.00
```

Admin puede bajarlo o subirlo segun pruebas, riesgo o nivel del negocio.

### Cupo diario usado

El sistema debe separar tres ideas:

```txt
daily_reserved_usd = todas las ordenes abiertas que todavia pueden requerir cumplimiento,
                     aunque la reserva haya nacido antes del dia UTC actual
daily_consumed_usd = ordenes ya completadas o consumidas durante el dia
daily_released_usd = ordenes liberadas; informativo, no bloquea
```

El calculo que decide si el negocio puede recibir otra orden es:

```txt
daily_remaining_usd =
  daily_limit_usd
  - daily_reserved_usd
  - daily_consumed_usd
```

Nunca se calcula desde el frontend.

### Estados que reservan

Una orden debe contar contra el limite diario mientras el negocio todavia tenga una obligacion posible:

- `waiting_payment`
- `payment_reported`
- `payment_rejected` si todavia puede corregirse o revisarse
- `payment_confirmed`
- `delivered` si aun no esta cerrada
- `disputed`

### Estados que liberan

Una orden libera el cupo diario si termina sin que el negocio haya usado liquidez:

- cancelada antes de pago reportado;
- expirada antes de pago reportado;
- pago rechazado y orden terminada sin obligacion;
- resolucion de disputa que no consume liquidez del negocio.

Liberar no cuenta contra el limite diario.

### Estados que consumen

Una orden consume cupo diario si el negocio efectivamente cumplio:

- orden completada;
- pago entregado por el negocio;
- resolucion donde el negocio uso liquidez.

Una orden consumida no vuelve a abrir cupo hasta el siguiente dia operativo.

### Disputas

Una disputa no debe liberar cupo automaticamente.

La regla segura es:

```txt
disputa abierta = cupo retenido
disputa resuelta sin obligacion = released
disputa resuelta con obligacion = consumed
```

## Ejemplos

### Negocio con USD 1000 diarios

```txt
Limite diario: 1000.00
Orden completada hoy: 300.00
Orden abierta: 200.00
Disponible diario: 500.00
```

El cliente que pide `600.00` no debe poder abrir orden con ese negocio.

### Cancelacion antes de pago

```txt
Limite diario: 1000.00
Orden abierta: 100.00
Cliente cancela antes de pagar
Disponible diario vuelve a 1000.00
```

### Orden completada

```txt
Limite diario: 1000.00
Orden completada: 100.00
Disponible diario queda en 900.00 hasta el cambio de dia
```

## Matching cliente-negocio

Para mostrar un negocio en resultados, el backend debe validar:

```txt
amount_requested_usd <= effective_available_capacity_usd
amount_requested_usd <= daily_remaining_usd
amount_requested_usd between min_order_amount_usd and max_order_amount_usd
business is online
business is approved
business is not suspended or blocked
ad is active
```

El cliente puede ver:

```txt
Disponible para tu monto
```

El cliente no debe ver:

- capacidad declarada exacta;
- reservado exacto;
- consumido diario;
- restante diario exacto;
- razon interna de riesgo.

## UI negocio

El negocio debe ver:

- disponible declarado ahora;
- reservado en ordenes abiertas;
- limite diario;
- usado hoy;
- restante hoy;
- hora estimada de reinicio;
- mensaje claro si ya no puede recibir mas ordenes.

Texto recomendado:

```txt
Hoy puedes recibir hasta 1000.00 USD.
Usado o reservado hoy: 1000.00 USD.
Vuelve a estar disponible al reiniciar el dia operativo.
```

## UI admin

Admin debe ver:

- limite diario configurado;
- reservado activo;
- consumido hoy;
- restante hoy;
- ordenes que explican cada monto;
- zona horaria o regla de reinicio;
- ultima actualizacion;
- actor que cambio el limite o capacidad si aplica.

## Dia operativo

45A usa dia UTC. 45B debe inspeccionar si eso es suficiente.

Decision recomendada para no romper lo ya construido:

```txt
mantener UTC hasta que Owner apruebe una zona operativa distinta
```

Si se cambia a otra zona, debe existir contrato, migracion o plan de compatibilidad.
