# Slice 47D Scope

Estado: CONTRACTS_DRAFT_READY_FOR_OWNER_REVIEW

## Dentro Del Alcance

- Medir polling y requests repetidos.
- Definir presupuesto por superficie.
- Definir costo por usuario activo, negocio activo, orden, soporte, Dashboard
  y dolar generado.
- Definir backoff y pausa por visibilidad de pestana.
- Definir single-flight y request coalescing por recurso.
- Definir jerarquia de cache segura: memoria local, Redis y DB.
- Definir retencion de adjuntos temporales, logs y notificaciones.
- Definir lazy loading, miniaturas y compresion para imagenes/adjuntos.
- Definir presupuesto de logs, metricas y polling por flujo.
- Definir reglas contra cardinalidad alta: no user_id, email, request_id o
  texto libre como etiquetas de metricas.
- Proponer optimizaciones sin cambiar reglas de negocio.

## Fuera Del Alcance

- Migracion de Railway, Cloudflare, Supabase o Upstash.
- Sustituir Redis o DB sin contrato separado.
- Cambio de base de datos.
- Eliminacion de audit logs.
- Cambio de lifecycle financiero.
- Cambios visuales grandes.

## Regla AFOS

Ahorrar costo no puede ocultar fallas criticas ni borrar evidencia necesaria.
