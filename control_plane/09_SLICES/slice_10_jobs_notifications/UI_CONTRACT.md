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
This slice only implements automatic completion by timer:

```txt
delivered -> completed
completion_reason = auto_completed_after_24h
```

`R-10_CONFIRM_RECEIVED`, manual confirmation and rating remain future contract
unless another approved slice explicitly owns them.
