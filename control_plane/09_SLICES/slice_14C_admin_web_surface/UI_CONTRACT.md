# UI_CONTRACT.md

## Superficie

Admin Web Desktop.

## Reglas visuales

- Desktop-first.
- Sidebar o navegacion lateral persistente.
- Top bar administrativa con usuario, rol, estado de sesion y acciones seguras.
- Tablas densas pero legibles.
- Filtros, busqueda y cursor pagination.
- Panel de detalle o split view.
- Estados: loading, empty, error, forbidden, offline y success.
- Responsive minimo para laptop/tablet.
- Mantener identidad NODO, tokens visuales y copy aprobado.

## Prohibiciones UI

- No Telegram Mini App shell.
- No Telegram bottom nav.
- No Telegram MainButton como navegacion primaria.
- No `@telegram-apps/telegram-ui` como sistema obligatorio.
- No `themeParams` como fuente de tema.
- No hero landing.
- No dashboard generico sin contrato.
- No claims de escrow, fondos protegidos, pago garantizado o garantia de entrega.

## Pantallas owned por 14C

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

## Pantallas compuestas desde slice 08

- A-04_PENDING_CREDIT_PAYMENTS
- A-05_CREDIT_PAYMENT_DETAIL
- A-13_MANUAL_ADJUSTMENTS

Admin Web puede enlazarlas o componerlas, pero no cambia reglas de creditos ni ownership.
