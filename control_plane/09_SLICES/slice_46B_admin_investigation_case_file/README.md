# Slice 46B - Admin Investigation Case File

Estado: DRAFT

## Objetivo

Crear el contrato para una ficha de investigacion en Admin Web.

46A permite encontrar una pista. 46B debe permitir abrir un expediente de solo
lectura para entender rapidamente que paso alrededor de esa pista, sin saltar a
ciegas entre Negocios, Clientes, Ordenes, Soporte, Intake y Audit.

La ficha no decide culpa, no recupera dinero, no promete garantia y no cambia
estados. Solo organiza evidencia autorizada para que soporte/admin pueda
investigar con orden.

## Problemas Que Cubre

- Cliente dice que envio dinero, pero no recuerda el negocio.
- Cliente cerro la app y no sabe llegar a la conversacion.
- Ticket se archivo o se cerro y soporte necesita reconstruir que paso.
- Negocio entro con codigo de referencia y Admin necesita verlo junto a su
  solicitud, ficha creada y negocio aprobado.
- Hay varios tickets sobre la misma orden o usuario y soporte necesita unir el
  contexto.
- Una alerta de chat fuera de plataforma abre una orden y Admin necesita ver
  mensajes, ticket, negocio, cliente y timeline en el mismo lugar.
- Negocio dice que el cliente nunca pago, pero existe reporte de pago o
  conversacion relacionada.
- Cliente reporta pago a un nombre parecido y soporte necesita comparar ordenes
  recientes, montos, negocios y timestamps.

## Fuentes Externas Revisadas

- Stripe recomienda organizar evidencia por cronologia y tipo:
  https://docs.stripe.com/disputes/best-practices
- Square centraliza disputa, evidencia, estado y fecha limite desde el
  dashboard:
  https://squareup.com/help/us/en/article/3882-payment-disputes-walkthrough
- Amazon Pay pide fecha, monto, ID de orden/transaccion y descripcion del
  problema para investigar disputas:
  https://pay.amazon.com/help/201754740
- Airbnb prohibe pagos y comunicacion fuera de plataforma para mantener control
  operativo:
  https://www.airbnb.com/help/article/2799

## Que Debe Mostrar La Ficha

- Resumen factual: pista inicial, anchor, estado, ultima actividad y conteos.
- Personas y negocio: cliente, negocio, owner, telefono/Telegram enmascarado y
  links internos.
- Ordenes relacionadas: codigo publico, monto, estado, fechas y negocio.
- Tickets relacionados: activos y archivados, estado, creador y ultima
  actividad.
- Intake/registro: codigo de referencia, datos minimos de solicitud y negocio
  creado, si existe.
- Evidencia segura: existencia de comprobantes, adjuntos y documentos por
  metadata, sin descarga automatica.
- Timeline: eventos clave en orden cronologico.
- Rutas de accion: abrir orden, abrir ticket, abrir negocio, abrir cliente,
  abrir intake o abrir visor de chat autorizado.
- Checklist deterministico de revision, basado solo en datos presentes o
  ausentes. No debe recomendar culpables ni inventar conclusion.

## Que No Construye

- No busca texto dentro de todos los mensajes privados.
- No descarga adjuntos automaticamente.
- No muestra signed URLs ni paths de storage.
- No exporta expedientes.
- No crea score de fraude ni declara culpables.
- No cambia estados de orden, ticket, negocio, cliente o intake.
- No reabre tickets.
- No borra datos.
- No toca pagos, creditos, Base USDC, Zelle, reputacion ni bots Telegram.
- No ejecuta migraciones ni deploy.

## Decision Cerrada

La ficha debe ser carga lazy desde Admin Web. La busqueda 46A sigue liviana. El
expediente 46B se carga solo cuando Admin decide investigar un resultado.

Despues de la inspeccion del Builder, la decision es crear endpoint admin
dedicado de solo lectura:

```txt
GET /api/v1/admin/investigation/case-file
```

No se debe componer la ficha en frontend usando cinco endpoints detallados,
porque eso aumenta payload, acopla pantallas y puede exponer datos privados de
mas.

## Reglas Cerradas

- No usar `severity_hint`.
- No usar `suggested_next_step`.
- No usar frases como "probable fraude", "culpa", "pago valido" o
  "recuperable".
- Si se necesita orientar a Admin, usar `review_checklist` con checks
  deterministas: presente, ausente, no revisado o no autorizado.
- `support` activo solo ve lo permitido por la politica de soporte. Si el anchor
  no es visible para ese rol, el endpoint responde `404`.
- `admin` y `super_admin` pueden ver la ficha allowlist completa.
- Las secciones se paginan por separado. El cursor pertenece a una seccion y no
  puede reutilizarse en otra.
- El timeline solo usa eventos allowlist y nunca `metadata_json` crudo,
  razones privadas ni cuerpos de mensajes.

## Criterios De Aceptacion

- Admin puede abrir una ficha desde un resultado de 46A.
- La ficha responde preguntas basicas sin navegar por cinco pantallas.
- Incluye activos y archivados cuando sean parte del caso.
- No incluye cuerpos privados salvo que abra un visor autorizado especifico.
- No expone secretos, rutas de storage, signed URLs ni datos bancarios completos.
- Genera auditoria de lectura sin guardar cuerpos de mensajes ni texto libre.
- No devuelve campos opinativos como `severity_hint` o `suggested_next_step`.
- La pantalla es compacta, agrupada y scrollable.
- Un fallo en una seccion no rompe toda la ficha.
