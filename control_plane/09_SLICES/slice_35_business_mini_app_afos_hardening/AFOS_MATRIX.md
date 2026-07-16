# AFOS_MATRIX.md

## Estado

Slice 35 hardening matrix: APPROVED_FOR_BUILD_SCOPE.

## Componentes

| Area | Frontend owner | Backend authority | Estado actual | Hardening requerido |
| --- | --- | --- | --- | --- |
| Surface access | `useBusinessAccessModel` | `/api/v1/surface/session` y business access policies | Backend decide acceso, status y link activo. | Mantener frontend como presentacion y no usar `businesses/me` como gate. |
| PIN operativo | `businessPinGuards`, `BusinessPinScreen` | `BusinessService.require_unlocked_business_pin` | PIN protege metodos de cobro, ads, creditos y ordenes sensibles. | Incluir online/offline en la matriz sensible. |
| Metodos de cobro | `useBusinessAccessModel`, `PaymentMethodsScreen` | business payment methods service | Zelle y USDT TRC20 activo/propio se validan en backend; frontend muestra masked account. | Separar modelo de payment methods del hook de acceso. |
| Anuncios | `useBusinessAdsModel`, ads screens | ads service/state machine | Backend valida negocio, metodo de cobro, creditos, rangos y ownership. | Reducir hook de acciones y completar `ad_republish` breadcrumb. |
| Creditos Base USDC | `useBusinessCreditsModel`, credits screens | credit service/onchain verifier | Backend crea compra y acredita solo con verifier. | Separar tx hash action state y agregar `credit_tx_submit`. |
| Ordenes negocio | `useBusinessOrdersModel`, order screens | order business ops | Backend valida ownership, PIN, estado e idempotency. | Estados por accion y breadcrumbs de acciones. |
| Chat/soporte | chat/support hooks and screens | chat/support backend | Backend conserva ownership y adjuntos privados. | Estados por accion sin capturar mensajes completos. |
| Observability | `clientTelemetry.ts` | observability ingest service | Redaccion existe; ingest configurable. | Agregar duracion segura y slow sensitive breadcrumbs. |

## Reglas

- Frontend no decide dinero, creditos, ownership, estados finales ni autorizacion.
- Backend es autoridad para PIN, access link, negocio aprobado, metodo de cobro activo, creditos, ordenes y verifier on-chain.
- No persistir ni emitir wallet privada, PIN, Zelle completo, wallet USDT completa en breadcrumbs, tx hash completo, `storage_path`, `account_value`, tokens o signed URLs.
- No cambiar endpoints activos ni estados runtime en este slice.
