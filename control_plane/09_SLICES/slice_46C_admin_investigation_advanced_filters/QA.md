# Slice 46C QA

Estado: DRAFT

## Casos Obligatorios

### Cliente No Recuerda El Negocio

Entrada:

- `client_hint`;
- rango de monto;
- ventana de fecha.

Resultado:

- devuelve ordenes candidatas;
- muestra negocio y cliente enmascarado;
- permite abrir ficha 46B;
- no muestra chats completos.

### Cliente Recuerda Monto Y Dia

Entrada:

- `amount_min_usd`;
- `amount_max_usd`;
- `created_from`;
- `created_to`.

Resultado:

- devuelve candidatos dentro del rango;
- ordena por fecha reciente;
- indica `amount_in_range` y `created_in_window`.

### Negocio Dice Que No Reconoce Pago

Entrada:

- `business_hint`;
- ventana de fecha;
- rango de monto opcional.

Resultado:

- devuelve ordenes del negocio compatibles;
- indica si existe reporte de pago;
- no decide si el pago fue valido.

### Filtros Insuficientes

Entrada:

- solo `client_hint` o solo `business_hint`.

Resultado:

- responde `ADMIN_INVESTIGATION_FILTER_REQUIRED`;
- no hace busqueda amplia.

### Fecha Demasiado Amplia

Entrada:

- ventana mayor a 31 dias.

Resultado:

- responde `ADMIN_INVESTIGATION_DATE_RANGE_INVALID`.

## Pruebas De Seguridad

- Cliente, negocio y usuario sin sesion reciben rechazo.
- Support sin permisos recibe rechazo o resultados no visibles.
- Support con permisos recibe solo campos enmascarados.
- La respuesta no contiene:
  - cuerpos de mensajes;
  - `storage_path`;
  - signed URLs;
  - `file_asset_id`;
  - wallets completas;
  - datos bancarios completos;
  - tokens;
  - `risk_level`;
  - `trust_level`;
  - `severity_hint`;
  - `suggested_next_step`.
- Audit no guarda hints crudos.
- La respuesta usa `Cache-Control: private, no-store`.

## Pruebas De UX

- Pantalla compacta con filtros claros.
- Resultados scrollables.
- Boton `Investigar` abre ficha 46B.
- Boton `Abrir orden` conserva navegacion existente.
- Error de filtros insuficientes explica que se necesita mas informacion.
- No bloquea campana ni soporte.

## Comandos Esperados

```powershell
python -m pytest apps/api/tests/test_admin_investigation_candidates.py -q --tb=short
python -m pytest apps/api/tests/test_admin_console.py apps/api/tests/test_admin_investigation_case_file.py -q --tb=short
python -m pytest apps/api/tests -q
python -m ruff check apps/api scripts
python -m compileall apps/api apps/web/src scripts
pnpm --filter @nodo/web build
git diff --check
```
