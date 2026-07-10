# UI_CONTRACT.md

Screens affected in slice 04:

- R-05_CREATE_ORDER
- R-06_ORDER_SUMMARY
- R-12_MY_ORDERS

Screens explicitly out of slice 04:

- R-07_PAYMENT_INSTRUCTIONS, except link/disabled state toward slice 05.
- B-11_INCOMING_ORDERS, belongs to slice 06 unless later explicitly authorized.

Real screen filenames:

- Use `R-06_ORDER_SUMMARY.md`, not `R-06_ORDER_CREATED.md`.
- Use `B-11_INCOMING_ORDERS.md`, not `B-11_INCOMING_ORDER.md`.

## UI rules

- Follow `07_UI_UX/VISUAL_REFERENCE.md` and `SCREEN_LAYOUT_MASTER.md`.
- Telegram Mini App mobile-first layout.
- Use `@telegram-apps/telegram-ui` where applicable.
- Use Telegram SDK/MainButton/themeParams/safe areas.
- Include loading, empty, error, offline, forbidden and success states.
- Use required disclaimers for payment/order responsibility.
- Do not create landing/marketing pages instead of functional screens.
- Do not promise escrow, protected funds, guaranteed transaction or guaranteed delivery.

## Sensitive display

- Create/order summary/my orders must not reveal full payment instructions.
- Show only masked/summary instruction data until slice 05.
- No `account_value` full display.
- No business documents, storage paths or private internal IDs.

## Copy/disclaimer

Create order disclaimer:

```txt
NODO registra la orden y la evidencia, pero no recibe ni retiene fondos. Pagaras directamente al negocio seleccionado.
```

Payment instructions disclaimer belongs to R-07/slice 05:

```txt
Paga solo a los datos mostrados en esta orden. NODO no toca fondos ni puede revertir pagos hechos fuera de las instrucciones.
```
