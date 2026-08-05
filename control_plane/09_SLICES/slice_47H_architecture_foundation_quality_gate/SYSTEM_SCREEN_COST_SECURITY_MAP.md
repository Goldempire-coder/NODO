# NODO System, Screen, Cost And Security Map

Estado: DRAFT_READY_FOR_OWNER_REVIEW

Fecha: 2026-08-05

## Proposito

Este documento mapea donde vive el sistema NODO hoy y define como organizarlo
para que la app siga siendo segura y barata.

No es una autorizacion para construir, desplegar, migrar o declarar
`READY_FOR_REAL_USE`. Es un mapa informado para saber:

- donde vive cada pantalla;
- que hook/modelo la gobierna;
- que API llama;
- que modulo backend decide;
- que datos son fuente de verdad;
- que se puede conservar en pantalla;
- que nunca debe depender del frontend;
- donde conviene ahorrar costo sin debilitar seguridad.

## Resumen Ejecutivo

NODO ya esta organizado como monolito modular:

- `apps/web`: una app Next.js con tres superficies visibles:
  Cliente, Negocio y Admin Web.
- `apps/api`: una API FastAPI unica con modulos por dominio.
- `database/migrations`: fuente de verdad del schema PostgreSQL.
- `control_plane`: contratos, slices, reglas y gates.
- `scripts`: validaciones, migraciones, staging, smoke y diagnosticos.

La estrategia recomendada no es microservicios ni Kubernetes. La estrategia
correcta para minimo costo es:

1. mantener backend unico;
2. separar responsabilidades internas;
3. hacer que el backend sea autoridad final;
4. dejar en pantalla solo estado de experiencia y datos ya autorizados;
5. evitar polling innecesario;
6. cachear solo lecturas publicas o efimeras;
7. usar PostgreSQL como fuente canonica;
8. usar Redis solo para locks, idempotencia, rate limits y cache corta;
9. no descargar archivos automaticamente;
10. medir antes de optimizar o migrar proveedor.

## Fuentes Leidas

- `control_plane/00_GOVERNANCE/CODE_ARCHITECTURE_MASTER.md`
- `control_plane/00_GOVERNANCE/ENGINEERING_GUARDRAILS.md`
- `control_plane/01_PRODUCT/SURFACE_ARCHITECTURE_MASTER.md`
- Surface boundaries contract under `control_plane/02_ARCHITECTURE/`
- Observability architecture contract under `control_plane/02_ARCHITECTURE/`
- Cost strategy from slice 47D
- arbol de `apps/web/src/screens`
- arbol de `apps/web/src/hooks`
- arbol de `apps/web/src/api`
- arbol de `apps/api/app/modules`
- migraciones `database/migrations`
- historial git de hotspots y bug magnets.

## Superficies Frontend

| Superficie | Entrada | Shell | Modelo principal | Pantallas |
| --- | --- | --- | --- | --- |
| Cliente Mini App | `apps/web/src/app/page.tsx` | `apps/web/src/screens/client/ClientWorkspaceShell.tsx` | `apps/web/src/hooks/useClientWorkspaceModel.ts` | `apps/web/src/screens/client/*` |
| Negocio Mini App | `apps/web/src/app/business/page.tsx` | `apps/web/src/screens/business-app/BusinessMiniAppShell.tsx` | `apps/web/src/hooks/useBusinessMiniAppModel.ts` | `apps/web/src/screens/business-app/*` |
| Admin Web | auth/admin entry + shell admin | `apps/web/src/screens/admin-web/AdminWebShell.tsx` | `apps/web/src/hooks/useAdminWebModel.ts` | `apps/web/src/screens/admin-web/*` |
| Auth | app entry/surface login | `apps/web/src/screens/auth/*` | `apps/web/src/hooks/useTelegramAuth.ts` + API session | `AdminWebEntryPage`, `AuthEntryPage`, `TelegramEntryPage` |

## Pantallas Cliente

