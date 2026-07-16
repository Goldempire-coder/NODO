# Business Mini App AFOS Audit - 2026-07-16

Estado: `READY_FOR_HARDENING_SLICE`

Auditor: Codex
Alcance: Mini App Negocio NODO, API backend asociada, pruebas existentes, telemetria frontend/backend y slices 34T-34Z.
No alcance: app cliente, admin completo, produccion, deploy, proveedor Railway/Cloudflare, llaves privadas, cambio de infraestructura.

## 1. Veredicto

La Mini App Negocio ya no se ve como un modulo improvisado. Hay separacion real de responsabilidades y varias reglas sensibles viven en backend. Aun no esta lista para declararse production-ready porque falta cerrar evidencia AFOS formal, separar algunos hooks grandes, medir transiciones de pantalla con evidencia automatizada y completar logs accionables para errores de negocio antes de que los reporte el usuario.

Decision:

`BUSINESS_MINI_APP_READY_FOR_AFOS_HARDENING_SLICE`

No declarar:

- `READY_FOR_REAL_USE`
- `APPROVED_FOR_PRODUCTION`
- `AUTH/SECURITY COMPLETE`

## 2. Perfil De Riesgo

Clasificacion AFOS propuesta: `C`

Motivo:

- Marketplace con multiples partes.
- Maneja creditos con valor economico.
- Tiene flujo Base USDC.
- Tiene Zelle del negocio.
- Tiene ordenes, disputas, evidencia y soporte.
- Un fallo puede crear perdida financiera, fraude, reclamos o exposicion de datos.

Nota: los subcontroles de creditos, ledger, ordenes, pagos y wallet deben tratarse con severidad tipo `D` aunque el producto completo se clasifique como `C`.

## 3. Evidencia Revisada

Frontend Mini App Negocio:

- `apps/web/src/hooks/useBusinessMiniAppModel.ts`
- `apps/web/src/hooks/business-mini-app/useBusinessAccessModel.ts`
- `apps/web/src/hooks/business-mini-app/useBusinessAdsModel.ts`
- `apps/web/src/hooks/business-mini-app/useBusinessCreditsModel.ts`
- `apps/web/src/hooks/business-mini-app/useBusinessHomeSummaryModel.ts`
- `apps/web/src/hooks/business-mini-app/businessPinGuards.ts`
- `apps/web/src/screens/business-app/BusinessMiniAppShell.tsx`
- `apps/web/src/screens/business-app/BusinessDashboardScreen.tsx`
- `apps/web/src/screens/business-app/BusinessAdsScreens.tsx`
- `apps/web/src/screens/business-app/BusinessCreditsScreens.tsx`
- `apps/web/src/screens/business-app/BusinessOrdersScreens.tsx`
- `apps/web/src/screens/business-app/ads/BusinessAdCard.tsx`
- `apps/web/src/screens/business-app/ads/BusinessAdDetailPanel.tsx`
- `apps/web/src/observability/clientTelemetry.ts`

Backend:

- `apps/api/app/modules/businesses/service.py`
- `apps/api/app/modules/ads/service.py`
- `apps/api/app/modules/ads/management.py`
- `apps/api/app/modules/credits/business_purchases.py`
- `apps/api/app/modules/observability/service.py`
- `apps/api/app/modules/orders/business_ops.py`
- `apps/api/app/modules/orders/create_order_flow.py`

Pruebas:

- `apps/api/tests/test_auth_lifecycle_static.py`
- `apps/api/tests/test_ads_marketplace.py`
- `apps/api/tests/test_business_access_control.py`
- `apps/api/tests/test_business_order_ops.py`
- `apps/api/tests/test_credits_referrals.py`

Slicing previo:

- `governance/builder_reports/slice_34T_business_mini_app_security_observability_architecture_BUILDER_REPORT.md`
- `governance/builder_reports/slice_34U_business_mini_app_architecture_reliability_hardening_BUILDER_REPORT.md`
- `governance/builder_reports/slice_34V_business_mini_app_clean_architecture_BUILDER_REPORT.md`
- `governance/builder_reports/slice_34W_business_ads_screen_component_split_BUILDER_REPORT.md`
- `governance/builder_reports/slice_34X_business_credit_movements_ui_removal_BUILDER_REPORT.md`
- `governance/builder_reports/slice_34Y_business_credits_purchase_ux_cleanup_BUILDER_REPORT.md`
- `governance/builder_reports/slice_34Z_business_zelle_reliability_cleanup_BUILDER_REPORT.md`

## 4. Mapa Actual De Responsabilidades

### Frontend

`useBusinessMiniAppModel.ts`

