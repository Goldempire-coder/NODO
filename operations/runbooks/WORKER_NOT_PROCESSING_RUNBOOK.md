# RUNBOOK: Worker not processing

Estado de validacion: NOT VALIDATED

## SINTOMA

Ordenes no expiran, creditos on-chain no se verifican, jobs se acumulan.

## SEVERIDAD INICIAL

SEV-2; SEV-1 si afecta creditos.

## DIAGNOSTICO

- Revisar `GET /api/v1/admin/jobs/runs`.
- Ejecutar dry-run de expire/escalate:
  ```powershell
  # requiere JWT admin
  # POST /api/v1/admin/jobs/expire-and-escalate-orders/dry-run
  ```
- Revisar watcher Base USDC logs/result si existe runner.

## GAPS

No hay scheduler/runner operativo versionado para `verify_base_usdc_credit_purchases_worker`.

## PROHIBICIONES

- No ejecutar job real duplicado sin lock.
