# Builder Prompt - Slice 46D Admin Support Playbooks And Repair Queue

Usa estos skills antes de trabajar:

- `spec-driven-development`
- `planning-and-task-breakdown`
- `api-and-interface-design`
- `security-and-hardening`
- `frontend-ui-engineering`
- `observability-and-instrumentation`
- `code-review-and-quality`
- `git-workflow-and-versioning`

## Modo

Inspeccion solamente.

No modifiques archivos. No escribas codigo. No hagas deploy. No hagas commit.
Entrega primero un mapa y un reporte para revision del Owner.

## Autoridad

AFOS y los contratos del repo gobiernan. Este slice es:

```txt
control_plane/09_SLICES/slice_46D_admin_support_playbooks_and_repair_queue
```

Debes leer:

- `README.md`
- `SCOPE.md`
- `API_CONTRACT.md`
- `SECURITY_CONTRACT.md`
- `QA.md`
- `control_plane/09_SLICES/slice_46A_admin_operational_search`
- `control_plane/09_SLICES/slice_46B_admin_investigation_case_file`
- `control_plane/09_SLICES/slice_46C_admin_investigation_advanced_filters`
- `control_plane/09_SLICES/slice_44B_admin_order_chat_evidence_viewer`
- `control_plane/09_SLICES/slice_20B_support_ticket_center`
- `control_plane/06_API_CONTRACTS/ADMIN_API.md`
- `control_plane/06_API_CONTRACTS/SUPPORT_API.md`
- RBAC/staff/support/admin modules relevantes.

## Objetivo

Mapear como Admin y Soporte deben resolver problemas reales despues de ubicar
un caso. No construyas reparaciones todavia.

Queremos saber:

- que casos operativos existen;
- cuales ya se pueden resolver con el Dashboard actual;
- cuales estan parcialmente cubiertos;
- cuales requieren reparacion;
- que mini-slice debe arreglar cada brecha.

## Casos Minimos A Mapear

1. Cliente pago pero no recuerda el negocio.
2. Cliente cerro la app y perdio la conversacion.
3. Cliente reporta pago despues de que la orden expiro.
4. Negocio dice que no reconoce el pago.
5. Negocio entro con codigo de recomendacion y Admin necesita verlo.
6. Ticket cerrado o archivado y usuario vuelve a preguntar.
7. Varios tickets hablan del mismo problema.
8. Adjuntos enviados por cliente o negocio necesitan revision segura.
9. Alerta de chat fuera de plataforma necesita seguimiento.
10. Admin encuentra el caso, pero no existe boton o accion clara para continuar.

## Entrega

Devuelve:

1. Estado: `INSPECTION_COMPLETE_READY_FOR_OWNER_REVIEW`.
2. Repo status y rama.
3. Archivos, modulos y contratos revisados.
4. Matriz de casos:
   - caso;
   - pistas iniciales;
   - pantalla o endpoint actual;
   - evidencia disponible;
   - estado `cubierto|parcial|no_cubierto|no_aplica`;
   - brecha;
   - reparacion sugerida;
   - mini-slice recomendado.
5. Mapa del Dashboard actual.
6. Lista priorizada de reparaciones.
7. Riesgos de privacidad, costo y operacion.
8. Tests propuestos.
9. Que NO tocaste.

## Reglas

- No leer cuerpos privados de mensajes como fuente de busqueda general.
- No descargar adjuntos.
- No usar datos reales de produccion.
- No exponer secretos, tokens, bancos completos, wallets completas, signed URLs
  ni `storage_path`.
- No declarar culpa, fraude, pago valido o recuperacion.
- No proponer una accion que cambie estado sin auditoria y contrato separado.
- No ampliar permisos de soporte sin contrato RBAC separado.
- No tocar pagos, creditos, USDC, Zelle, reputacion, capacidad ni bots.
- No crear migraciones.
- No ejecutar deploy.
- No declarar `READY_FOR_REAL_USE`.

## Validacion Esperada

```powershell
git status --short --branch
git diff --check
```

Si decides ejecutar pruebas, explica por que fueron necesarias. Como este es un
slice de inspeccion, no se espera suite completa salvo que hayas tocado archivos,
lo cual no debes hacer en esta fase.