- Ensambla submodelos.
- Agrega `X-NODO-Surface=business_mini_app`.
- Maneja navegacion, historial, notice y busy global.
- No debe volver a contener logica de dominio.

`useBusinessAccessModel.ts`

- Perfil de negocio.
- Estado de acceso.
- Zelle.
- PIN de negocio.
- Online/offline.

`useBusinessAdsModel.ts`

- Crear, listar, editar, pausar, reactivar, borrar y republicar anuncios.
- Coordina refresco de wallet despues de mutaciones que afectan creditos.
- Registra breadcrumbs de accion.

`useBusinessCreditsModel.ts`

- Balance de creditos.
- Compra Base USDC.
- Compra pendiente y tx hash.
- Recuperacion de compra pendiente por `purchase_id`.

`useBusinessOrdersModel.ts`

- Lista de ordenes abiertas, por verificar e historial.
- Detalle por `public_order_code`.
- Confirmar pago, rechazar reporte y marcar enviado.

`clientTelemetry.ts`

- Request/correlation/operation IDs.
- Breadcrumbs de pantalla y accion.
- Ingesta opcional desactivada por flag.
- Redaccion de campos sensibles.

### Backend

`BusinessService`

- Autoridad de acceso de negocio.
- PIN de negocio.
- Zelle aprobado/activo.
- Online/offline.
- Auditoria de cambios sensibles.

`AdService`

- Autoridad de publicar, editar, pausar, reactivar, archivar y republicar anuncios.
- Valida rango autorizado.
- Valida metodo de pago aprobado y activo.
- Bloquea o consume creditos segun regla.
- Limpia cache marketplace tras cambios.

`CreditService / BusinessPurchases`

- Crea compras Base USDC.
- No acredita por pegar tx hash.
- Valida wallet configurada y tx hash.
- Acredita solo con verificacion on-chain/backend.

`OrderService`

- Crea ordenes solo si anuncio y negocio estan disponibles.
- Usa `public_order_code`.
- Protege ownership de detalle de orden.
- Maneja confirmacion, entrega y estados de historial.

## 5. Controles AFOS Relevantes

| Control | Estado | Evidencia | Riesgo residual |
| --- | --- | --- | --- |
| Backend autoriza acciones sensibles | `PARTIAL_PASS` | PIN, Zelle, anuncios, creditos y ordenes tienen backend checks | Falta matriz unica accion -> endpoint -> test |
| Cliente no decide reglas financieras | `PASS` | `AdService`, `BusinessPurchases`, credit holds y order actions validan servidor | Mantener tests de manipulacion directa |
| Ownership por recurso | `PASS` | Tests de Zelle ajeno, orden ajena, negocio propio | Extender a soporte/chat con imagenes en slice posterior |
| PIN para acciones sensibles | `PARTIAL_PASS` | `businessPinGuards.ts`, `BusinessService.require_unlocked_business_pin` | Falta matriz de acciones sensibles aprobada |
| Zelle multiple editable/borrable | `PARTIAL_PASS` | Slice 34Z + tests backend | Falta walkthrough Telegram final y medicion de fallo real |
| Anuncio con Zelle borrado no vende | `PASS` | `test_deleted_zelle_hides_active_ad_from_marketplace_and_blocks_order` | Mantener en regression |
| Online/offline oculta anuncios | `PASS` | `test_business_offline_hides_marketplace_ad_and_blocks_direct_order_creation` | UI necesita evidencia manual final |
| Ordenes con numero reclamable | `PASS` | `BusinessOrdersScreens.tsx`, `test_business_orders_history_filter_and_public_order_code_for_claims` | Falta validacion cliente vs negocio end-to-end |
| Credit purchase Base USDC sin private key | `PASS` | Public wallet + tx hash + verifier backend | Falta staging provider validation completa |
| No secretos en logs frontend | `PARTIAL_PASS` | Redaccion en `clientTelemetry.ts` y `ObservabilityIngestService` | Ingesta apagada; falta tablero/retencion |
| Transiciones de pantalla fluidas | `PARTIAL_PASS` | Refactor mejoro UX manualmente | Falta benchmark automatico por pantalla |
| Hooks pequenos y cohesivos | `PARTIAL_FAIL` | Hook principal es ensamblador | `useBusinessAccessModel` 387 lineas, `useBusinessAdsModel` 372, `useBusinessCreditsModel` 257 |
| Slice oficial del endurecimiento actual | `FAIL` | Hay builder reports 34T-34Z | No hay paquete contractual oficial en `control_plane/09_SLICES` para el hardening final |

## 6. Hallazgos

