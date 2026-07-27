# BUILDER_PROMPT.md

## Prompt

SKILLS A USAR:

- `spec-driven-development`: para respetar el slice y no inventar alcance.
- `api-and-interface-design`: para revisar contrato, payloads, rutas y limites.
- `security-and-hardening`: porque la ficha relaciona datos privados de clientes, negocios, ordenes y soporte.
- `code-review-and-quality`: para mapear responsabilidades actuales y detectar codigo duplicado o acoplado.
- `frontend-ui-engineering`: para proponer una ficha compacta, scrollable y operativa en Admin Web.
- `observability-and-instrumentation`: para definir auditoria sin filtrar cuerpos ni secretos.
- `test-driven-development`: para proponer pruebas antes de implementar.
- `git-workflow-and-versioning`: para no mezclar cambios previos ni ensuciar el repo.

MODO: INSPECCION Y PLAN SOLAMENTE.

No modifiques archivos. No hagas deploy. No ejecutes migraciones. No hagas
commit. No hagas push. No limpies ni reviertas cambios ajenos. No declares
`READY_FOR_REAL_USE`.

Objetivo:

Mapear como construir `slice_46B_admin_investigation_case_file`: una ficha de
investigacion en Admin Web que permita entender un problema de cliente/negocio
desde una pista encontrada por 46A, sin saltar entre cinco modulos y sin exponer
datos privados de mas.

Contexto:

- 46A ya agrego una lupa operativa de solo lectura.
- 44B ya agrego visor admin de evidencia de chat de orden.
- Soporte ya tiene tickets activos y archivados.
- Admin necesita resolver casos reales como:
  - cliente envio dinero y no recuerda negocio;
  - cliente cerro la app y no encuentra la conversacion;
  - negocio entro con codigo de referencia;
  - ticket se cerro y hay que reconstruir que paso;
  - alerta de posible negocio fuera de plataforma;
  - varios tickets pertenecen al mismo caso.

Inspeccion obligatoria:

1. Revisar slice docs:
   - `control_plane/09_SLICES/slice_46A_admin_operational_search`
   - `control_plane/09_SLICES/slice_44B_admin_order_chat_evidence_viewer`
   - `control_plane/09_SLICES/slice_46B_admin_investigation_case_file`

2. Revisar Admin Web:
   - modelo/hook de investigacion 46A;
   - navegacion `admin://...`;
   - pantallas de orden, negocio, cliente, intake, soporte y audit;
   - donde seria mas limpio abrir la ficha.

3. Revisar backend:
   - rutas admin existentes;
   - repositorios admin;
   - search 46A;
   - soporte activo/archivado;
   - ordenes, negocios, clientes, intake y audit logs;
   - permisos RBAC actuales para `admin`, `super_admin` y `support`.

4. Revisar evidencia:
   - payment report o resumen de pago;
   - documentos de intake;
   - adjuntos de tickets;
   - chat evidence de orden;
   - timeline de eventos.

5. Revisar seguridad:
   - no cuerpos completos en ficha inicial;
   - no `storage_path`;
   - no signed URLs;
   - no tokens, PIN, headers o secretos;
   - telefonos/Telegram enmascarados;
   - audit logs sin texto libre sensible.

Entrega requerida:

1. `ESTADO`: `INSPECTION_COMPLETE_READY_FOR_OWNER_REVIEW`
2. Mapa actual con archivos exactos.
3. Que ya existe y se puede reutilizar.
4. Que falta para que Admin tenga una ficha real de investigacion.
5. Decision recomendada:
   - componer ficha en frontend con endpoints actuales, o
   - crear endpoint dedicado `GET /api/v1/admin/investigation/case-file`.
   Explica por que.
6. Contrato propuesto de DTO, errores, permisos y auditoria.
7. Plan de implementacion por pasos.
8. Archivos probables a tocar.
9. Tests que agregarias.
10. Riesgos, rollback y que NO tocarias.
11. Confirmacion explicita de que no modificaste archivos, no hiciste deploy,
    no ejecutaste migraciones, no tocaste pagos/creditos/Zelle/Base USDC,
    reputacion, bots ni estados de orden.

Regla de alcance:

El Builder solo puede mapear y proponer. La implementacion requiere aprobacion
posterior del Owner.
