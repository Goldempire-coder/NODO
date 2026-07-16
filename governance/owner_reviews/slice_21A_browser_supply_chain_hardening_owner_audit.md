# slice_21A_browser_supply_chain_hardening - Owner Audit

## Estado

PASSED_AFTER_OWNER_AUDIT_FIX

## Resultado

El hardening de browser/supply-chain cerró el hallazgo HIGH de `valibot` y el MODERATE de `postcss` mediante overrides auditados. El frontend quedó separado por superficie con `AuthEntryPage` como router liviano y carga dinámica para Admin Web y Mini Apps.

## Fix aplicado durante owner audit

Corregí `apps/web/src/screens/auth/AdminWebEntryPage.tsx` para que el Admin Web no confíe en un `user` guardado en `sessionStorage`.

Antes:
- guardaba token + user en `sessionStorage`;
- al recargar, podía montar `AdminWebWorkspace` usando el user cacheado si `canReadAdmin(user)` pasaba.

Después:
- guarda solo `nodo_admin_access_token`;
- en cada recarga revalida el token contra `/api/v1/users/me` con `X-NODO-Surface: admin_web`;
- si el backend rechaza o el usuario ya no puede leer admin, limpia el token y no monta el panel.

## Validaciones ejecutadas por owner audit

- `corepack pnpm --filter @nodo/web build`: PASS.
- `corepack pnpm audit --prod`: PASS, `No known vulnerabilities found`.
- `corepack pnpm why valibot --filter @nodo/web`: `valibot 1.2.0`.
- `corepack pnpm why postcss --filter @nodo/web`: `postcss 8.5.10`.
- `python -m pytest apps/api/tests -q`: PASS, `188 passed, 1 warning`.
- Scan frontend source/build: sin secretos, `storage_path`, `account_value`, private keys, seed phrases, bot tokens ni claims prohibidos.
- Scan Admin Web auth/admin folders: sin `@telegram-apps`, `useTelegramAuth`, `window.Telegram`, `themeParams` ni `MainButton`.

## Observaciones

- `apps/web/src/app/layout.tsx` todavía importa `@telegram-apps/telegram-ui/dist/styles.css` globalmente. Esto no carga runtime JS de Telegram en Admin Web, pero no es aislamiento visual/CSS perfecto. Para aislarlo al 100%, Admin Web debería moverse a ruta/layout propio o el sistema de estilos Telegram debería dejar de ser global.
- `apps/web/public/_headers` usa CSP incremental con `unsafe-inline` por compatibilidad con Next static export. Es aceptable como primer cierre, pero debe endurecerse luego con hashes/nonces o rutas separadas si el pipeline lo permite.
- El Admin Web sigue usando un gate mínimo por token backend existente. No reemplaza una UX completa de login admin desktop.

## Confirmaciones

- No hice deploy.
- No declaré `READY_FOR_REAL_USE`.
- No cambié backend de negocio.
- No cambié DB/migraciones.
- No cambié reglas de órdenes, pagos, créditos, disputas, soporte, bots ni watchers.
