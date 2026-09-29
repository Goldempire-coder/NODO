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

- Validar firma/hash de Telegram con `BOT_TOKEN` por defecto.
- Si `X-NODO-Surface: business_mini_app`, tambien puede validar con `BUSINESS_INTAKE_BOT_TOKEN` para permitir apertura desde Bot Registro Negocios; ese token no es valido para `client_mini_app`.
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

## Enforcement de estado autenticado

- Las operaciones privadas y cualquier mutacion deben consultar el estado
  vigente del usuario en el repositorio autoritativo en cada request.
- El `jti` del access token debe corresponder a la sesion durable activa del
  mismo usuario. Una sesion revocada, expirada o rotada devuelve
  `SESSION_EXPIRED`; un access token sin `sub`/`jti` validos devuelve
  `UNAUTHENTICATED`.
- Un JWT malformado, con firma invalida, segmentos ilegibles, JSON no valido o
  claims obligatorios ausentes/de tipo inesperado devuelve
  `401 UNAUTHENTICATED`; nunca se expone como error interno `500`.
- Un cache local de proceso no puede mantener acceso operativo despues de que
  Admin bloquee o suspenda al usuario.
- La unica excepcion permitida es la lectura publica del marketplace mediante
  claims JWT firmados dentro de la ventana corta contratada. Esa excepcion no
  autoriza chat, archivos, ordenes, pagos, entregas ni otra mutacion.
- El estado vigente del negocio y su access link tambien se revalida antes de
  acciones de la superficie Negocio.

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

- El refresh token identifica la sesion que debe cerrarse; no requiere que el
  access token siga vigente.
- Si el access token de esa sesion estaba vigente, queda invalidado de inmediato
  porque su `jti` deja de corresponder a una sesion activa.
- Revoca la fila `sessions` y su refresh token.
- No revoca otras sesiones activas del mismo usuario.
- Un access token expirado o malformado no impide cerrar la sesion identificada
  por un refresh token valido y no debe causar respuesta `500`.
- Si el refresh token no identifica una sesion activa, responder de forma
  idempotente sin revelar si la sesion existia.
- Logout repetido debe ser seguro/idempotente.
- Auditar `user_logout`.

## Identidad transitoria para limites de solicitudes

- Auth y creditos usan el mismo resolvedor y el mismo hash transitorio por request.
- `TRUSTED_PROXIES` vacio (default): ignorar `X-Forwarded-For`; usar el peer TCP.
- Solo configurar IPs/CIDRs de proxies cuya procedencia y comportamiento se hayan
  verificado. No se permiten comodines, nombres DNS ni redes `/0`. No confiar
  en redes privadas completas solo por ser privadas.
- Con peer confiable, recorrer todas las cabeceras `X-Forwarded-For` de derecha
  a izquierda, omitiendo unicamente proxies confiables. Usar el primer salto no
  confiable; ante salto malformado o cadena sin cliente no confiable, usar el peer.
- Iniciar Uvicorn con `--no-proxy-headers` (incluido en Dockerfile). De lo contrario
  puede reemplazar el peer antes de que la aplicacion aplique esta regla.
  Revisar cualquier comando de arranque alternativo; `FORWARDED_ALLOW_IPS` no
  sustituye `TRUSTED_PROXIES`.
- La identidad resuelta solo se usa para contadores con TTL en memoria/Redis;
  no se agrega a sesiones, auditoria, logs o respuestas. Se conserva el tratamiento
  existente del peer en sesiones; no se incorpora seguimiento nuevo de IP.
- Antes de un despliegue autorizado, comprobar la topologia de proxies, el
  comportamiento XFF (append/sanitize), aislamiento del origen y comandos reales.
  Sin esa evidencia, no declarar resuelto el reparto de limites en el proveedor:
  el default seguro puede agrupar usuarios tras un proxy.
- Desactivar proxy headers en Uvicorn tambien deja de interpretar
  `X-Forwarded-Proto`. Verificar HTTPS y redirecciones de barra final en staging
  antes de publicar; esta tarea no cambia configuraciones del proveedor.
- El fallback local limpia llaves caducadas en la siguiente solicitud cuando
  vence el intervalo de limpieza (60 s). No elimina contadores activos. Es local
  al proceso; no reemplaza la coordinacion Redis entre workers ni un limite de
  memoria ante cardinalidad ilimitada dentro de una ventana activa.

## Errores esperados

- TELEGRAM_INIT_DATA_INVALID
- TELEGRAM_INIT_DATA_EXPIRED
- USER_SUSPENDED
- SESSION_EXPIRED
- UNAUTHENTICATED
- RATE_LIMITED
