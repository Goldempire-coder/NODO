# slice_18D_cloud_load_runner_report

## Estado

READY_FOR_CLOUD_RUNNER_EXECUTION

No se declara `READY_FOR_REAL_USE`.

## Objetivo

Dejar preparado un runner de carga cloud para que las pruebas de capacidad no dependan de la PC local ni de su red.

## Construido

- `scripts/cloud_load_runner.py`
- `.github/workflows/nodo-cloud-load-runner.yml`

## Escenarios soportados

- `health`
- `ready`
- `version`
- `marketplace`

## Que mide

- latencia observada por el runner
- `X-NODO-Process-Time-Ms`
- status codes
- errores de transporte
- Railway edge usado
- throughput
- p50/p95/p99

## Marketplace

El escenario `marketplace` autentica usuarios sinteticos sin DB directa:

- usa `BOT_TOKEN` desde env/secret
- firma `initData` como Telegram
- llama `/api/v1/auth/telegram`
- usa los access tokens para `GET /api/v1/ads/search`
- no guarda tokens en evidencia

Este escenario crea usuarios sinteticos con `run_id` en username. Deben limpiarse luego con cleanup staging por `run_id`.

## GitHub Actions

Workflow creado:

`.github/workflows/nodo-cloud-load-runner.yml`

Inputs manuales:

- `base_url`
- `scenario`
- `requests`
- `concurrency`
- `remitters`

Secret requerido solo para marketplace:

- `NODO_STAGING_BOT_TOKEN`

El workflow sube evidencia JSON como artifact.

## Smoke local ejecutado

Archivo:

`evidence/slice_runs/slice18d_cloud_runner_local_health_smoke_20260710171846.json`

Resultado:

- Scenario: `health`
- Requests: `20`
- Concurrency: `5`
- Errors: `0`
- Client p95: `7588.5691 ms`
- Server p95: `1.3793 ms`
- Railway edge: `mia1`

Este smoke confirma que el runner captura correctamente la diferencia entre latencia cliente y tiempo interno del servidor. No se usa como prueba de capacidad porque corrio desde la PC local.

## Validaciones locales

- Pytest completo API: `172 passed, 1 warning`
- Ruff: OK
- Compileall: OK
- Frontend build: OK

## Primeros runs cloud recomendados

1. Health baseline:

```txt
scenario=health
requests=600
concurrency=100
```

2. Marketplace c100:

```txt
scenario=marketplace
requests=600
concurrency=100
remitters=140
```

3. Marketplace c250:

```txt
scenario=marketplace
requests=1000
concurrency=250
remitters=300
```

4. Solo si c250 pasa sin errores y Railway metrics se mantienen sanas:

```txt
scenario=marketplace
requests=2000
concurrency=500
remitters=600
```

## Criterio de avance

PASS:

- error rate `0`
- status 5xx `0`
- `server_process_time.p95` bajo
- Railway HTTP p95 bajo
- runner cloud p95 razonable
- cleanup ejecutado si scenario marketplace

BLOCKED:

- 5xx
- errores de transporte repetidos desde cloud
- Railway p95 alto
- server_process_time p95 alto
- CPU/memoria saturadas
- cleanup pendiente de datos sinteticos

## Confirmaciones

- No se cambio producto.
- No se tocaron reglas de negocio.
- No se tocaron migraciones.
- No se tocaron endpoints sensibles.
- No se imprimieron secretos.
- No se declaro capacidad 10k.
- No se declaro `READY_FOR_REAL_USE`.
