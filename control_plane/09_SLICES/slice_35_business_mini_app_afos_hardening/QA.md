# QA.md

## Comandos obligatorios

```powershell
python -m pytest apps/api/tests/test_auth_lifecycle_static.py -q --tb=short
python -m pytest apps/api/tests/test_ads_marketplace.py -q --tb=short
python -m pytest apps/api/tests/test_business_access_control.py -q --tb=short
python -m pytest apps/api/tests/test_business_order_ops.py -q --tb=short
python -m pytest apps/api/tests/test_credits_referrals.py -q --tb=short
python -m pytest apps/api/tests -q
python -m ruff check apps/api scripts
python -m compileall apps/api apps/web/src scripts
pnpm --filter @nodo/web build
```

Si `corepack` o `pnpm` no existe en el runtime, documentar el comando alternativo exacto y la version usada.

## Scans obligatorios

```powershell
rg -n "private_key|seed phrase|mnemonic|BEGIN PRIVATE|account_value|storage_path|signed_url|console\\.log|dangerouslySetInnerHTML" apps/web/src apps/api/app
rg -n "recordActionBreadcrumb\\(" apps/web/src/hooks/business-mini-app
rg -n "wallet|zelle|token|pin|tx_hash" apps/web/src/observability apps/api/app/modules/observability
```

Los matches esperados deben explicarse. Los valores reales de secretos bloquean el slice.

## Evidencia requerida

- Builder report.
- Test results JSON o salida cruda copiable.
- Line count antes/despues.
- Matriz AFOS.
- Matriz de acciones sensibles.
- Lista de archivos tocados.
- Riesgos pendientes por severidad.

## Prueba manual sugerida despues de deploy staging

No ejecutar en este slice si no hay deploy autorizado. Dejar checklist:

- abrir desde Telegram real;
- entrar como negocio aprobado;
- ver Inicio con creditos y online/offline;
- agregar Zelle y USDT TRC20;
- borrar uno;
- crear anuncio con metodo de cobro activo;
- editar anuncio y cambiar metodo de cobro;
- pausar/reactivar;
- generar compra Base USDC;
- copiar wallet/monto;
- ver orden abierta;
- ver historial con numero de orden;
- abrir soporte.
