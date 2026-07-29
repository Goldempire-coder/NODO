# Slice 47B - Operational Alerting Dashboard

Estado: CONTRACTS_DRAFT_READY_FOR_OWNER_REVIEW

## Objetivo

Hacer que el Dashboard avise automaticamente cuando algo operativo importante
pasa o se traba. El owner no debe depender de refrescar pantallas ni revisar
manual cada modulo para saber que hay problemas.

## Problema Que Cubre

NODO ya tiene notificaciones operativas iniciales, pero falta una politica
completa de alertas accionables: soporte sin atender, pagos o creditos trabados,
intake pendiente, jobs fallidos, errores repetidos, storage fallando, Redis/DB
degradado y eventos de riesgo.

Las alertas deben mirar sintomas que el usuario siente: no pudo crear orden,
no ve negocios disponibles, soporte no responde, pago/credito queda trabado o
una pantalla empieza a fallar. CPU, memoria o proveedor caido son causas para
investigar, no la unica razon para despertar al operador.

## Resultado Esperado

- Catalogo de alertas con severidad, dueno y accion.
- Reglas para no crear ruido ni duplicados.
- Alertas agrupadas por modulo: soporte, intake, ordenes, creditos, jobs,
  infraestructura y seguridad.
- Reglas por anomalia y patrones de logs: aumento de errores, latencia p99,
  retries, timeouts, pool agotado, cuota agotada y eventos repetidos.
- Alertas de costo y ruido: Redis, storage, logs, retries y polling fuera del
  comportamiento esperado.
- Separacion entre alerta inmediata y tarea operativa no urgente.
- Cada alerta debe abrir una pantalla accionable.
- Cada alerta debe tener estado: nueva, leida, resuelta o descartada.

## Dependencias

- 47A observabilidad base.
- Admin notifications existentes.
- 20B soporte.
- 46A-46D investigacion admin.

## No Construir Todavia

- No WebSocket si polling/backoff alcanza.
- No push externo ni proveedor nuevo.
- No alertar con cuerpos de mensajes privados.
- No resolver tickets u ordenes automaticamente.
- No crear pagos, creditos o cambios financieros.
