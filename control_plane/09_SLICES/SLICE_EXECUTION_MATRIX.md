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

## Slice 19

| Orden | Slice | Objetivo | Dependencias | Estado contractual |
|---|---|---|---|---|
| 19 | slice_19_base_usdc_usdt_credit_topups | Compra/acreditacion de creditos con Base USDC on-chain; USDT Base fuera de MVP hasta contrato oficial | 00-18,08,14B1 | READY_FOR_OWNER_APPROVAL_TO_BUILD_19 |

## Slice 20A

| Orden | Slice | Objetivo | Dependencias | Estado contractual |
|---|---|---|---|---|
| 20A | slice_20A_admin_users_business_control | Centro de Operaciones: control admin de usuarios, negocios y access links | 00-19,14B1,14C | READY_FOR_OWNER_APPROVAL_TO_BUILD_20A |

## Slice 20B

| Orden | Slice | Objetivo | Dependencias | Estado contractual |
|---|---|---|---|---|
| 20B | slice_20B_support_ticket_center | Centro de soporte real para cliente, negocio y Admin Web; tickets, mensajes, adjuntos privados, asignacion, escalamiento y cierre sin mezclar disputa formal | 00-20A,14A,14B,14C | READY_FOR_OWNER_APPROVAL_TO_BUILD_20B |

## Slice 20C

| Orden | Slice | Objetivo | Dependencias | Estado contractual |
|---|---|---|---|---|
| 20C | slice_20C_internal_staff_roles | Delegacion interna segura: staff_profiles, staff_permissions, staff_invites, permisos minimos, audit y Admin Web staff center | 00-20B,14C,20A | READY_FOR_OWNER_APPROVAL_TO_BUILD_20C |

## Slice 24

| Orden | Slice | Objetivo | Dependencias | Estado contractual |
|---|---|---|---|---|
| 24 | slice_24_observability_debuggability | Observabilidad segura: correlation IDs, request logs, breadcrumbs, session replay estructurado sin video, retencion, masking, Admin Web diagnostics | 00-23,20B,20C | READY_FOR_OWNER_APPROVAL_TO_BUILD_24 |

## Slice 31

| Orden | Slice | Objetivo | Dependencias | Estado contractual |
|---|---|---|---|---|
| 31A | slice_31A_backup_restore_disaster_recovery_report_first | Auditoria report-first de backup, restore y disaster recovery sin ejecutar acciones reales | 00-30 | REPORT_READY |
| 31B | slice_31B_backup_restore_contracts_and_sops | Contratos, SOPs y runbooks de backup/restore/DR; sin scripts, sin backups reales y sin restore | 31A | READY_FOR_OWNER_REVIEW |

## Slice 35

| Orden | Slice | Objetivo | Dependencias | Estado contractual |
|---|---|---|---|---|
| 35 | slice_35_business_mini_app_afos_hardening | Endurecimiento AFOS de Mini App Negocio: arquitectura limpia, matriz de acciones sensibles, observabilidad segura, fluidez de pantallas y evidencia de controles sin tocar cliente app, deploy ni produccion | 14B,19,20B,24,34T-34Z | READY_FOR_OWNER_APPROVAL_TO_BUILD_35 |

## Slice 37

| Orden | Slice | Objetivo | Dependencias | Estado contractual |
|---|---|---|---|---|
| 37 | slice_37_client_mini_app_afos_hardening | Endurecimiento AFOS de Mini App Cliente: arquitectura limpia, estados por accion, breadcrumbs seguros, separacion cliente/negocio y repo organizado antes de probar Admin Web | 04,05,07,14A,20B,24,35,36 | READY_FOR_OWNER_REVIEW |

## Slice 42A

| Orden | Slice | Objetivo | Dependencias | Estado contractual |
|---|---|---|---|---|
| 42A | slice_42A_business_reputation_foundation | Contrato, modelo reconstruible, DTOs por audiencia y privacidad de reputacion; sin UI ni escritura funcional de ratings | 03,04,06,07,09 | BUILD_APPROVED_SLICE_A |
