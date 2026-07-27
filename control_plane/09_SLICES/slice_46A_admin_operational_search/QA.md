# Slice 46A QA

## Pruebas Obligatorias

- Admin busca por telefono y ve cliente, orden y ticket relacionados.
- Admin busca por codigo de referencia y ve negocio o intake relacionado.
- Support activo puede buscar.
- Negocio o cliente no pueden buscar.
- Menos de 3 caracteres devuelve error seguro.
- La respuesta no contiene cuerpos de mensaje, `storage_path`, `file_asset_id`,
  signed URLs ni valores bancarios completos.
- Audit log registra `admin_operational_search_performed` sin texto crudo.
- El boton de cada resultado abre la pantalla correspondiente.

## Comandos

```powershell
python -m pytest apps/api/tests/test_admin_console.py -q --tb=short
python -m pytest apps/api/tests -q
python -m ruff check apps/api scripts
python -m compileall apps/api apps/web/src scripts
pnpm --filter @nodo/web build
git diff --check
```

## Smoke Manual Staging

1. Entrar a Admin Web.
2. Abrir `Buscar`.
3. Buscar por codigo de orden real de staging.
4. Abrir la orden desde el resultado.
5. Volver a `Buscar`.
6. Buscar por telefono o codigo de referencia.
7. Abrir intake, negocio, cliente o ticket segun aplique.
8. Confirmar que la campana y soporte siguen funcionando.
