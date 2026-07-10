# DO_NOT_INVENT.md

## Superficies

El builder NO puede inventar:

- Admin dentro de Mini App Cliente.
- Registro/verificacion de negocio dentro de Mini App Cliente.
- Autoaprobacion de negocios desde el bot.
- Acceso de negocio sin negocio aprobado y Telegram ID asociado.
- Soporte general que cambie estados de orden.
- Chat operativo que funcione como disputa formal.
- Nuevas superficies o apps sin contrato.
- Origenes CORS compartidos para admin web y mini apps sin contrato.

El builder NO puede inventar:

- Métodos de pago fuera de zelle/usdt_trc20.
- Efectivo, ciudades o puntos de entrega.
- Estados no listados en ENUMS_AND_STATUS_MASTER.
- Claims de garantía, escrow o fondos protegidos.
- Campos de DB no definidos.
- Endpoints no definidos.
- Permisos no definidos.
- Métricas falsas en UI.
- Logos alternos o paletas no aprobadas.
- Pantallas no listadas en SCREEN_CATALOG.
- Flujos por WhatsApp fuera de la app.

Si falta información, debe parar y reportar: BLOCKED_BY_MISSING_CONTRACT.
