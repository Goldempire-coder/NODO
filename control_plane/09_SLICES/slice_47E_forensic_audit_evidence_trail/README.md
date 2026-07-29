# Slice 47E - Forensic Audit And Evidence Trail

Estado: CONTRACTS_DRAFT_READY_FOR_OWNER_REVIEW

## Objetivo

Fortalecer la capacidad de reconstruir que paso en un caso sensible sin depender
de memoria, chat externo o capturas sueltas.

## Problema Que Cubre

Cuando un cliente, negocio o auditor pregunta que ocurrio, NODO debe poder
reconstruir el timeline: usuario, negocio, orden, ticket, acciones admin,
evidencia, notificaciones y cambios de estado. La respuesta debe ser factual,
no una conclusion inventada.

## Resultado Esperado

- Matriz de eventos forenses obligatorios.
- Politica de audit append-only.
- Registro selectivo de requests criticos con redaccion fuerte y sin guardar
  payloads completos por defecto.
- Snapshots o puntos de reconstruccion antes de cambios sensibles cuando
  aplique.
- Rutas para abrir evidencia solo con accion explicita.
- Enmascaramiento de datos privados.
- Retencion y acceso por rol.
- Export o reporte futuro definido como fuera del MVP si no se aprueba.

## Dependencias

- 44B evidencia de chat de orden.
- 46B ficha de investigacion.
- 46D playbooks.
- 47A observabilidad.

## No Construir Todavia

- No exportar expedientes completos.
- No descargar evidencia automaticamente.
- No guardar cuerpos privados en timeline general.
- No declarar fraude, culpa o pago valido.
- No permitir borrado de audit logs.
