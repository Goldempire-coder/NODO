# Slice 47P1 - Carga, Concurrencia E Integridad Local

Estado: `READY_FOR_VALIDATOR_REVIEW`

Fecha de evidencia: 2026-08-05

47P1 agrega un harness parametrizado para medir carreras reales contra
PostgreSQL local desechable. No cambia producto, runtime, cache, indices ni
flujo chat-first. Esta evidencia local no declara readiness de produccion.

## 1. Entorno Y Limites

| Campo | Resultado |
| --- | --- |
| Repo | `C:\Users\carlo\Documents\Playground\NODO` |
| Rama | `codex/intake-admin-review-v2` |
| HEAD inspeccionado | `1828a5cf0882f5617df895ecb3bbfbdf3e06ba64` |
| Worktree | Sucio por trabajo previo; 47P1 no limpio ni revirtio cambios ajenos |
| API | FastAPI in-process mediante `httpx.ASGITransport` |
| Base | PostgreSQL 16 local desechable, puerto 55432 |
| Coordinacion | Redis 7 local desechable, puerto 56379 |
| Migraciones | `0001` a `0048` aplicadas desde cero sin fallos |
| Maquina | 12 CPU logicos; 8.378 GiB disponibles al inicio del gate |
| Proveedores externos | Desactivados |
| Costo | Local/gratis, salvo uso normal de CPU, RAM y disco |

La concurrencia efectiva reportada es el pico de requests simultaneos en el
cliente ASGI local. No mide concurrencia de red externa ni workers de una
plataforma de hosting. CPU corresponde al proceso Python; memoria disponible
corresponde a la maquina. CPU de contenedores no se midio por separado.

Skills aplicados:

- `performance-optimization`: baseline antes de cualquier optimizacion.
- `test-driven-development` y `pytest-skill`: contrato rojo antes del harness.
- `supabase-postgres-best-practices`: pruebas sobre locks, transacciones y
  constraints reales; no se agregaron indices sin `EXPLAIN`.
- `observability-and-instrumentation`: percentiles, status, conteos finales y
  recursos por escenario.
- `security-and-hardening`: guard local, redaccion por patron y evidencia sin
  payloads privados.
- `incremental-implementation`: prueba roja, corrida diagnostica y gate limpio.
- `planning-and-task-breakdown`: separacion de product gates e infra probes.

## 2. Harness Y Comandos

Harness: `scripts/p2p_load_concurrency_47p1.py`

Prueba de contrato:

```powershell
python -m pytest apps/api/tests/test_performance_concurrency_47p1.py -q --tb=short
```

Smoke funcional opt-in contra servicios locales:

```powershell
$env:NODO_RUN_47P1_LOCAL_INTEGRATION='1'
python -m pytest apps/api/tests/test_performance_concurrency_47p1.py::test_47p1_local_smoke_executes_product_gates_and_writes_safe_evidence -q --tb=short
```

Sin PostgreSQL/Redis locales o sin la variable opt-in, esta prueba se marca
`SKIPPED`; no reporta un PASS ficticio. El modo CLI equivalente ejecuta los
product gates reales, no una simulacion reducida:

```powershell
python scripts/p2p_load_concurrency_47p1.py --smoke --env-file .env.local.example --levels 50,100 --run-id 47p1-validator-fix-20260805 --output .local/47p1/validator_fix_smoke.json
```

Preparacion local:

```powershell
docker compose -f docker-compose.local.yml up -d postgres redis
python scripts/local_infra_check.py --env-file .env.local.example --require-services --output .local/47p1/infra_check.json
python scripts/apply_local_migrations.py --env-file .env.local.example --reset --output .local/47p1/migrations_gate.json
```

Gate ejecutado:

```powershell
python scripts/p2p_load_concurrency_47p1.py --env-file .env.local.example --levels 50,100,250 --chat-orders 10 --messages-per-order 5 --run-id 47p1-gate-final-20260805 --output .local/47p1/concurrency_47p1_20260805.json
```

Evidencia agregada:

- `.local/47p1/concurrency_47p1_20260805.json`
- `.local/47p1/concurrency_47p1_20260805.ndjson`
- `.local/47p1/infra_check.json`
- `.local/47p1/migrations_gate.json`
- `.local/47p1/validator_fix_smoke.json`
- `.local/47p1/validator_fix_smoke.ndjson`
- `.local/47p1/validator_fix_full.json`
- `.local/47p1/validator_fix_full.ndjson`

El JSON/NDJSON no conserva IDs de usuarios, negocios, anuncios u ordenes;
tampoco cuerpos de chat, Pago Movil, wallets, tokens, URLs o paths privados.
`local_hardening_common.redacted()` clasifica nombres de variables de forma
case-insensitive por patrones sensibles (`TOKEN`, `SECRET`, `KEY`, `PASSWORD`,
URLs de base/Redis, webhooks, privados y credenciales). El `infra_check.json`
fue regenerado: 13 claves sensibles quedaron redactadas, incluida
`BUSINESS_INTAKE_BOT_TOKEN`.

### Smoke Del Fix De Validator

| Verificacion | Resultado |
| --- | --- |
| Suite 47P1 sin opt-in | 6 PASS, 1 SKIPPED intencional |
| Smoke local opt-in | 1 PASS |
| c50 | PASS; 50 requests; 0 errores inesperados |
| c100 | PASS; 100 requests; 0 errores inesperados |
| Product gates | PASS |
| Violaciones de invariante | 0 |
| JSON/NDJSON | 2 escenarios consistentes y parseables |
| Gate completo actual c50/c100 | 14/14 PASS; 225 requests; 0 violaciones |
| c500/c1000 | `NOT_TESTED`; siguen siendo `INFRA_PROBE` opcional |

