# ACCEPTANCE_CRITERIA - slice_31B_backup_restore_contracts_and_sops

El slice queda aceptable para owner review solo si:

- Todos los componentes Tier 0/Tier 1 tienen backup status explicito.
- Todos los componentes Tier 0/Tier 1 tienen restore status explicito.
- Todo `UNKNOWN` queda marcado.
- Todo `PROVIDER_ACCESS_REQUIRED` queda marcado.
- Todo owner no asignado queda marcado como `OWNERSHIP NOT DEFINED -- RELEASE RISK`.
- No hay afirmaciones de restore probado sin evidencia.
- No hay comandos destructivos nuevos.
- No se ejecutaron backups/restores/exportaciones/deploys.
- El release productivo sigue bloqueado mientras no existan restore drills validados.

## Estado esperado

`READY_FOR_OWNER_REVIEW`
