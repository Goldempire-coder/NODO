# UI_CONTRACT.md

Screens owned by slice 09:

- A-01_ADMIN_DASHBOARD
- A-02_PENDING_BUSINESSES
- A-03_BUSINESS_VERIFICATION_DETAIL
- A-06_DISPUTES_LIST
- A-07_DISPUTE_DETAIL
- A-08_EVASION_REPORTS
- A-09_BUSINESS_RISK_DETAIL
- A-10_USERS_REMITTERS
- A-11_AUDIT_LOGS
- A-12_SYSTEM_METRICS

Screens linked/composed from slice 08, not re-owned by slice 09:

- A-04_PENDING_CREDIT_PAYMENTS
- A-05_CREDIT_PAYMENT_DETAIL
- A-13_MANUAL_ADJUSTMENTS

UI rules:

- Follow 07_UI_UX/VISUAL_REFERENCE.md and SCREEN_LAYOUT_MASTER.md.
- Telegram Mini App mobile-first layout.
- Include loading, empty, error, forbidden and success states.
- Use required disclaimers for payments, verification, credits and responsibility.
- Do not create landing/marketing pages instead of functional screens.
- Admin dispute detail must show that NODO records an operational decision and
  does not receive, retain, transfer or guarantee funds.
- Support must see read-only controls. Resolve/approve/reject/adjust controls
  must be hidden visually and denied by backend.
- A-12 uses calculated/read-model metrics. It must not display fake data.
- No UI may show `storage_path`, raw signed URLs, full payment instructions,
  `account_value`, tokens or secrets.
