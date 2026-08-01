# QA

Required regression coverage:

- Order creation without `receiver_data` creates one waiting order and one
  capacity reservation.
- Waiting-payment chat is available only to the two participants.
- The virtual message is returned without audit or Telegram duplication.
- Compact `Enviar Zelle` is owner-only and deduplicated across keys.
- Manual configured Zelle unlocks payment.
- Similar or external contact does not unlock payment and remains moderated.
- Instructions and report return `ORDER_PAYMENT_DETAILS_NOT_SHARED` before
  configured Zelle sharing.
- Existing cancellation, capacity, 49A integrity and notification tests pass.
- Client confirmation omits receiver fields and opens chat after order create.
- Client payment action stays hidden until the backend capability allows it.
- Client chat refreshes silently only while `order-chat` and the document are
  visible, without overlapping list requests.
- Silent refresh failure preserves the current messages and capabilities.
- Refreshed capabilities can enable `Pago enviado` after the business shares
  configured Zelle.
- Client and business initial chat loads return the latest bounded message
  window, including a newly shared Zelle after older history.
- Business chat polling is visible-only, single-flight and preserves current
  messages and capabilities after a silent failure.
- `Pago enviado` opens the compact report form directly; there is no
  intermediate instructions screen.
- A late payment-instructions response cannot replace state after the client
  changes chat or begins opening another order.
- Opening another report clears the prior order's sender, reference and
  evidence state.
- Payment amount is read-only and submitted from the order snapshot.
- The PostgreSQL Zelle report constraint accepts the locked amount and proof
  without requiring legacy sender/reference fields.
- Transport failures during final report submission render controlled Spanish
  copy instead of the browser `failed to fetch` text.
- Client and business support keep one stable layout while the keyboard opens;
  focus does not activate a separate compact mode or delayed forced scroll.
- Visible form controls use at least 16px text and the shared viewport hook
  coalesces real viewport resizes without depending on visual-viewport scroll.
- Empty receiver data renders `Pago Movil pendiente en chat`; legacy values
  remain masked and no fallback values are invented.
- Chat attachments can be opened by Cliente and Negocio participants through an
  explicit temporary URL action, without exposing storage paths.
- While a participant is inside the order chat, success toasts and global
  attention banners do not cover the conversation.
- Chat headers remain compact and typing mode keeps the message composer
  visible on mobile.

Commands:

```powershell
python -m pytest apps/api/tests/test_simplified_p2p_negotiation_flow_static.py -q --tb=short
python -m pytest apps/api/tests/test_order_creation.py apps/api/tests/test_chat_disputes.py apps/api/tests/test_payment_instructions_reports.py -q --tb=short
python -m pytest apps/api/tests -q --tb=short
python -m ruff check apps/api scripts
python -m compileall apps/api apps/web/src scripts
pnpm --filter @nodo/web build
git diff --check
```
