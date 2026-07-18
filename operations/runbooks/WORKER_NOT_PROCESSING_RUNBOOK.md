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
- Revisar watcher Base USDC:
  - `base_usdc_credit_watcher_finished`
  - `base_usdc_credit_watcher_failed`
  - env `ONCHAIN_CREDIT_WATCHER_ENABLED`
  - env `BASE_RPC_URL`
  - env `NODO_CREDIT_RECEIVING_WALLET_BASE`
  - compras `pending_payment` o `pending_onchain_confirmation` con `tx_hash`.

## GAPS

- El scheduler Base USDC existe dentro del API runtime.
- Falta prueba provider/staging con una transaccion controlada.
- Falta alerta real conectada a `base_usdc_credit_watcher_failed` o backlog/edad de compras pendientes.

## PROHIBICIONES

- No ejecutar job real duplicado sin lock.
