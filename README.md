# NODO

Proyecto gobernado para construir NODO por slices.

Estado actual: `READY_FOR_BUILDER_DOCS`

Este repositorio todavia no contiene implementacion de producto. La primera capa creada es la arquitectura de gobierno para que Cursor/Builder no invente reglas, estados, permisos, copy, pantallas ni arquitectura tecnica.

## Carpetas principales

- `control_plane/`: fuente de verdad del producto, dominio, seguridad, UI, slices, QA y handoff.
- `.cursor/rules/`: reglas activas para Cursor antes de cualquier edicion.
- `governance/`: protocolos de trabajo, reportes del builder, revision del owner y control de cambios.
- `evidence/`: evidencias por slice, pruebas, capturas, logs y reportes de ejecucion.
- `implementation/`: espacio reservado para la implementacion real cuando el owner apruebe iniciar slices.

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
- `READY_FOR_REAL_USE`: solo puede declararlo el owner despues de pruebas reales.

El builder no puede declarar `READY_FOR_REAL_USE`.

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
