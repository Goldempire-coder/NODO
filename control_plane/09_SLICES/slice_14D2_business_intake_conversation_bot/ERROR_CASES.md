# ERROR_CASES.md

- `TELEGRAM_BOT_NOT_CONFIGURED`: falta `BUSINESS_INTAKE_BOT_TOKEN`.
- `FORBIDDEN`: secret invalido o bot equivocado.
- `RATE_LIMITED`: limite por IP/user/chat.
- `BOT_INPUT_INVALID`: input no corresponde al paso actual, formato invalido o texto excesivo.
- `BOT_UPLOAD_INVALID`: MIME/tipo no permitido, video/audio o archivo invalido.
- `STORAGE_UNAVAILABLE`: storage privado no disponible.
- `STORAGE_UPLOAD_FAILED`: fallo guardando archivo.
- `VALIDATION_ERROR`: monto/rango/listas no validas.

UX segura:
- No stack traces.
- No token.
- No `storage_path`.
- No prometer aprobacion.
