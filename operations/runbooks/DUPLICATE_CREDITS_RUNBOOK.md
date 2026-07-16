# RUNBOOK: Duplicate credits

Estado de validacion: NOT VALIDATED

## SINTOMA

Un negocio tiene creditos duplicados, tx hash reutilizado o ledger duplicado.

## SEVERIDAD INICIAL

SEV-1.

## PRIMEROS CINCO MINUTOS

1. Congelar acciones manuales de creditos.
2. Preservar purchase IDs, ledger IDs y request IDs.
3. Revisar si hay `ONCHAIN_TX_ALREADY_USED`.

## DIAGNOSTICO

- Verificar `credit_purchases`.
- Verificar `credits_ledger` por `related_credit_purchase_id`.
- Verificar onchain tx log.
- Revisar audit events.

## MITIGACION

- Suspender temporalmente compra de creditos si hay riesgo activo.
- No borrar ledger. Crear accion correctiva auditada en slice/operacion aprobada.

## PROHIBICIONES

- No editar saldos manualmente en DB.
- No borrar filas para cuadrar.
