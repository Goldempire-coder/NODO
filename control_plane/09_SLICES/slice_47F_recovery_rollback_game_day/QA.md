# Slice 47F QA

Estado: CONTRACTS_DRAFT_READY_FOR_OWNER_REVIEW

## Pruebas Esperadas

- Post-deploy smoke tiene pasos claros y evidencia.
- Synthetic check detecta fallo de login, soporte, busqueda o creacion de orden
  antes de depender de reporte humano.
- Rollback frontend documentado y ensayable.
- Rollback backend documentado y ensayable.
- Rollback gate usa error rate, latencia y una metrica de negocio, no solo
  `health`.
- Restore aislado valida conteos e invariantes.
- Redis caido tiene runbook y degradacion segura.
- Storage caido no pierde audit ni expone datos.
- Game day no toca produccion.

## Smoke Manual

- Ejecutar post-deploy smoke staging.
- Simular deploy defectuoso en entorno seguro.
- Confirmar que operador puede seguir el runbook sin builder.
- Ejecutar robot cliente en staging con datos de prueba aprobados.
