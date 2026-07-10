# ARCHITECTURE_CLEANLINESS_AUDIT - 2026-07-09

## Estado

```txt
ARCHITECTURE_IMPROVED_BUT_NOT_CLEAN_ENOUGH_TO_SCALE
DO_NOT_ADVANCE_FEATURES_BEFORE_P0_P1_REPAIRS
```

## Resumen sin maquillaje

El sistema ya no es el monolito inicial. La separacion de superficies mejoro:

- Mini App Cliente existe separada.
- Mini App Negocio existe separada.
- Admin Web existe separado.
- Bot Registro Negocios existe separado.
- Backend esta organizado por dominios.
- SQL esta mayormente contenido en repositories, no mezclado dentro de services.

Pero todavia hay deuda que puede dañar escalabilidad si seguimos agregando features encima:

- Backend conserva endpoints legacy que contradicen la nueva arquitectura de negocio por bot/admin.
- Frontend conserva tipos globales y componentes viejos mixtos.
- Algunos services y repositories ya estan demasiado grandes.
- Admin Web y bot intake tienen modelos grandes que van a crecer mal si no se dividen ahora.

## P0 - Reparar antes de seguir producto

### P0.1 - Self-onboarding de negocio sigue activo en backend

Evidencia:

```txt
apps/api/app/modules/businesses/routes.py:60
POST /businesses

apps/api/app/modules/businesses/policy.py:10
OWNER_ELIGIBLE_ROLES = {"remitter", "business_owner"}

apps/api/app/modules/businesses/service.py:154
create_business(...)

apps/api/app/modules/businesses/service.py:167-169
si user.role != "business_owner", cambia el rol a business_owner
```

Problema:

La arquitectura nueva dice que el negocio entra por Bot Registro Negocios, luego admin revisa, luego admin vincula acceso. Pero este endpoint aun permite que un usuario elegible cree negocio directamente y cambie rol.

Riesgo:

- Se salta el flujo bot/admin.
- Abre la puerta a negocios creados por la via vieja.
- Hace dificil garantizar que todo negocio aprobado tenga origen/revision clara.

Reparacion quirurgica:

1. Marcar endpoints legacy como internal-only o bloquearlos para usuarios normales.
2. `POST /api/v1/businesses` no debe convertir `remitter -> business_owner`.
3. Crear/activar negocio debe pasar por admin/intake/access link.
4. Tests negativos: remitter no puede crear negocio por endpoint legacy.

## P1 - Arquitectura que debe limpiarse para escalar

### P1.1 - Tipo global `BusinessView` mezcla cliente, negocio y admin

Evidencia:

```txt
apps/web/src/types/domain.ts:2
export type BusinessView =

apps/web/src/constants/views.ts
lista vistas cliente + negocio + admin

apps/web/src/constants/navigation.ts:23
fallbackViewFor(view: BusinessView)
```

Problema:

Aunque las superficies ya estan separadas visualmente, el tipo principal todavia permite mezclar vistas de cliente, negocio y admin.

Riesgo:

- Un hook de cliente puede aceptar una vista de negocio.
- Un fallback puede mandar a una pantalla incorrecta.
- El proximo builder puede reintroducir mezcla sin que TypeScript lo bloquee.

Reparacion quirurgica:

1. Crear `ClientView`, `BusinessMiniAppView`, `AdminWebView`.
2. Eliminar o reducir `BusinessView` global.
3. Cada superficie debe aceptar solo su tipo.
4. `navigation.ts` global debe desaparecer o dividirse por superficie.

### P1.2 - Frontend viejo mixto sigue en el arbol

Evidencia:

```txt
apps/web/src/screens/business/BusinessWorkspace.tsx:7
apps/web/src/screens/business/WorkspaceShell.tsx:70
apps/web/src/screens/business/BusinessOperationsScreens.tsx:9
apps/web/src/screens/business/AdminConsoleScreens.tsx:9
apps/web/src/screens/business/VerificationScreens.tsx:7
apps/web/src/hooks/useBusinessWorkspaceModel.ts:18
```

Problema:

Estos archivos representan el workspace viejo donde se mezclaban cliente, negocio, verificacion y admin. Ya no aparecen importados desde `AuthEntryPage`, pero siguen en el repo.

Riesgo:

- Confusion para builders futuros.
- Duplicacion de logica.
- Reintroduccion accidental de pantallas negocio/admin en Mini App Cliente.

Reparacion quirurgica:

1. Confirmar que no se importan en ningun entrypoint activo.
2. Moverlos a archivo legacy claramente prohibido o eliminarlos si ya no tienen uso.
3. Quitar hooks viejos asociados.
4. Tests/scans: cliente no puede importar `screens/business/*` legacy.

### P1.3 - `OrderService` esta demasiado grande

Evidencia:

```txt
apps/api/app/modules/orders/service.py:106
class OrderService

apps/api/app/modules/orders/service.py:221
create_order(...)

apps/api/app/modules/orders/service.py:709
confirm_business_payment(...)
```

Tamano:

```txt
apps/api/app/modules/orders/service.py = 951 lineas
OrderService = 914 lineas
```

Problema:

El dominio de ordenes ya contiene demasiadas responsabilidades en una sola clase:

- crear orden
- revelar instrucciones
- evidencia
- reportar pago
- operaciones de negocio
- delivery
- expiracion materializada
- auditoria
- idempotencia
- cache invalidation

