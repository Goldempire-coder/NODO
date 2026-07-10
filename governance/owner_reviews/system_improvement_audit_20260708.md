# NODO System Improvement Audit - 2026-07-08

## Estado

NOT_READY_FOR_REAL_USE

Este reporte no intenta vender un verde. El resultado real es:

- La integridad se mantuvo en los tramos ejecutados.
- Los errores HTTP fueron `0` en los runs recientes.
- Los invariantes criticos quedaron en `0`.
- Pero el sistema/pruebas todavia no demuestran capacidad real para `profile 25` completo, mucho menos 200-1000 clientes simultaneos.

## Evidencia base

Reportes usados:

- `governance/owner_reviews/real_services_internal_order_profile_20260708.md`
- `governance/owner_reviews/real_services_profile25_attempt_20260708.md`

Runs clave:

- `real_services_profile25_after_jobs_20260708_200000`
  - detenido por duracion excesiva;
  - llego a `50` negocios, `15` ads, `0` ordenes;
  - no escribio JSON final.
- `real_services_profile25_bounded_20260708_203500`
  - timeout controlado a `620.194s`;
  - `18/50` negocios;
  - `0` ads;
  - `0` ordenes;
  - `182` requests;
  - `0` errores;
  - invariantes `0`;
  - p95 `4803.595 ms`;
  - p99 `9634.5524 ms`.

Cleanup:

- Ambos runs quedaron con `0` entidades operativas vivas despues de cleanup.
- Usuarios y audit logs quedan retenidos por diseno append-only.

## Hallazgos

### P0 - El harness actual no prueba bien el flujo que queremos escalar

Archivo:

- `scripts/stress_local.py`

Evidencia:

- `PROFILE_TARGETS["25"]` define `50` negocios, `500` ordenes, `500` busquedas.
- `run_stress()` ejecuta fases secuenciales:
  - primero crea/verifica/aprueba/vincula todos los negocios;
  - luego crea anuncios;
  - luego busca marketplace;
  - luego crea ordenes;
  - luego completa workflows.
- En el bounded run, despues de `620s`, seguia en `seed_businesses`.

Impacto:

- No sabemos todavia como se comportan `500` ordenes reales bajo profile 25, porque nunca llegamos a esa fase.
- Tampoco estamos probando clientes simultaneos de verdad en este profile; estamos pagando un setup secuencial muy caro.

Arreglo requerido:

1. Separar perfiles:
   - `profile_business_onboarding_real`
   - `profile_marketplace_reads_real`
   - `profile_order_flow_real`
   - `profile_mixed_concurrent_real`
2. Crear dataset preparado reutilizable o snapshot controlado de negocios aprobados/anuncios activos.
3. Agregar stress concurrente real por escenarios, no solo secuencial.
4. Mantener tambien un e2e end-to-end, pero no usarlo como unica prueba de capacidad.

### P0 - El flujo de seed usa self-onboarding legacy, no la arquitectura nueva de negocio

Archivos:

- `scripts/local_smoke.py`
- `scripts/stress_local.py`
- `apps/api/app/modules/businesses/service.py`

Evidencia:

- `create_approved_business()` llama:
  - `POST /api/v1/businesses`
  - 4 veces `POST /api/v1/businesses/{id}/verification-documents`
  - `POST /api/v1/businesses/{id}/submit-verification`
  - `POST /api/v1/admin/businesses/{id}/approve`
  - `POST /api/v1/admin/businesses/{id}/access-links`
  - activacion directa de payment method por fixture.
- Pero la arquitectura nueva decidida por owner es:
  - Bot Registro Negocios capta;
  - Admin revisa/crea/aprueba;
  - backend vincula acceso con `business_access_links`;
  - Mini App Negocio entra por `surface/session`.

Impacto:

- Las pruebas de stress estan midiendo fuerte un camino que ya no representa la operacion normal del negocio.
- Aun asi, ese camino existe en backend y puede ser deuda/security-surface si queda disponible sin una razon clara.

Arreglo requerido:

1. Definir si `POST /api/v1/businesses` queda solo internal/test/admin o si se elimina de superficies reales.
2. Crear ruta/admin tooling de seed/aprobacion compatible con el modelo nuevo, sin usar self-onboarding viejo como centro del stress.
3. Agregar test negativo: Mini App Negocio no puede crear/verificar negocio por self-onboarding.
4. Ajustar harness para usar el flujo oficial nuevo o un fixture interno claramente marcado.

### P0 - No hay prueba real suficiente de concurrencia de ordenes

Archivo:

- `scripts/stress_local.py`

Evidencia:

