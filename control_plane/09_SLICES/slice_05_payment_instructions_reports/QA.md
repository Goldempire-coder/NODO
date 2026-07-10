# QA.md

Required QA for slice 05:

- reveal own `waiting_payment` order OK.
- reveal order ajena blocked without leaking existence.
- reveal expired order blocked.
- reveal sets `payment_data_revealed_at` and `payment_data_revealed_by`.
- reveal writes audit `payment_instructions_viewed`.
- reveal does not create payment report.
- reveal does not change order status.
- report valid Zelle changes `waiting_payment -> payment_reported`.
- report valid USDT TRC20 changes `waiting_payment -> payment_reported`.
- report invalid payment method fails.
- report without required evidence fails when Zelle.
- report expired order fails.
- report foreign order fails safely.
- report does not consume credits.
- report keeps ad `in_order`.
- report keeps credits blocked.
- report does not confirm business receipt.
- report does not deliver.
- idempotent retry returns same result.
- same idempotency key with different payload fails.
- upload evidence owner-only.
- upload evidence returns or accepts `pending_payment_report_id`.
- Zelle report validates `proof_file_id` belongs to `pending_payment_report_id`.
- upload evidence rejects invalid MIME.
- upload evidence rejects file over 5 MB.
- upload evidence does not expose `storage_path`.
- audit events and state events are written.
- frontend build.
- runners 00, 01, 02, 03, 04 and 05.
- backend pytest accumulated.
- ruff.
- compileall.
- frontend source/build secret and private data scan.

Gate:

- Unit tests for services/state/policies.
- Integration tests for endpoints.
- RBAC/ownership tests.
- Audit event verification.
- Manual smoke for affected screens.
- Builder report must list commands run and tests not run with reason.
