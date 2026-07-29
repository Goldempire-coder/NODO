# Slice 47B QA

Estado: CONTRACTS_DRAFT_READY_FOR_OWNER_REVIEW

## Pruebas Esperadas

- Ticket nuevo produce alerta y abre el ticket correcto.
- Intake nuevo produce alerta y abre intake correcto.
- Job fallido produce alerta sin duplicarse sin limite.
- Error repetido produce alerta agregada, no una alerta por request.
- Subida de error rate o latencia p99 produce alerta accionable con ventana y
  umbral definidos.
- Desviacion de costo o volumen produce alerta agregada, no spam por request.
- Patron de log critico produce una alerta agrupada sin duplicar ruido.
- Resolver o descartar actualiza contador.
- Alertas no contienen cuerpos privados ni secretos.
- Polling no corre agresivo en pantanas ocultas.

## Smoke Manual

- Estar en Negocios y recibir soporte nuevo.
- Estar en Dashboard y recibir intake nuevo.
- Resolver alerta y confirmar que desaparece.
