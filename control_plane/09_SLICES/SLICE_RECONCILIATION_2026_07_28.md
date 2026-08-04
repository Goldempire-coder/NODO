# Slice Reconciliation - 2026-07-28

Estado: READY_FOR_OWNER_REVIEW

## Alcance

Reconciliacion documental y validacion de staging antes de mover pantallas del
Dashboard o Mini Apps. No cambia codigo runtime, UI, reglas de negocio,
migraciones ni datos.

## Evidencia de staging

- Branch: `codex/intake-admin-review-v2`
- Commit desplegado: `03f44935d4ec0885d289337ba99aa33426882972`
- Backend version: `staging-admin-investigation-46c-03f4493`
- Backend `/health`: OK
- Backend `/ready`: OK, database y Redis listos
- Web staging `/business/`: HTTP 200
- Plan de migraciones staging: `pending=[]`
- Migracion `0035_business_available_capacity_matching.up.sql`: applied
- Migracion `0036_business_daily_limit_query_indexes.up.sql`: applied
- Schema validation staging: 40 tablas, 217 indices, Redis ping true, sin failures

## Slices reconciliados

| Slice | Estado reconciliado | Evidencia | Pendiente |
| --- | --- | --- | --- |
| 45A capacity matching | Staging con migracion 0035 aplicada | plan de migraciones sin pendientes | smoke funcional desde Cliente/Negocio/Admin |
| 45B daily limit governance | Staging con 0035/0036 aplicadas | backend desplegado en commit 03f4493 | smoke funcional del limite diario |
| 45C daily limit query indexes | STAGING_APPLIED_PENDING_EXPLAIN_PROFILE | migracion 0036 aplicada | `EXPLAIN` con volumen representativo |
| 46A operational search | STAGING_DEPLOYED_PENDING_OWNER_SMOKE | commit `7ef4da9`, endpoint/UI incluidos en staging actual | prueba autenticada desde Admin Web |
| 46B case file | STAGING_DEPLOYED_PENDING_OWNER_SMOKE | commit `3196d35`, endpoint protegido responde auth gate | prueba autenticada desde Admin Web |
| 46C advanced filters | STAGING_DEPLOYED_PENDING_OWNER_SMOKE | commit `03f4493`, endpoint protegido responde auth gate | prueba autenticada desde Admin Web |
| 46D support playbooks and repair queue | CONTRACTS_READY_PENDING_OWNER_REVIEW | slice documental creado, sin runtime | inspeccion Builder report-first antes de reparar Dashboard |
| 47A observability base | CONTRACTS_DRAFT_READY_FOR_OWNER_REVIEW | slice documental creado | inspeccion Builder report-first |
| 47B operational alerting | CONTRACTS_DRAFT_READY_FOR_OWNER_REVIEW | slice documental creado | inspeccion Builder report-first |
| 47C jobs/retries/reconciliation | CONTRACTS_DRAFT_READY_FOR_OWNER_REVIEW | slice documental creado | inspeccion Builder report-first |
| 47D cost/noise control | CONTRACTS_DRAFT_READY_FOR_OWNER_REVIEW | slice documental creado | inspeccion Builder report-first |
| 47E forensic audit/evidence trail | CONTRACTS_DRAFT_READY_FOR_OWNER_REVIEW | slice documental creado | inspeccion Builder report-first |
| 47F recovery/rollback/game day | CONTRACTS_DRAFT_READY_FOR_OWNER_REVIEW | slice documental creado | inspeccion Builder report-first |
| 47G preproduction security launch gate | CONTRACTS_DRAFT_READY_FOR_OWNER_REVIEW | slice documental creado | inspeccion Builder report-first antes de cualquier autorizacion de produccion |

## Lista de reparaciones antes de tocar Dashboard

1. Ejecutar inspeccion 46D para convertir casos operativos en reparaciones concretas.
2. Ejecutar smoke autenticado en Admin Web para 46A, 46B y 46C.
3. Probar que 46C encuentra candidatos con pistas reales: cliente, negocio, monto y fecha.
4. Probar que 46B abre la ficha correcta desde un resultado de 46A/46C.
5. Probar que 44B abre evidencia de chat solo por accion explicita.
6. Probar flujo 45A/45B desde Cliente/Negocio: monto solicitado, capacidad disponible y limite diario.
7. Ejecutar `EXPLAIN` de 45C antes de afirmar que el indice cubre volumen historico.
8. Registrar bugs concretos de Dashboard solo despues de esos smokes.
9. Ejecutar 47A-47F uno por uno, empezando por 47A, sin mezclar operabilidad,
   alertas, jobs, costo, auditoria forense y recuperacion en un solo paquete.
10. Ejecutar 47G como gate final antes de produccion: rotacion de secretos,
    Telegram Web, Supabase/RLS, storage, IDOR, headers, dependencias y smoke
    autenticado.

## No autorizado por este documento

- No declara `READY_FOR_REAL_USE`.
- No autoriza produccion.
- No reemplaza QA manual del owner.
- No autoriza cambios de UI del Dashboard.
- No ejecuta migraciones ni borra datos.
