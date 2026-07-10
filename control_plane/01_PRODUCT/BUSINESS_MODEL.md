# BUSINESS_MODEL.md

NODO monetiza con creditos comprados por negocios para publicar y operar anuncios dentro del marketplace.

## Regla principal

Los creditos son publicitarios/listing. No son comision por transaccion, no son saldo de clientes y no representan fondos de remesas.

## Paquetes

- 5 creditos = $10
- 15 creditos = $25
- 50 creditos = $75
- 200 creditos = $250

## Costo por anuncio

- $20-$100 = 1 credito
- $100-$500 = 2 creditos
- $500-$2,000 = 3 creditos
- Mas de $2,000 = fuera de MVP o revision manual

## Vida del anuncio

- 1 anuncio activo dura 7 dias desde su activacion.
- Si no genera una transaccion completada durante esos 7 dias, expira.
- Si el negocio quiere seguir visible, debe crear/renovar anuncio usando creditos.
- Si el anuncio llega a su expiracion mientras tiene una orden activa, no corta esa orden; solo impide nuevas ordenes sobre ese anuncio.

## Bloqueo, consumo y liberacion de creditos

Cada anuncio vale creditos segun el rango de monto maximo del anuncio.

- Publicar un anuncio de $20-$100 bloquea 1 credito.
- Publicar un anuncio de $100-$500 bloquea 2 creditos.
- Publicar un anuncio de $500-$2,000 bloquea 3 creditos.
- Mas de $2,000 no esta disponible en MVP o requiere revision manual.
- Un click no consume creditos.
- Crear una orden no consume creditos adicionales.
- El credito se consume cuando el negocio confirma que recibio el pago.
- El credito se libera si la orden expira o se cancela antes de pago confirmado.
- Si el anuncio expira sin pago confirmado, los creditos bloqueados se liberan.
- NODO no cobra spread ni comision monetaria sobre el monto cambiado.

### Ejemplo de bloqueo

```txt
creditos disponibles: 15
creditos bloqueados: 0

Publica anuncio de $100-$500
Costo: 2 creditos

creditos disponibles: 13
creditos bloqueados: 2
```

Los creditos todavia no se consumieron. Solo estan apartados.

### Ejemplo de liberacion

```txt
creditos disponibles: 13
creditos bloqueados: 2

Orden expiro o se cancelo antes de pago confirmado

creditos disponibles: 15
creditos bloqueados: 0
```

El negocio no pierde creditos si el cliente no pago.

### Ejemplo de consumo

```txt
creditos disponibles: 13
creditos bloqueados: 2
creditos consumidos: 0

Negocio confirma: Recibi el pago

creditos disponibles: 13
creditos bloqueados: 0
creditos consumidos: 2
```

El anuncio se archiva porque ya cumplio su funcion.

## Hold y release de orden

Esta regla protege al negocio de curiosos y evita que un mismo anuncio sea tomado varias veces al mismo tiempo.

- Click / abrir detalle del anuncio: no crea hold.
- Crear orden: genera hold temporal de disponibilidad/capacidad, no de cobro adicional.
- Si no reporta pago dentro del tiempo definido, la orden expira y el hold se libera.
- Si reporta pago, el hold se mantiene hasta confirmacion, rechazo, disputa o expiracion segun state machine.
- Si la orden se cancela o expira sin pago reportado, el negocio no pierde creditos adicionales por ese curioso.
- Si hay abuso repetido, se controla con rate limits/cooldowns del remitente, no cobrando al negocio por clicks abandonados.

## Compra de creditos

- Stripe: pago automatico, acreditacion por webhook verificado e idempotente.
- Zelle: comprobante manual, acreditacion solo por aprobacion admin.
- USDT TRC20: comprobante/hash manual, acreditacion solo por aprobacion admin.

## Fundadores

- 5 a 10 negocios fundadores.
- 1 mes gratis.
- Uso ilimitado sin cobrar creditos durante ese mes.
- Siempre respetan limites de monto/riesgo.
- No elimina verificacion, auditoria ni limites.
- Al expirar, el negocio debe comprar creditos para seguir publicando/activando anuncios.

## Referidos

- 5 creditos por negocio referido aprobado.
- Maximo 20 creditos por negocio referente.
- Se acreditan solo cuando el admin aprueba el negocio referido.
