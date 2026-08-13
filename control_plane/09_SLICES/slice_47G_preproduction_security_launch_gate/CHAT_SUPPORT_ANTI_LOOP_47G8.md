# 47G8 Chat And Support Anti-loop

## Scope

Protect Cliente/Negocio order chat and Support ticket conversations from
frontend retry loops, bots and repeated-message spam.

## Runtime Rule

- Chat message creation uses `CHAT_MESSAGE_RATE_LIMIT_*`.
- Chat repeated body uses `CHAT_DUPLICATE_MESSAGE_RATE_LIMIT_*`.
- Chat attachment upload uses `CHAT_ATTACHMENT_RATE_LIMIT_*`.
- Support message creation uses `SUPPORT_MESSAGE_RATE_LIMIT_*`.
- Support repeated body uses `SUPPORT_DUPLICATE_MESSAGE_RATE_LIMIT_*`.
- Support attachment upload uses `SUPPORT_ATTACHMENT_RATE_LIMIT_*`.
- Repeated-body keys use a normalized body hash, not raw text.
- Rejections return the existing neutral `RATE_LIMITED`.

## Defaults

```txt
CHAT_MESSAGE_RATE_LIMIT_MAX_ATTEMPTS=10
CHAT_MESSAGE_RATE_LIMIT_WINDOW_SECONDS=60
CHAT_DUPLICATE_MESSAGE_RATE_LIMIT_MAX_ATTEMPTS=2
CHAT_DUPLICATE_MESSAGE_RATE_LIMIT_WINDOW_SECONDS=60
CHAT_ATTACHMENT_RATE_LIMIT_MAX_ATTEMPTS=6
CHAT_ATTACHMENT_RATE_LIMIT_WINDOW_SECONDS=60
SUPPORT_MESSAGE_RATE_LIMIT_MAX_ATTEMPTS=10
SUPPORT_MESSAGE_RATE_LIMIT_WINDOW_SECONDS=60
SUPPORT_DUPLICATE_MESSAGE_RATE_LIMIT_MAX_ATTEMPTS=2
SUPPORT_DUPLICATE_MESSAGE_RATE_LIMIT_WINDOW_SECONDS=60
SUPPORT_ATTACHMENT_RATE_LIMIT_MAX_ATTEMPTS=6
SUPPORT_ATTACHMENT_RATE_LIMIT_WINDOW_SECONDS=60
```

## Non-actions

- No payment, wallet, credit, order-state, dispute or hold changes.
- No frontend changes.
- No new dependency.
- No raw message text in rate-limit keys, logs or audit metadata.

## Validation

- TDD must prove chat loops are cut before the general business limit.
- TDD must prove support loops are cut before the general business limit.
- TDD must prove repeated text is limited while different text is allowed.
- Existing idempotency, notifications, permissions and archived-ticket behavior
  must remain green.

## Local Evidence

- Red phase: four targeted tests failed before runtime enforcement existed.
- Targeted anti-loop tests: `4 passed`.
- Chat and Support regression: `80 passed`.
- Full API suite: `961 passed, 38 skipped`.
- Ruff, compileall and `git diff --check`: PASS.
- Secret Guard: only reviewed false positives in examples, bucket names and a
  documentation path string; no secrets.

## Remaining Work

Provider-level alerting and Telegram Admin notification for repeated rate-limit
abuse belongs to a later alerting slice.
