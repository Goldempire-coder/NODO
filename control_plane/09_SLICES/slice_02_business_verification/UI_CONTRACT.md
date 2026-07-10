# UI_CONTRACT.md

Screens affected:

- B-01_BUSINESS_ONBOARDING
- B-02_BUSINESS_VERIFICATION_FORM
- B-03_VERIFICATION_PENDING
- A-02_PENDING_BUSINESSES
- A-03_BUSINESS_VERIFICATION_DETAIL

UI rules:

- Follow `07_UI_UX/VISUAL_REFERENCE.md` and `SCREEN_LAYOUT_MASTER.md`.
- Telegram Mini App mobile-first layout for business screens.
- Admin screens may be denser but still use NODO visual system.
- Include loading, empty, error, forbidden, offline and success states where applicable.
- Use required disclaimers for verification and responsibility.
- Do not create landing/marketing pages instead of functional screens.
- Use `@telegram-apps/telegram-ui` where practical.
- Respect Telegram `themeParams` and safe areas.
- Use MainButton for the primary CTA on business Mini App screens.
- Reduced motion must be respected for any animation.

Business verification form:

- Captures business data and private verification documents.
- Document upload is included in slice 02 via private storage + `file_assets`.
- Show document metadata only after upload: file type, mime, size, created_at.
- Never show storage path or permanent URL.
- Show validation for missing required fields/documents.

Admin verification detail:

- Show sensitive business fields only to authorized admin/super_admin.
- Support view must keep sensitive data masked and cannot approve/reject.
- Approve/reject requires confirmation UI.
- Reject requires reason.
- Opening a document uses short signed URL and must be represented as auditable action.
