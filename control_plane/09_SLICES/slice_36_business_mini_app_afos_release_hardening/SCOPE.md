# SCOPE

## Construir

- Confirmacion interna de borrado de anuncios sin `window.confirm`.
- Estados frontend de metodos de cobro nombrados como `PaymentMethod`, no `Zelle`, porque ahora cubren Zelle y USDT TRC20.
- Regla backend `BUSINESS_DAILY_LIMIT_EXCEEDED` para impedir que anuncios abiertos (`active`, `in_order`) excedan `business.daily_limit_usd`.
- Contratos de anuncios/riesgo alineados con la regla diaria.
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

