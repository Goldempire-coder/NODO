# slice_34U_business_mini_app_architecture_reliability_hardening

Estado final: READY_FOR_OWNER_REVIEW

## Objetivo

Endurecer la Mini App Negocio en puntos observados durante prueba real: acciones que parecian congeladas, Zelle que no se borraba de forma confiable, anuncios retirados con flujo fragil de dos pasos, Home con creditos stale, y rutas legacy de compra de creditos que ya no deben ser el camino activo.

## Alcance ejecutado

- No deploy.
- No produccion.
- No migraciones.
- No private keys.
- No cambios de infraestructura.
- No cambios al verifier on-chain.

## Cambios principales

### Creditos legacy

- Se agrego `LEGACY_CREDIT_PAYMENT_METHODS_ENABLED`, apagado por defecto.
- Stripe/manual payments responden `410 CREDIT_PAYMENT_METHOD_DISABLED` cuando la bandera esta apagada.
- Base USDC sigue siendo el flujo activo de compra.

### Zelle

- PATCH/DELETE de Zelle aceptan `Idempotency-Key`.
- El frontend envia llaves idempotentes para editar y borrar Zelle.
- Borrar un Zelle ya inactivo devuelve exito idempotente si pertenece al negocio.
- El manejo de PIN pendiente ya distingue entre PIN validado y fallo real de borrado.

### Anuncios

- Archivar/borrar un anuncio activo ahora es una sola operacion backend.
- El frontend ya no hace pause + archive como dos llamadas separadas.
- El credito se consume en el backend durante archive, con auditoria existente.

### Home / transiciones

- Home ya no mantiene copia local propia de `creditWallet`.
- La pantalla principal lee directamente el wallet del modelo central.
- Tocar Inicio refresca aunque ya estes en Home.
- Mientras Home refresca, el contador principal muestra estado de carga en vez de mantener un numero viejo como valido.

## Validacion ejecutada

- `python -m pytest apps/api/tests/test_ads_marketplace.py apps/api/tests/test_credits_referrals.py apps/api/tests/test_auth_lifecycle_static.py -q --tb=short` -> `62 passed, 1 warning`
- `python -m pytest apps/api/tests -q` -> `352 passed, 1 warning`
- `python -m ruff check apps/api scripts` -> passed
- `python -m compileall apps/api apps/web/src scripts` -> passed
- `pnpm --filter @nodo/web build` con Node bundled -> passed
- `git diff --check` -> passed

## Riesgos pendientes

- No se ejecuto prueba manual final dentro de Telegram despues de estos cambios.
- No se hizo deploy staging.
- El texto pequeno de Home ahora se refresca, pero la experiencia final depende de la Mini App real y del deploy activo.
- Stripe/manual siguen existiendo en codigo historico para compatibilidad y tests, pero quedan bloqueados por bandera apagada por defecto.

## Veredicto

READY_FOR_OWNER_REVIEW
