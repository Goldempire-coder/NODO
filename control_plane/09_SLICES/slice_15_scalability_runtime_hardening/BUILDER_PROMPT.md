# BUILDER_PROMPT.md

```txt
Trabaja en: C:\Users\carlo\Documents\Playground\NODO

MODO: REPORT_FIRST
Slice: slice_15_scalability_runtime_hardening

Objetivo:
Preparar NODO para escalar runtime de marketplace y trafico concurrente sin tumbar PostgreSQL, sin debilitar operaciones sensibles y sin declarar READY_FOR_REAL_USE.

Antes de construir:
1. Lee obligatoriamente:
   - control_plane/00_GOVERNANCE/SOURCE_OF_TRUTH.md
   - control_plane/00_GOVERNANCE/DO_NOT_INVENT.md
   - control_plane/09_SLICES/SLICE_EXECUTION_MATRIX.md
   - control_plane/09_SLICES/SLICE_CONTRACTS_MASTER.md
   - control_plane/09_SLICES/slice_15_scalability_runtime_hardening/*
   - governance/owner_reviews/performance_runtime_capacity_report_02_20260710.md
   - control_plane/11_OPERATIONS/ENVIRONMENT_VARIABLES.md
   - control_plane/06_API_CONTRACTS/ADS_API.md
   - control_plane/05_SECURITY/SURFACE_ACCESS_POLICY.md
   - apps/api/app/auth/dependencies.py
   - apps/api/app/modules/ads/*
   - apps/api/app/shared/db/connection.py
   - scripts/capacity_real.py

2. Entrega BUILDER_UNDERSTANDING_REPORT con:
   - que construirias
   - que NO tocarias
   - endpoints afectados
   - riesgos de seguridad
   - plan de stress
   - si detectas bloqueo: BLOCKED_BY_CONTRACT_CONFLICT, BLOCKED_BY_SECURITY_GAP, BLOCKED_BY_INFRA_CAPACITY o BLOCKED_BY_MISSING_CONTRACT

3. No construyas hasta aprobacion owner.

Si se aprueba build:
- Optimiza solo marketplace reads y runtime config.
- Mantiene auth fuerte para mutaciones y datos sensibles.
- Implementa cache/guardrails con invalidacion correcta.
- Ajusta workers/pool/thread docs y envs con evidencia.
- Ejecuta c100/c200 marketplace y flujo mixto.
- Entrega BUILDER_REPORT, evidence md y test_results json.

Prohibido:
- READY_FOR_REAL_USE.
- Declarar 10,000 simultaneos sin prueba cloud real.
- Mover permisos al frontend.
- Debilitar ordenes/pagos/admin/negocio/creditos/chat/bot.
```

