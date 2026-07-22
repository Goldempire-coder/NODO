# QA

## Pruebas obligatorias

El Builder debe ejecutar, como minimo:

```powershell
python -m pytest apps/api/tests/test_auth_lifecycle_static.py -q --tb=short
python -m pytest apps/api/tests/test_business_access_control.py -q --tb=short
python -m pytest apps/api/tests/test_admin_operational_notifications.py -q --tb=short
python -m pytest apps/api/tests -q
python -m ruff check apps/api scripts
python -m compileall apps/api apps/web/src scripts
pnpm --filter @nodo/web build
git diff --check
```

Si `pnpm` o `node` no estan en PATH, usar el runtime local ya conocido:

```powershell
$env:PATH="C:\Users\carlo\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin;$env:PATH"
pnpm --filter @nodo/web build
```

## Scans obligatorios

```powershell
rg -n "risk_level|trust_level|storage_path|signed_url|private_key|seed phrase|mnemonic|BEGIN PRIVATE|console\.log|dangerouslySetInnerHTML" apps/api/app apps/web/src
```

El Builder debe explicar coincidencias esperadas. No puede convertir un match
real sensible en falso positivo sin evidencia.

## Evidencia minima

- `git status --short --branch` antes y despues.
- Resumen de archivos tocados.
- Tests ejecutados con resultado.
- Riesgos residuales.
- Confirmacion de no deploy y no produccion.
