# AUTH_TELEGRAM.md

Contrato de autenticacion para Telegram Mini App.

## Flujo

1. Frontend obtiene `initData` desde Telegram Mini App SDK.
2. Frontend envia `initData` al backend.
3. Backend valida firma con bot token.
4. Backend crea o actualiza usuario.
5. Backend emite session JWT corto.
6. Frontend usa JWT para APIs.

## Reglas

- Prohibido confiar en datos de Telegram enviados sin validar.
- Prohibido validar initData solo en frontend.
- Rechazar initData expirado.
- Rechazar hash invalido.
- No guardar bot token en frontend.
- Telegram ID interno no debe mostrarse como identificador publico.
- Endpoint canonico: `POST /api/v1/auth/telegram`.
- Endpoint antiguo prohibido: `POST /auth/telegram-login`.

## Sesion

- JWT corto.
- Refresh controlado.
- Usar tabla `sessions` en MVP.
- Guardar solo `refresh_token_hash`, nunca refresh token plano.
- Refresh rota token y actualiza sesion.
- Logout invalida/revoca sesion.
- Usuarios suspendidos no pueden operar.

## Errores

- TELEGRAM_INIT_DATA_INVALID.
- TELEGRAM_INIT_DATA_EXPIRED.
- USER_SUSPENDED.
- SESSION_EXPIRED.

## Tests

- initData valido.
- initData con hash invalido.
- initData expirado.
- usuario nuevo.
- usuario existente.
- usuario suspendido.