| Vista | Donde vive | Hook/modelo | Backend principal | Autoridad |
| --- | --- | --- | --- | --- |
| Welcome/terminos/perfil inicial | `ClientOnboardingScreens.tsx` | `useClientWorkspaceModel`, `useClientWorkspaceState` | `users`, `surface`, auth | Backend valida sesion; pantalla solo guia |
| Marketplace busqueda/lista/detalle | `ClientMarketplaceScreens.tsx` | `useClientMarketplaceModel` | `ads`, `businesses`, `business_capacity`, reputation snapshot | Backend filtra negocios, monto, estado y disponibilidad |
| Crear orden/confirmacion | `ClientOrderScreens.tsx` | `useRemitterOrdersModel` | `orders`, `ads`, `business_capacity` | Backend congela tasa, monto, negocio, metodo y reserva |
| Ordenes/mensajes | `ClientOrderScreens.tsx` | `useRemitterOrdersModel` | `orders`, `notifications/attention` | Backend decide estados y pendientes |
| Chat por orden | `ClientOrderChatScreen.tsx` | `useClientChatDisputesModel`, `usePaymentReportModel` | `chat`, `orders/payment_routes`, `receiver_details` | Backend valida participante, estado, reveal y reporte |
| Reportar pago legacy | `ClientPaymentScreens.tsx` | `usePaymentReportModel` | `orders/payment_routes` | Backend toma monto de la orden y valida estado |
| Soporte cliente | `ClientSupportScreen.tsx` | `useSurfaceSupportModel` | `support` | Backend valida ownership/ticket/superficie |

## Pantallas Negocio

| Vista | Donde vive | Hook/modelo | Backend principal | Autoridad |
| --- | --- | --- | --- | --- |
| Dashboard | `BusinessDashboardScreen.tsx` | `useBusinessMiniAppModel`, `useBusinessHomeSummaryModel` | `businesses`, `orders`, `attention` | Backend decide acceso negocio y summary |
| Anuncios | `BusinessAdsScreens.tsx` | `useBusinessAdsModel`, `useBusinessAdActionsModel` | `ads`, `credits`, `business_capacity` | Backend valida PIN, creditos, rango y estado |
| Metodos Zelle/USDT | `BusinessAdsScreens.tsx` / `PaymentMethodsScreen` | `useBusinessPaymentMethodsModel`, `businessPaymentMethodHelpers` | `businesses/payment-methods` | Backend valida metodo, ownership y PIN |
| Ordenes entrantes | `BusinessOrdersScreens.tsx` | `useBusinessOrdersModel` | `orders/business_routes` | Backend valida owner participante y estado |
| Chat negocio | `BusinessChatScreen.tsx` | `useBusinessChatModel` | `chat`, `orders/business_routes` | Backend valida participante y acciones financieras |
| Creditos | `BusinessCreditsScreens.tsx` | `useBusinessCreditsModel` | `credits` | Backend valida compra, wallet, ledger y proof |
| PIN/reglas/perfil | `BusinessPinScreen.tsx`, `BusinessSettingsScreen.tsx` | `useBusinessAccessModel` | `businesses/public_routes` | Backend valida PIN y surface access |
| Soporte negocio | `BusinessSupportScreen.tsx` | `useSurfaceSupportModel` | `support` | Backend valida negocio/recurso/ticket |

## Pantallas Admin Web

| Area | Donde vive | Hook/modelo | Backend principal | Autoridad |
| --- | --- | --- | --- | --- |
| Shell/dashboard | `AdminWebShell.tsx`, `AdminWebScreens.tsx` | `useAdminWebModel`, `useAdminOverviewModel` | `admin`, `admin_notifications` | Backend RBAC/staff permissions |
| Incidentes/metricas/friccion | `AdminOverviewScreens.tsx` | `useAdminIncidentModel`, `useAdminDashboardMetricsModel`, `useAdminUXFrictionModel` | `admin`, `observability` | Backend agrega datos seguros |
| Usuarios/negocios | `AdminUserScreens.tsx`, `AdminBusinessScreens.tsx` | `useAdminUsersModel`, `useAdminBusinessesModel` | `admin`, `businesses/admin_routes` | Backend RBAC + audit |
| Ordenes/disputas | `AdminOrderDisputeScreens.tsx` | `useAdminOrdersDisputesModel` | `admin`, `disputes` | Backend decide acceso y resolucion |
| Investigacion | `AdminInvestigation*` | `useAdminInvestigation*` | `admin/investigation` | Backend aplica RBAC y masking |
| Evidencia chat | `AdminOrderChatEvidencePanel.tsx` | `useAdminOrderChatEvidenceModel` | `admin/order-chat-evidence` | Endpoint auditado; no chat general |
| Soporte | `AdminSupportScreens.tsx` | `useAdminSupportModel` | `support/admin` | Backend staff/RBAC/scope |
| Creditos | `AdminCreditScreens.tsx` | `useAdminCreditsModel` | `credits/admin` | Backend ledger/audit |
| Intake | `AdminBusinessIntakeScreens.tsx` | `useAdminBusinessIntakeModel` | `business_intake/admin` | Backend documentos privados |
| Staff | `AdminStaffScreens.tsx` | `useAdminStaffModel` | `staff` | Backend permisos granulares |
| Audit logs | `AdminAuditScreens.tsx` | `useAdminAuditLogsModel` | `admin/audit-logs` | Backend allowlist/masking |

