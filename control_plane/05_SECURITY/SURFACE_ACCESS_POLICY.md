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
- Usuario `restricted`, `blocked` o `dormant` no puede entrar a superficies operativas salvo contrato futuro explicito; `blocked` tampoco puede refrescar/operar.
- La Mini App Negocio requiere usuario autenticado `active`, rol `business_owner`, negocio `approved`, `business_access_links.status = active`, y Telegram initData que corresponda al usuario vinculado.
- La Mini App Negocio requiere PIN operativo antes de ejecutar mutaciones sensibles. El PIN se configura por `business_access_link`, nunca se guarda en claro, desbloquea una sesion corta y puede bloquearse manualmente desde Perfil.
- El bot no autoriza acceso; solo captura datos, notifica y abre la puerta. Admin Web manda y backend aplica.
- Suspender/bloquear negocio y suspender/bloquear acceso Telegram/persona son controles separados.
- La Mini App Negocio puede gestionar sus metodos propios permitidos por backend, como Zelle/titular, solo despues de desbloquear PIN. El backend valida ownership, estado, capacidad y auditoria; el usuario no puede escribir IDs manuales para saltarse controles.
- El Panel Admin Web requiere rol `admin`, `super_admin` o `support`; `support` es read-only salvo contrato explicito.
- Admin Web 20A puede buscar/ver usuarios y access links; mutaciones de usuario/access link requieren backend RBAC, reason, idempotencia y audit.
- Soporte 20B se autoriza por superficie y recurso:
  - Cliente solo `client_general` y `client_order` propios.
  - Negocio solo `business_general`, `business_order`, `business_ad` y `business_credit` de su negocio.
  - Admin Web opera cola de soporte segun RBAC; `support` puede responder/asignar/escalar/resolver/cerrar tickets pero no ejecutar mutaciones criticas de orden, creditos, anuncios, disputas o accesos.
- Staff 20C dentro de Admin Web requiere `users.status = active`, `staff_profiles.status = active`, rol base compatible y permisos activos por accion/scope.
- La superficie `admin_web` debe pedir capacidades staff al backend; no puede inferirlas solo desde `users.role`.
- El Bot Registro Negocios no crea negocio activo, no publica anuncios y no da acceso al marketplace de negocios.
- El frontend puede ocultar UI por superficie, pero nunca es autoridad de permisos.
- Todo acceso denegado por superficie debe responder error seguro `SURFACE_ACCESS_DENIED` y auditar `surface_access_denied` cuando aplique.
- `GET /api/v1/surface/session` es el gate canonico de Mini App Negocio; `/api/v1/businesses/me` no reemplaza la validacion de superficie.
- `GET /api/v1/surface/session` debe devolver estado de PIN para Mini App Negocio: requerido, configurado, desbloqueado y bloqueo temporal si aplica. El frontend puede mostrar la pantalla de PIN, pero el backend sigue bloqueando acciones sensibles con `BUSINESS_PIN_*`.

## CORS/origenes

- Cada superficie debe tener origen permitido separado en runtime.
- Admin web no debe compartir origen publico con la Mini App Cliente.
- Bot webhooks deben validar secreto/firma de webhook y no depender de CORS.

## Datos sensibles

- Ninguna superficie expone `storage_path`, tokens, secretos, datos bancarios completos ni evidencia privada completa sin permiso y signed URL corta.
- Los documentos de intake y adjuntos de soporte usan storage privado.
