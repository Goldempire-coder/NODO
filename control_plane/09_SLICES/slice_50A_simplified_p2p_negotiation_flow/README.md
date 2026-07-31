# Slice 50A Simplified P2P Negotiation Flow

Status: IMPLEMENTED_LOCAL - VALIDATOR_REVIEW_REQUIRED

This slice implements only 50A1 and 50A2:

- amount -> business -> minimal confirmation -> create order -> private chat;
- optional legacy `receiver_data`;
- chat available in `waiting_payment`;
- virtual negotiation-created message;
- configured Zelle shared manually or with compact `Enviar Zelle`;
- payment instructions and payment report blocked until configured Zelle is in
  a visible business message;
- client chat refreshes locally every five seconds only while its view is open
  and the document is visible;
- compact `Pago enviado` validates instructions in the background and opens the
  report form directly;
- missing legacy receiver data is shown as pending coordination in chat, never
  as fabricated masked values;
- locked payment-report amount in the client UI.

The Owner correction is authoritative: any first business message means only
that the business responded. Only sharing the configured Zelle enables payment.

No migration, deployment, credit rule, Base USDC flow, support rewrite,
reputation change or expiration scheduler is part of this slice.