Riesgo:

- Cambiar una regla de pago puede romper confirmacion.
- Cambiar expiracion puede afectar crear orden.
- Los tests pasan, pero el mantenimiento se vuelve caro.

Reparacion quirurgica:

Dividir sin cambiar comportamiento:

- `OrderCreationService`
- `PaymentInstructionsService`
- `PaymentReportService`
- `BusinessOrderOpsService`
- `OrderExpirationService`
- helpers compartidos: payloads/masking/audit

### P1.4 - `BusinessIntakeService` concentra flujo bot, API y admin

Evidencia:

```txt
apps/api/app/modules/business_intake/service.py:166
class BusinessIntakeService

apps/api/app/modules/business_intake/service.py:219
process_telegram_update(...)

apps/api/app/modules/business_intake/service.py:347
_handle_text_step(...)

apps/api/app/modules/business_intake/service.py:450
_handle_telegram_document(...)
```

Tamano:

```txt
apps/api/app/modules/business_intake/service.py = 784 lineas
BusinessIntakeService = 689 lineas
process_telegram_update = 111 lineas
```

Problema:

El bot conversacional, documentos, API submit/contact, admin accept/reject/delete y auditoria viven en una sola clase.

Riesgo:

- Cada ajuste de copy o step del bot toca una clase critica.
- Facil duplicar mensajes o romper idempotencia.
- Dificil probar steps individuales sin cargar todo el service.

Reparacion quirurgica:

- `BusinessIntakeConversationService`
- `BusinessIntakeDocumentService`
- `BusinessIntakeAdminReviewService`
- `BusinessIntakeApplicationService`
- `BotStepStateMachine`

### P1.5 - Repositories Postgres son grandes pero aceptables por ahora

Evidencia:

```txt
apps/api/app/modules/orders/repository.py:335
PostgresOrderRepository

apps/api/app/modules/credits/repository.py:393
PostgresCreditRepository

apps/api/app/modules/ads/repository.py:348
PostgresAdRepository

apps/api/app/modules/businesses/repository.py:383
PostgresBusinessRepository

apps/api/app/modules/business_intake/repository.py:304
PostgresBusinessIntakeRepository
```

Problema:

No es malo que SQL viva en repositories. Lo malo es que algunas clases ya concentran muchas operaciones distintas.

Reparacion despues de services:

- Solo dividir repositories cuando el service ya este separado.
- No refactorizar SQL primero; eso seria mas riesgoso.

## P2 - Limpieza necesaria pero no bloqueante

### P2.1 - Admin Web model grande

Evidencia:

```txt
apps/web/src/hooks/useAdminWebModel.ts = 680 lineas
```

Problema:

Admin Web junta dashboard, negocios, ordenes, disputas, creditos, jobs e intake en un hook.

Reparacion:

- `useAdminDashboardModel`
- `useAdminBusinessesModel`
- `useAdminOrdersModel`
- `useAdminDisputesModel`
- `useAdminCreditsModel`
- `useAdminIntakeModel`

### P2.2 - Pantallas grandes

Evidencia:

```txt
apps/web/src/screens/admin-web/AdminWebScreens.tsx = 499 lineas
apps/web/src/screens/client/RemitterScreens.tsx = 494 lineas
apps/web/src/screens/business/BusinessOperationsScreens.tsx = 503 lineas
```

Reparacion:

- Una pantalla por archivo.
- Cards/list rows como componentes chicos.
- No tocar diseno ni copy durante el primer corte.

### P2.3 - `apiRequest` es correcto pero basico

Evidencia:

```txt
apps/web/src/api/client.ts
```

Estado:

Centraliza auth, request id y error handling. Bien.

Mejora futura:

- typed wrappers por dominio.
- retry controlado solo en lecturas seguras.
- timeout/cancelacion para pantallas lentas.

## Lo que esta bien

- SQL no esta metido en services.
- Routes son relativamente delgadas.
- Backend esta por modulos.
- Mini App Cliente, Mini App Negocio y Admin Web ya tienen entrypoints separados.
- Bot cliente y Bot Registro Negocios estan separados por token/webhook.
- `surface/session` existe como gate de Mini App Negocio.
- Storage privado esta centralizado.
- Los tests acumulados han cubierto muchas reglas importantes.

## Orden recomendado de reparacion

```txt
1. P0.1 bloquear self-onboarding legacy de negocio.
2. P1.1 separar tipos de vista por superficie.
3. P1.2 retirar frontend legacy mixto.
4. P1.4 partir BusinessIntakeService.
5. P1.3 partir OrderService.
6. P2.1 partir Admin Web model.
7. P2.2 partir pantallas grandes.
```

## Regla para los cortes

Cada corte debe cumplir:

```txt
1 archivo o grupo pequeno de archivos.
Sin cambio visual si es refactor.
Sin cambio de endpoints salvo P0.1.
Tests antes y despues.
Scans de superficie.
Reporte corto con riesgo residual.
```

## Conclusion

NODO no esta en estado Frankenstein global como al inicio. Pero tampoco esta limpio para escalar sin disciplina.

El mayor problema actual no es rendimiento. Es arquitectura preventiva:

```txt
quitar rutas legacy peligrosas,
cerrar tipos por superficie,
eliminar workspace mixto,
partir services grandes.
```

