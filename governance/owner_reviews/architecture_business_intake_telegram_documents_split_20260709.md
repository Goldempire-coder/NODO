# Architecture Refactor Report - Business Intake Telegram Documents Split

## Estado

PASSED_AFTER_REFACTOR

## Objetivo

Separar el manejo de documentos enviados por Telegram fuera del flujo conversacional del Bot Registro Negocios, sin cambiar comportamiento, validaciones, storage, respuestas ni contratos.

## Cambios realizados

- Cree `apps/api/app/modules/business_intake/telegram_documents.py`.
- Movi al nuevo modulo:
  - deteccion de media prohibida
  - deteccion de archivos permitidos
  - extraccion de `file_id`, `file_unique_id`, nombre, MIME, tamano y tipo de documento
  - validacion de MIME/tamano
  - descarga del archivo Telegram via callback
  - storage privado en `file_assets`
  - dedupe por update/file
  - audit `business_intake_document_uploaded`
  - payload publico de documento sin `storage_path`
- `conversation.py` ahora solo decide cuando una actualizacion es archivo y delega.
- `service.py` conserva uploads REST y admin/API publica.

## Medicion despues del corte

- `service.py`: 423 lineas
- `conversation.py`: 520 lineas
- `telegram_documents.py`: 181 lineas
- Bot/intake `process_telegram_update` en `service.py`: 5 lineas

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
- No cambie reglas de documentos: MIME, 5 MB, storage privado, no `storage_path`.
- No cambie aprobacion/link/acceso de negocios.
- No hice deploy.
- No declare `READY_FOR_REAL_USE`.

## Riesgo residual

`conversation.py` todavia contiene el estado paso a paso completo. Esta bien para el corte actual. El siguiente candidato real es separar el contrato de pasos/transiciones a un modulo pequeno, o pasar a otro hotspot: `orders/service.py`.
