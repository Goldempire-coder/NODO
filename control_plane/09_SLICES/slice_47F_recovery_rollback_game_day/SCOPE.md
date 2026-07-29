# Slice 47F Scope

Estado: CONTRACTS_DRAFT_READY_FOR_OWNER_REVIEW

## Dentro Del Alcance

- Revisar SOPs y runbooks actuales.
- Definir escenarios de recuperacion.
- Definir pruebas staging no destructivas.
- Definir synthetic checks de cliente, negocio y admin.
- Definir canary/rollback gates cuando aplique.
- Definir evidencia requerida para rollback/restore.
- Definir gaps de kill switch y modo seguro.

## Fuera Del Alcance

- Restore real sin aprobacion.
- Produccion.
- Rotacion real de secretos.
- Borrado de datos.
- Migraciones nuevas sin contrato.
- Canary real si la infraestructura actual no lo soporta sin contrato.

## Regla AFOS

Un backup no probado no cuenta. Un rollback no ensayado no cuenta.