- El profile real no llego a ordenes.
- La fase `create_orders` es un loop secuencial.
- `complete_workflow_order()` tambien ejecuta evidencia, reporte, confirmacion y entrega secuencialmente por orden.

Impacto:

- No podemos afirmar que aguanta 200-1000 clientes simultaneos.
- No se ha probado suficientemente:
  - doble intento de crear orden contra el mismo anuncio;
  - confirmaciones simultaneas;
  - reportes de pago simultaneos;
  - race entre expiracion/job y acciones humanas;
  - locks de creditos bajo concurrencia.

Arreglo requerido:

1. Crear `scripts/concurrent_order_stress.py` o extender `concurrency_local.py`.
2. Escenarios minimos:
   - 50 usuarios buscando marketplace al mismo tiempo.
   - 25 usuarios creando ordenes contra distintos anuncios.
   - 10 usuarios intentando competir por el mismo anuncio.
   - 25 reportes de pago simultaneos.
   - 25 confirmaciones de negocio simultaneas.
   - job dry-run mientras hay ordenes en estados mixtos.
3. Medir:
   - errores;
   - p95/p99;
   - invariantes;
   - locks/idempotency conflicts;
   - duplicados de credit consumption;
   - anuncios vendidos dos veces.

### P1 - `submit-verification` es lento y tiene round trips/audits seriales

Archivo:

- `apps/api/app/modules/businesses/service.py`

Evidencia:

- Bounded run:
  - `POST /api/v1/businesses/{id}/submit-verification`
  - count `18`
  - avg `4490.6724 ms`
  - p95 `5136.8919 ms`
- En servicio:
  - lista archivos;
  - actualiza negocio;
  - agrega payment methods;
  - escribe audit `payment_method_added`;
  - crea submission;
  - escribe audit `business_submitted`.

Impacto:

- Onboarding/verificacion se vuelve cuello de botella.
- Si el bot/admin intake termina usando rutas parecidas, el problema reaparece.

Arreglo requerido:

1. Agregar profiling interno para `submit-verification`.
2. Crear metodo repository transaccional para:
   - validar archivos;
   - actualizar negocio;
   - crear payment methods;
   - crear submission;
   - devolver payload minimo.
3. Usar `audit.write_many` para `payment_method_added` + `business_submitted`.
4. Considerar mover validacion pesada/documentos a proceso admin/async si no debe bloquear al usuario.

### P1 - Upload de documentos de negocio depende de Supabase Storage en cada archivo

Archivos:

- `scripts/local_smoke.py`
- `apps/api/app/modules/businesses/service.py`
- `apps/api/app/shared/storage/private.py`

Evidencia:

- Cada negocio en el harness sube 4 documentos.
- Bounded run:
  - `POST /api/v1/businesses/{id}/verification-documents`
  - count `72`
  - avg `2764.0354 ms`
  - p95 `3048.7578 ms`
  - p99 `9678.8255 ms`
- `SupabasePrivateStorage._upload()` hace un POST HTTP por archivo.

Impacto:

- Storage real domina el tiempo de onboarding.
- Los spikes remotos ya se observaron tambien en `payment-evidence`.

Arreglo requerido:

1. Perfilar storage por bucket y tipo de archivo.
2. Reducir documentos obligatorios del stress cuando la prueba no sea de onboarding.
3. Para flujo real, evaluar:
   - direct upload con signed URLs desde cliente/bot controlado;
   - procesamiento asyncrono;
   - retry con backoff controlado;
   - size optimization antes de upload.
4. Mantener storage privado y no exponer `storage_path`.

### P1 - Admin approve/access-link/credits-adjust son lentos y se usan masivamente en seed

Archivos:

- `apps/api/app/modules/businesses/service.py`
- `apps/api/app/modules/credits/service.py`
- `apps/api/app/modules/credits/repository.py`

Evidencia bounded:

- `POST /api/v1/admin/businesses/{id}/access-links`
  - avg `3668.0184 ms`
  - p95 `4170.7138 ms`
- `POST /api/v1/admin/businesses/{id}/approve`
  - avg `3534.7116 ms`
  - p95 `3938.9028 ms`
- `POST /api/v1/admin/credits/adjust`
  - avg `3463.8561 ms`
  - p95 `3837.9482 ms`

Impacto:

- El seed de 50 negocios multiplica este costo.
- Si el admin real aprueba negocios manualmente, no es catastrófico por volumen humano, pero para pruebas y tooling es inviable.

Arreglo requerido:

