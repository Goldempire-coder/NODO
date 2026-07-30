# Slice 49A - Order, payment, cancellation, capacity and expiration integrity

## Objective

Prevent contradictory P2P state when payment reporting, cancellation, expiration,
capacity reservation, and business availability actions race.

## Approved behavior

- Payment reporting and pre-payment cancellation are mutually exclusive.
- The first transition committed from `waiting_payment` wins.
- Payment reports require the exact order amount.
- A canonical transaction hash or uploaded proof file can belong to only one
  payment report.
- Payment-instruction reveal and pre-payment cancellation serialize on the same
  order lock.
- Active-order limits are revalidated inside the final order transaction.
- A business may decline a `waiting_payment` order through a structured action.
- Pre-payment chat remains disabled.
- Expiration automation is not enabled by this slice without separate runtime
  evidence and operational approval.

## Expiration execution evidence

- The expiration processor and singleton job lock exist in the backend.
- The API lifespan in `apps/api/app/main.py` does not start an order-expiration
  loop.
- This slice does not add a Railway cron, process, replica, or scheduler.
- Automatic execution therefore remains operationally unproven; the existing
  guarded/manual job path remains available for a separately approved runtime
  decision.
- PostgreSQL evaluates expiration against `clock_timestamp()` after acquiring
  the order lock, not against a stale application timestamp.

## Status

Implementation only. No deploy, migration execution, or production change is
authorized by this slice.