## API Frontend

Los clientes HTTP viven en `apps/web/src/api`.

| Archivo | Responsabilidad |
| --- | --- |
| `client.ts` | request base, auth refresh, errores API |
| `session.ts` | session storage/refresh por superficie |
| `auth.ts`, `users.ts`, `surface.ts` | login, usuario, session surface |
| `ads.ts`, `businesses.ts`, `businessAds.ts` | marketplace y negocio/anuncios |
| `orders.ts`, `businessOrders.ts`, `paymentReports.ts` | ordenes, acciones negocio, pago reportado |
| `chat.ts` | mensajes, adjuntos, reveal de datos |
| `support.ts` | soporte Cliente/Negocio/Admin |
| `credits.ts` | creditos y compras |
| `notifications.ts` | attention summary y acknowledge |
| `admin.ts` | Admin Web agregado |

Regla: estos archivos no deben contener reglas de negocio. Solo tipan y llaman
al backend.

## Backend Modules

| Modulo | Donde vive | Responsabilidad | Datos principales |
| --- | --- | --- | --- |
| Auth/users/surface | `apps/api/app/auth`, `apps/api/app/routes`, `modules/users` | Telegram auth, JWT, sesiones, superficie | `users`, `sessions` |
| Businesses | `modules/businesses` | negocio, acceso, PIN, payment methods, admin review | `businesses`, `business_payment_methods`, `business_access_links` |
| Business intake | `modules/business_intake` | bot intake, solicitudes y documentos | `business_intake_requests`, `file_assets` |
| Ads/marketplace | `modules/ads` | anuncios, busqueda, cache, credit holds | `ads`, `credit_wallets`, `credits_ledger` |
| Business capacity | `modules/business_capacity` | capacidad disponible, reservas, limite diario | `business_capacity`, `business_capacity_reservations` |
| Orders | `modules/orders` | orden, estados, pago reportado, completion, rating | `orders`, `order_state_events`, `payment_reports`, `order_receiver_details`, `ratings` |
| Chat | `modules/chat` | mensajes, adjuntos, reveal Zelle/USDT/Pago Movil, anti-evasion | `messages`, `message_attachments`, `file_assets` |
| Disputes | `modules/disputes` | disputa formal y resolucion admin | `disputes`, `dispute_events` |
| Support | `modules/support` | tickets, mensajes, adjuntos, admin/support workflow | `support_tickets`, `support_messages`, `support_ticket_events`, `file_assets` |
| Notifications | `modules/notifications` | attention summary, Telegram jobs, notification jobs | `notification_jobs`, `surface_attention_read_state` |
| Admin | `modules/admin`, `modules/admin_notifications`, `modules/staff` | admin dashboard, investigation, staff, audit views | `staff_profiles`, `staff_permissions`, `admin_notifications`, `audit_logs` |
| Credits | `modules/credits` | credit purchases, ledgers, Stripe/manual/Base | `credit_purchases`, `credit_purchase_onchain_payments`, `credits_ledger` |
| Jobs | `modules/jobs` | expirations, completion, retries, worker/scheduler | `job_runs`, domain tables |
| Observability | `modules/observability` | frontend events y diagnostics | `frontend_observability_events` |

## Backend Routing

Los routers se montan en `apps/api/app/main.py` con prefijo `/api/v1`.

