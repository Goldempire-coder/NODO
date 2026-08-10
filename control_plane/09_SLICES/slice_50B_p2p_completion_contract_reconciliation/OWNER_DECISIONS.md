# Owner Decisions

These decisions are approved and require no further product interpretation.

1. In the normal P2P path, reporting payment does not consume publication
   credit.
2. Official business confirmation of received Zelle changes
   `payment_reported -> payment_confirmed` and consumes publication credit
   exactly once.
3. Chat text such as `recibido` has no state, credit or capacity effect.
4. Operational capacity is reserved at order creation, released only by a
   pre-report cancellation or expiration, retained through active/disputed
   states and consumed at `completed`.
5. Simple cancellation is restricted to `waiting_payment` before a payment
   report. Later problems use support or formal dispute.
6. After payment reporting, the business may confirm receipt or use `Reportar
   problema con pago` to open a formal dispute. It cannot reject or close the
   reported payment directly. The structured dispute reason is
   `payment_not_received_or_incomplete`.
7. Pago Movil is chat-first in the normal P2P path. The structured
   receiver-details resource is required before business delivery and is shown
   as a compact chat bubble; free chat text never satisfies this requirement.
8. Full receiver details are visible only to the two order participants.
   Admin/support access requires a future explicit, audited reveal contract.
9. The remitter owner can confirm receipt only from `delivered`. The official
   transition is `delivered -> completed`.
10. Manual completion does not consume publication credit again. It consumes
    operational capacity exactly once and enables rating when no dispute blocks
    it.
11. Automatic completion is only a 24-hour backup after `delivered`, requires
    no open/in-review dispute and uses the same atomic completion transition.
12. A formal dispute can open from `payment_reported`, historical
    `payment_rejected`, `payment_confirmed` or `delivered`. New business actions
    must not create `payment_rejected`; the state remains readable only for
    legacy orders and administrative recovery.
13. An open/in-review dispute blocks manual and automatic completion.
14. In `waiting_payment`, only the remitter and business owner participants may
    read or write the private order chat.
15. Existing ad-expiration and admin dispute-resolution credit outcomes remain
    governed by their own approved contracts. 50B0 does not silently redefine
    those exceptional terminal outcomes.
16. When an order that reached `payment_reported` later ends in `completed` or
    `cancelled`, the business enters a neutral 15-minute publication cooldown.
    A cancellation before payment reporting does not start this cooldown, and
    any Admin block or restriction continues to dominate after it expires.
