# Staging Concurrency Policy

Estado: OFFICIAL
Ultima actualizacion: 2026-07-12

## Diagnostico oficial

Clasificacion actual:

- `CONNECTION_TRANSPORT_LIMIT_IDENTIFIED_LOCALLY`
- GitHub Actions corroboration: `PENDING / BLOCKED_BY_GITHUB_ACTIONS_TOOLING`
- Marketplace product path: `NOT PRIMARY BOTTLENECK`
- DB/cache/frontend: `NOT PRIMARY BOTTLENECK`

Evidencia base:

- `evidence/slice_runs/slice_33A6_summary.json`
- `evidence/slice_runs/slice_33A7_summary.json`
- `governance/builder_reports/slice_33A6_ttfb_queue_source_isolation_BUILDER_REPORT.md`
- `governance/builder_reports/slice_33A7_connection_origin_and_route_confirmation_BUILDER_REPORT.md`

33A6/33A7 muestran que rutas livianas tambien sufren TTFB alto:

- `/api/v1/health`
- `/api/v1/ready`
- `/api/v1/version`

La evidencia mas fuerte es que `/api/v1/version` tuvo backend p95 bajo mientras TTFB p95 estuvo en segundos, y curl midio `tcp_connect_p95` alrededor de 7 segundos en muestras locales. Por esa razon no se debe optimizar marketplace, DB, cache ni frontend usando esta evidencia como causa primaria.

## Regla de gates staging

| Nivel | Uso permitido | Puede bloquear producto | Interpretacion |
|---|---|---:|---|
| c25 | Product gate staging | Si | Valida funcionalidad y regresiones bajo carga moderada. |
| c50 | Product gate staging recomendado maximo | Si | Maximo recomendado para gates de producto en staging actual. |
| c100+ | Infra/edge/transport probe | No, si backend p95 sigue bajo y domina TTFB/tcp_connect | Abre investigacion de transporte, origen, edge, ingress o harness. |

`c100+` sigue permitido, pero debe ser explicito como `infra-probe`. No es un gate obligatorio de producto en staging actual.

## Regla de interpretacion

Si una corrida c100+ falla o degrada, evaluar en este orden:

1. Confirmar `X-NODO-Process-Time-Ms` y `Server-Timing`.
2. Comparar client p95 contra backend p95.
3. Revisar `ttfb_or_headers_ms`.
4. Revisar curl phases si existen:
   - `time_namelookup`
   - `time_connect`
   - `time_appconnect`
   - `time_starttransfer`
5. Si backend p95 esta bajo y TTFB/tcp_connect domina, clasificar como transporte/infra/harness, no como bug de producto.

## Cuando c100 falla pero backend p95 es bajo

No hacer automaticamente:

- subir pool DB;
- subir workers;
- cambiar plan Railway/Supabase/Upstash;
- optimizar queries de marketplace;
- reducir payload sin evidencia;
- culpar frontend;
- bloquear release de producto solo por c100+ staging.

Si c100+ muestra backend p95 bajo, abrir investigacion de:

- origen del runner;
- ruta local vs GitHub Actions;
- ruta publica vs URL directa si existe;
- keepalive/conexion TCP;
- HTTP/2;
- Railway edge/ingress/runtime con evidencia vendor.

## Tooling policy

`scripts/cloud_load_runner.py` debe tratar:

- `--run-purpose product-gate` como default;
- `product-gate` con concurrencia mayor a c50 como rechazo;
- `--run-purpose infra-probe` como modo explicito para c100+.

El workflow `.github/workflows/nodo-cloud-load-runner.yml` debe usar c50 como default para product gates.

## Backlog

No ejecutar como parte de esta politica:

- `33C_http2_staging_spike`: probar HTTP/2 con dependencia controlada y sin cambiar producto.
- `33D_railway_route_provider_research`: revisar evidencia Railway/vendor sin afirmar limite hasta tener datos.
- `33E_direct_url_or_alt_origin_probe`: comparar public URL contra direct URL/otro origen si existe una ruta segura.

## Limites

Esta politica ajusta solo staging gates. No baja el estandar de produccion. Antes de produccion siguen pendientes pruebas reales multi-origen, observabilidad provider, DR, seguridad y aprobacion owner.
