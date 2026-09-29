# STATE_CONTRACT.md

Official state behavior for this slice.

## ad.status

- draft
- active
- in_order
- paused
- expired
- archived
- suspended

## Transitions in slice 03

- `draft -> active`: publish ad; validates approved business and sufficient credits; always blocks credits, without Founder exemption.
- `active -> paused`: owner pauses; does not change `expires_at`.
- `paused -> active`: allowed only if `expires_at > now()` and business remains approved.
- `active -> expired`: passive expiration materialized when service reads or mutates a vencido ad.
- `paused -> expired`: same passive expiration; pausing does not extend lifetime.
- `paused -> archived`: owner archives.
- `expired -> archived`: owner archives historical ad.

## Transitions reserved for future slices

- `active -> in_order`: `slice_04_order_creation`.
- `in_order -> active|archived`: order/payment state machine in later slices.
- `any -> suspended`: admin/risk flow in admin/risk slices unless owner authorizes endpoint in slice 03.

## Expiration decision

Slice 03 implements passive/materialized expiration:

- Search excludes vencido ads even if persisted `status` is still `active` or `paused`.
- Detail can return `AD_NOT_AVAILABLE` or effective `expired`.
- Mutations over vencido active/paused ads must first materialize `status = expired`.
- Materialization writes audit event `ad_expired`.
- If there is no active order/payment and the ad has a credit hold, materialization must release hold via credit service and write `credits_released`.
- Bulk worker expiration remains in `slice_10_jobs_notifications`.

## Rules

- No state outside `04_DATA/ENUMS_AND_STATUS_MASTER.md`.
- All transitions go through a state machine/service.
- Transitions validate actor, ownership, business status, current state and allowed next state.
- State changes create audit events.
- Pausing never changes `expires_at`.
- If a state conflict appears, stop with `BLOCKED_BY_CONTRACT_CONFLICT`.
