# Slice 50A Simplified P2P Negotiation Flow

Status: IMPLEMENTED_LOCAL - VALIDATOR_REVIEW_REQUIRED

This slice implements only 50A1 and 50A2:

- amount -> business -> minimal confirmation -> create order -> private chat;
- optional legacy `receiver_data`;
- chat available in `waiting_payment`;
- virtual negotiation-created message;
- configured Zelle or USDT wallet shared manually or with the compact business
  action;
- payment instructions and payment report blocked until the configured account
  is in a visible business message;
- client chat refreshes locally every five seconds only while its view is open
  and the document is visible;
- compact `Pago enviado` validates instructions and submits the report from the
  active order chat without navigating to a separate payment screen;
- Zelle can be reported without a photo; proof remains optional and may be
  requested by the business in the order chat;
- missing legacy receiver data is shown as pending coordination in chat, never
  as fabricated masked values;
- locked payment-report amount in the client UI.

The Owner correction is authoritative: any first business message means only
that the business responded. Only sharing the configured Zelle or USDT wallet
enables payment.

No migration, deployment, credit rule, Base USDC flow, support rewrite,
reputation change or expiration scheduler is part of this slice.

Owner-approved navigation rule:

- NODO displays and copies the configured Zelle or USDT value inside chat;
- NODO does not open a bank or external wallet application;
- the client may leave Telegram manually and return to the same order chat;
- reporting payment, Pago Movil and rating keep the client in that chat;
- terminal chats do not need a reopen action in the client order list. The
  order number remains available for support and operational follow-up.
