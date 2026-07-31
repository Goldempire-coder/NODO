# Scope

## Included

- Reconcile the eight persisted order states used by the final P2P flow.
- Define the exact credit and operational-capacity effects of each transition.
- Define `POST /api/v1/orders/{id}/confirm-received`.
- Define a structured, sensitive and idempotent Pago Movil receiver-data
  resource rendered as a chat-style bubble.
- Define the 24-hour automatic-completion backup contract.
- Reconcile dispute, rating, notification, audit and waiting-payment chat rules.
- Assign future implementation work to 50B1 and later operational slices.

## Excluded

- Backend or frontend runtime changes.
- Database schema or migrations.
- Scheduler activation or infrastructure changes.
- Admin dispute-resolution changes.
- Payment-provider, Base USDC, Zelle, credit-purchase or support rewrites.
- Production, deployment, commit or push.

## Future Build Boundary

- 50B1 may implement secure receiver details and manual receipt confirmation.
- Before activating those endpoints, 50B1 must deprecate the legacy
  order-creation `receiver_data` input and remove legacy receiver values from
  general business-order detail. Legacy data cannot satisfy the secure receiver
  requirement.
- A later explicitly approved operational slice may activate reminders and the
  24-hour auto-complete scheduler after singleton, retry and monitoring proof.
- Admin/support reveal of full receiver details requires an explicit endpoint,
  RBAC permission and audited purpose. It is not granted by this slice.
