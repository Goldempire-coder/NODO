# Slice 47D - Cost And Noise Control

Estado: CONTRACTS_DRAFT_READY_FOR_OWNER_REVIEW

## Objetivo

Bajar costo operativo y ruido del sistema sin perder visibilidad. NODO debe ser
liviano: menos polling inutil, menos Redis quemado, menos storage basura, menos
logs gigantes y menos llamadas repetidas.

## Problema Que Cubre

Staging ya mostro que Redis puede agotarse por polling y controles repetidos.
Un dashboard operativo barato necesita saber cuando refrescar, cuando pausar y
cuando agrupar eventos.

La estrategia oficial esta en `COST_STRATEGY.md`: medir costo por flujo,
eliminar trabajo inutil y evaluar proveedores solo con numeros reales.

## Resultado Esperado

- Mapa de consumo por frontend, backend, Redis, DB, storage y logs.
- Costo estimado por usuario activo, negocio activo, orden, ticket de soporte,
  hora de Dashboard y dolar generado.
- Politica de polling por pantalla.
- Pausa en pestana oculta.
- Single-flight para evitar requests solapados.
- Request coalescing para compartir cargas iguales en curso.
- Backoff en errores.
- Cache por capas: memoria local segura, Redis para coordinacion y DB como
  fuente canonica.
- Lazy loading, miniaturas y compresion para imagenes/adjuntos cuando aplique.
- Presupuesto de senales: que se mide siempre, que se muestrea y que se evita
  por costo o privacidad.
- Control de cardinalidad para no crear metricas imposibles de pagar o operar.
- Retencion y limpieza segura de datos temporales.

## Dependencias

- 47A observabilidad base.
- 47B alertas.
- Admin Web, Cliente y Negocio.
- Upstash/Redis, storage y Cloudflare Pages actuales.

## No Construir Todavia

- No migrar de proveedor en este slice.
- No eliminar Redis sin contrato separado.
- No borrar evidencia o auditoria.
- No reducir seguridad por ahorrar costo.
- No cachear datos sensibles en cliente.
