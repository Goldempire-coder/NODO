# DOMAIN_CONTRACT.md

## Conceptos

### Limite por operacion

El negocio puede operar por defecto:

```txt
min_order_amount_usd = 20.00
max_order_amount_usd = 100.00
daily_limit_usd = 1000.00
```

Admin puede ajustar esos valores para pruebas o revision operativa.

### Capacidad disponible declarada

`declared_available_capacity_usd` es el monto que el negocio dice tener disponible ahora para cambiar.

Ejemplo:

```txt
Negocio declara disponible: 40.00
Rango por operacion: 20.00 - 100.00
Cliente pide: 80.00
Resultado: no puede abrir orden con ese negocio
```

### Capacidad reservada

`reserved_capacity_usd` es la suma de montos de ordenes abiertas que todavia pueden requerir que el negocio cumpla.

Estados que deben reservar capacidad:

- orden creada y esperando pago del cliente;
- pago reportado, pendiente de revision;
- pago confirmado, pendiente de entrega;
- disputa abierta.

Estados que liberan capacidad:

- orden cancelada antes de pago;
- orden expirada sin pago reportado;
- pago rechazado y orden terminada sin obligacion del negocio;
- orden revertida por resolucion que no consume liquidez del negocio.

Estados que consumen capacidad:

- orden completada;
- pago entregado por el negocio;
- resolucion donde el negocio efectivamente uso la liquidez.

Cuando se consume capacidad, no se devuelve automaticamente al disponible. El negocio debe subir su disponible si quiere seguir operando.

### Capacidad efectiva

```txt
effective_available_capacity_usd =
  declared_available_capacity_usd
  - reserved_capacity_usd
```

El backend tambien debe respetar:

```txt
amount_usd >= min_order_amount_usd
amount_usd <= max_order_amount_usd
amount_usd <= effective_available_capacity_usd
amount_usd <= daily_limit_remaining_usd
business.availability = online
business.status = approved and not suspended/blocked
```

`daily_limit_usd` limita las reservas abiertas y los montos consumidos durante
el dia UTC. Liberar o cancelar una orden antes de que exista obligacion del
negocio restaura capacidad efectiva y cupo diario. El presupuesto diario se
reinicia al cambiar el dia UTC.

## Matching cliente-negocio

El cliente indica el monto que quiere cambiar.

El marketplace solo muestra negocios/anuncios donde:

```txt
amount_requested_usd between ad.amount_min_usd and ad.amount_max_usd
amount_requested_usd <= business.effective_available_capacity_usd
business is online
business is approved
ad is active and not expired
```

Si el negocio queda con menos de `min_order_amount_usd` efectivo, debe desaparecer de resultados para nuevas ordenes hasta que:

- suba su capacidad disponible;
- una orden reservada se libere;
- admin ajuste limites;
- cambie su estado operativo.

## Reserva al crear orden

`POST /api/v1/orders` debe ejecutar en una sola operacion segura:

1. validar anuncio, negocio, rango, estado y monto;
2. calcular capacidad efectiva vigente;
3. rechazar si no alcanza;
4. crear reserva de capacidad ligada a `order_id`;
5. crear orden;
6. auditar `business_capacity_reserved`.

Dos clientes al mismo tiempo no pueden reservar el mismo monto.

## Liberacion o consumo

Cada transicion relevante de orden debe actualizar la reserva:

- cancelacion antes de pago: `released`;
- expiracion antes de pago: `released`;
- pago rechazado sin obligacion: `released`;
- completada: `consumed`;
- disputa: se mantiene reservada hasta resolucion.

La operacion debe ser idempotente: repetir la misma transicion no duplica reserva, liberacion ni consumo.

## UI negocio

El negocio necesita un control simple:

```txt
Estoy online
Disponible ahora: [ 40.00 USD ]
Guardar
```

Debe ver:

- disponible declarado;
- reservado en ordenes abiertas;
- disponible real restante;
- aviso si queda bajo el minimo;
- boton para ponerse offline.

## UI cliente

El cliente debe elegir monto antes o durante la busqueda. La lista debe mostrar solo opciones que pueden cubrirlo.

Texto recomendado:

```txt
Disponible para tu monto
```

No mostrar el monto exacto disponible al cliente salvo aprobacion posterior del Owner.

## UI admin

Admin debe ver por negocio:

- capacidad declarada;
- capacidad reservada;
- capacidad efectiva;
- limite por operacion;
- limite diario;
- online/offline;
- ordenes que explican reservas.

Admin puede ajustar capacidad y limites con audit log.

## No custodia

Esta capacidad no representa fondos custodiados por NODO. Es una declaracion operativa del negocio para controlar matching y prevenir ordenes imposibles.
