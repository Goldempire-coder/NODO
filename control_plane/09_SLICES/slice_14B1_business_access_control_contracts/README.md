# slice_14B1_business_access_control_contracts

Contrato para cerrar el acceso gobernado de Mini App Negocio antes de construir cambios de producto.

Estado objetivo:
- `business_access_links` es el vinculo canonico usuario/Telegram/negocio.
- `GET /api/v1/surface/session` es el gate canonico de `business_mini_app`.
- Bot no autoriza.
- Admin/backend deciden y aplican.
- Mini App Negocio obedece capabilities y access_state.

Este slice contractual no construye backend, frontend, migraciones ni deploy.