| Area | Ruta base |
| --- | --- |
| Auth | `/auth/*` |
| Surface | `/surface/session` |
| Businesses | `/businesses`, `/business/*`, `/admin/businesses/*` |
| Ads | `/ads/search`, `/ads/{id}`, `/business/ads/*` |
| Orders Cliente | `/orders`, `/orders/mine`, `/orders/{id}`, `/orders/{id}/cancel`, `/orders/{id}/rating` |
| Orders Negocio | `/business/orders`, `/business/orders/{id}/*` |
| Payment reports | `/orders/{id}/payment-instructions`, `/payment-evidence`, `/payment-report` |
| Chat | `/orders/{id}/messages`, `/share-zelle`, `/share-payment-details`, `/message-attachments` |
| Support | `/support/tickets`, `/admin/support/tickets` |
| Notifications | `/notifications/attention-summary`, `/notifications/attention/acknowledge` |
| Admin | `/admin/*` |
| Jobs | `/admin/jobs/*` |
| Observability | `/observability/events` |

## Database Truth Map

| Dominio | Tablas fuente de verdad |
| --- | --- |
| Usuarios/sesion | `users`, `sessions` |
| Auditoria/jobs/base | `audit_logs`, `job_runs`, `app_metadata` |
| Negocios | `businesses`, `business_verification_submissions`, `business_access_links`, `business_payment_methods` |
| Archivos privados | `file_assets` + storage privado |
| Anuncios/creditos | `ads`, `credit_wallets`, `credits_ledger`, `credit_purchases`, `credit_purchase_onchain_payments` |
| Ordenes | `orders`, `order_state_events`, `payment_reports`, `order_receiver_details` |
| Chat/disputas | `messages`, `message_attachments`, `disputes`, `dispute_events` |
| Soporte | `support_tickets`, `support_messages`, `support_ticket_events` |
| Staff/Admin | `staff_profiles`, `staff_permissions`, `staff_invites`, `admin_credentials`, `admin_notifications` |
| Intake | `business_intake_requests` |
| Reputacion | `ratings`, `business_public_reputation_snapshots` |
| Capacidad | `business_capacity`, `business_capacity_reservations` |
| Attention/observabilidad | `surface_attention_read_state`, `notification_jobs`, `frontend_observability_events` |

## Que Puede Vivir En Pantalla

La pantalla puede conservar datos para experiencia, no para autoridad:

- vista actual;
- formularios en progreso;
- mensajes ya autorizados;
- snapshot visual de una orden ya cargada;
- lista de negocios obtenida por API;
- estado de loading/error;
- ultimo resultado valido no sensible;
- badges/attention visibles;
- copia local de texto publico;
- archivos seleccionados antes de subir.

La pantalla puede ocultar botones para guiar al usuario, pero el backend debe
rechazar la accion igualmente si el usuario manipula la app.

## Que Debe Mandar Siempre El Backend

El backend es autoridad para:

- identidad Telegram/JWT;
- rol, surface y staff permissions;
- ownership de negocio, orden, ticket, adjunto y archivo;
- estados de orden, disputa, ticket, anuncio y creditos;
- tasa, monto, metodo y snapshots de orden;
- creacion/cancelacion/expiracion/completion;
- pago reportado y confirmacion recibida;
- revelacion de Zelle, USDT y Pago Movil;
- signed URLs de archivos privados;
- rating permitido y snapshot publico;
- creditos, capacidad, reservas y limites diarios;
- idempotencia y race conditions;
- audit logs;
- rate limits;
- notificaciones durables.

## Estrategia De Costo Minimo

### 1. Mantener monolito modular

No hay evidencia actual que justifique microservicios. Separar procesos antes
de medir aumentaria costo fijo, observabilidad y complejidad.

Mantener:

- un backend FastAPI;
- una base PostgreSQL;
- Redis compartido solo para coordinacion/cache corta;
- storage privado;
- frontend estatico en Cloudflare Pages.

### 2. Reducir polling por superficie

Estado actual observado:

- attention global: `15s`, visible-only, backoff/jitter.
- chat Cliente y Negocio: refresco activo en pantalla.
- soporte Cliente/Negocio: `5-8s` en pantalla.
- Admin: background `15s`, soporte `5s`.

Estrategia:

