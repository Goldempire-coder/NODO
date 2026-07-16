# UI_CONTRACT.md

## B-05 BUY CREDITS

- Mostrar Base USDC como flujo principal.
- Mostrar red: Base.
- Mostrar token: USDC.
- Mostrar monto exacto.
- Mostrar wallet destino publica.
- Mostrar expiracion.
- Prohibido mostrar private keys, seed phrases, RPC data o claims de anonimato/evasion.
- Stripe/Zelle/USDT TRC20 manual se muestran solo como legacy/fallback si el backend los habilita.

## B-06 CREDIT PAYMENT PENDING

- Para Base USDC muestra estado:
  - esperando pago
  - detectado
  - esperando confirmaciones
  - acreditado
  - en revision
  - vencido
  - rechazado
- Permite pegar tx hash mediante endpoint contratado.
- No acredita desde frontend.
- No aceptar screenshot como acreditacion.

## B-07 CREDITS LEDGER

- Mostrar ledger `purchase` de Base USDC como compra de creditos.
- Mostrar tx hash masked/truncated cuando aplique.
- No mostrar RPC internals.

## Admin credit review

- Admin puede ver casos `under_review` con metadata segura.
- Acciones criticas requieren reason e idempotencia.
- Support read-only.

## Copy obligatorio

- "Los creditos son para publicar anuncios en NODO."
- "NODO no recibe, retiene, transfiere ni garantiza fondos de remesas."
- "Envia solo USDC en Base a la direccion indicada para esta compra."
- "Pagos en otra red o token no se acreditan automaticamente."
