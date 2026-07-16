# slice_21A_browser_supply_chain_hardening_BUILDER_REPORT

## Estado final

READY_FOR_OWNER_REVIEW

No se declaro READY_FOR_REAL_USE. No se hizo deploy.

## Lectura obligatoria

Leidos:

- `control_plane/00_GOVERNANCE/SOURCE_OF_TRUTH.md`
- `control_plane/00_GOVERNANCE/DO_NOT_INVENT.md`
- `control_plane/00_GOVERNANCE/ENGINEERING_GUARDRAILS.md`
- `control_plane/01_PRODUCT/SURFACE_ARCHITECTURE_MASTER.md`
- `control_plane/02_ARCHITECTURE/ADMIN_WEB_ARCHITECTURE.md`
- `control_plane/05_SECURITY/SENSITIVE_DATA_POLICY.md`
- `control_plane/05_SECURITY/SECRETS_POLICY.md`
- `control_plane/10_QA/SECURITY_TESTS.md`

Nota: no se encontro un archivo local con nombre `SECURITY_BROWSER_SUPPLY_CHAIN_AUDIT_REPORT - NODO` en repo ni attachments. Se ejecuto el build usando los hallazgos exactos incluidos en el prompt y los contratos de seguridad/superficies.

## Que se construyo

- Se cerro el HIGH de supply-chain de `valibot <1.2.0` mediante override auditado a `valibot@1.2.0`, porque `@telegram-apps/sdk@3.11.8` sigue siendo la version mas reciente y aun declara `valibot@1.0.0`.
- Se cerro el hallazgo moderado de `postcss <8.5.10` mediante override a `postcss@8.5.10`.
- Se separo el entrypoint frontend por superficie:
  - `AuthEntryPage` queda como router liviano.
  - `TelegramEntryPage` contiene la carga Telegram para Mini App Cliente y Mini App Negocio.
  - `AdminWebEntryPage` contiene el gate Admin Web sin Telegram.
- Se evito que Admin Web dependa de `useTelegramAuth`, `@telegram-apps/*`, `window.Telegram`, `themeParams`, `MainButton` o bottom nav Telegram.
- Se agrego un gate minimo gobernado para Admin Web usando token backend existente y validacion contra `/api/v1/users/me` con `X-NODO-Surface: admin_web`.
- Se agrego CSP inicial para Cloudflare Pages en `apps/web/public/_headers`.
- Se removieron `NEXT_PUBLIC_SUPABASE_URL` y `NEXT_PUBLIC_SUPABASE_ANON_KEY` del runtime loader frontend porque no se usan en `apps/web/src`.
- Se agrego `pytest.ini` para que el comando requerido `python -m pytest apps/api/tests -q` use `apps/api` como `PYTHONPATH`.

## Que NO se construyo

- No se cambio backend de negocio.
- No se cambio DB ni migraciones.
- No se tocaron ordenes, pagos, creditos, disputas, soporte, bots ni watchers.
- No se cambio copy o UI funcional salvo estilos minimos del gate Admin Web.
- No se hizo deploy.
- No se declaro READY_FOR_REAL_USE.

## Archivos modificados

- `package.json`
- `pnpm-lock.yaml`
- `pytest.ini`
- `apps/web/public/_headers`
- `apps/web/src/lib/env.ts`
- `apps/web/src/app/globals.css`
- `apps/web/src/screens/auth/AuthEntryPage.tsx`
- `apps/web/src/screens/auth/TelegramEntryPage.tsx`
- `apps/web/src/screens/auth/AdminWebEntryPage.tsx`
- `governance/builder_reports/slice_21A_browser_supply_chain_hardening_BUILDER_REPORT.md`
- `evidence/slice_runs/slice_21A_browser_supply_chain_hardening_evidence.md`
- `evidence/slice_runs/slice_21A_browser_supply_chain_hardening_test_results.json`

## Comparativa antes/despues

### Supply chain

Antes:

