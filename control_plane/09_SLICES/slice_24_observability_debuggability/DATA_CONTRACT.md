# DATA_CONTRACT - slice_24_observability_debuggability

## Modelo principal

Tabla contratada para futura migracion: `observability_events`.

Esta tabla almacena eventos diagnosticos redaccionados y con TTL. No es audit log formal, no es ledger financiero y no debe usarse como fuente de verdad de negocio.

Columnas:

- `id uuid primary key`
- `event_id text not null unique`
- `event_type text not null`
- `severity text not null`
- `event_timestamp timestamptz not null`
- `received_at timestamptz not null default now()`
- `request_id text null`
- `correlation_id text null`
- `operation_id text null`
- `session_id text null`
- `surface text not null`
- `app_version text null`
- `build_id text null`
- `actor_user_id uuid null`
- `user_id_masked text null`
- `business_id uuid null`
- `order_id uuid null`
- `ticket_id uuid null`
- `credit_purchase_id uuid null`
- `tx_hash_masked text null`
- `telegram_update_id bigint null`
- `webhook_source text null`
- `method text null`
- `route_template text null`
- `status_code integer null`
- `duration_ms numeric(12,3) null`
- `error_code text null`
- `screen text null`
- `previous_screen text null`
- `action text null`
- `metadata_json jsonb null`
- `expires_at timestamptz not null`

## Valores permitidos

`severity`:

- `debug`
- `info`
- `warn`
- `error`

`surface`:

- `client_mini_app`
- `business_mini_app`
- `admin_web`
- `client_bot`
- `business_intake_bot`
- `backend_api`
- `worker`
- `webhook`

`event_type`:

- `view_changed`
- `action_clicked`
- `form_submitted`
- `api_request_started`
- `api_request_completed`
- `api_request_failed`
- `auth_refresh_started`
- `auth_refresh_completed`
- `auth_refresh_failed`
- `offline`
- `online`
- `visible_error_shown`
- `critical_operation_started`
- `critical_operation_completed`
- `critical_operation_failed`
- `backend_request_completed`
- `backend_request_failed`
- `storage_failure`
- `cache_failure`
- `db_pool_saturation`
- `rate_limit_triggered`
- `idempotency_conflict`
- `webhook_received`
- `watcher_step_failed`

## Constraints

- `event_id` debe ser unico para idempotencia de ingestion.
- `metadata_json` debe estar redaccionado antes de persistir.
- `route_template` debe ser plantilla, no URL cruda con query sensible.
- `expires_at` obligatorio.
- `duration_ms` debe ser `>= 0` cuando exista.
- `status_code` debe estar entre `100` y `599` cuando exista.
- `session_id`, `correlation_id`, `operation_id` y `request_id` no pueden contener tokens ni query strings.

## Datos prohibidos

Prohibido persistir en `observability_events`, logs operativos o metadata:

- Authorization/Cookie;
- `access_token` o `refresh_token`;
- Telegram `initData` completo;
- `BOT_TOKEN` o `BUSINESS_INTAKE_BOT_TOKEN`;
- JWT secrets, service role keys, private keys, seed phrases;
- `account_value`;
- `storage_path`;
- signed URLs;
- full tx hash;
- phone completo salvo contrato explicito futuro;
- documentos completos;
- mensajes completos de chat/tickets.
