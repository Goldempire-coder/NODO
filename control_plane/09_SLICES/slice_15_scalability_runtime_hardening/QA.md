# QA.md

## Tests obligatorios

- Backend pytest completo.
- Ruff.
- Compileall.
- Frontend build.
- Scan frontend: sin secretos, `storage_path`, `account_value` ni claims prohibidos.

## Stress obligatorio

Minimo:

```txt
marketplace c100
marketplace c200
flujo mixto c50/c100
```

Si pasa:

```txt
marketplace c500
marketplace c1000
```

No intentar c500/c1000 si c100/c200 falla por timeout, DB saturation o error rate.

## Metricas a reportar

- total requests.
- total errors.
- error rate.
- p50.
- p95.
- p99.
- throughput.
- DB connection failures.
- Redis failures.
- invariant violations.
- logs con `too many clients`, `ReadTimeout`, `ReadError`, `OperationalError`, `RATE_LIMITED`, `500`.

## Criterios minimos para pasar build local

- Error rate `0.0` en c100 y c200 marketplace.
- Sin `too many clients already`.
- Sin invariantes rotas.
- p95 mejora contra el reporte 02 o se documenta bloqueo concreto.

## Criterio para hablar de 10,000 clientes

No se puede declarar soporte 10,000 simultaneos con pruebas locales.

Para declarar capacidad 10,000 se requiere:

- entorno cloud real.
- Redis real.
- Supabase real con limite conocido.
- configuracion workers/pool documentada.
- monitoreo activo.
- stress externo gradual hasta 10,000.
- reporte owner.

