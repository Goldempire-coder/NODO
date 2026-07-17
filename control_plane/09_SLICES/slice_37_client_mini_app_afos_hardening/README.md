# slice_37_client_mini_app_afos_hardening

Estado contractual: `READY_FOR_OWNER_REVIEW`

## Objetivo

Endurecer la Mini App Cliente con metodo AFOS sin tocar Admin Web todavia.

Este slice organiza el flujo cliente para que las responsabilidades queden separadas:

- cliente busca negocios y crea ordenes;
- backend valida ownership, estado, limites, idempotencia y dinero;
- frontend solo muestra pantallas y llama APIs;
- acciones sensibles tienen estado propio y breadcrumb seguro;
- soporte/chat/disputa no exponen adjuntos privados ni rutas internas;
- el repo queda listo para probar Admin Web despues.

## Alcance construido

- Helper compartido de telemetria de acciones en `apps/web/src/hooks/actionTelemetry.ts`.
- Estados por accion en Mini App Cliente para marketplace, ordenes, pagos, chat, disputa y soporte.
- Botones con feedback especifico: `Buscando...`, `Creando...`, `Subiendo...`, `Enviando...`, `Abriendo...`.
- Breadcrumbs seguros para acciones criticas del cliente.
- Matriz AFOS y matriz de acciones sensibles.

## Fuera de alcance

- No Admin Web.
- No deploy.
- No produccion.
- No reglas financieras nuevas.
- No Base USDC.
- No Zelle negocio.
- No migraciones.
- No cambios de API contract backend.
- No `READY_FOR_REAL_USE`.

## Resultado permitido

- `READY_FOR_OWNER_REVIEW`
- `BLOCKED_BY_EVIDENCE`

## Resultado no permitido

- `READY_FOR_REAL_USE`
- `APPROVED_FOR_PRODUCTION`
- `PRODUCTION_READY`
