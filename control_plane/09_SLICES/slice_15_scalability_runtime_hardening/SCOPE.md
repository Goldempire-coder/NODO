# SCOPE.md

## Incluye

- Ruta/servicio de lectura de marketplace optimizado para alto trafico.
- Autenticacion liviana solo para lecturas no sensibles del marketplace.
- Cache compartido de marketplace con Redis mas cache local L1 cuando aplique.
- Invalidacion de cache al cambiar anuncios, crear orden o materializar expiracion.
- Configuracion segura de workers, thread limit y pool por worker.
- Guardrails para evitar `too many clients already`.
- Stress harness para marketplace c100/c200/c500 progresivo.
- Stress mixto minimo: buscar, detalle, crear orden, instrucciones y reportar pago.
- Reporte de capacidad con evidencia JSON/logs.

## No incluye

- Debilitar auth de crear orden.
- Debilitar auth de payment instructions/report.
- Debilitar auth de negocio, creditos, admin, soporte, chat o bot.
- Cambiar reglas de ordenes, creditos, pagos, anuncios o disputas.
- Comprar infraestructura nueva automaticamente.
- Auto-scaling real sin aprobacion owner.
- Declarar `READY_FOR_REAL_USE`.
- Declarar soporte para 10,000 simultaneos sin prueba cloud real.

## Meta tecnica del slice

Dejar el sistema listo para subir por etapas:

```txt
100 simultaneos
200
500
1000
2500
5000
10000
```

El builder solo debe intentar las etapas permitidas por la infraestructura disponible. Si la infraestructura local/cloud no alcanza, debe reportar `BLOCKED_BY_INFRA_CAPACITY`.

