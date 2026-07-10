# ERROR_CASES.md

- `BOT_CONTACT_REQUIRED`: falta contacto compartido o `contact.user_id` no coincide con `telegram_user_id`.
- `BOT_UPLOAD_INVALID`: MIME no permitido, video en MVP, archivo mayor a 5 MB o archivo invalido.
- `BUSINESS_INTAKE_NOT_FOUND`: solicitud no existe o no pertenece al contexto seguro del bot.
- `BUSINESS_INTAKE_STATUS_INVALID`: accion no permitida para estado actual.
- `STORAGE_UNAVAILABLE`: storage privado no disponible.
- `STORAGE_UPLOAD_FAILED`: fallo seguro al subir archivo.
- `RATE_LIMITED`: demasiados updates o uploads.
- `FORBIDDEN`: webhook/firma invalida.
- `VALIDATION_ERROR`: payload invalido.

Todos los errores deben ser seguros, sin stack traces, secretos, tokens ni `storage_path`.