## 3. Resultado Ejecutivo

| Metrica | Resultado |
| --- | --- |
| Escenarios | 15/15 PASS |
| c50 PRODUCT_GATE | PASS |
| c100 PRODUCT_GATE | PASS |
| c250 INFRA_PROBE | PASS |
| Requests medidos | 475 |
| Errores esperados | 404 conflictos controlados |
| Errores inesperados | 0 |
| Violaciones de invariante | 0 |
| Duracion completa | 20.6352 s |
| CPU proceso Python | 9.5000 s; 3.836% de la capacidad total de la maquina |
| Memoria disponible final | 8.138 GiB |
| `LOCAL_RESOURCE_LIMIT` | 0 escenarios |

## 4. Contencion Del Mismo Anuncio

| Nivel | Gate | Status | Resultado HTTP | p50 | p95 | p99 | DB final |
| --- | --- | --- | --- | ---: | ---: | ---: | --- |
| c50 | PRODUCT_GATE | PASS | 1x201, 49x409 | 522.24 ms | 546.90 ms | 551.96 ms | 1 orden, 1 reserva, 1 evento, 1 audit, 1 job |
| c100 | PRODUCT_GATE | PASS | 1x201, 99x409 | 518.03 ms | 670.02 ms | 676.20 ms | 1 orden, 1 reserva, 1 evento, 1 audit, 1 job |
| c250 | INFRA_PROBE | PASS | 1x201, 249x409 | 1210.74 ms | 1537.16 ms | 1547.24 ms | 1 orden, 1 reserva, 1 evento, 1 audit, 1 job |

Todos los perdedores recibieron el conflicto esperado `AD_NOT_AVAILABLE`. La
reserva final fue exactamente 50.00 USD en cada nivel.

## 5. Invariantes De Negocio

| Escenario | Resultado | Evidencia final |
| --- | --- | --- |
| Dos anuncios con `active_order_limit=1` | PASS | 1x201, 1x409; una orden y una reserva |
| Zelle + USDT contra capacidad compartida | PASS | 2 ordenes; 2 reservas por 100.00 USD total |
| Dos publicaciones Zelle | PASS | un anuncio activo y un conflicto controlado |
| Dos publicaciones USDT | PASS | un anuncio activo y un conflicto controlado |
| Zelle + USDT de 60 contra disponibilidad 100 | PASS | solo un anuncio activo; maximo comprometido 60 |
| Confirmar pago recibido dos veces | PASS | un evento de confirmacion y un consumo de credito |
| Marcar entregado dos veces | PASS | un evento, un audit y un job; reserva aun `reserved` |
| Completion doble | PASS | un evento completed; reserva `consumed` una vez |
| Pago vs cancelacion | PASS | un ganador; orden cancelada sin reporte y reserva released en esta corrida |
| Pago vs expiracion | PASS | un ganador; orden payment_reported y reserva retained en esta corrida |

La carrera pago/expiracion puede terminar validamente del otro lado en otra
corrida. El gate valida consistencia entre estado, reporte y reserva, no fuerza
un ganador especifico.

## 6. Chat Y Pago Movil

### Burst De Chat

- 10 ordenes independientes.
- 5 mensajes concurrentes por orden; 50 requests totales.
- Resultado: 50x201, cero mezcla entre ordenes y cero violaciones de ownership.
- p50 537.21 ms, p95 607.32 ms, p99 623.74 ms.
- Las respuestas no incluyeron campos privados de storage, reveal o Pago Movil.

### Receiver Details

- Entrega sin datos estructurados: 409
  `ORDER_RECEIVER_DETAILS_REQUIRED`.
- Telefono extranjero: 400 `ORDER_RECEIVER_DETAILS_INVALID`.
- `0414 1234567`: aceptado por runtime y PostgreSQL con migracion 0048.
- Update invalido directo en PostgreSQL: rechazado por constraint.
- Reveal participante: 200 y `Cache-Control: private, no-store`.
- Pago Movil no aparecio en `messages.body`.
- Un audit de share, un audit de reveal y un evento de entrega.

## 7. Clasificacion De Fallos

- c50 y c100 son `PRODUCT_GATE`: cualquier error inesperado, cero ganador o
  violacion de integridad falla el slice.
- c250, c500 y c1000 son `INFRA_PROBE`: agotamiento local sin corrupcion se
  clasifica `LOCAL_RESOURCE_LIMIT`.
- Mas de una orden/reserva, capacidad excedida, ownership cruzado o efectos
  duplicados siempre es `INTEGRITY_VIOLATION`, incluso en un infra probe.

## 8. NOT_TESTED Y Riesgos Pendientes

- c500: `NOT_TESTED`; opcional y no necesario para el product gate 47P1.
- c1000: `NOT_TESTED`; opcional y no necesario para el product gate 47P1.
- Browser movil/teclado: `NOT_TESTED`; no se toco frontend.
- Transporte HTTP real, balanceador y latencia de hosting: `NOT_TESTED`.
- CPU/RAM por contenedor PostgreSQL/Redis: `NOT_TESTED`.
- Staging autenticado: `NOT_TESTED`; no se envio carga a staging.
- La latencia ASGI local no es un SLO de produccion.
- Las familias de create-order locks, chat latest-window y receiver-details
  quedan candidatas para `EXPLAIN` medido en 47P3; 47P1 no agrega indices.

## 9. Confirmaciones

- No deploy.
- No produccion.
- No staging.
- No migraciones fuera de PostgreSQL local desechable.
- No cache.
- No indices.
- No cambios financieros ni de producto.
- No secretos en evidencia.
- No `READY_FOR_REAL_USE`.