- `corepack pnpm audit --prod` fallaba con HIGH por `valibot >=0.31.0 <1.2.0`.
- Ruta vulnerable: `apps/web > @telegram-apps/sdk@3.11.8 > valibot@1.0.0`.
- Ruta vulnerable: `apps/web > @telegram-apps/sdk@3.11.8 > @telegram-apps/bridge@2.11.0 > valibot@1.0.0`.
- Tambien reportaba MODERATE por `postcss <8.5.10`.

Despues:

- `corepack pnpm audit --prod`: `No known vulnerabilities found`.

### Bundle inicial

Antes:

- `/` route size: `40 kB`
- First Load JS: `142 kB`
- Shared First Load JS: `102 kB`

Despues:

- `/` route size: `1.52 kB`
- First Load JS: `104 kB`
- Shared First Load JS: `102 kB`

Chunks relevantes despues:

- Admin Web: `982.1fd588d1b17de445.js`, 64137 bytes.
- Client surface: `785.fdff3b73473e164d.js`, 56464 bytes.
- Business surface: `319.ff7469e0a5059e5b.js`, 54957 bytes.
- Telegram runtime: `773.307478264e3f00fb.js`, 31748 bytes.
- Telegram entry: `444.db6d90322bfac837.js`, 5634 bytes.

## Validaciones ejecutadas

- `corepack pnpm --filter @nodo/web build`: PASS.
- `corepack pnpm audit --prod`: PASS, no known vulnerabilities.
- `python -m pytest apps/api/tests -q`: PASS, `188 passed, 1 warning in 37.39s`.
- `python -m ruff check apps/api scripts`: PASS, `All checks passed!`.
- `python -m compileall apps/api apps/web/src scripts`: PASS.
- Scan frontend source/build/evidence para secretos, `storage_path`, `account_value`, private keys, seed phrases, bot tokens y claims prohibidos: PASS.
- Scan Admin Web contra Telegram SDK/UI/auth: PASS.
- Scan de `NEXT_PUBLIC_SUPABASE_URL` y `NEXT_PUBLIC_SUPABASE_ANON_KEY` en frontend source/build: PASS.
- Verificacion de Cliente/Negocio con Telegram: PASS, carga concentrada en `TelegramEntryPage`, hooks Telegram cliente y hooks Telegram negocio.
- Verificacion de chunks: PASS, Admin Web queda en chunk separado y no en el chunk inicial comun de cliente.

## CSP

Se agrego `apps/web/public/_headers` con CSP inicial:

- `default-src 'self'`
- `object-src 'none'`
- `base-uri 'self'`
- `frame-ancestors 'self' https://web.telegram.org https://*.telegram.org`
- `connect-src` limitado a API NODO staging/prod y Telegram.

Limitacion documentada: se mantienen `script-src 'self' 'unsafe-inline'` y `style-src 'self' 'unsafe-inline'` por compatibilidad inicial con Next static export. La siguiente mejora natural seria pasar a hashes/nonces si el pipeline lo permite.

## Riesgos residuales

- El gate Admin Web es minimo y usa token backend existente validado por `/api/v1/users/me`; no implementa todavia una experiencia completa de login admin desktop. No arrastra Telegram y no inventa autorizacion frontend, pero conviene formalizar un auth admin web completo en una fase dedicada.
- CSP es incremental para no romper Next static export ni Telegram Mini App; debe endurecerse con hashes/nonces cuando el runtime lo soporte.
- El audit report con el nombre exacto indicado por el prompt no estaba disponible como archivo local; los hallazgos fueron aplicados desde el prompt y confirmados con `pnpm audit`.

## Confirmaciones

- No deploy.
- No READY_FOR_REAL_USE.
- No cambios de reglas de negocio.
- No cambios de backend domain logic.
- No cambios de DB schema ni migraciones.
- No cambios de workers/pool.
- No cambios de ordenes, pagos, creditos, disputas, soporte, bots ni watchers.
