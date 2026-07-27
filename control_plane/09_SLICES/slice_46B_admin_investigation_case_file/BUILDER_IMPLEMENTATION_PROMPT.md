# BUILDER_IMPLEMENTATION_PROMPT.md

## Prompt

SKILLS A USAR:

- `spec-driven-development`: para implementar solo el contrato aprobado.
- `api-and-interface-design`: para mantener DTO, errores, paginacion y rutas estables.
- `security-and-hardening`: porque la ficha cruza datos de clientes, negocios, ordenes, soporte e intake.
- `code-review-and-quality`: para separar responsabilidades y evitar mezclar detalles privados en la ficha.
- `frontend-ui-engineering`: para crear una vista Admin compacta, scrollable y operativa.
- `observability-and-instrumentation`: para auditar la lectura sin guardar cuerpos, motivos privados ni secretos.
- `test-driven-development`: para escribir primero las regresiones criticas.
- `git-workflow-and-versioning`: para mantener el paquete separado y no ensuciar el repo.

MODO: IMPLEMENTACION DEL SLICE 46B.

Antes de tocar codigo:

1. Verifica `git status --short --branch`.
2. Confirma que solo trabajaras `slice_46B_admin_investigation_case_file`.
3. Lee estos documentos completos:
   - `control_plane/09_SLICES/slice_46B_admin_investigation_case_file/README.md`
   - `control_plane/09_SLICES/slice_46B_admin_investigation_case_file/API_CONTRACT.md`
   - `control_plane/09_SLICES/slice_46B_admin_investigation_case_file/SECURITY_CONTRACT.md`
   - `control_plane/09_SLICES/slice_46B_admin_investigation_case_file/QA.md`
   - `control_plane/09_SLICES/slice_46A_admin_operational_search`
   - `control_plane/09_SLICES/slice_44B_admin_order_chat_evidence_viewer`

Objetivo:

Implementar una ficha de investigacion Admin de solo lectura:

```txt
GET /api/v1/admin/investigation/case-file
```

La ficha debe permitir investigar un anchor exacto:

- `user`
- `business`
- `business_intake`
- `order`
- `support_ticket`

Alcance obligatorio:

1. Backend dedicado con DTO allowlist.
2. RBAC:
   - `admin` y `super_admin`: ficha allowlist completa.
   - `support` activo: solo lo permitido por politica de soporte.
   - anchor no visible para `support`: `404`.
3. `Cache-Control: private, no-store`.
4. Auditoria `admin_investigation_case_file_viewed`.
5. Paginacion por seccion:
   - `section=all|orders|support_tickets|business_intakes|evidence|timeline`
   - `cursor` opaco ligado a seccion y anchor.
6. Timeline seguro:
   - solo eventos allowlist;
   - sin cuerpos;
   - sin motivos privados;
   - sin `metadata_json` crudo.
7. Frontend Admin:
   - nueva vista compacta y scrollable;
   - boton `Investigar` desde resultados de 46A;
   - conservar botones actuales de abrir destino directo;
   - links internos a orden, ticket, negocio, cliente, intake y visor 44B si aplica.
8. Fallo parcial:
   - una seccion puede mostrar error seguro sin romper toda la ficha.

Prohibido:

- No usar `severity_hint`.
- No usar `suggested_next_step`.
- No declarar fraude, culpa, pago valido ni recuperacion.
- No devolver cuerpos completos de chat/tickets en la ficha inicial.
- No devolver `storage_path`, signed URLs, PIN, tokens, wallets completas, datos bancarios completos ni `metadata_json` crudo.
- No descargar adjuntos automaticamente.
- No crear tablas ni migraciones salvo que encuentres bloqueo tecnico y lo reportes primero.
- No cambiar estados.
- No reabrir/cerrar/resolver tickets.
- No tocar pagos, creditos, Base USDC, Zelle, reputacion, bots Telegram ni estados de orden.
- No deploy, no produccion, no reset DB, no secretos.
- No commit ni push salvo aprobacion explicita del Owner.

Tests obligatorios:

1. RBAC para `admin`, `super_admin`, `support`, cliente, negocio, staff inactivo y sin sesion.
2. Cinco anchors validos.
3. Anchor no visible para `support` devuelve `404`.
4. Activos y archivados aparecen cuando son parte del caso.
5. Paginacion por seccion y cursor no reutilizable en otra seccion.
6. Fallo parcial de una seccion no rompe las demas.
7. Audit log seguro sin cuerpos, motivos privados ni metadata libre.
8. Respuesta sin `severity_hint`, `suggested_next_step`, storage paths, signed URLs, PIN, tokens, wallets completas ni datos bancarios completos.
9. Frontend: boton `Investigar` desde 46A y vista case-file scrollable.
10. 44B se abre como accion explicita, no como cuerpo incrustado en la ficha inicial.

Validacion esperada:

```powershell
python -m pytest apps/api/tests/test_admin_investigation_case_file.py -q --tb=short
python -m pytest apps/api/tests/test_admin_console.py apps/api/tests/test_admin_order_chat_evidence.py apps/api/tests/test_support_ticket_center.py -q --tb=short
python -m pytest apps/api/tests -q
python -m ruff check apps/api scripts
python -m compileall apps/api apps/web/src scripts
pnpm --filter @nodo/web build
git diff --check
```

Entrega:

1. `ESTADO`: `READY_FOR_VALIDATOR_REVIEW` o `BLOCKED_WITH_EVIDENCE`.
2. Resumen simple de que construiste.
3. Archivos tocados exactos.
4. Tests ejecutados y resultados.
5. Riesgos pendientes.
6. Confirmacion de no deploy, no produccion, no migraciones, no secretos y no cambios fuera del slice.
