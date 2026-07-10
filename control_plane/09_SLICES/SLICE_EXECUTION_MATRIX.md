# SLICE_EXECUTION_MATRIX.md

Este documento gobierna el orden de construccion. Ningun slice puede saltar dependencias ni tocar dominios de otro slice sin permiso explicito del owner.

## Estado global

Estado documental: READY_FOR_BUILDER_DOCS.

Estado de producto: PRE-BUILD. No existe autorizacion automatica de READY_FOR_REAL_USE. Esa decision es solo del owner despues de QA, monitoreo, deploy y prueba real controlada.

## Slices oficiales

| Orden | Slice | Objetivo | Depende de | Estado documental |
| --- | --- | --- | --- | --- |
| 00 | slice_00_foundation | Repo, arquitectura, tooling, envs, CI, migraciones base | ninguno | READY_FOR_BUILDER |
| 01 | slice_01_auth_telegram | Login Telegram Mini App, usuario, sesion, roles | 00 | READY_FOR_BUILDER |
| 02 | slice_02_business_verification | Onboarding y verificacion de negocios | 00,01 | READY_FOR_BUILDER |
| 03 | slice_03_ads_marketplace | Anuncios, ranking, busqueda, disponibilidad | 00,01,02 | READY_FOR_BUILDER |
| 04 | slice_04_order_creation | Creacion de orden con snapshot del anuncio | 00,01,02,03 | READY_FOR_BUILDER |
| 05 | slice_05_payment_instructions_reports | Instrucciones y reporte de pago del remitente | 04 | READY_FOR_BUILDER |
| 06 | slice_06_business_order_ops | Confirmacion de pago, entrega y operaciones del negocio | 05 | READY_FOR_BUILDER |
| 07 | slice_07_chat_disputes | Chat por orden, disputa, evidencia y resolucion | 04,05,06 | READY_FOR_BUILDER |
| 08 | slice_08_credits_referrals | Creditos publicitarios, Stripe, Zelle, USDT, fundadores | 00,01,02 | READY_FOR_BUILDER |
| 09 | slice_09_admin_console | Panel admin funcional completo | 00-08 | READY_FOR_BUILDER |
| 10 | slice_10_jobs_notifications | Workers, notificaciones, expiraciones y recordatorios | 04-09 | READY_FOR_BUILDER |
| 11 | slice_11_hardening_deploy | Seguridad, carga, observabilidad, backup, deploy | 00-10 | READY_FOR_BUILDER |

## Contrato minimo por slice

Cada carpeta de slice debe contener y respetar:

- README.md: proposito, dependencias, archivos autorizados.
- SCOPE.md: que se construye y que queda fuera.
- DATA_CONTRACT.md: tablas, columnas, indices, constraints y migraciones.
- STATE_CONTRACT.md: estados permitidos y transiciones.
- API_CONTRACT.md: endpoints, payloads, errores e idempotencia.
- SECURITY_CONTRACT.md: auth, RBAC, rate limits, datos sensibles.
- UI_CONTRACT.md: pantallas, componentes, copy, estados vacios/carga/error.
- AUDIT_EVENTS.md: eventos obligatorios.
- ERROR_CASES.md: errores esperados y respuesta UX/API.
- QA.md: tests unitarios, integracion, contrato, seguridad y manuales.
- DO_NOT_BUILD.md: limites explicitos.
- BUILDER_REPORT.md: reporte final obligatorio.

## Regla de independencia tecnica

El builder debe separar routes/controllers, schemas/DTOs, services, repositories, state machines, policies/RBAC, audit logger, notification jobs, payment adapters, storage adapters, UI components y feature hooks/state.

Prohibido mezclar queries, permisos, transiciones, auditoria y response HTTP en una misma funcion.

## Gate antes de empezar un slice

El builder debe entregar primero un Understanding Report con slice asignado, documentos leidos, pantallas afectadas, tablas afectadas, endpoints afectados, estados afectados, permisos afectados, riesgos detectados y limites de scope.

Si el owner no aprueba ese reporte, no se construye.

## Gate antes de cortar un slice

El reporte final debe incluir archivos tocados, lineas exactas tocadas, funciones/componentes tocados, contratos cumplidos, pruebas ejecutadas, pruebas no ejecutadas y razon, riesgos residuales y que NO se toco.

No se permite declarar un slice listo sin revisar lineas exactas.

## Slice 14

| Orden | Slice | Objetivo | Dependencias | Estado contractual |
|---|---|---|---|---|
| 14 | slice_14_surface_separation_support_intake | Separacion de superficies, bot intake de negocios y soporte/tickets | 00-11 | CONTRACTS_READY |
| 14A | slice_14A_client_surface_cleanup | Mini App Cliente separada de negocio/admin | 00-14 | BUILT_PENDING_OWNER_REVIEW |
| 14B | slice_14B_business_mini_app_surface | Mini App Negocio separada con metodos aprobados y sin admin/cliente | 00-14A | OWNER_AUDIT_FIX_ACCEPTED |
| 14B1 | slice_14B1_business_access_control_contracts | Acceso negocio gobernado: surface/session, business_access_links y admin linking | 00-14B | CONTRACTS_READY |
| 14C | slice_14C_admin_web_surface | Panel Admin Web Desktop separado, sin shell Telegram/Mini App | 00-14B | READY_FOR_BUILDER |
| 14D | slice_14D_business_intake_bot | Bot Registro Negocios: intake conversacional, contacto validado, documentos privados y solicitud pendiente | 00-14B1,14C | READY_FOR_OWNER_APPROVAL_TO_BUILD_14D |
| 14D2 | slice_14D2_business_intake_conversation_bot | Bot Registro Negocios separado: `BUSINESS_INTAKE_BOT_TOKEN`, webhook propio, pasos conversacionales canonicos, persistencia parcial y descarga privada de documentos Telegram | 00-14D | CONTRACTS_READY |

## Slice 15

| Orden | Slice | Objetivo | Dependencias | Estado contractual |
|---|---|---|---|---|
| 15 | slice_15_scalability_runtime_hardening | Escalabilidad runtime: marketplace reads, cache, auth liviana no sensible, workers/pool y stress progresivo | 00-14D2 | READY_FOR_OWNER_APPROVAL_TO_BUILD_15 |
