# Final P2P State Machine

## State Table

`Credit` means the publication credit held for the ad. `Capacity` means the
business operational USD capacity reserved for the order.

| State | Actor and official action | Endpoint current/proposed | Credit effect | Capacity effect | Chat | Dispute | Simple cancel | Rating |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `waiting_payment` | Remitter reports payment; remitter cancels; business uses `No puedo atender`; timeout expires | Current report/cancel/cannot-attend endpoints | No consume; ad credit remains held | Reserved; release once only on cancel/expire | Yes, participants only | No | Yes, before report only | No |
| `payment_reported` | Business confirms or rejects; participant opens dispute | Current business confirm/reject and dispute endpoints | Confirm consumes once; reject/dispute leaves hold unchanged | Retained | Yes | Yes | No | No |
| `payment_rejected` | Participant opens dispute or follows contracted correction/support flow | Current dispute endpoint; correction is future contract | Still held; no consume from rejection | Retained | Yes | Yes | No | No |
| `payment_confirmed` | Remitter shares structured receiver details; business marks Pago Movil sent; participant opens dispute | Proposed receiver-details endpoints; current `mark-delivered`; current dispute endpoint | Already consumed exactly once at entry | Retained | Yes; sensitive payload is not message body | Yes | No | No |
| `delivered` | Remitter confirms receipt; participant opens dispute; auto-complete backup runs after 24h | Proposed `POST /orders/{id}/confirm-received`; current dispute endpoint; future job | No new consume | Retained until completion | Yes | Yes, before completion wins | No | No |
| `completed` | Terminal; remitter may rate under rating contract | Current rating endpoint | Manual/auto path: already consumed, no second consume. Admin-resolved path keeps its existing dispute-credit contract | Consumed exactly once | No new messages | No new dispute | No | Yes, if completion reason and dispute rules pass |
| `disputed` | Admin/super_admin resolves under dispute contract; participants may add dispute chat evidence | Current admin dispute-resolution and messages endpoints | Depends on `previous_order_status`; never double move | Retained until terminal resolution; completed consumes, cancelled releases | Yes | Already open/in review | No | No |
| `cancelled` | Terminal | Current cancellation/expiration/admin-resolution endpoints | Pre-report cancel does not consume; admin dispute outcome follows dispute contract | Released exactly once | No new messages | No new dispute | Already terminal | No |

## Allowed Transitions

| From | To | Official cause |
| --- | --- | --- |
| quote/no order | `waiting_payment` | `POST /api/v1/orders` succeeds |
| `waiting_payment` | `payment_reported` | Remitter submits a valid payment report |
| `waiting_payment` | `cancelled` | Remitter cancels before report, business cannot attend, or timeout expires |
| `payment_reported` | `payment_confirmed` | Business officially confirms received Zelle |
| `payment_reported` | `payment_rejected` | Business officially rejects/unrecognizes the report |
| `payment_reported` | `disputed` | Participant or contracted timeout opens formal dispute |
| `payment_rejected` | `disputed` | Participant opens formal dispute |
| `payment_confirmed` | `delivered` | Business officially marks Pago Movil sent after valid receiver data exists |
| `payment_confirmed` | `disputed` | Participant or contracted timeout opens formal dispute |
| `delivered` | `completed` | Remitter confirms receipt or 24-hour backup completes without open/in-review dispute |
| `delivered` | `disputed` | Participant opens dispute before completion wins |
| `disputed` | `completed` | Admin/super_admin terminal resolution |
| `disputed` | `cancelled` | Admin/super_admin terminal resolution |

## Prohibited Transitions

| Attempt | Rule |
| --- | --- |
| Any chat message -> state change | Text never confirms payment, delivery or receipt |
| `waiting_payment` -> `delivered|completed` | Payment report and official business confirmation cannot be skipped |
| `payment_reported|payment_rejected|payment_confirmed|delivered|disputed` -> simple `cancelled` | Post-report problems require formal dispute/admin resolution |
| `payment_reported` -> `delivered` | Business must officially confirm received Zelle first |
| `payment_confirmed` -> `delivered` without valid receiver details | Return `ORDER_RECEIVER_DETAILS_REQUIRED` |
| `delivered` -> `completed` while dispute is `open|in_review` | Return `ORDER_COMPLETION_BLOCKED_BY_DISPUTE` |
| `completed|cancelled` -> any nonterminal state | Terminal states do not reopen implicitly |
| Any completion -> second credit consume | Publication credit was consumed at `payment_confirmed` |
| Any replay -> second capacity release/consume | Capacity effects are exact-once |

## Concurrency Rule

`delivered -> completed` and `delivered -> disputed` must lock the same order
and validate the current dispute state in the same transaction. Exactly one
transition wins; the loser returns a safe state conflict and creates no partial
capacity, event, audit or notification effect.
