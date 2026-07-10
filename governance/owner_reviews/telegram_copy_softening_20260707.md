# NODO Telegram copy softening - 2026-07-07

Estado: `STAGING_DEPLOYED_FOR_OWNER_REVIEW`

No se declara `READY_FOR_REAL_USE`.

## Objetivo

Reducir lenguaje que puede asustar al cliente en la Mini App de Telegram y mantener la proteccion de NODO sin repetir avisos legales en cada pantalla.

## Cambios principales

- Welcome copy mas directo: comparar negocios verificados, elegir tasa y crear orden.
- Terminos suavizados: se explica que el pago se realiza directamente con el negocio, sin usar lenguaje repetido de retencion/garantia.
- Marketplace trust banner suavizado.
- Detalle de negocio mantiene una guia antes de crear orden: revisar monto, tasa y negocio.
- Formulario de crear orden ya no repite el disclaimer duro.
- Mensajes `Empty state`, `Forbidden` y copy tecnico fueron reemplazados por estados humanos.
- `evidencia` visible en errores principales fue reemplazado por `comprobante`.
- Disclaimers backend usados como notices fueron suavizados.

## Validacion

- `corepack pnpm --filter @nodo/web build`: OK.
- `python -m pytest apps/api/tests -q`: 100 passed, 1 warning conocido Starlette/httpx.
- `python -m ruff check apps/api scripts`: OK.
- `python -m compileall apps/api scripts`: OK.
- Backend Railway deploy: `ad10677b-4e43-4ad7-88ad-65a15e608dcc`.
- Frontend Cloudflare deploy: `https://d1605611.nodo-staging.pages.dev`.
- Canonical frontend: `https://nodo-staging.pages.dev`.
- Public `/ready`: database OK, Redis OK.

## Published JS check

`https://nodo-staging.pages.dev/_next/static/chunks/app/page-e2a4cdcaffe59ea7.js`

- `Compara negocios verificados`: true.
- `Revisa monto, tasa y negocio`: true.
- `Estamos ajustando la conexion`: true.
- `NODO no recibe`: false.
- `Empty state`: false.
- `Forbidden`: false.
- Railway API base URL present: true.

## Pendiente

- Owner debe revisar visualmente desde Telegram.
- El bot aun no tiene handler backend de `/start` con mensaje de bienvenida y boton `Abrir NODO`; eso debe construirse como tarea separada.
