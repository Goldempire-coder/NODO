# AUTH_API.md

Contrato canonico de autenticacion Telegram.

## Regla de versionado

Todas las rutas auth usan prefijo:

```txt
/api/v1
```

Endpoint antiguo prohibido:

```txt
POST /auth/telegram-login
```

## POST /api/v1/auth/telegram

Valida `initData` de Telegram Mini App en backend y crea/actualiza usuario.

Request:

```json
{
  "init_data": "query-string-from-telegram"
}
```

Response 200:

```json
{
  "data": {
    "access_token": "jwt",
    "refresh_token": "opaque-refresh-token",
    "token_type": "Bearer",
    "expires_in": 900,
    "user": {
      "id": "uuid",
      "username": "string|null",
      "first_name": "string|null",
      "last_name": "string|null",
      "role": "remitter",
      "status": "active"
    }
  },
  "request_id": "req_..."
}
```

Rules:

- Validar firma/hash de Telegram con `BOT_TOKEN`.
- Rechazar `initData` expirado.
- No aceptar datos Telegram enviados sin firma valida.
- No guardar raw `initData`.
- No exponer `telegram_id` como identificador publico.
- Crear `sessions` con `refresh_token_hash`; nunca guardar refresh token plano.
- Auditar `user_created` si crea usuario.
- Auditar `user_login` si autentica.
- Auditar `auth_failed` si falla validacion.

## POST /api/v1/auth/refresh

Renueva access token usando refresh token.

Request:

```json
{
  "refresh_token": "opaque-refresh-token"
}
```

Response 200:

```json
{
  "data": {
    "access_token": "jwt",
    "refresh_token": "opaque-refresh-token",
    "token_type": "Bearer",
    "expires_in": 900
  },
  "request_id": "req_..."
}
```

Rules:

- Buscar por hash del refresh token.
- Rechazar sesion revocada o expirada.
- Rotar refresh token en cada refresh.
- Actualizar `sessions.last_used_at`.
- Auditar `session_refreshed`.

## POST /api/v1/auth/logout

Revoca la sesion actual.

Request:

```json
{
  "refresh_token": "opaque-refresh-token"
}
```

Response 200:

```json
{
  "data": {
    "logged_out": true
  },
  "request_id": "req_..."
}
```

Rules:

- Requiere access token valido.
- Revoca la fila `sessions`.
- Logout repetido debe ser seguro/idempotente.
- Auditar `user_logout`.

## Errores esperados

- TELEGRAM_INIT_DATA_INVALID
- TELEGRAM_INIT_DATA_EXPIRED
- USER_SUSPENDED
- SESSION_EXPIRED
- UNAUTHENTICATED
- RATE_LIMITED

