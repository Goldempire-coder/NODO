# SECURITY_CONTRACT.md

Security requirements for `slice_06_business_order_ops`.

## Auth/RBAC/ownership

- Require auth JWT on every endpoint.
- Require active `business_owner`.
- Load approved business owned by actor.
- Allow only orders whose `orders.business_id` belongs to actor business.
- Do not leak existence of foreign orders.
- Do not allow `business_operator` in MVP.
- Do not allow admin/support mutations in this slice.

## Controls

- Backend RBAC, not frontend-only hiding.
- Ownership checks for user/business/order resources.
- State machine checks for every mutation.
- Rate limits on list/detail/confirm/reject/deliver.
- `Idempotency-Key` on confirm/reject/deliver.
- Audit log for every sensitive state/data change.
- State event for every order transition.
- Safe errors following `ERROR_CONTRACT.md`.

## Sensitive data

- Never expose `storage_path`.
- Never expose tokens or secrets.
- Do not expose full payment instructions.
- Do not expose `account_value` in business list/detail unless a future contract grants it.
- `tx_hash` may be full only in business detail when needed to verify USDT; logs/audit/list use masked/truncated.

If any control is missing, stop with `BLOCKED_BY_SECURITY_GAP`.

