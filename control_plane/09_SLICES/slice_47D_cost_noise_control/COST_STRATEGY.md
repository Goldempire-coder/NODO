# Slice 47D Cost Strategy

Estado: CONTRACTS_DRAFT_READY_FOR_OWNER_REVIEW

## Principio

NODO no baja costos apagando controles importantes. Baja costos eliminando
trabajo inutil, requests repetidos, polling agresivo, storage sin disciplina,
logs ruidosos y reintentos que no tienen salida.

No se migra proveedor sin medicion previa, impacto esperado, rollback y
aprobacion del owner.

## Metricas Norte

El sistema debe poder estimar:

- Costo por usuario activo diario.
- Costo por negocio activo.
- Costo por orden creada.
- Costo por ticket de soporte.
- Costo por hora de Dashboard abierto.
- Costo por dolar generado.
- Costo por flujo fallido o reintentado.

Estas metricas no deben usar datos privados como labels de metricas.

## Orden De Ahorro

1. Medir llamadas, Redis, DB, storage y logs por flujo.
2. Reducir polling y requests duplicados.
3. Agregar backoff, single-flight y request coalescing.
4. Usar cache por capas cuando sea seguro.
5. Ordenar storage: lazy loading, miniaturas, compresion y retencion.
6. Controlar el costo del error: circuit breaker, retry con limite y estado
   terminal inspeccionable.
7. Evaluar proveedores solo con numeros reales.

## Cache Por Capas

Orden recomendado:

1. Memoria local para datos seguros, no privados y de vida corta.
2. Redis para coordinacion, locks, idempotencia y datos efimeros necesarios.
3. DB como fuente canonica.

Reglas:

- No cachear datos sensibles en cliente.
- No usar cache para saltar autorizacion.
- No cachear saldos, permisos o disponibilidad como autoridad final si pueden
  cambiar durante el flujo.
- Cada cache debe tener TTL, invalidacion y evidencia de beneficio.

## Request Coalescing

Si varias partes piden el mismo recurso al mismo tiempo, NODO debe preferir una
sola carga compartida cuando sea seguro.

Ejemplos:

- Una pantalla no debe disparar varias veces el mismo fetch por re-render.
- Varios componentes del Dashboard no deben consultar el mismo contador por
  separado si pueden compartir respuesta.
- Un refresh en curso debe bloquear otro refresh del mismo recurso.

## Storage

Reglas de costo:

- No abrir ni descargar adjuntos automaticamente.
- Cargar imagenes solo cuando el operador o usuario las necesita.
- Usar miniaturas o metadata en listados.
- Comprimir formatos cuando no destruya evidencia necesaria.
- Separar archivo temporal de evidencia auditada.
- No borrar evidencia auditada sin politica aprobada.

## Costo Del Error

Un fallo repetido puede gastar mas que el uso legitimo. Por eso:

- Cada retry debe tener limite.
- Los reintentos deben usar backoff con jitter cuando aplique.
- Errores permanentes deben ir a estado terminal visible.
- Una dependencia rota debe activar corte temporal cuando seguir llamandola
  solo aumenta costo y ruido.
- La accion principal no debe duplicarse por reintentos.

## Alertas De Costo

Las alertas deben cubrir:

- Redis comandos por hora fuera de lo esperado.
- Storage creciendo fuera de lo esperado.
- Endpoint con error rate o retry rate alto.
- Logs aumentando de volumen sin nueva release que lo justifique.
- Dashboard generando requests recurrentes fuera de presupuesto.
- Job con backlog, edad o heartbeat anormal.

## Decisiones Futuras

Quedan fuera de este slice y requieren contrato separado:

- Mover storage a R2.
- Reemplazar Redis por PostgreSQL, KV o Durable Objects.
- Mover endpoints a Workers.
- Cambiar Railway o Supabase.
- Agregar proveedor externo de FinOps u observabilidad.
