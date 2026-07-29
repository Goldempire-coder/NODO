# Slice 48B Scope

Estado: CONTRACTS_DRAFT_READY_FOR_BUILDER_MAPPING

## Incluido En El Mapeo

- Revisar que eventos de orden ya generan Telegram para Negocio y Cliente.
- Revisar si mensajes de chat cliente-negocio generan aviso a la contraparte.
- Revisar si respuestas de soporte generan aviso al participante.
- Revisar si Mini App Negocio tiene badges o solo aviso temporal.
- Revisar si Mini App Cliente tiene badges o solo aviso temporal.
- Revisar deep links actuales desde Telegram hacia orden, chat y soporte.
- Revisar dedupe, retry y fallos permanentes de Telegram.
- Revisar costo actual de polling en negocio, cliente, soporte y chat.
- Proponer un contrato de no leidos por superficie.
- Proponer UI minima nativa: badge, banner y accion directa.
- Proponer pruebas antes de implementar.

## Incluido En Una Implementacion Posterior

Solo con aprobacion del Owner:

- Endpoint liviano de unread counts para Negocio y Cliente.
- Productores de eventos faltantes para chat y soporte.
- Badges en navegacion inferior.
- Banner interno accionable.
- Marcado de leido por orden/chat/ticket.
- Pruebas backend, frontend estaticas y smoke manual en staging.

## Fuera Del Alcance

- WebSocket o push nativo real.
- Migrar proveedores.
- Cambiar Telegram bots o tokens.
- Cambios de pagos, creditos, USDC, Zelle, reputacion o capacidad.
- Cambios a estados de orden, disputa o soporte.
- Crear un sistema de marketing notifications.
- Mostrar cuerpos completos de mensajes dentro de badges o notificaciones.
- Notificaciones con datos bancarios, wallets, comprobantes, storage paths o
  URLs firmadas.

## Regla AFOS

Una notificacion importante debe responder tres preguntas sin revelar privado:

- Que paso.
- Donde debo tocar para verlo.
- Si requiere accion ahora o solo es informativa.
