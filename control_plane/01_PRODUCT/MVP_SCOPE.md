# MVP_SCOPE.md

El MVP de NODO se construye como producto listo para uso masivo controlado, no como demo. El alcance inicial debe soportar 200 negocios, 10,000 clientes y 2,000 ordenes activas/concurrentes.

## Incluido

- Telegram Bot como entrada/notificador.
- Telegram Mini App como interfaz principal.
- Remitentes con Telegram auth.
- Negocios registrados con revision manual completada.
- Admin panel funcional completo.
- Anuncios Zelle -> pago movil Venezuela.
- Anuncios USDT -> pago movil Venezuela.
- Ordenes persistentes con snapshot de tasa, limites e instrucciones.
- Reporte de pago con evidencia.
- Confirmacion de pago por negocio.
- Entrega por pago movil.
- Confirmacion de recibido por remitente.
- Chat por orden.
- Rating.
- Disputas simples con evidencia.
- Reportes de evasion.
- Creditos publicitarios para negocios.
- Stripe para compra automatica de creditos.
- Zelle/USDT manual para compra de creditos con aprobacion admin.
- Fundadores 30 dias dentro de limites de riesgo.
- Referidos.
- Audit logs.
- Notificaciones.
- Jobs de expiracion/recordatorio.
- Rate limits, idempotencia, locks y monitoreo.

## Excluido

- Efectivo.
- Ciudades o filtro de cercania.
- Entrega presencial.
- Escrow.
- Custodia de fondos.
- Procesar pagos de remesas.
- Garantizar entrega o solvencia.
- Cash App / Venmo / Wise.
- Validacion automatica on-chain de USDT por red.
- Wallet interna para clientes.
- Smart contracts.
- KYC automatico.
- IA.
- App nativa iOS/Android.
