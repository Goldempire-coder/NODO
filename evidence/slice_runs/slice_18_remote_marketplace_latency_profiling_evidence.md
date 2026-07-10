# Evidence - slice_18_remote_marketplace_latency_profiling

## Scope ejecutado
Profiling seguro para `GET /api/v1/ads/search` y agregacion en `scripts/capacity_real.py`.

## Gate de seguridad
`_profile` solo se adjunta cuando:

- `APP_ENV=staging`
- `ENABLE_STAGING_PROFILING=1`
- `X-NODO-Profile: 1`

Tests cubren:

- Sin env/header no hay `_profile`.
- Staging + env sin header no hay `_profile`.
- Header sin env no hay `_profile`.
- Production nunca devuelve `_profile`.
- Staging + env + header devuelve `_profile`.
- `_profile` no contiene `account_value`, `storage_path`, Authorization, Bearer, SQL ni nombres de secretos.

## Etapas instrumentadas
- `auth:marketplace_validate_header`
- `auth:marketplace_decode_access_token`
- `auth:marketplace_claim_user` o fallback DB
- `service:marketplace_access`
- `service:rate_limit`
- `service:validate_search_params`
- `cache:key_build`
- `cache:version_lookup` / `cache:version_cached`
- `cache:local_get`
- `cache:shared_get`
- `cache:hit`
- `cache:lock_wait`
- `cache:set_local`
- `cache:set_shared`
- `db:acquire`
- `db:query:list_marketplace_ads_with_businesses`
- `db:row_map:list_marketplace_ads_with_businesses`
- `service:rank`
- `service:payload`
- route `total_ms`

## Harness
`scripts/capacity_real.py` ahora acepta:

```powershell
--profile-marketplace
```

Con ese flag:

- envia `X-NODO-Profile: 1` solo en marketplace reads
- captura `_profile`
- limita raw profiles a 50
- agrega `profile_summary` con percentiles por etapa, cache hits, auth modes y p95 DB/route

Sin el flag no manda `X-NODO-Profile`.

## Validaciones
- Targeted profile API tests: passed.
- Targeted capacity profile tests: passed.
- Full backend pytest: `170 passed, 1 warning`.
- Ruff: `All checks passed!`.
- Compileall: OK.
- Frontend build: OK.
- Frontend source/build scan: sin matches para secretos, `storage_path`, `account_value` ni claims prohibidos.

## No ejecutado
No se corrio staging remoto ni stress real en esta fase. El objetivo era instrumentar y dejar listo el harness.
