# Architecture Refactor Report - Business Intake Conversation Split

## Estado

PASSED_AFTER_REFACTOR

## Objetivo

Separar la conversacion Telegram del Bot Registro Negocios fuera de `BusinessIntakeService`, sin cambiar comportamiento, endpoints, textos, estados, storage ni reglas de negocio.

## Cambios realizados

- Cree `apps/api/app/modules/business_intake/conversation.py`.
- Movi al nuevo modulo:
  - prompts del bot
  - boton `Comenzar registro`
  - envio de mensajes Telegram
  - descarga de archivos Telegram
  - parseo de update/message
  - idempotencia conversacional por update
  - manejo de `/start`
  - flujo de pasos
  - `finalizar`
  - documentos recibidos por Telegram
- `BusinessIntakeService.process_telegram_update` queda como delegador.
- Mantengo compatibilidad con tests existentes que monkeypatchean `service.telegram_send_message` y `service.telegram_download_file`.
- `service.py` conserva endpoints REST, admin review, uploads REST y serializacion admin.

## Medicion despues del corte

- `apps/api/app/modules/business_intake/service.py`: 423 lineas
- `apps/api/app/modules/business_intake/conversation.py`: 642 lineas
- `service.py process_telegram_update`: 5 lineas
- `conversation.py process_telegram_update`: 80 lineas
- `conversation.py _handle_text_step`: 42 lineas
- `service.py _admin_review`: 50 lineas

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
- No cambie reglas de aprobacion/link/acceso de negocio.
- No hice deploy.
- No declare `READY_FOR_REAL_USE`.

## Riesgo residual

`conversation.py` ya esta dedicado al bot, pero todavia concentra conversacion y documentos Telegram. El siguiente corte recomendado es separar documentos Telegram/storage en un modulo `documents.py` o `telegram_documents.py`.
