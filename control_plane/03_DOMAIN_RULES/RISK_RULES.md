# RISK_RULES.md

Negocio nuevo:
- min_order_amount_usd = 20
- max_order_amount_usd = 100
- daily_limit_usd = 1000
- active_order_limit = 1

Negocio en crecimiento:
- min_order_amount_usd = 100
- max_order_amount_usd = 500
- daily_limit_usd = 5000
- active_order_limit asignado por admin/backend segun historial.

Negocio avanzado:
- min_order_amount_usd = 500
- max_order_amount_usd = 2000
- daily_limit_usd = 10000
- requiere criterios duros: historial exitoso, bajo dispute rate, verificacion reforzada y aprobacion admin.

Cliente nuevo:
- max_order_amount_usd = 100
- active_order_limit = 1
- expired_orders_daily_limit = 3

Pausa automática:
- 3 reportes abiertos en 24h pausa anuncios y alerta admin.
