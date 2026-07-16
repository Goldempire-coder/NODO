# STATE_CONTRACT.md

## credit_purchase.status para Base USDC

- pending_payment
- pending_onchain_confirmation
- detected
- verified
- credited
- under_review
- expired
- rejected
- verification_failed

## Transiciones permitidas

- pending_payment -> detected
- pending_payment -> pending_onchain_confirmation
- pending_payment -> expired
- pending_payment -> under_review
- pending_payment -> verification_failed
- detected -> pending_onchain_confirmation
- detected -> under_review
- detected -> verification_failed
- pending_onchain_confirmation -> verified
- pending_onchain_confirmation -> under_review
- pending_onchain_confirmation -> verification_failed
- verified -> credited
- under_review -> rejected

Terminales:

- credited
- expired
- rejected
- verification_failed

## Reglas

- `credited` requiere ledger purchase y wallet actualizada.
- `verified` no puede ser visible como acreditado hasta completar transaccion ledger/wallet.
- Confirmaciones insuficientes no acreditan.
- Expirado no acredita automaticamente.
- Sobrepago acredita solo el paquete si cumple minimo; no crea credito extra automatico.
- Pago parcial queda `under_review`.
