# SURFACE_ACCESS_POLICY.md

## Objetivo

Definir acceso por superficie sin duplicar RBAC. El backend unico sigue siendo la autoridad de auth, permisos, ownership y estados.

## Superficies canonicas

- `client_mini_app`: remitentes/clientes.
- `business_mini_app`: negocios aprobados con `business_access_links.status = active` asociado a usuario/Telegram validado.
- `admin_web`: owner/admin/super_admin/support en web desktop.
- `business_intake_bot`: captacion de negocios referidos/interesados.

## Reglas

- La Mini App Cliente no puede mostrar ni ejecutar flujos de negocio/admin.
- La Mini App Negocio requiere usuario autenticado `active`, rol `business_owner`, negocio `approved`, `business_access_links.status = active`, y Telegram initData que corresponda al usuario vinculado.
- El bot no autoriza acceso; solo captura datos, notifica y abre la puerta. Admin Web manda y backend aplica.
- Suspender/bloquear negocio y suspender/bloquear acceso Telegram/persona son controles separados.
- La Mini App Negocio puede leer metodos de pago propios aprobados mediante selector controlado por backend; no puede crear, editar, aprobar, borrar ni escribir IDs manuales de metodos.
- El Panel Admin Web requiere rol `admin`, `super_admin` o `support`; `support` es read-only salvo contrato explicito.
- El Bot Registro Negocios no crea negocio activo, no publica anuncios y no da acceso al marketplace de negocios.
- El frontend puede ocultar UI por superficie, pero nunca es autoridad de permisos.
- Todo acceso denegado por superficie debe responder error seguro `SURFACE_ACCESS_DENIED` y auditar `surface_access_denied` cuando aplique.
- `GET /api/v1/surface/session` es el gate canonico de Mini App Negocio; `/api/v1/businesses/me` no reemplaza la validacion de superficie.

## CORS/origenes

- Cada superficie debe tener origen permitido separado en runtime.
- Admin web no debe compartir origen publico con la Mini App Cliente.
- Bot webhooks deben validar secreto/firma de webhook y no depender de CORS.

## Datos sensibles

- Ninguna superficie expone `storage_path`, tokens, secretos, datos bancarios completos ni evidencia privada completa sin permiso y signed URL corta.
- Los documentos de intake y adjuntos de soporte usan storage privado.
