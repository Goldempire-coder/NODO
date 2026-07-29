# Slice 47F - Recovery, Rollback And Game Day

Estado: CONTRACTS_DRAFT_READY_FOR_OWNER_REVIEW

## Objetivo

Probar que NODO puede recuperarse cuando algo sale mal: deploy defectuoso,
DB/Redis/storage fallando, migracion incompatible, backup requerido o funcion
peligrosa que debe apagarse.

## Problema Que Cubre

Tener SOPs no basta. Deben ensayarse. El sistema debe demostrar rollback,
restore, modo seguro y pasos claros para reducir dano sin depender del builder.

## Resultado Esperado

- Mapa de rollback por frontend, backend, DB, Redis, storage y bots.
- Smoke de post-deploy definido.
- Monitoreo sintetico: robot cliente/negocio/admin que pruebe caminos criticos
  en staging y avise antes de que un usuario real reporte.
- Canary o despliegue gradual cuando el entorno lo permita, con gatillos de
  rollback por error rate, latencia y metrica de negocio.
- Game days seguros en staging.
- Validacion de backup/restore en entorno aislado.
- Runbooks con dueno, gatillos y evidencia.
- Lista de kill switches necesarios.

## Dependencias

- 31B backup/restore contracts.
- SOPs de deploy, rollback y post-deploy.
- 47A observabilidad.
- 47B alertas.
- 47C jobs.

## No Construir Todavia

- No ejecutar restore real sin aprobacion explicita.
- No borrar datos.
- No tocar produccion.
- No rotar secretos reales sin runbook aprobado.
- No hacer pruebas destructivas fuera de staging.
