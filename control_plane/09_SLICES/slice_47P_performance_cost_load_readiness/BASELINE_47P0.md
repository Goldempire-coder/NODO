# Slice 47P0 - Baseline Local Y Harness P2P

Estado: `READY_FOR_VALIDATOR_REVIEW`

Fecha: 2026-08-05

47P0 deja un harness local repetible y evidencia medible del flujo P2P actual.
No agrega cache, indices ni optimizaciones. 47P0.1 reconcilia la contradiccion
que PostgreSQL real revelo entre la validacion runtime de telefonos de Pago
Movil y el constraint vigente de la base.

## 1. Alcance Y Entorno

| Campo | Resultado |
| --- | --- |
| Repo | `C:\Users\carlo\Documents\Playground\NODO` |
| Rama | `codex/intake-admin-review-v2` |
| HEAD inspeccionado | `1828a5cf0882f5617df895ecb3bbfbdf3e06ba64` |
| Worktree antes de 47P0 | Sucio por trabajo previo: 68 tracked modificados y 11 entradas untracked |
| API | FastAPI in-process mediante ASGI TestClient |
| Base | PostgreSQL real local 16, desechable, puerto 55432 |
| Coordinacion | Redis real local 7, desechable, puerto 56379 |
| Migraciones | `0001` a `0047` aplicadas sin fallos en la base local |
| Storage | Archivo privado local con payload minimo sintetico |
| Proveedores externos | Desactivados; no Telegram real, banco, wallet, USDC ni pagos reales |
| Costo | Local/gratis, salvo uso normal de CPU, RAM y disco de la maquina |

Los IDs, actores, negocios, mensajes y archivos del harness son sinteticos. La
evidencia JSON completa se escribe bajo `.local/` y no imprime tokens, cuerpos
privados, wallets, datos bancarios ni URLs firmadas.

## 2. Harness Canonico

Archivo: `scripts/p2p_baseline_local.py`

El harness usa `order_id` y los endpoints vigentes. No usa `receiver_data`
legacy. Un `run_id` nuevo es obligatorio por corrida para conservar la semantica
real de idempotencia en Redis incluso si PostgreSQL fue reseteado.

Preparacion local:

```powershell
docker compose -f docker-compose.local.yml up -d postgres redis
python scripts/local_infra_check.py --env-file .env.local.example --require-services --output .local/47p0_infra_check.json
python scripts/apply_local_migrations.py --env-file .env.local.example --reset --output .local/47p0_migrations.json
```

Flujo funcional:

```powershell
python scripts/p2p_baseline_local.py --env-file .env.local.example --scenario functional --run-id 47p0-functional-<timestamp> --output .local/47p0_functional.json
```

Concurrencia PostgreSQL real local:

```powershell
python scripts/p2p_baseline_local.py --env-file .env.local.example --scenario concurrency --same-ad-requests 50 --run-id 47p0-concurrency-<timestamp> --output .local/47p0_concurrency.json
```

Todo en una base recien reseteada:

```powershell
python scripts/p2p_baseline_local.py --env-file .env.local.example --scenario all --same-ad-requests 50 --run-id 47p0-all-<timestamp> --output .local/47p0_all.json
```

El guard `assert_local_database_url` rechaza hosts no locales. Estos comandos no
se deben apuntar a staging o produccion.

## 3. Cobertura Funcional

### PostgreSQL Real Local

Los dos flujos ejecutados llegaron a `completed` y recibieron un rating:

1. Crear negocio aprobado con capacidad, creditos y metodos Zelle/USDT.
2. Publicar un anuncio Zelle y uno USDT dentro de disponibilidad declarada.
3. Crear orden.
4. Enviar mensajes Cliente y Negocio.
5. Negocio comparte Zelle o wallet USDT dentro del chat.
6. Cliente obtiene instrucciones privadas y marca pago enviado.
7. Zelle ejercita comprobante opcional y reveal explicito auditado.
8. Negocio confirma pago recibido.
9. Cliente comparte Pago Movil estructurado.
10. Negocio revela Pago Movil y marca entregado.
11. Cliente confirma recepcion y califica.
12. Dashboard/ordenes negocio y soporte Cliente se leen al final.

Resultado de `47p0-functional-20260805-1342`:

| Metrica | Resultado |
| --- | ---: |
| Requests medidas | 40 |
| Errores HTTP | 0 |
| p50 local | 37.3267 ms |
| p95 local | 60.0673 ms |
| p99 local | 66.7102 ms |
| Checks privados `no-store` | 14/14 |
| Zelle completed/rated | Si/Si |
| USDT completed/rated | Si/Si |

