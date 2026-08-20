# REGRESSION_CHECKLIST.md

Checklist corto de regresion. Para el gate completo usar
`control_plane/11_OPERATIONS/STABILITY_GATE.md`.

## Flujos minimos

- Auth Cliente, Negocio y Admin.
- Cliente home, marketplace, search, create order, payment report, chat,
  received/completed, rating e historial.
- Negocio access gate, online/offline, create ad, orders open/verify/history,
  payment confirm, payment problem/dispute, support y credits.
- Admin dashboard, notifications, businesses, clients, orders, disputes,
  credits, audit, intake, support, jobs y search.
- Credit ledger: hold, release, consume, expire, purchase, admin adjustment y
  referral bonus.
- Scroll/paginacion en listas largas y chats.
- No copy de escrow, garantia, custodia, fondos protegidos o recuperacion
  garantizada.
