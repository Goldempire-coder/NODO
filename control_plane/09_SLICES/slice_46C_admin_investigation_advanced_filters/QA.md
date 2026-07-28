# Slice 46C QA

Estado: STAGING_DEPLOYED_PENDING_OWNER_SMOKE

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
- ordena por fecha reciente con desempate por `order_id`;
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

### Rangos Incompletos

Entrada:

- solo `amount_min_usd`;
- o solo `created_from`.

Resultado:

- responde `ADMIN_INVESTIGATION_AMOUNT_RANGE_INVALID` o
  `ADMIN_INVESTIGATION_DATE_RANGE_INVALID`;
- no ejecuta busqueda amplia.

### Estado De Soporte Filtra Candidatos

Entrada:

- filtros suficientes de orden;
- `support_status_group=archived`.

Resultado:

- devuelve solo ordenes con al menos un ticket relacionado `resolved` o
  `closed`;
- no devuelve ordenes con tickets solamente activos;
- el filtro ocurre antes de `LIMIT`.

### Paginacion Segura

Entrada:

- busqueda valida con mas de 25 candidatos.

Resultado:

- devuelve `next_cursor` opaco;
- la pagina siguiente conserva filtros y orden;
- cursor alterado responde `ADMIN_INVESTIGATION_CURSOR_INVALID`;
- cursor reutilizado con otros filtros o rol responde
  `ADMIN_INVESTIGATION_CURSOR_INVALID`.
- las mismas reglas de Support, aunque lleguen reordenadas o duplicadas,
  mantienen valido el cursor;
- un cambio real en permisos de Support invalida el cursor.

### Pistas Textuales Literales

Entrada:

- `client_hint` o `business_hint` con `%`, `_` o `\`.

Resultado:

- los tres caracteres se buscan literalmente;
- no se convierten en comodines SQL;
- memory y Postgres conservan la misma semantica.

## Pruebas De Seguridad

- Cliente, negocio y usuario sin sesion reciben rechazo.
- Support sin permisos recibe rechazo o resultados no visibles.
- Support con permisos recibe solo campos enmascarados.
- Support con permisos limitados no recibe ordenes fuera de cola/asignacion,
  incluso cuando hay mas de 25 coincidencias antes del filtro de alcance.
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
- Cursor no contiene hints crudos.
- La respuesta usa `Cache-Control: private, no-store`.

## Pruebas De UX

- Pantalla compacta con filtros claros.
- Resultados scrollables.
- Boton `Investigar` abre ficha 46B.
- Boton `Abrir orden` conserva navegacion existente.
- Error de filtros insuficientes explica que se necesita mas informacion.
- Cambiar cualquier filtro limpia resultados y cursor anteriores.
- `Cargar mas` solo usa los filtros exactos que generaron el cursor.
- Una respuesta iniciada con filtros anteriores no reemplaza resultados nuevos.
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
