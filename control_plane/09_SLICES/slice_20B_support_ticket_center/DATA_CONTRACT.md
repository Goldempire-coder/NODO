# DATA_CONTRACT.md

## Tablas

### support_tickets

Columnas:
- `id uuid primary key`
- `requester_user_id uuid not null`
- `requester_role text not null`
- `requester_surface text not null`
- `business_id uuid null`
- `order_id uuid null`
- `ad_id uuid null`
- `credit_purchase_id uuid null`
- `assigned_support_user_id uuid null`
- `scope text not null`
- `category text not null`
- `status text not null`
- `priority text not null default 'normal'`
- `subject text not null`
- `last_message_at timestamptz null`
- `escalated_at timestamptz null`
- `resolved_at timestamptz null`
- `closed_at timestamptz null`
- `created_at timestamptz not null`
- `updated_at timestamptz not null`

Rules:
- Reemplaza `created_by_user_id` por nombre canonico `requester_user_id` para 20B.
- `requester_surface` permite `client_mini_app`, `business_mini_app`, `admin_web`.
- `ad_id` solo se usa con `scope = business_ad`.
- `credit_purchase_id` solo se usa con `scope = business_credit`.
- `order_id` solo se usa con `scope in ('client_order', 'business_order')`.
- Ticket de soporte no cambia estado de orden, credito ni anuncio.

### support_messages

Columnas:
- `id uuid primary key`
- `ticket_id uuid not null`
- `sender_user_id uuid not null`
- `sender_role text not null`
- `body text not null`
- `visibility text not null`
- `created_at timestamptz not null`
- `updated_at timestamptz not null`
- `deleted_at timestamptz null`

Rules:
- Body max 2000 caracteres.
- Audit metadata no copia body completo.
- `visibility` usa `participants`, `support_internal` o `admin_internal`.

### support_ticket_events

Columnas:
- `id uuid primary key`
- `ticket_id uuid not null`
- `actor_user_id uuid not null`
- `actor_role text not null`
- `event_type text not null`
- `from_status text null`
- `to_status text null`
- `reason text null`
- `metadata_json jsonb not null default '{}'`
- `created_at timestamptz not null`

Rules:
- Append-only.
- No contiene body completo, `storage_path`, signed URLs, tokens, secretos, `account_value` ni evidencia privada completa.

## Adjuntos

No se crea tabla `support_attachments` en MVP.

Todo adjunto usa `file_assets`:
- `resource_type = support_ticket` para adjunto inicial de ticket.
- `resource_type = support_message` para adjunto de mensaje.
- `file_type = support_attachment`.
- MIME permitido: `image/jpeg`, `image/png`, `image/webp`, `application/pdf`.
- Tamano maximo: 5 MB.
- Storage privado.
- `storage_path` solo vive internamente y nunca se expone.

## Indices requeridos

- `support_tickets(requester_user_id, status, updated_at desc)`.
- `support_tickets(business_id, status, updated_at desc)` parcial cuando `business_id is not null`.
- `support_tickets(order_id, created_at desc)` parcial cuando `order_id is not null`.
- `support_tickets(ad_id, created_at desc)` parcial cuando `ad_id is not null`.
- `support_tickets(credit_purchase_id, created_at desc)` parcial cuando `credit_purchase_id is not null`.
- `support_tickets(assigned_support_user_id, status, updated_at desc)` parcial cuando `assigned_support_user_id is not null`.
- `support_tickets(scope, category, status, priority, updated_at desc)`.
- `support_messages(ticket_id, created_at asc)`.
- `support_ticket_events(ticket_id, created_at asc)`.
