# ACCEPTANCE_CRITERIA

## PASS

- No quedan usos de `window.confirm` en pantallas Mini App Negocio.
- No quedan estados `savingZelleId`, `deletingZelleId` o `isSavingZelle` en Mini App Negocio.
- Zelle y USDT TRC20 pueden coexistir como anuncios separados si la exposicion total queda dentro de `business.daily_limit_usd`.
- Crear, editar anuncio activo, reactivar o republicar bloquea cuando la exposicion abierta supera `business.daily_limit_usd`.
- El contrato `ADS_API.md` documenta `BUSINESS_DAILY_LIMIT_EXCEEDED`.
- Tests sensibles, lint, compile y build web pasan.
- No se agregan secretos, private keys, seed phrases, IPs o wallets privadas al repo.

## FAIL

- Cualquier accion sensible depende de una confirmacion nativa del browser.
- Zelle y USDT se gestionan con estado o copy que implique un solo metodo.
- Se puede abrir exposicion Zelle + USDT por encima del limite diario del negocio.
- Hay evidencia faltante o no reproducible.

