# ACCEPTANCE_CRITERIA

## PASS

- No quedan usos de `window.confirm` en pantallas Mini App Negocio.
- No quedan estados `savingZelleId`, `deletingZelleId` o `isSavingZelle` en Mini App Negocio.
- Zelle y USDT pueden coexistir como anuncios separados si existe como maximo
  uno `active` por metodo y la suma de sus maximos queda dentro de
  `declared_available_capacity_usd`.
- Crear, editar un anuncio activo, reactivar o republicar bloquea cuando supera
  el limite por metodo o la disponibilidad declarada.
- El contrato `ADS_API.md` documenta que publicar no consume
  `business.daily_limit_usd`; la orden lo revalida y reserva.
- Tests sensibles, lint, compile y build web pasan.
- No se agregan secretos, private keys, seed phrases, IPs o wallets privadas al repo.

## FAIL

- Cualquier accion sensible depende de una confirmacion nativa del browser.
- Zelle y USDT se gestionan con estado o copy que implique un solo metodo.
- La suma de maximos de anuncios activos Zelle + USDT supera la disponibilidad
  declarada, o se documentan cupos diarios separados por metodo.
- Hay evidencia faltante o no reproducible.
