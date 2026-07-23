# BUILDER_PROMPT.md

## Prompt

SKILLS A USAR:

- `spec-driven-development`: para respetar el slice y no inventar alcance.
- `code-review-and-quality`: para mapear responsabilidades actuales antes de tocar codigo.
- `security-and-hardening`: porque se va a exponer cuerpo de mensajes a una superficie admin autorizada.
- `api-and-interface-design`: para decidir si conviene extender detalle de orden o crear endpoint admin dedicado.
- `frontend-ui-engineering`: para revisar el panel admin y evitar una UI pesada o infinita.
- `observability-and-instrumentation`: para auditar la lectura admin sin filtrar mensajes.
- `test-driven-development`: para proponer pruebas antes de implementar.
- `git-workflow-and-versioning`: para no mezclar cambios previos ni ensuciar el repo.

MODO: INSPECCION Y PLAN SOLAMENTE.

No modifiques archivos. No hagas deploy. No ejecutes migraciones. No hagas commit. No limpies ni reviertas cambios ajenos. No declares `READY_FOR_REAL_USE`.

Objetivo:

Inspeccionar `slice_44B_admin_order_chat_evidence_viewer` y proponer un plan para que Admin pueda abrir una alerta anti-evasion y ver la conversacion completa de la orden desde el dashboard, sin meter el cuerpo completo del mensaje en notificaciones, logs, telemetry ni audit logs.

Contexto:

- `slice_44_order_chat_anti_evasion` detecta mensajes del negocio que invitan a operar fuera de NODO.
- La alerta debe guardar solo senales canonicas redacted.
- La notificacion abre `admin://order/{order_id}`.
- El detalle admin de orden hoy debe revisarse para confirmar si incluye o no mensajes completos.
- Si no los incluye, el plan debe proponer como agregarlos de forma read-only, autorizada, auditable y scrollable.

Inspeccion obligatoria:

1. Revisar rutas y modelos admin de orden:
   - `apps/api/app/modules/admin/*`
   - repositorios Postgres y memoria del admin order detail
   - pantallas admin de orden/disputa

2. Revisar chat de orden:
   - rutas de chat
   - servicio de chat
   - repositorios de mensajes
   - reglas de ownership y permisos
   - adjuntos si existen

3. Revisar notificaciones admin:
   - modelo de `admin_notifications`
   - metadata disponible
   - parseo de `admin://order/{id}`
   - si hay forma segura de pasar `message_id` para highlight

4. Revisar seguridad:
   - que ningun payload admin exponga `storage_path`, signed URLs iniciales, PIN, tokens, `account_value` o secretos
   - que logs/audit no guarden cuerpo completo
   - que usuarios no admin no puedan leer chat de orden desde admin

5. Revisar UI:
   - donde agregar panel de chat en Admin Order Detail
   - como hacerlo scrollable y compacto
   - como destacar el mensaje detectado sin hacer la pantalla gigante

Entrega requerida:

1. `ESTADO`: `INSPECTION_COMPLETE_READY_FOR_OWNER_REVIEW`
2. Mapa actual con archivos exactos.
3. Hallazgos ordenados por severidad.
4. Decision recomendada:
   - extender endpoint admin order detail, o
   - crear endpoint admin dedicado para mensajes.
   Explica por que.
5. Plan de implementacion por pasos.
6. Archivos que tocarias.
7. Tests que agregarias.
8. Riesgos y rollback.
9. Confirmacion explicita de que no modificaste archivos, no hiciste deploy, no ejecutaste migraciones, no tocaste pagos/creditos/Zelle/Base USDC/ratings/estados de orden.

Regla de alcance:

El Builder solo puede planear. La implementacion requiere aprobacion posterior del Owner.

