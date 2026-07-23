# B-13_BUSINESS_CHAT.md

SCREEN_ID: B-13_BUSINESS_CHAT
actor: business
slice: slice_07_chat_disputes
status: DRAFT_CONTROLLED

purpose:
Chat inside business order.

route:
/business/orders/:id/chat

entry points:
Order detail

exit points:
B-12_BUSINESS_ORDER_DETAIL

data required:
- authenticated user/session
- data defined by `06_API_CONTRACTS/MESSAGES_API.md`
- data defined by `06_API_CONTRACTS/DISPUTES_API.md` when dispute state is shown

read strategy:
- Read only data needed for this screen.
- Use loading skeleton.
- Use error/retry if request fails.
- Use empty state when list is empty.

write strategy:
- Writes only through approved API endpoints.
- No direct state transitions outside backend state machine.

Telegram UI rules:
- Use @telegram-apps/telegram-ui where possible.
- Respect themeParams.
- Use official NODO logo and tokens.
- Use MainButton only for primary CTA.

MainButton behavior:
None

validation:
message required

permissions:
own business order

states:
- loading
- empty
- error
- offline
- success where applicable

audit events:
- message_created
- message_attachment_uploaded
- dispute_message_created when applicable
- order_chat_off_platform_solicitation_detected when a business-owner message triggers internal anti-evasion review

slice boundary:
- This screen does not belong to slice 06.
- Slice 06 may only show a link or disabled/coming-next state toward this screen.
- Chat endpoints, messages and disputes belong to slice 07 or later contracts.
- `message_sent` is not a canonical audit event.
- `message_blocked` is not a canonical audit event in slice 07.
- Anti-evasion detection does not block messages and does not close the 24h delivered-resolution window.
- NODO registra evidencia y estado; no recibe, retiene, transfiere ni garantiza fondos.

QA checklist:
Anti-evasion active
- no `storage_path`
- no full payment instructions
- no `account_value`

## Slice 14B1 access contract

- Requires `surface/session` allowed for `business_mini_app` or explicit read/respond capability for suspended business.
- Chat access is never granted by frontend role alone.
- Blocked business/link/user cannot send messages; read-only visibility requires backend capability.
