# BUSINESS_MINI_APP_SURFACE.md

## Owner

Mini App Negocio.

## Incluye

- Login Telegram.
- Dashboard negocio.
- Creditos.
- Crear/gestionar anuncios.
- Selector visual de metodos de pago propios aprobados para crear anuncios.
- Metodos de pago solo lectura o placeholder gobernado en 14B.
- Ordenes entrantes.
- Confirmar pago recibido.
- Rechazar reporte de pago.
- Marcar entregado.
- Chat por orden.
- Soporte con NODO.
- Perfil negocio.
- Historial.

## Acceso

Solo `business_owner` activo con negocio aprobado y `business_access_links.status = active` asociado al Telegram ID validado.

Gate canonico:

- `GET /api/v1/surface/session`
- Header `X-NODO-Surface: business_mini_app`

`GET /api/v1/businesses/me` puede hidratar datos de negocio, pero no reemplaza el gate de superficie.

Estados visibles:

- `no_business_link`: mostrar "Sin negocio asociado".
- `business_not_approved`: mostrar "Negocio no aprobado".
- `business_suspended`: mostrar estado read-only/historial solo si capabilities backend lo permiten.
- `business_blocked`: mostrar cuenta bloqueada/contactar soporte; no operar.
- `user_not_active`: denegar acceso.
- `link_suspended`: mostrar acceso suspendido/contactar NODO.
- `link_revoked`: mostrar acceso no vigente.
- `link_blocked`: mostrar acceso bloqueado.
- `allowed`: entrar al espacio negocio con capabilities de backend.

## No permite

- Autoaprobarse.
- Saltarse verificacion.
- Ver otros negocios.
- Ver admin.
- Resolver disputas como admin.
- Crear, editar, aprobar, deshabilitar o borrar metodos de pago en 14B.
- Escribir manualmente IDs de metodos de pago para publicar anuncios.
