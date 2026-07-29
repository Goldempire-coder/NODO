# Slice 47C QA

Estado: CONTRACTS_DRAFT_READY_FOR_OWNER_REVIEW

## Pruebas Esperadas

- Ejecutar el mismo job dos veces no duplica efectos.
- Un fallo temporal reintenta con limite.
- Reintentos usan backoff con jitter cuando aplica.
- Una dependencia repetidamente fallida activa corte temporal o estado visible
  sin generar tormenta de requests.
- Un fallo permanente queda visible.
- Un job sin heartbeat o demasiado viejo queda visible.
- Backlog alto queda medido sin tumbar la API.
- Reprocesar un job fallido conserva idempotencia.
- Expirar orden no rompe reservas, soporte ni auditoria.
- Notificacion fallida no bloquea la accion principal.
- Reconciliacion reporta diferencias sin modificarlas automaticamente.

## Smoke Manual

- Simular notificacion fallida.
- Simular job vencido.
- Revisar que Admin pueda ver el problema sin tocar DB manualmente.
