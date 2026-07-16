# UI_CONTRACT - slice_24_observability_debuggability

## Frontend surfaces

Mini App Cliente, Mini App Negocio and Admin Web may capture safe breadcrumbs only when enabled by env and backend policy.

No user-facing redesign is part of this slice.

## Error UI

Critical user-facing errors should show:

- safe message;
- `request_id`;
- `correlation_id` when available;
- no stack trace;
- no internal route, SQL or secrets.

## Admin Web diagnostic view

Future Admin Web may include Observability/Diagnostics view with:

- search by `request_id`, `correlation_id`, `session_id`, resource id and date;
- timeline of redacted events;
- filters by surface, status and error code;
- export redacted evidence;
- role-based masking.

Support must not see financial/private documents unless a separate permission and contract allow it.

## No video replay

The UI must not record video, screenshots, DOM snapshots or complete user messages.
