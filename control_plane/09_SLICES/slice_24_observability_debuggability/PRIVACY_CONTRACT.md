# PRIVACY_CONTRACT - slice_24_observability_debuggability

## Privacy posture

NODO observability records operational facts, not private content.

Allowed examples:

- route template;
- status code;
- duration;
- safe error code;
- screen/view name;
- action name;
- masked user id;
- resource ids when the viewer is authorized;
- coarse online/offline state;
- app version/build id.

Disallowed examples:

- message bodies;
- document contents;
- exact phone numbers unless future contract grants reveal;
- full tx hashes;
- full payment instructions;
- signed URLs;
- raw Telegram updates;
- raw webhook payloads;
- raw request/response bodies.

## Masking

Minimum masking:

- `user_id_masked`: `usr_****abcd` or equivalent non-sensitive display.
- `phone`: `+58*******123`.
- `tx_hash_masked`: `0xabc...789`.
- `telegram_update_id`: allowed because it is operational, not authorization.

Admin/super_admin may see internal resource IDs when needed. Support and staff see only what their scope allows.

## Export

Diagnostic exports must be redacted. Exporting observability evidence creates an audit event and cannot include secrets or private payloads.
