# BUILDER_REPORT - slice_27B_cloud_scalability_cost_runner

## Estado final

READY_FOR_OWNER_REVIEW

## Objetivo

Preparar el runner cloud para medir escalabilidad vs costo sin depender de la PC local. Este slice no declara capacidad 10k, no calcula dolares inventados y no cambia producto.

## Cambios realizados

- `.github/workflows/nodo-cloud-load-runner.yml`
  - Agrega input manual `profile_marketplace`.
  - Si se activa, pasa `--profile-marketplace` al runner.

- `scripts/cloud_load_runner.py`
  - Agrega `--profile-marketplace`.
  - En marketplace envia `X-NODO-Profile: 1` cuando se pide.
  - Captura `cost_units`:
    - requests medidos;
    - requests de setup;
    - usuarios sinteticos creados;
    - bytes de respuesta;
    - ms cliente acumulados;
    - ms backend acumulados;
    - requests perfilados;
    - conteo de stages;
    - cache hit counts;
    - errores de transporte.
  - No convierte a dolares: el output dice explicitamente que se requieren exports reales de billing.

- `apps/api/tests/test_staging_validation_tooling.py`
  - Tests del summary `cost_units`.
  - Test de header `X-NODO-Profile`.
  - Verifica que no se persistan tokens/Authorization en el summary.

## Smoke ejecutado

Se ejecuto un smoke minimo desde esta maquina solo para validar formato del JSON:

```powershell
python scripts\cloud_load_runner.py --base-url https://nodo-api-production.up.railway.app --scenario health --requests 2 --concurrency 1 --run-id local_cost_runner_smoke --output evidence\slice_runs\slice_27B_cloud_runner_local_health_smoke.json
```

Resultado:

- `2/2` OK.
- `cost_units` presente.
- `cleanup.required=false`.

Este smoke no es prueba de capacidad porque corrio desde PC local.

## Validaciones

- `python -m pytest apps\api\tests\test_staging_validation_tooling.py -q --tb=short`: 50 passed, 1 warning.
- `$env:PYTHONPATH='apps/api'; python -m pytest apps\api\tests -q`: 249 passed, 1 warning.
- `python -m ruff check apps\api scripts`: All checks passed.
- `python -m compileall apps\api apps\web\src scripts`: OK.
- `corepack pnpm --filter @nodo/web build`: OK.
- `python -m json.tool evidence\slice_runs\slice_27B_cloud_runner_local_health_smoke.json`: OK.

## Proximo uso recomendado en GitHub Actions

1. Baseline barato:

```txt
scenario=health
requests=100
concurrency=20
profile_marketplace=false
```

2. Marketplace c100 con costo/perfil:

```txt
scenario=marketplace
requests=600
concurrency=100
remitters=140
profile_marketplace=true
```

3. Marketplace c200 solo si c100 pasa:

```txt
scenario=marketplace
requests=1000
concurrency=200
remitters=240
profile_marketplace=true
```

## Que NO hice

- No ejecute GitHub Actions.
- No corri carga cloud real.
- No toque Railway/Supabase/Upstash/Cloudflare.
- No cambie backend producto.
- No cambie frontend producto.
- No cambie migraciones.
- No calcule costo en dolares sin billing real.
- No declare READY_FOR_REAL_USE.

## Riesgos residuales

- `marketplace` crea usuarios sinteticos y requiere cleanup por `run_id`.
- `profile_marketplace=true` solo devuelve stages si staging tiene `ENABLE_STAGING_PROFILING=1`.
- El runner cloud aun no cubre order-create/mixed/Base USDC; este slice deja lista la primera matriz cloud para lectura/visitante.
