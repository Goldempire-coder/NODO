# DO_NOT_BUILD.md

Este slice empieza como contrato y mapeo. No implementar codigo hasta que Owner apruebe el plan de Builder.

## No tocar

- Pagos.
- Base USDC.
- Zelle.
- Creditos.
- Soporte.
- Intake.
- Reputacion.
- Bots Telegram.
- Produccion.
- Infraestructura.
- Migraciones ejecutadas en staging.
- Reset de base de datos.
- Backfills inventados.

## No mezclar

No mezclar 45B con:

- multiples ordenes por anuncio;
- cambios de pricing;
- ranking por reputacion;
- legal agreements;
- optimizacion de Redis;
- soporte/chat.

## No afirmar

No afirmar:

- `READY_FOR_REAL_USE`;
- que staging esta listo;
- que el limite diario quedo probado en real;
- que clientes reales pueden entrar;
- que el negocio tiene fondos reales.

## Regla de seguridad

Si el sistema no puede calcular cupo diario con evidencia, debe fallar cerrado para nuevas ordenes.

