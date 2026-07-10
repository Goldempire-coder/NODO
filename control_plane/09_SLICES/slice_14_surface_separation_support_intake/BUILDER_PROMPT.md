# BUILDER_PROMPT.md

Antes de construir `slice_14_surface_separation_support_intake`, el builder debe entregar BUILDER_UNDERSTANDING_REPORT y confirmar que entiende:

- Mini App Cliente queda solo para remitentes/clientes.
- Mini App Negocio queda solo para negocios aprobados/asociados.
- Panel Admin Web es desktop/admin, fuera de la Mini App Cliente.
- Bot Registro Negocios crea solicitudes, no negocios activos.
- Backend unico conserva RBAC, audit, storage, ordenes, creditos, soporte y jobs.
- Soporte general/ticket no es disputa.
- Chat operativo no es disputa.
- No se declara READY_FOR_REAL_USE.