1. Perfilar internamente cada endpoint admin.
2. Usar batch audit cuando haya varias escrituras.
3. Revisar idempotency/rate-limit Redis por endpoint.
4. Crear herramienta interna de seed aprobada por contrato para tests, sin saltarse invariantes productivas.

### P1 - Auth Telegram real esta alrededor de 2s por login

Evidencia bounded:

- `POST /api/v1/auth/telegram`
  - count `20`
  - avg `2236.1505 ms`
  - p95 `2539.421 ms`
  - p99 `2964.2538 ms`

Impacto:

- En entrada de Mini App, 2-3s se siente lento.
- Si se combina con llamadas iniciales de perfil/surface/session/marketplace, la app puede sentirse trabada.

Arreglo requerido:

1. Perfilar auth:
   - validacion initData;
   - user upsert;
   - session create;
   - audit;
   - Redis/rate limit.
2. Evitar llamadas redundantes al abrir Mini App.
3. Cachear/rehusar session donde sea seguro.
4. Medir tiempo de pantalla inicial hasta marketplace.

### P1 - Falta separar stress de lectura de marketplace del stress de mutaciones

Impacto:

- El usuario cliente principalmente abre, busca negocios, compara, crea orden y reporta pago.
- Las pruebas actuales se atascan antes de medir lecturas/search/list.

Arreglo requerido:

1. Dataset preparado de 20-100 anuncios activos.
2. Prueba solo lectura:
   - busquedas concurrentes;
   - filtros por monto/metodo;
   - detalle de negocio;
   - mis ordenes.
3. Medir p95/p99 y cacheabilidad.

### P2 - La instrumentacion existe, pero todavia no cubre todas las rutas lentas

Ya se agrego profiling interno para:

- orders create;
- confirm-payment;
- payment-evidence;
- business ads;
- jobs dry-run.

Falta profiling interno para:

- auth telegram;
- business create;
- verification document upload;
- submit-verification;
- admin approve;
- admin access-link;
- admin credits adjust.

Arreglo requerido:

1. Agregar profiling opt-in con `NODO_INTERNAL_PROFILING=1`.
2. No exponer perfiles en respuestas normales.
3. Mantenerlos solo en harness/test.

### P2 - Falta reporte de capacidad con limites honestos

El sistema necesita una tabla clara:

- Que soporta hoy probado.
- Que no soporta aun.
- Cual fue la carga.
- Cuales servicios reales estaban conectados.
- Cuales rutas quedaron lentas.
- Cuales invariantes pasaron.

Arreglo requerido:

Crear `REAL_SERVICES_CAPACITY_REPORT.md` con:

- baseline;
- profile initial;
- bounded profile 25;
- concurrent order stress;
- marketplace read stress;
- bot intake smoke;
- admin smoke.

## Plan recomendado de arreglo

### Paso 1 - Arreglar pruebas antes de seguir subiendo carga

Entregable:

- Nuevo harness o extension:
  - `real_seed_prepared_businesses`
  - `real_order_flow_stress`
  - `real_marketplace_read_stress`
  - `real_concurrent_order_race_stress`

Criterio:

- Poder medir ordenes sin pagar onboarding completo cada vez.
- Poder medir onboarding por separado.

### Paso 2 - Perfilar y optimizar onboarding/admin setup

Orden:

1. `submit-verification`
2. `verification-documents`
3. `admin approve`
4. `admin access-link`
5. `admin credits adjust`
6. `auth telegram`

Criterio:

- Reducir p95 de cada endpoint o documentar dependencia externa si no se puede.

### Paso 3 - Probar flujo cliente real con dataset preparado

Escenario:

- 25-50 negocios/anuncios activos preparados.
- 50-200 clientes simulados.
- Busqueda + detalle + crear orden.

Criterio:

- `0` double order.
- `0` negative balances.
- `0` invalid transitions.
- p95 aceptable para marketplace y crear orden.

### Paso 4 - Probar flujo pago/negocio concurrente

Escenario:

- payment evidence/report simultaneo;
- business confirm simultaneo;
- mark delivered simultaneo;
- job dry-run durante estados mixtos.

Criterio:

- `0` double credit consumption.
- `0` invalid transitions.
- `0` job lock failures.

### Paso 5 - Repetir profile 25 completo end-to-end

Solo despues de arreglar lo anterior.

## Decision de auditoria

No recomiendo decir que NODO esta listo para carga real alta.

Si seguimos correctamente, el proximo trabajo no debe ser "subir a profile 50". Debe ser:

1. construir pruebas separadas y concurrentes;
2. optimizar onboarding/admin setup;
3. medir flujo cliente/ordenes con dataset preparado;
4. repetir profile 25 end-to-end.

