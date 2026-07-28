# Builder Prompt - Slice 46C Admin Investigation Advanced Filters

Usa estos skills antes de trabajar:

- `spec-driven-development`
- `api-and-interface-design`
- `security-and-hardening`
- `code-review-and-quality`
- `frontend-ui-engineering`
- `test-driven-development`
- `performance-optimization`
- `git-workflow-and-versioning`

## Modo

Primero inspecciona y entrega plan. No modifiques archivos hasta recibir
aprobacion del Owner. Si ya recibiste aprobacion de implementacion en un turno
posterior, confirma que los contratos incluyen cursor, rangos completos, RBAC de
support y orden deterministico antes de tocar codigo.

## Autoridad

AFOS y los contratos del repo gobiernan. Este slice es:

```txt
control_plane/09_SLICES/slice_46C_admin_investigation_advanced_filters
```

Debes leer:

- `README.md`
- `API_CONTRACT.md`
- `SECURITY_CONTRACT.md`
- `QA.md`
- `control_plane/09_SLICES/slice_46A_admin_operational_search`
- `control_plane/09_SLICES/slice_46B_admin_investigation_case_file`
- `control_plane/06_API_CONTRACTS/ADMIN_API.md`
- `control_plane/06_API_CONTRACTS/ERROR_CONTRACT.md`
- RBAC/staff/support/admin modules relevantes.

## Objetivo

Mapear como implementar:

```txt
GET /api/v1/admin/investigation/order-candidates
```

La busqueda avanzada debe encontrar ordenes candidatas cuando soporte solo
tiene pistas incompletas: cliente, negocio, monto, fecha o estado.

## Entrega De Inspeccion

Devuelve:

1. Estado: `INSPECTION_COMPLETE_READY_FOR_OWNER_REVIEW`.
2. Repo status y rama.
3. Mapa actual:
   - donde viven ordenes;
   - donde viven tickets;
   - donde viven payment reports;
   - donde se hace 46A;
   - donde se abre 46B;
   - como se gobierna support RBAC.
4. Plan de implementacion por pasos.
5. Archivos probables.
6. Riesgos de privacidad/costo.
7. Tests propuestos.
8. Que NO tocaras.

## Reglas

- Todos los filtros se combinan con `AND`.
- Rechaza rangos incompletos: `amount_min_usd`/`amount_max_usd` deben venir
  juntos, igual que `created_from`/`created_to`.
- `support_status_group=active|archived` filtra candidatos antes de
  `ORDER BY`, cursor y `LIMIT`; no es solo un contador.
- Orden inicial: `created_at DESC`, `order_id DESC`. No inventes score.
- Cursor opaco firmado y ligado al fingerprint de filtros, rol y alcance. Cursor
  alterado, vencido o reutilizado con otros filtros responde
  `ADMIN_INVESTIGATION_CURSOR_INVALID`.
- Support no se autoriza por `user.role` solamente:
  - support activo con `view_orders_masked` puede ver candidatos enmascarados;
  - support activo sin `view_orders_masked` solo ve ordenes ligadas a tickets
    dentro de su cola visible o asignacion vigente;
  - support sin permiso aplicable recibe `FORBIDDEN`;
  - el filtro de alcance de support va antes de `LIMIT`.
- No buscar cuerpos de mensajes.
- No exponer datos bancarios completos.
- No exponer storage paths, signed URLs ni file IDs internos.
- No guardar `client_hint` ni `business_hint` crudos en audit, logs de app o
  telemetria. Como son query params, la UI no debe pedir bancos completos,
  wallets, PIN, tokens ni cuerpos de mensajes.
- No crear migracion sin evidencia y aprobacion.
- No tocar pagos, creditos, USDC, Zelle, bots, reputacion ni capacidad.
- No hacer deploy.
- No hacer commit.
- No declarar `READY_FOR_REAL_USE`.

## Validacion Esperada Si Luego Se Aprueba Implementacion

```powershell
python -m pytest apps/api/tests/test_admin_investigation_candidates.py -q --tb=short
python -m pytest apps/api/tests/test_admin_console.py apps/api/tests/test_admin_investigation_case_file.py -q --tb=short
python -m pytest apps/api/tests -q
python -m ruff check apps/api scripts
python -m compileall apps/api apps/web/src scripts
pnpm --filter @nodo/web build
git diff --check
```
