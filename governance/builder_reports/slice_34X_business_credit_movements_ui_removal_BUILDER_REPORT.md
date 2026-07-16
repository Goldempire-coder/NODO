# slice_34X_business_credit_movements_ui_removal

Estado final: `READY_FOR_OWNER_REVIEW`

## Objetivo

Remover la pantalla `Movimientos` de creditos de la Mini App Negocio porque no aportaba informacion accionable para el negocio y aumentaba ruido en una seccion sensible.

## Cambios realizados

- Se quito `credits-ledger` del catalogo de vistas de la Mini App Negocio.
- Se elimino el boton `Movimientos` del dashboard de creditos.
- Se elimino `CreditsLedgerScreen` del router de pantallas del negocio.
- Se elimino el estado frontend `creditLedger` y la accion `loadCreditLedger`.
- Se elimino el cliente frontend `listBusinessCreditLedger` porque ya no lo consume la Mini App Negocio.
- Se elimino el tipo frontend `CreditLedgerEntry` y su export desde `domain.ts`.
- Se agregaron tests estaticos para bloquear la reintroduccion accidental de `Movimientos` en la Mini App Negocio.

## Fuera de alcance

- No se elimino el ledger/auditoria del backend.
- No se elimino ningun registro financiero.
- No se cambio la logica de creditos, compras, consumos, bloqueos ni referidos.
- No se cambio admin ni operaciones internas.
- No se hizo deploy.
- No se toco produccion.

## Razon operativa

El negocio necesita ver balance util, comprar creditos y operar anuncios. El ledger crudo no explicaba suficientemente que paso ni ayudaba a resolver una accion concreta. La trazabilidad de movimientos debe existir para auditoria interna, soporte y administracion, pero no debe ocupar una pantalla de la Mini App Negocio hasta que exista una UX clara y accionable.

## Validacion ejecutada

- `python -m pytest apps/api/tests/test_auth_lifecycle_static.py -q --tb=short` -> `7 passed`
- `python -m pytest apps/api/tests -q` -> `352 passed, 1 warning`
- `python -m ruff check apps/api scripts` -> passed
- `python -m compileall apps/api apps/web/src scripts` -> passed
- `pnpm --filter @nodo/web build` con Node runtime bundled -> passed
- `git diff --check` -> passed con warnings existentes de CRLF/LF

## Riesgos pendientes

- La seccion de creditos todavia debe evolucionar hacia un resumen claro de compras pendientes, pagos en Base USDC y creditos disponibles.
- Si se reintroduce historial para negocio en el futuro, debe ser una pantalla explicativa y filtrada, no el ledger interno crudo.
