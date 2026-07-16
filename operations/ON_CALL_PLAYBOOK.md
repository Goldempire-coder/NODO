# ON_CALL_PLAYBOOK

Estado: OFFICIAL
Ultima actualizacion: 2026-07-11

## Playbook de las 2:00 AM

Recibiste una alerta. No asumas la causa. Sigue este orden.

1. Confirma que la alerta es real.
   - Revisa si hay mas de un usuario, endpoint o proveedor afectado.
   - Si hay API URL disponible, ejecuta:
     ```powershell
     Invoke-RestMethod "$env:NODO_STAGING_API_BASE_URL/health" -Headers @{"X-Request-Id"="ops_health_<timestamp>"}
     Invoke-RestMethod "$env:NODO_STAGING_API_BASE_URL/ready" -Headers @{"X-Request-Id"="ops_ready_<timestamp>"}
     Invoke-RestMethod "$env:NODO_STAGING_API_BASE_URL/version" -Headers @{"X-Request-Id"="ops_version_<timestamp>"}
     ```
2. Identifica entorno afectado: local, staging o production.
3. Confirma alcance: cliente, negocio, admin, bot, creditos, DB, Redis, storage.
4. Determina severidad con `SEVERITY_MATRIX.md`.
5. Revisa cambios recientes: deploy provider, Git commit, migrations, env changes.
6. Consulta metricas principales:
   - API status, p95/p99 latency, 5xx.
   - Supabase connections/errors.
   - Upstash Redis errors/latency.
   - Cloudflare Pages deploy status.
   - Railway deployment and logs.
7. Consulta logs con request ID.
8. Verifica dependencias externas.
9. Si hay riesgo financiero o de datos, detiene dano:
   - Pausar deploys.
   - Deshabilitar temporalmente flujo visible si existe feature flag documentado.
   - Bloquear usuario/negocio desde Admin si hay abuso confirmado.
10. Aplica solo mitigaciones documentadas.
   - Si el incidente involucra DB, storage, secrets, schema/deploy, Redis o audit logs, usa el runbook especifico en `runbooks/`.
   - No ejecutar restore sin owner approval, evidencia de backup disponible y SOP aplicable.
   - No ejecutar rollback de codigo si el schema puede ser incompatible; usar `runbooks/SCHEMA_DEPLOY_INCOMPATIBILITY_RUNBOOK.md`.
11. Registra cada accion con hora.
12. Valida recuperacion con flujo real.
13. Mantiene vigilancia.

## NO HAGAS ESTO A LAS 2:00 AM

- No borrar datos.
- No ejecutar migraciones improvisadas.
- No cambiar produccion manualmente sin evidencia.
- No rotar todos los secretos sin plan.
- No reiniciar repetidamente sin revisar impacto.
- No desactivar seguridad.
- No cambiar reglas de negocio para probar.
- No ejecutar scripts no revisados.
- No ejecutar backup/restore improvisado.
- No copiar datos reales a entornos no aprobados.
- No ocultar el incidente.
- No declarar recuperacion solo porque desaparecio una alerta.
