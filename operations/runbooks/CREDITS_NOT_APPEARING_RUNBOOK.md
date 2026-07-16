# RUNBOOK: Credits do not appear

Estado de validacion: NOT VALIDATED

## SINTOMA

Negocio pago Base USDC o envio hash, pero creditos no aparecen.

## SEVERIDAD INICIAL

SEV-2; SEV-1 si muchos negocios o monto alto.

## DIAGNOSTICO

1. Revisar compra en Admin Web.
2. Revisar status.
3. Revisar tx hash masked y audit.
4. Revisar que `BASE_RPC_URL` y wallet destino esten configurados.
5. Revisar watcher `verify_base_usdc_credit_purchases`.

## MITIGACION

- Si pago esta bajo confirmaciones: esperar confirmaciones.
- Si red/token/wallet incorrectos: marcar under_review/reject segun contrato.
- Si watcher caido: ejecutar recuperacion cuando exista scheduler/run command documentado.

## PROHIBICIONES

- No acreditar manualmente sin audit y reason.
- No aceptar hashes de otra red.