Estas latencias son backend in-process + PostgreSQL/Redis local. No incluyen DNS,
TLS, edge, Railway, Cloudflare, red movil ni render del navegador. No son un SLO
de produccion.

### In-memory

Las pruebas dirigidas existentes siguen siendo la capa rapida para contratos,
errores, ownership e idempotencia. 47P0 agrega regresiones in-memory para headers
privados y para que el harness/documento no vuelvan al flujo legacy. In-memory
no sustituye las carreras ni constraints de PostgreSQL real local.

## 4. Concurrencia PostgreSQL Real Local

Resultado de `47p0-concurrency-50-20260805-1342`:

| Escenario | Resultado |
| --- | --- |
| 50 clientes toman el mismo anuncio | 1 orden/reserva; 49 `AD_NOT_AVAILABLE` |
| Dos anuncios Zelle concurrentes | 1 activo; el otro `AD_LIMIT_NOT_ALLOWED` |
| Zelle 60 + USDT 60 con capacidad 100 | 1 activo por 60; el otro rechazado |
| Doble confirmacion de pago | 2 replays 200; 1 evento y 1 consumo de credito |
| Doble completion | 2 replays 200; 1 evento y reserva `consumed` |
| Pago vs cancelacion | Un ganador; DB termino cancelada, sin reporte, reserva liberada |
| Pago vs expiracion | Pago gano; reporte unico, estado `payment_reported`, reserva retenida |

Metricas agregadas de las requests concurrentes:

| Metrica | Resultado |
| --- | ---: |
| Requests medidas | 61 |
| Respuestas 4xx/5xx contadas como error por recorder | 52 |
| Respuestas 4xx esperadas por conflictos | 52 |
| Respuestas inesperadas | 0 |
| p50 local | 467.9846 ms |
| p95 local | 502.4812 ms |
| p99 local | 505.9034 ms |

El recorder cuenta todo 4xx como error; en esta corrida las 52 fueron los
conflictos esperados que prueban exclusividad. El resultado de cada escenario
contrasta status HTTP con filas finales de orden, reserva, ledger y eventos.

La corrida consolidada `47p0-all-20260805-1345` repitio ambos bloques con un
solo comando y termino con `exit_code=0`, cero violaciones, 40 requests
funcionales, 61 requests concurrentes y 14/14 headers privados correctos.

## 5. Hallazgo Cerrado Por 47P0.1

### Validacion De Telefono Con Paridad Runtime/PostgreSQL

- Causa raiz: `normalize_phone()` conservaba formatos locales mientras el
  constraint creado por 0040 exigia exclusivamente `+58` sin separadores.
- Runtime y PostgreSQL ahora aceptan la misma allowlist movil venezolana:
  `0412`, `0414`, `0416`, `0424`, `0426` o su equivalente `+58`, con siete
  digitos de suscriptor y separadores de presentacion seguros.
- El valor persiste en la presentacion normalizada del participante; el sistema
  no inventa ni obliga un prefijo `+58`.
- Numeros extranjeros, otros prefijos, longitudes incorrectas, letras, slash y
  caracteres SQL-like son rechazados por API y por la base.
- La migracion reversible
  `0048_receiver_details_phone_constraint_local_formats` hace preflight sin
  imprimir valores, no modifica filas y no borra historial.
- El rollback restaura el contrato de 0040 solo si todas las filas siguen siendo
  compatibles. Si ya hay telefonos locales, falla antes de quitar el constraint
  nuevo y conserva los datos.
- Evidencia PostgreSQL 16 local: migraciones 0001-0048, ciclo 0048 down/up,
  cuatro formatos validos, ocho invalidos, preflight historico y rollback
  fail-closed pasaron. El harness completo con `0414 1234567` termino sin
  violaciones.

## 6. Headers Privados

47P0 confirma `Cache-Control: private, no-store` en:

- GET de mensajes privados de orden;
- payment instructions;
- upload de evidencia de pago;
- reveal explicito de adjunto/evidencia;
- reveal de receiver-details;
- lista y detalle de soporte del participante;
- lista y detalle de soporte Admin;
- reveal Admin de adjunto de soporte.

Se agrego el header donde faltaba, sin cambiar payload, ownership, permisos ni
reglas de negocio.

## 7. Polling Y Request Budget

