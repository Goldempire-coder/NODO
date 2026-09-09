# NODO

Proyecto gobernado para construir NODO por slices.

Estado actual: `STAGING_PILOT_PREPARATION`

Este repositorio ya contiene implementacion de producto para backend FastAPI, frontend Next/Telegram Mini Apps, Admin Web, contratos de creditos, migraciones, pruebas, scripts de staging y documentacion operativa.

La documentacion gobierna el alcance para que ningun builder invente reglas, estados, permisos, copy, pantallas, despliegues o arquitectura tecnica. Antes del piloto, el estado permitido es `READY_FOR_OWNER_REVIEW` o `PILOT_CONTROLLED_REVIEW_REQUIRED`; el builder no puede declarar `READY_FOR_REAL_USE` ni `READY_FOR_PRODUCTION`.

## Carpetas principales

- `control_plane/`: fuente de verdad del producto, dominio, seguridad, UI, slices, QA y handoff.
- `.cursor/rules/`: reglas activas para Cursor antes de cualquier edicion.
- `governance/`: protocolos de trabajo, reportes del builder, revision del owner y control de cambios.
- `evidence/`: evidencias por slice, pruebas, capturas, logs y reportes de ejecucion.
- `apps/api/`: backend FastAPI.
- `apps/web/`: frontend Next exportado a Cloudflare Pages, incluyendo Cliente, Negocio, Admin Web y website.
- `apps/contracts/`: contratos locales/testnet para creditos NODO.
- `database/migrations/`: migraciones up/down.
- `operations/`: runbooks, SOPs, matriz de recuperacion y gate de piloto.
- `scripts/`: tooling de validacion, migracion, staging, smokes y deploy web.

## Regla principal

Ningun builder puede construir features sin:

1. Leer el orden obligatorio del `control_plane/README.md`.
2. Entregar un `BUILDER_UNDERSTANDING_REPORT`.
3. Recibir aprobacion del owner para el slice asignado.
4. Construir solo el slice asignado.
5. Entregar reporte de corte con archivos, lineas, pruebas y evidencia.

## Estados permitidos

- `READY_FOR_BUILDER_DOCS`: documentacion lista para iniciar slices.
- `READY_FOR_OWNER_REVIEW`: un slice fue construido y tiene evidencia para revision.
- `PILOT_CONTROLLED_REVIEW_REQUIRED`: candidato puede evaluarse para piloto pequeno, con riesgos documentados y sin declarar produccion abierta.
- `READY_FOR_REAL_USE`: solo puede declararlo el owner despues de pruebas reales.

El builder no puede declarar `READY_FOR_REAL_USE`.

## Piloto controlado

El piloto inicial debe usar alcance pequeno, negocios conocidos, clientes limitados y creditos manuales si el Owner decide no activar compras USDC reales. Staging sigue usando Base Sepolia/testnet para creditos on-chain hasta una aprobacion Owner separada de crypto production go-live.

Antes de abrir piloto, revisar `operations/PILOT_CONTROLLED_GATE.md`, `operations/CHANGE_MANAGEMENT.md`, `operations/DISASTER_RECOVERY.md`, `operations/MONITORING.md` y `control_plane/10_QA/DEPLOY_READINESS_GATE.md`.

## Inicio de trabajo

Antes de construir, abrir:

1. `control_plane/README.md`
2. `control_plane/13_HANDOFF/BUILDER_START_PROMPT.md`
3. `governance/workflow/SLICE_START_PROTOCOL.md`
4. `.cursor/rules/nodo-governance.mdc`

## Regla UI Telegram

Las pantallas de Mini App deben sentirse nativas dentro de Telegram.

Builder debe usar como base:

- `@telegram-apps/telegram-ui` para componentes donde aplique.
- Telegram Mini App SDK para `initData`, `themeParams`, `MainButton`, safe areas, haptics y viewport.
- Los tokens visuales de NODO en `control_plane/07_UI_UX/DESIGN_TOKENS.md`.
- Las reglas de `control_plane/07_UI_UX/TELEGRAM_MINI_APP_RULES.md`.
- Las reglas de motion en `control_plane/07_UI_UX/MOTION_AND_INTERACTION.md`.

No se permite construir una UI web generica ni desktop-first para las pantallas remitter/business.

La entrada/home debe incluir logo animado y microinteracciones controladas, sin loops pesados ni efectos que rompan performance.
