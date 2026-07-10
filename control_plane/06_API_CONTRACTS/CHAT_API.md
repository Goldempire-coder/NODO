# CHAT_API.md

Legacy routing note:

- This file is retained only as a compatibility pointer.
- Canonical message/chat API for slice 07 is `MESSAGES_API.md`.
- Canonical routes use `/api/v1`.

Canonical endpoints:

- GET /api/v1/orders/{id}/messages
- POST /api/v1/orders/{id}/messages
- POST /api/v1/orders/{id}/message-attachments

Rules:

- Do not use legacy `/orders/:id/messages` as API contract.
- Use backend RBAC, ownership, rate limit and audit.
- Use `messages` as canonical table; do not create `chat_messages`.