- mantener attention como resumen barato;
- pausar todo polling fuera de pantalla;
- bloquear solapamiento de requests;
- compartir refresh si varias partes piden lo mismo;
- subir intervalos de soporte/admin si no hay actividad;
- evaluar SSE/WebSocket solo cuando el volumen haga mas caro el polling.

### 3. Cachear solo lo seguro

Seguro para cache corta:

- marketplace publico ya filtrado;
- copy/labels publicos;
- estado de feature flags no sensible;
- perfiles publicos permitidos;
- attention summary por usuario/superficie con TTL corto si no rompe freshness.

No cachear como autoridad:

- permisos;
- saldos/creditos;
- capacidad disponible final;
- estados de orden;
- payment instructions sensibles;
- Pago Movil;
- signed URLs;
- datos bancarios completos;
- admin/support private data.

### 4. DB primero, Redis despues

PostgreSQL debe seguir siendo fuente canonica. Redis se usa para:

- locks temporales;
- idempotencia;
- rate limit;
- dedupe;
- cache versionada corta;
- worker singleton.

Si Redis falla, una mutacion sensible no debe fingir exito ni duplicar efectos.

### 5. Storage disciplinado

Reglas para bajar costo:

- no descargar adjuntos automaticamente;
- no precargar evidencias;
- no guardar signed URLs;
- lazy load de imagenes;
- miniaturas futuras si el volumen lo exige;
- limite de tamano por tipo;
- retencion diferenciada por evidencia/auditoria/temporal;
- no borrar evidencia auditada sin contrato.

### 6. Logs utiles, no ruidosos

Logs deben permitir investigar, pero no duplicar payloads ni llenar storage.

Guardar:

- request_id/correlation_id/operation_id;
- actor/recurso/accion/resultado;
- duracion;
- codigo de error;
- version/build;
- ids autorizados.

No guardar:

- tokens;
- Zelle completo;
- Pago Movil completo;
- wallet completa si no hace falta;
- signed URL;
- storage_path;
- cuerpos privados de chat;
- archivos.

### 7. Jobs por lotes y con evidencia

Jobs que conviene mantener centralizados:

- expiracion de ordenes;
- completion automatico;
- notificaciones;
- snapshots de reputacion;
- reconciliacion;
- cleanup/retention futura.

Cada job debe tener:

- singleton lock;
- batch size;
- idempotencia;
- run record;
- last success;
- backlog/age metric;
- error terminal visible.

### 8. Marketplace barato

Marketplace debe evitar:

- traer negocios que no pueden aceptar el monto;
- ordenar por metricas vivas privadas;
- queries sin cursor/indice;
- re-fetch completo por cada cambio pequeno.

Estrategia:

- filtro backend antes de limite;
- paginacion;
- cache corta versionada;
- invalidacion al cambiar anuncio/orden/capacidad;
- reputacion publica por snapshot, no por live ranking.

### 9. Frontend ligero

Mantener en frontend:

- navegacion;
- estados de UI;
- composicion visual;
- previews locales;
- botones compactos;
- mensajes de error humanos.

Evitar en frontend:

- reglas financieras;
- permisos;
- transiciones;
- validaciones finales;
- calculos canonicos;
- duplicar decisiones del backend;
- polling agresivo;
- formularios bloqueantes innecesarios.

## Que Hay Que Organizar

| Prioridad | Area | Problema/Riesgo | Estrategia |
| --- | --- | --- | --- |
| P0 | `globals.css` | Hotspot y bug magnet; estilos de todas las superficies mezclados | separar CSS por superficie/componente sin cambiar UX |
| P0 | chat Cliente/Negocio | Pantallas/hook muy movidos; riesgo de drift y costo por polling | crear contrato unico de chat surface y shared composer seguro |
| P0 | frontend polling | intervalos dispersos en pantallas | centralizar politica visible-only/backoff/coalescing |
| P0 | API clients | muchos archivos, buen limite, pero sin contrato generado | mantener tipos estrictos; evitar reglas de negocio en clients |
| P1 | Admin model | `useAdminWebModel.ts` es hotspot | modularizar por area sin tocar contratos |
| P1 | soporte | soporte tiene polling y UI similar en cliente/negocio | compartir modelo comun seguro y solo diferenciar surface |
| P1 | payments/chat | Zelle/USDT/Pago Movil viven entre chat y ordenes | documentar comando de dominio unico por accion financiera |
| P1 | jobs/scheduler | seguridad/costo dependen de ejecucion periodica demostrada | evidencia staging de scheduler, run age y backlog |
| P1 | storage | adjuntos pueden subir costo si se visualizan sin control | thumbnails/lazy/reveal explicito/retencion |
| P1 | observability | existe arquitectura, falta medir por flujo | costo por orden, chat, soporte, dashboard abierto |
| P2 | docs/runtime drift | muchos slices cambiaron reglas | reporte 47H debe producir reparaciones pequenas |
| P2 | dependency/cost gates | proveedor se mantiene, pero falta presupuesto medido | 47D + 47G + 47H antes de produccion |

