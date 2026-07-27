# Slice 46A - Admin Operational Search

Estado: DRAFT

## Objetivo

Agregar una lupa operativa en Admin Web para investigar problemas donde soporte
recibe solo una pista parcial:

- telefono o Telegram de cliente;
- nombre, ID o codigo de referencia de negocio;
- codigo publico de orden;
- ID o asunto de ticket;
- solicitud de intake todavia no aprobada.

La busqueda es solo lectura. No resuelve casos, no cambia estados, no descarga
adjuntos y no lee cuerpos de mensajes como fuente de busqueda.

## Problemas Que Cubre

- Cliente dice que pago, pero no recuerda el negocio.
- Cliente cerro la app y no sabe llegar a la conversacion.
- Negocio o cliente abrieron ticket y soporte necesita encontrar la orden.
- Negocio entro con codigo de referencia y Admin necesita ubicar la solicitud.
- Admin tiene un ID suelto y necesita saber si pertenece a cliente, negocio,
  intake, orden o soporte.

## Fuentes Externas Revisadas

- Stripe recomienda ordenar evidencia por tipo y cronologia en disputas:
  https://docs.stripe.com/disputes/best-practices
- Square centraliza el detalle de disputa, evidencia, estado y fecha limite:
  https://squareup.com/help/us/en/article/3882-payment-disputes-walkthrough
- Amazon Pay pide fecha, monto, ID de orden/transaccion y descripcion del
  problema para investigar disputas:
  https://pay.amazon.com/help/201754740
- Zelle advierte que no siempre puede revertir pagos enviados a usuarios
  inscritos, por eso NODO debe ubicar evidencia rapido:
  https://www.zelle.com/help-center
- Airbnb prohibe pagos/comunicacion fuera de plataforma para reducir perdida de
  control y soporte:
  https://www.airbnb.com/help/article/2799

## Fuera De Alcance

- Crear un expediente formal de caso.
- Busqueda full-text dentro de mensajes privados.
- Descargar adjuntos desde resultados.
- Cambiar estados de orden, ticket, negocio o usuario.
- Automatizar decisiones de fraude.
- Backfill, migraciones o nuevos indices.
