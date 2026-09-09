# Documentation Alignment Pilot Report

Fecha: 2026-09-09

Estado: READY_FOR_OWNER_REVIEW

## Objetivo

Alinear la documentacion vigente de NODO antes de seguir con pruebas operativas de piloto controlado.

Este cambio no toca runtime, logica de producto, backend, frontend de app, migraciones, proveedores, credenciales ni deploy.

## Decision documental vigente

- NODO esta en `STAGING_PILOT_PREPARATION`.
- El piloto controlado puede avanzar solo con alcance pequeno, negocios conocidos, clientes limitados, evidencia actual y aceptacion Owner de riesgos residuales.
- Produccion abierta sigue bloqueada hasta completar legal, rollback, backup/restore real, alertas criticas, ambientes separados y evidencia operativa.
- USDC real/Base mainnet no esta autorizado para piloto sin aprobacion Owner separada de crypto production go-live.
- Staging y pruebas crypto deben hablar de Base Sepolia/testnet.
- Si el Owner decide no activar compras USDC reales, los creditos del piloto pueden asignarse manualmente por Admin/Owner.

## Lenguaje oficial

NODO registra negocios, ofertas, ordenes, chat, evidencia, reputacion y creditos internos. El pago y la entrega entre cliente y negocio ocurren directamente entre las partes. NODO no recibe, retiene, mueve, transmite, libera ni garantiza fondos entre cliente y negocio.

Los creditos NODO son internos para servicios propios de plataforma. No son dinero, deposito, saldo custodiado, retiro disponible ni valor transferible.

## Cambios principales

- README raiz y control plane dejaron de describir el proyecto como solo pre-build.
- Se agrego `operations/PILOT_CONTROLLED_GATE.md` como gate oficial para piloto controlado.
- Operaciones ahora separa piloto controlado de produccion abierta.
- Rollback quedo documentado como minimo por redeploy de SHA anterior; la prueba staging y el rollback nativo de proveedor siguen pendientes de evidencia. No se equipara documentacion con validacion ejecutada.
- Backup/restore real contra proveedor sigue bloqueante para produccion abierta; para piloto requiere aceptacion Owner de riesgo.
- Alertas Telegram Admin quedaron documentadas como app-level existentes, separadas de alertas provider-as-code aun pendientes.
- Documentacion de Base USDC quedo alineada: Base Sepolia/testnet para staging/piloto; Base mainnet/USDC real bloqueado.
- Textos de cliente/negocio se suavizaron hacia `datos publicados`, `reportar evidencia`, `verificar ingreso`, `entrega acordada` y `coordinacion directa`.
- Se documento que nombres tecnicos heredados como `remitter`, `payment_reported` o `payment_instructions` no autorizan copy publico riesgoso.

## No tocado

- No se tocaron archivos bajo `apps/api/**`.
- No se tocaron archivos bajo `apps/web/src/**`.
- No se tocaron migraciones.
- No se tocaron scripts operativos.
- No se ejecuto deploy.
- No se modificaron variables reales de proveedores.
- No se expusieron secretos.

## Validacion ejecutada

- `git diff --check`: PASS.
- Busqueda de estado viejo `PRE-BUILD` / `READY_FOR_BUILDER_DOCS` como estado vigente: PASS, sin resultados activos.
- Busqueda de copy publico riesgoso en docs de UI/pantallas/operaciones: PASS con excepcion esperada de listas `Forbidden copy`.

## Revision previa a commit y push

- Alcance revisado: 51 archivos, exclusivamente Markdown y las plantillas `.env.example` / `.env.staging.example`.
- Diff completo revisado; ningun archivo de runtime, migracion o script operativo seleccionado.
- `secret-guard` sobre las adiciones detecto tres coincidencias de entropia: rutas de documentos en README, auditoria historica y change management. Se verificaron como falsos positivos, sin agregar excepciones globales.
- Comprobacion adicional de formato de tokens Telegram, claves privadas y valores sensibles en las plantillas: PASS. Las nuevas entradas sensibles estan vacias.
- Se corrigio la contradiccion que describia rollback staging como parcialmente validado; queda `DOCUMENTED / NOT VALIDATED IN STAGING`.
- Se precisaron worktree fuente, metadata de release Railway y verificacion backend-first; documentar comandos no significa ejecutarlos.
- Las consultas GET de version previas al commit reportaron backend y web en `c24726ada11e21c05154c64e4b3bfef6e8490826`, ambiente staging. Esto prueba identidad en ese momento, no rollback ni salud completa.
- Los cambios pendientes del website y los dos reportes read-only previos de Admin/Negocio quedan fuera de este commit y se preservan.
- No se ejecutaron tests de producto ni builds en este corte documental.

## Riesgos pendientes

- Falta revision legal profesional antes de produccion abierta.
- Falta backup/restore real validado contra proveedor.
- Falta rollback nativo o evidencia completa de proveedor para produccion abierta.
- Faltan alertas provider-as-code para API/DB/Redis/Cloudflare/Railway.
- Falta decision Owner separada para cualquier USDC real/Base mainnet.

## Veredicto

La documentacion queda alineada para continuar con preparacion de piloto controlado.

No queda autorizada produccion abierta.