### HIGH - Falta paquete AFOS oficial para la Mini App Negocio

Los slices 34T-34Z existen como builder reports, pero el estado final de la Mini App Negocio no tiene un paquete contractual unico en `control_plane/09_SLICES` que defina controles, alcance, no alcance, pruebas y salida. Esto vuelve dificil auditar el proximo cambio sin depender del chat o de reportes sueltos.

Accion: crear `slice_35_business_mini_app_afos_hardening`.

### HIGH - Hooks de dominio frontend aun grandes

Lineas actuales:

- `useBusinessAccessModel.ts`: 387
- `useBusinessAdsModel.ts`: 372
- `useBusinessCreditsModel.ts`: 257

No son necesariamente incorrectos, pero concentran formularios, mutaciones, errores, telemetria y navegacion. Eso aumenta riesgo de regresion cuando se arregla un boton o una pantalla.

Accion: separar en unidades de responsabilidad: estado/formularios, acciones API, PIN flow y refresh coordination.

### HIGH - Falta evidencia automatizada de fluidez de pantallas

El usuario observo que la app quedo mucho mas rapida despues de limpieza, pero no hay prueba automatizada que mida el tiempo de transicion entre pantallas ni detecte pantallas que muestran "cargando" innecesariamente.

Accion: agregar instrumentation/test de transicion local para pantallas principales y breadcrumbs de duracion sin datos sensibles.

### MEDIUM - Observabilidad existe pero no cierra el ciclo operativo

Hay breadcrumbs frontend e ingesta backend opcional. La ingesta esta apagada por diseno y no persiste. Esto es correcto para privacidad, pero todavia no permite alertar proactivamente cuando el boton "Borrar Zelle", "Reactivar anuncio" o "Generar pago" falla en staging.

Accion: definir eventos operativos minimos y criterios de activacion segura en staging.

### MEDIUM - Matriz de acciones sensibles no esta consolidada

Hay PIN y backend checks, pero falta una tabla oficial:

- accion
- requiere PIN si/no
- endpoint
- idempotency key
- audit event
- test
- razon de negocio

Accion: incluir en slice 35.

### MEDIUM - Flujo cliente vs negocio no validado aun end-to-end

La Mini App Negocio ya tiene ordenes, historial y `public_order_code`, pero falta caminar la app cliente contra negocio real/staging para confirmar notificaciones, chat, imagenes, reclamos y cierre.

Accion: no mezclar en slice 35. Crear slice posterior cliente-negocio end-to-end.

### LOW - Repo con muchos cambios sin consolidar

El worktree tiene muchas modificaciones y artefactos nuevos. No es un bug de producto, pero antes de deploy conviene generar manifiesto de cambios por slice y confirmar que no hay archivos temporales o reportes fuera de lugar.

Accion: slice 35 debe producir manifest final de archivos tocados y no tocar cambios ajenos.

## 7. Lo Que Ya Esta Bien

- El hook principal de la Mini App ya funciona como ensamblador.
- Home summary esta separado.
- PIN guards estan centralizados.
- Zelle tiene add/edit/delete con backend ownership, PIN e idempotencia.
- Anuncios tienen tarjeta y detalle separados.
- Ordenes muestran `public_order_code`.
- Online/offline existe y tiene test backend.
- La compra Base USDC no usa private key en frontend.
- La wallet destino es publica.
- Tx hash no acredita por si solo.
- Hay redaccion de telemetria en frontend y backend.
- Hay tests backend de creditos, ordenes, Zelle, anuncios y offline.

## 8. Slice Recomendado

Abrir:

`slice_35_business_mini_app_afos_hardening`

Objetivo:

Cerrar los riesgos pendientes de arquitectura limpia, evidencia AFOS, logs accionables, transiciones de pantalla y matriz de acciones sensibles sin construir cliente app ni tocar produccion.

Resultado esperado:

`READY_FOR_OWNER_REVIEW`

No resultado permitido:

`READY_FOR_REAL_USE`

## 9. Bloqueadores Antes De Produccion

- No hay walkthrough final Telegram Mini App real post-slice.
- No hay validacion end-to-end cliente contra negocio.
- No hay prueba de compra Base USDC completa en staging con RPC/provider y wallet configurada.
- No hay restore/DR real probado para datos Tier 0/Tier 1.
- No hay Production Gate AFOS completo para release exacto.

## 10. Confirmaciones

- No se modifico producto durante esta auditoria.
- No se hizo deploy.
- No se tocaron secretos.
- No se tocaron llaves privadas.
- No se accedio a proveedor.
- No se declaro readiness real.
