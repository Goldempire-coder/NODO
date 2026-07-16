# OWNER_REVIEW_CHECKLIST.md

Antes de aceptar una entrega o preparar deploy:

- Respeto el scope aprobado.
- No invento pantallas, metodos, estados, metricas ni infraestructura.
- El manifiesto pre-deploy en `control_plane/13_HANDOFF/` esta revisado.
- Todos los archivos runtime importados estan incluidos en el release candidate.
- Las migraciones incluidas tienen plan de apply, rollback y validacion.
- No hay secretos, API keys, private keys, seed phrases ni RPC keys reales en repo, logs o evidencia.
- Las variables de entorno nuevas estan documentadas como placeholders.
- Zelle/Base USDC usan datos enmascarados cuando corresponde.
- No se agrego efectivo, ciudad, escrow, garantia financiera ni copy de custodia.
- Audit logs existen donde aplica.
- Permisos, ownership y RBAC estan validados.
- UI es consistente con tokens/logo y no bloquea acciones sensibles sin feedback.
- Tests, build, lint y secret scan pasaron sobre el release candidate exacto.
- Builder report completo y sin `READY_FOR_REAL_USE`.
