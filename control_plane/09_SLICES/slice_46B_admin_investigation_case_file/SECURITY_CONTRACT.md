# Slice 46B Security Contract

Estado: STAGING_DEPLOYED_PENDING_OWNER_SMOKE

## Principio

La ficha de investigacion ayuda a reconstruir contexto, pero no convierte Admin
Web en exportador de datos privados ni en juez automatico del caso.

## Roles

Permitidos:

- `super_admin`: lectura allowlist completa.
- `admin`: lectura allowlist completa.
- `support` activo: solo lectura limitada por politica de soporte.

No permitidos:

- cliente;
- negocio;
- business owner;
- staff inactivo;
- actor sin sesion.

`support` no hereda visibilidad completa de Admin. Cada seccion debe respetar
la visibilidad vigente de soporte. Si el anchor no es visible para `support`, el
endpoint responde `404`.

## Datos Permitidos

- IDs internos para abrir pantallas admin.
- Codigo publico de orden.
- Estado de orden, ticket, negocio e intake.
- Montos de orden y timestamps operativos.
- Nombre publico del negocio.
- Telefono/Telegram en forma enmascarada.
- Codigo de referencia de intake o negocio cuando ya es dato admin.
- Metadata de adjuntos/documentos sin URL ni path.
- Conteos y relaciones entre entidades.
- Checklist deterministico de revision sin conclusiones.

## Datos Prohibidos En La Ficha Inicial

- Cuerpo completo de chats o tickets.
- PIN, tokens, JWT, bot tokens o secrets.
- `storage_path`.
- Signed URLs.
- Datos bancarios completos, wallets completas o instrucciones completas de pago.
- `file_asset_id` si expone almacenamiento interno.
- Payloads crudos de proveedor.
- Texto libre crudo en audit logs.
- `severity_hint`.
- `suggested_next_step`.
- Conclusiones narrativas sobre culpa, fraude, pago valido o recuperacion.
- `metadata_json` crudo.
- Razones privadas de acciones admin o soporte.

## Acciones Prohibidas

- Cambiar estados.
- Cerrar, resolver, reabrir o escalar tickets.
- Aprobar, suspender o bloquear negocios.
- Crear ordenes.
- Editar capacidad o limites.
- Descargar adjuntos sin accion separada y auditada.
- Exportar expedientes fuera del dashboard.

## Auditoria

Cada lectura debe registrar:

- actor;
- rol;
- anchor tipo/id;
- conteos por seccion;
- secciones truncadas;
- resultado;
- request id;
- ambiente/version si el sistema ya lo adjunta.

La auditoria nunca guarda cuerpos de mensajes, textos libres, URLs firmadas,
paths de storage ni datos bancarios completos.

## Timeline Seguro

- Solo eventos allowlist.
- Sin cuerpos de mensajes.
- Sin motivos privados.
- Sin `metadata_json` crudo.
- Sin payloads de proveedor.
- Sin afirmar que dos entidades son "el mismo caso" si la relacion no viene por
  ID directo.

## Privacidad Y Costo

- Carga lazy: no cargar ficha si Admin solo abre la lupa.
- Cada grupo tiene limite y paginacion o truncado.
- No hacer listas ilimitadas.
- No descargar archivos para pintar la ficha.
- No usar full-text sobre mensajes privados en este slice.
- `no-store` para evitar cache compartido de datos admin.
- Paginacion por seccion. No se permite un cursor global que mezcle permisos o
  estados.

## Riesgos Pendientes

- Si se necesita descargar evidencia, debe ser otro sub-slice con endpoint
  autorizado, expiracion, auditoria y limites de tamano.
- Si se necesita fusionar tickets, debe ser otro slice con reglas de evidencia.
- Si se necesita decision formal de disputa, debe ser otro flujo operativo.