| Superficie | Endpoint | Intervalo | Visible-only | No overlap | Backoff | Riesgo |
| --- | --- | --- | --- | --- | --- | --- |
| Cliente chat | `GET /orders/{id}/messages` | 5 s | Si | Si | No | 12/min; hydration terminal puede agregar requests |
| Negocio chat | `GET /orders/{id}/messages` | 5 s | Si | Si | No | 12/min por chat visible |
| Cliente/Negocio attention | `GET /notifications/attention-summary` | 15 s | Si | Si | Si, 15-120 s + jitter | 4/min; consulta compuesta |
| Cliente soporte | list + detail | 8 s | Solo vista montada | No | No | Hasta 15/min con detalle |
| Negocio soporte | list + detail | 5 s | Solo vista montada | No | No | Hasta 24/min con detalle |
| Admin global | dashboard + notifications | 15 s | No | No | No | 8/min por operador |
| Admin soporte | list + detail | 5 s | Solo vista montada | No | No | Hasta 24/min adicionales |

47P0 solo mapea. No modifica polling ni agrega cache.

## 8. Queries Para 47P3

Estas familias requieren dataset representativo y `EXPLAIN (ANALYZE, BUFFERS)`
antes de proponer indices:

1. Marketplace con agregado lateral de capacidad.
2. Attention ordenado por `updated_at`.
3. Ventana de mensajes por orden y ultimo mensaje multiorden.
4. Listado/detalle de soporte con filtros y cursor.
5. Agregados del dashboard negocio.

No indices fueron agregados en 47P0.

## 9. Lo No Probado

- `NOT_TESTED`: navegador real, teclado movil y conteo de requests desde UI.
- `NOT_TESTED`: 10/50/100 usuarios recorriendo el flujo completo durante varios
  minutos; esta corrida valida carreras puntuales, no carga sostenida.
- `NOT_TESTED`: degradacion o reinicio de Redis durante mutaciones.
- `NOT_TESTED`: archivos grandes y concurrencia de uploads.
- `NOT_TESTED`: USDC/Base credit purchase; se excluyo para no tocar pagos o RPC.
- `NOT_TESTED`: scheduler externo real de expiracion.
- `NOT_TESTED`: staging autenticado y transporte externo.
- `NOT_TESTED`: CPU, memoria, conexiones y locks del proveedor.

## 10. Harness Legacy

- `scripts/local_smoke.py`: reutilizable para helpers, auth y guard local, pero
  su secuencia P2P directa representa flujo anterior.
- `scripts/local_surface_cross_smoke.py`: cobertura parcial, no flujo completo
  vigente.
- `scripts/concurrency_local.py`: no es autoridad para anuncios actuales porque
  sus fixtures permiten varios anuncios del mismo metodo.
- `scripts/capacity_real.py`: util para capacidad PostgreSQL, pero usa setup
  directo y no reemplaza el flujo HTTP canonico.

El nuevo entrypoint 47P0 es `scripts/p2p_baseline_local.py`.

## 11. Proximos Mini-Slices

1. 47P0.1: paridad de telefono runtime/PostgreSQL completada localmente.
2. 47P1: ampliar carreras y degradacion Redis con PostgreSQL real.
3. 47P2: medir y reducir polling solo con presupuesto aprobado.
4. 47P3: EXPLAIN con cardinalidad antes de cualquier indice.
5. 47P4: pool, queue lag, scheduler y metricas de baja cardinalidad.
6. 47P5: smoke staging pequeno y autenticado, solo con aprobacion.

## 12. Validacion Ejecutada

| Validacion | Resultado |
| --- | --- |
| Regresiones 47P0 | 4 passed |
| Receiver/chat/pagos/ordenes 47P0.1 | 96 passed |
| Chat/pagos/receiver/rating/support/capacidad/marketplace/ordenes | 193 passed |
| Regresion final de routers privados | 71 passed |
| Suite API completa final | 729 passed, 1 warning deprecado de TestClient/httpx |
| Migraciones PostgreSQL local | 0001-0048 aplicadas; 0048 down/up paso |
| Constraint 0048 PostgreSQL local | 4 validos y 8 invalidos; preflight y rollback fail-closed pasaron |
| Harness `47p01-final-20260805` PostgreSQL/Redis | Exit 0, 0 violaciones; 40 requests funcionales y 61 concurrentes |
| Ruff `apps/api scripts` | Pass |
| `compileall apps/api scripts` | Pass |
| `git diff --check` | Exit 0; warnings CRLF solo en archivos preexistentes |
| Secret Guard archivos 47P0 | Sin hallazgos |
| Next build | No aplica: 47P0 no modifico frontend |

## 13. Limites Y Confirmaciones

- No cache agregada.
- No indices agregados.
- No cambios financieros.
- No cambios de UX o flujo.
- No deploy ni trafico de staging.
- No migraciones en staging/produccion.
- No secretos ni datos reales.
- No se declara `READY_FOR_REAL_USE`.
