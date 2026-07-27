# Slice 46A Security Contract

## Principio

La lupa ayuda a ubicar el lugar correcto del dashboard, pero no sustituye las
pantallas autorizadas ni convierte soporte en un exportador de datos.

## Datos Permitidos

- IDs internos necesarios para abrir pantallas admin.
- Codigo publico de orden.
- Estado operativo.
- Nombre de negocio.
- Telefono o Telegram solo en forma enmascarada dentro de resultados.
- Codigo de referencia cuando ya es un dato admin/intake.
- Vinculos entre cliente, negocio, orden y ticket.

## Datos Prohibidos

- Cuerpo de mensajes de soporte o chat.
- Storage paths.
- Signed URLs.
- `file_asset_id`.
- Tokens, JWT, bot tokens, secretos o headers de proveedor.
- Datos bancarios completos, wallets privadas o instrucciones de pago completas.
- Evidencia privada como comprobantes o documentos.

## Auditoria

Evento obligatorio:

- `admin_operational_search_performed`

Metadata permitida:

- hash corto de la busqueda normalizada;
- largo de la busqueda;
- limite solicitado;
- conteo por grupo.

Metadata prohibida:

- texto crudo escrito por admin;
- IDs de resultados;
- cuerpos de mensajes;
- datos privados.

## Riesgos Pendientes

- No reemplaza expediente formal de investigacion.
- No calcula responsabilidad ni fraude.
- No incluye descarga de adjuntos.
- No incluye paginacion entre grupos mas alla de `limit` por grupo.
