# CONCURRENCY_TESTS.md

Pruebas obligatorias para validar el objetivo de 2,000 ordenes activas/concurrentes.

## Objetivo

Validar que NODO puede operar con:

- 200 negocios.
- 10,000 usuarios.
- 2,000 ordenes activas/concurrentes.
- busqueda marketplace concurrente.
- reportes de pago simultaneos.
- chat por orden.
- webhooks Stripe repetidos o retrasados.

## Escenarios minimos

1. 10,000 usuarios autenticados en pool de prueba.
2. 200 negocios aprobados con anuncios activos.
3. 2,000 creaciones de orden durante ventana corta con idempotency keys.
4. 2,000 reportes de pago con adjunto simulado.
5. 1,000 confirmaciones de negocio.
6. 1,000 entregas.
7. 500 chats activos con mensajes alternados.
8. 200 disputas abiertas y resueltas.
9. 500 compras de credito Stripe simuladas con webhook duplicado.
10. 200 compras manuales de credito revisadas por admin.

## Metricas requeridas

- Error rate menor a 1% en endpoints no dependientes de terceros.
- Cero doble acreditacion.
- Cero doble orden por misma idempotency key.
- Cero balance negativo.
- Cero transicion invalida aceptada.
- p95 razonable definido por entorno antes de deploy.

## Evidencia requerida

El builder debe entregar comando usado, dataset usado, resultados crudos, errores encontrados, limites del entorno y cambios realizados por hallazgos.

Sin esta evidencia, el producto no puede pasar a READY_FOR_OWNER_REVIEW.
