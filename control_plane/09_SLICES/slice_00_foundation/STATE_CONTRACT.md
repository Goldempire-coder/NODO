# STATE_CONTRACT.md

Official state behavior for this slice:

No domain state changes. Only infrastructure readiness states.

Rules:

- No state outside 04_DATA/ENUMS_AND_STATUS_MASTER.md.
- All transitions go through a state machine/service.
- Transitions must validate actor, ownership, current state and allowed next state.
- State changes must create audit events.
- If a state conflict appears, stop with BLOCKED_BY_CONTRACT_CONFLICT.