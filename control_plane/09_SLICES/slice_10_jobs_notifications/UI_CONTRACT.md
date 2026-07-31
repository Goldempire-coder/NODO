# UI_CONTRACT.md

No new public UI is required for this slice, but existing screens must reflect job-driven states.

Affected UI states:

- Remitter order timer for waiting_payment.
- One-time extension control for +15 minutes.
- Payment reported waiting for business response.
- Dispute opened because business did not confirm payment.
- Dispute opened because business confirmed payment but did not deliver.
- Delivered state with 24h auto-close warning.
- Completed with completion_reason auto_completed_after_24h.

Admin UI should show job-created disputes, job run errors and order timeline/audit events.

Slice 10 must not build `R-10_CONFIRM_RECEIVED` manual remitter confirmation.
This slice defines the automatic-completion timer contract:

```txt
delivered -> completed
completion_reason = auto_completed_after_24h
```

Slice 50B0 contracts `R-10_CONFIRM_RECEIVED`; 50B1 may implement it. Rating
remains governed by Slice 42B. Slice 10 does not own either manual action.
The automatic transition remains a contract; scheduler activation and
operational evidence must be revalidated by a later approved operational slice.
