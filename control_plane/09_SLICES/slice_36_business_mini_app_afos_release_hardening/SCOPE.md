# SCOPE

## Construir

- Confirmacion interna de borrado de anuncios sin `window.confirm`.
- Estados frontend de metodos de cobro nombrados como `PaymentMethod`, no `Zelle`, porque ahora cubren Zelle y USDT TRC20.
- Regla contractual vigente: maximo un anuncio `active` Zelle y uno USDT, con
  suma de `amount_max_usd` dentro de la disponibilidad declarada.
- `business.daily_limit_usd` se valida y reserva al crear una orden; publicar
  anuncios no lo consume.
- Contratos de anuncios y capacidad alineados con esta separacion.
- Builder report y evidencia del slice.

## No construir

- No deploy.
- No produccion.
- No wallet privada.
- No app cliente.
- No cambios de provider.
- No cambio de acreditacion Base USDC.
- No migraciones nuevas.
- No READY_FOR_REAL_USE.
