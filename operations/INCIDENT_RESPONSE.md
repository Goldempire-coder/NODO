# INCIDENT_RESPONSE

Estado: OFFICIAL
Ultima actualizacion: 2026-07-11

## Proceso oficial

1. Nombrar Incident Commander.
2. Abrir canal de incidente.
3. Registrar hora, entorno, sintoma y primer impacto.
4. Confirmar severidad con `SEVERITY_MATRIX.md`.
5. Congelar cambios no urgentes.
6. Preservar evidencia: logs, request IDs, payloads redacted, run IDs, screenshots, evidence JSON.
7. Ejecutar solo runbooks documentados.
8. Mitigar dano antes de buscar causa perfecta.
9. Escalar al llegar al limite de autoridad.
10. Validar recuperacion con flujo real.
11. Mantener vigilancia.
12. Crear postmortem.

## Reglas SEV-1

- No borrar datos.
- No aplicar migraciones improvisadas.
- No desactivar RBAC, rate limits, idempotencia, audit ni validaciones.
- No rotar todos los secretos sin plan.
- No editar DB manualmente sin evidencia y aprobacion.
- No cerrar incidente sin validar flujo real.

## Evidencia minima

- Fecha/hora con timezone.
- Entorno afectado.
- Commit/build id si existe.
- Endpoint o componente.
- Request ID o run ID.
- Captura de error o JSON redacted.
- Comando ejecutado.
- Resultado obtenido.
- Decision tomada y aprobador.
