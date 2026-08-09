# Slice 42D0 Rating Pause, Operation Report And Publication Hold Contract

Estado: `OWNER_APPROVED_CONTRACT_RECONCILIATION`

## Objetivo

Definir, sin implementar runtime, una ventana operativa posterior a cada rating,
un reporte de operacion ligado a una orden real y un hold de publicacion que
requiere liberacion administrativa.

Este slice gobierna los futuros slices:

- `42D1`: persistencia transaccional de la pausa por rating;
- `42D2`: guard de publicacion, marketplace y creacion directa de orden;
- `42E1`: reporte estructurado de operacion, implementado localmente sin hold;
- `42F1`: hold operativo y liberacion administrativa;
- `42F2`: alerta Telegram Admin idempotente.

## Decisiones cerradas

- Todo rating valido de 1 a 5 activa la misma pausa de 15 minutos. Aplicarla
  solo a ratings bajos permitiria inferir la calificacion individual.
- La pausa cubre al negocio completo y todos sus anuncios Zelle y USDT.
- La pausa no cambia el estado del anuncio, no mueve creditos, no cambia
  capacidad financiera y no modifica reputacion publica.
- La pausa esta activa mientras `database_now < ad_publication_paused_until` y
  vence cuando `database_now >= ad_publication_paused_until`. Esta frontera
  evita que el mismo instante sea activo y vencido a la vez.
- El cliente reporta una operacion fuera del chat y selecciona una orden propia.
  El backend deriva el negocio desde la orden.
- Un reporte creado mientras la pausa esta activa crea un hold durable. El hold
  no vence con la pausa ni se libera al cerrar el ticket.
- Admin y Super Admin pueden liberar un hold. Support solo puede hacerlo con el
  permiso explicito `release_business_publication_hold`; el rol base no basta.
- La alerta Telegram se dirige a usuarios Admin/Super Admin activos con Telegram
  vinculado. No se crea un job por `recipient_role` sin destinatario concreto.

## Estados reportables

Son reportables:

- `payment_confirmed`;
- `delivered`;
- `completed`;
- `payment_rejected`;
- `disputed`;
- `cancelled`.

No son reportables:

- `waiting_payment`;
- `payment_reported`;
- `expired`;
- orden inexistente o ajena.

`payment_reported` mantiene su flujo P2P/disputa vigente. El reporte estructurado
no reemplaza una disputa ni muta la orden. No se establece un limite adicional
por antiguedad en 42D0: una orden retenida en Historial puede reportarse una vez,
pero solo un reporte creado durante la pausa activa puede crear hold.

## Superficies

Entradas permitidas: Soporte, Mis ordenes y una futura vista Historial si existe.
42E1 agrega la accion compacta en el detalle de Mis ordenes sin entrada desde el
chat. Un selector adicional dentro de Soporte o Historial queda fuera mientras
la accion de orden cubra el flujo aprobado.

Entradas prohibidas: chat P2P, negocio escrito manualmente, busqueda manual de
negocio y ticket generico usado como autoridad para restringir publicacion.

## No autorizado por este contrato

- runtime, migraciones, endpoints, UI, jobs o scheduler dentro de 42D0;
- cambios de pagos, creditos, capacidad financiera o reputacion publica;
- notificaciones al negocio por rating o reporte;
- `READY_FOR_REAL_USE`, deploy, staging o produccion.
