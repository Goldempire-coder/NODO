# STATE_CONTRACT.md

Official business verification states:

- pending
- approved
- rejected
- suspended
- blocked

Draft form state may exist in UI/submission workflow, but it is not a `business.verification_status` enum unless explicitly added later.

`under_review` is not a verification status. It belongs to `business.risk_level`.

Rules:

- No state outside 04_DATA/ENUMS_AND_STATUS_MASTER.md.
- All transitions go through a state machine/service.
- Transitions must validate actor, ownership, current state and allowed next state.
- State changes must create audit events.
- If a state conflict appears, stop with BLOCKED_BY_CONTRACT_CONFLICT.

Allowed transitions:

- UI/workflow draft -> business.verification_status pending when business record is created.
- pending -> approved by admin/super_admin.
- pending -> rejected by admin/super_admin with reason.
- rejected -> pending when owner resubmits verification.
- approved -> suspended by admin/super_admin in a later/admin-capable flow.
- suspended -> approved by admin/super_admin in a later/admin-capable flow.
- approved/suspended -> blocked by admin/super_admin in a later/admin-capable flow.

Slice 02 implements create/pending, resubmit from rejected, approve and reject only. Suspended/blocked are official states but not full management flows in this slice unless explicitly approved later.
