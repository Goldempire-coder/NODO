# Slice 52B - Admin Credit Ledger And Blockchain Reconciliation

Estado: `IMPLEMENTED_READY_FOR_VALIDATOR_REVIEW`

## Objetivo

Permitir que Admin investigue una compra de creditos y compare, bajo demanda, la
compra, la evidencia on-chain segura y el movimiento de ledger relacionado.

52B es una proyeccion de lectura y UI Admin. No acredita creditos, no cambia
wallets, no mueve fondos y no modifica watcher, verificador ni reglas financieras.

## Decisiones Owner

- La unica ruta Admin de rechazo es
  `POST /api/v1/admin/credit-purchases/{id}/reject`.
- La ruta cubre compras manuales `pending_manual_review` y compras
  `base_usdc_onchain` en `under_review`.
- No se crea `/api/v1/admin/credit-purchases/{id}/onchain-reject`.
- El listado usa una proyeccion liviana y paginada.
- El detalle carga reconciliacion y ledger solo por accion explicita.
- Hashes y direcciones se muestran enmascarados por defecto.
- Ver valores completos queda fuera de 52B y requeriria razon y auditoria.

## Autoridad contractual

`control_plane/06_API_CONTRACTS/CREDITS_API.md` es el contrato canonico vigente.
Las referencias a `onchain-reject` en el slice historico 19 y en la pantalla
documental A-05 quedan supersedidas por esta decision y no autorizan crear esa
ruta.

## Fuera de alcance

- Contrato Solidity o smart contract.
- Wallet real, private keys, fondos o RPC config.
- Cambios de acreditacion, precios, paquetes, referrals o ledger financiero.
- Cambios en Cliente, Negocio, P2P, anuncios, ordenes o pagos.
- Migraciones, deploy, staging y produccion.

## Readiness

Este contrato habilita un slice posterior de implementacion local. No declara
`READY_FOR_REAL_USE` ni `READY_FOR_PRODUCTION`.
