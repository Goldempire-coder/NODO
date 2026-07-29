# Slice 47E QA

Estado: CONTRACTS_DRAFT_READY_FOR_OWNER_REVIEW

## Pruebas Esperadas

- Accion admin sensible produce audit.
- Cambio de estado de orden/ticket produce evento reconstruible.
- Apertura de evidencia privada queda auditada.
- Timeline no contiene cuerpos privados.
- Metadata no contiene storage_path, file_asset_id publico, tokens, wallets o bancos completos.
- Actor, recurso, fecha, version y request quedan enlazados.
- Acciones sensibles tienen evidencia suficiente para reconstruir antes y
  despues sin exponer datos privados.
- La evidencia forense no depende de mensajes de chat ni capturas manuales.

## Smoke Manual

- Abrir caso 46B.
- Abrir evidencia 44B.
- Revisar audit de apertura y timeline sin datos privados.