## Hotspots Observados En Git

Archivos mas movidos y/o asociados a fixes:

- `apps/api/tests/test_auth_lifecycle_static.py`
- `apps/web/src/app/globals.css`
- `apps/web/src/hooks/useAdminWebModel.ts`
- `apps/web/src/app/admin-web.css`
- `apps/web/src/hooks/useClientWorkspaceModel.ts`
- `apps/web/src/screens/business-app/BusinessSupportScreen.tsx`
- `apps/web/src/screens/business-app/BusinessChatScreen.tsx`
- `apps/web/src/screens/client/ClientOrderChatScreen.tsx`
- `apps/web/src/hooks/business-mini-app/useBusinessChatModel.ts`
- `apps/web/src/hooks/workspace/useClientChatDisputesModel.ts`
- `apps/api/app/modules/chat/service.py`

Interpretacion: las pantallas de chat/soporte/admin y estilos globales son las
zonas con mas riesgo de complejidad accidental. No significa que esten mal;
significa que deben tener contratos y limites mas fuertes.

## Estrategia Por Fases

### Fase A - Mapa y congelamiento de autoridad

- Aprobar este mapa como referencia inicial.
- Ejecutar 47H report-first.
- No permitir que Builder mueva pantallas grandes sin entender hooks, API y
  backend propietario.

### Fase B - Reducir costo sin cambiar producto

- Medir requests por flujo real.
- Centralizar polling.
- Eliminar requests duplicados.
- Confirmar cache versionada de marketplace.
- Mantener storage lazy.
- Medir costo por orden, chat, ticket y dashboard abierto.

### Fase C - Organizar frontend

- Dividir CSS por superficie.
- Aislar chat composer.
- Aislar action chips financieros.
- Dejar hooks por dominio, no por parche.
- Mantener frontend como experiencia, no autoridad.

### Fase D - Endurecer backend donde manda

- Verificar cada accion critica con backend-only authority.
- Revalidar idempotencia, locks y constraints.
- Asegurar audit y observability por flujo.
- Ejecutar PostgreSQL real para carreras criticas.

### Fase E - Production gate barato y seguro

- 47G: secretos, Telegram Web, RLS, storage, IDOR, headers.
- 47H: arquitectura, costo, modulos, pruebas, recuperacion.
- Smoke autenticado Cliente/Negocio/Admin.
- No `READY_FOR_REAL_USE` sin evidencia real.

## Decisiones Pendientes

- `UNKNOWN_INPUT`: presupuesto mensual objetivo por etapa.
- `UNKNOWN_INPUT`: numero esperado de negocios activos al lanzamiento.
- `UNKNOWN_INPUT`: ordenes por dia esperadas en S1/S2/S3.
- `UNKNOWN_INPUT`: tamano promedio permitido/real de imagenes de chat y soporte.
- `UNKNOWN_INPUT`: retencion final de chats, adjuntos, tickets y audit logs.
- `DECISION_REQUIRED`: cuanto polling maximo aceptamos por chat activo antes de
  evaluar SSE/WebSocket.
- `DECISION_REQUIRED`: si se separaran builds fisicos por superficie o se
  mantendran shells dentro de `apps/web` hasta medir escala.
- `DECISION_REQUIRED`: presupuesto de observabilidad externa vs logs propios.

## No Tocar Por Este Mapa

- No runtime.
- No migraciones.
- No deploy.
- No produccion.
- No reglas financieras.
- No estados de orden.
- No creditos.
- No Zelle/USDT/Pago Movil.
- No reputacion.
- No soporte.
- No datos reales.

Este mapa solo organiza el terreno para decidir con menos ruido.
