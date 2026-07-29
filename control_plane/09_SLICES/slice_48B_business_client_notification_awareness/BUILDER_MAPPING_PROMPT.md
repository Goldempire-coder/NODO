# Builder Prompt - Slice 48B Notification Awareness Mapping

Actua como Builder en modo inspeccion para NODO.

## Skills Que Puedes Usar

Usa estos skills antes de trabajar:

- `spec-driven-development`
- `code-review-and-quality`
- `security-and-hardening`
- `observability-and-instrumentation`
- `performance-optimization`
- `frontend-ui-engineering`
- `api-and-interface-design`
- `documentation-and-adrs`
- `git-workflow-and-versioning`

## Autoridad

AFOS y los contratos del repo mandan. Este prompt solo autoriza inspeccion y
mapeo. No implementes codigo, no hagas deploy, no ejecutes migraciones, no
toques produccion, no agregues dependencias y no cambies secretos.

Trabaja sobre:

`control_plane/09_SLICES/slice_48B_business_client_notification_awareness/`

## Objetivo

Mapear como funcionan hoy las notificaciones de Mini App Negocio y Mini App
Cliente, dentro y fuera de Telegram, para evitar que un negocio o cliente no se
entere de:

- una orden nueva;
- un pago reportado;
- un mensaje nuevo en chat de orden;
- una respuesta de soporte;
- un cierre/resolucion de soporte;
- una cancelacion antes de pago;
- una alerta importante que requiere accion.

## Preguntas Que Debes Responder

1. Si el negocio esta fuera de la app, que eventos le llegan por Telegram?
2. Si el cliente esta fuera de la app, que eventos le llegan por Telegram?
3. Si el negocio esta dentro de la app, donde ve burbujas, badges o avisos?
4. Si el cliente esta dentro de la app, donde ve burbujas, badges o avisos?
5. Los mensajes de chat cliente-negocio avisan a la contraparte?
6. Las respuestas de soporte avisan al participante?
7. Los deep links abren exactamente la orden/chat/ticket correcto?
8. Que pasa si Telegram falla temporal o permanentemente?
9. Que polling existe hoy y cuanto puede costar?
10. Que datos privados podrian filtrarse si hacemos esto mal?

## Archivos A Revisar

Revisa al menos:

- `apps/api/app/modules/notifications/`
- `apps/api/app/modules/orders/`
- `apps/api/app/modules/chat/`
- `apps/api/app/modules/support/`
- `apps/api/app/main.py`
- `apps/api/app/core/config.py`
- `apps/web/src/hooks/useBusinessMiniAppModel.ts`
- `apps/web/src/hooks/business-mini-app/`
- `apps/web/src/screens/business-app/`
- `apps/web/src/hooks/useClientWorkspaceModel.ts`
- `apps/web/src/hooks/workspace/`
- `apps/web/src/screens/client/`
- `apps/web/src/api/`
- contratos relevantes en `control_plane/06_API_CONTRACTS/`
- reglas relevantes en `control_plane/03_DOMAIN_RULES/`

## Entregable

Entrega un reporte con este formato:

```markdown
# Slice 48B Mapping Report

## 1. Estado
INSPECTION_COMPLETE_READY_FOR_OWNER_REVIEW

## 2. Repo
- Rama:
- Head:
- Estado git:
- Archivos modificados: ninguno

## 3. Mapa Actual
Tabla:
Evento | Productor actual | Receptor | Canal Telegram | Aviso dentro de app | Deep link | Dedupe | Estado

## 4. Hallazgos
Ordenados por severidad:
- CRITICAL
- HIGH
- MEDIUM
- LOW

## 5. Brechas Principales
Explica en lenguaje simple donde Negocio o Cliente pueden quedarse ciegos.

## 6. Plan Recomendado
Divide en mini tareas:
- backend productores faltantes;
- unread counts livianos;
- badges UI negocio;
- badges UI cliente;
- deep links;
- pruebas;
- staging smoke.

## 7. Archivos Probables
Lista exacta.

## 8. Pruebas Propuestas
Lista exacta.

## 9. Riesgos
Privacidad, costo, duplicados, Telegram, Redis/API.

## 10. Confirmaciones
No runtime changes, no deploy, no migration, no secrets, no production.
```

## Reglas

- No digas que algo funciona sin evidencia.
- No uses mensajes privados como prueba visible.
- No inventes WebSocket ni push nativo.
- No aumentes polling sin medir costo.
- Si encuentras conflicto de contrato, marca `BLOCKED_BY_CONTRACT_CONFLICT`.
- Si falta informacion, marca `UNKNOWN` y di que evidencia falta.
