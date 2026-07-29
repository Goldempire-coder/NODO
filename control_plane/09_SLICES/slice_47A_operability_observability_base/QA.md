# Slice 47A QA

Estado: CONTRACTS_DRAFT_READY_FOR_OWNER_REVIEW

## Pruebas Esperadas

- Logs no contienen tokens, wallets, bancos, storage paths ni cuerpos privados.
- Requests criticos tienen `request_id` o equivalente.
- Eventos de cliente, negocio y admin incluyen superficie y version.
- Errores de API tienen codigo seguro y no exponen stack trace.
- Breadcrumbs de UI no contienen payload sensible.
- Metricas por flujo permiten distinguir fallo de cliente, negocio, admin,
  backend, Telegram, DB, Redis, storage o red.
- Metricas de costo por flujo usan labels acotados y no incluyen usuario,
  email, telefono, request_id, wallets, bancos o texto libre.
- Latencia se registra con percentiles o buckets utiles, no solo promedio.
- Health, ready y version siguen disponibles.
- Ready verifica dependencias criticas y reporta degradacion sin filtrar
  secretos.

## Smoke Manual

- Crear ticket soporte desde cliente y negocio.
- Abrir ficha admin y verificar rastro sin leer cuerpos privados automaticamente.
- Forzar error controlado y confirmar que se puede ubicar la superficie.
- Medir un flujo lento y confirmar que la evidencia indica donde se trabo.

## Criterio De Paso

El builder debe entregar mapa, brechas, pruebas y cambios propuestos. Si se
implementa despues, el reporte debe incluir evidencia cruda de comandos.
