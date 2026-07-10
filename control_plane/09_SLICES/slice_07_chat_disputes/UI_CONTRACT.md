# UI_CONTRACT.md

Screens affected:

- R-09_ORDER_TRACKING_CHAT
- B-13_BUSINESS_CHAT

Screens explicitly out of slice 07:

- R-10_CONFIRM_RECEIVED
- R-11_RATING
- A-06_DISPUTES_LIST
- A-07_DISPUTE_DETAIL

UI rules:

- Follow 07_UI_UX/VISUAL_REFERENCE.md and SCREEN_LAYOUT_MASTER.md.
- Telegram Mini App mobile-first layout.
- Include loading, empty, error, forbidden and success states.
- Use required disclaimers for payments, verification, credits and responsibility.
- Do not create landing/marketing pages instead of functional screens.

Copy requirements:

- NODO registra evidencia y estado; no recibe, retiene, transfiere ni garantiza fondos.
- El chat no reemplaza la confirmacion de pago ni la entrega.
- Abrir disputa no garantiza resultado; habilita revision con evidencia.

Forbidden copy:

- escrow
- fondos protegidos
- garantia de entrega
- NODO recibio tu dinero
- pago garantizado
- transaccion asegurada

R-09 requirements:

- Show order tracking and party chat for remitter-owned order.
- Show dispute CTA only when backend capabilities allow it.
- Do not build confirm received/completion/rating.

B-13 requirements:

- Show business chat for own business order.
- Show dispute state if order is disputed.
- Do not build admin resolution or remitter confirmation.
