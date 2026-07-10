# Architecture Refactor Report - Business Intake Bot

## Estado

PASSED_AFTER_REFACTOR

## Objetivo

Reducir complejidad en `apps/api/app/modules/business_intake/service.py` sin cambiar comportamiento del bot de negocios, endpoints, storage, estados, mensajes, RBAC ni reglas de negocio.

## Cambios realizados

- `process_telegram_update` ahora delega:
  - parseo/validacion de update Telegram
  - respuesta vacia para updates no manejables
  - start/draft del intake
  - busqueda o creacion de intake activo
  - paso legacy de contacto compartido
- `_handle_text_step` ahora delega:
  - submit por texto `finalizar`
  - calculo de campos/transicion por step
- `_admin_review` ahora delega:
  - armado de payload de negocio
  - creacion de negocio desde intake cuando admin lo pide

## Medicion despues del corte

- `process_telegram_update`: 80 lineas
- `_handle_text_step`: 42 lineas
- `_conversation_fields_for_step`: 57 lineas
- `_maybe_create_business_from_intake`: 41 lineas
- `_admin_review`: 50 lineas

## Validacion ejecutada

- Bot/intake specific tests: `22 passed, 1 warning`
- Backend pytest completo: `133 passed, 1 warning`
- Ruff: passed
- Compileall: passed
- Frontend build: passed

## Scope no tocado

- No cambie copy del bot.
- No cambie endpoints.
- No cambie migraciones.
- No cambie frontend.
- No cambie storage privado.
- No cambie creacion/aprobacion/link de negocio.
- No hice deploy.
- No declare `READY_FOR_REAL_USE`.

## Riesgo residual

`business_intake/service.py` sigue siendo un service grande porque concentra API publica, flujo conversacional, documentos y admin review. El corte actual deja el flujo principal mas legible sin partir archivos aun. El siguiente corte recomendado, si se decide continuar, es mover la conversacion del bot a un archivo dedicado tipo `conversation.py`.
