# Slice 46D API Contract

Estado: IMPLEMENTATION_46D1_46D2_READY_FOR_OWNER_REVIEW

## Contrato Inicial

46D no aprueba ningun endpoint nuevo.

## Endpoints Reutilizados Por 46D1 Y 46D2

### Ficha De Investigacion

`GET /api/v1/admin/investigation/case-file`

46D1 usa unicamente campos allowlist ya entregados por 46B. El panel no hace
una consulta propia y no agrega cuerpos privados a la respuesta.

### Staff Activo

`GET /api/v1/admin/staff?status=active&limit=50`

La UI 46D2 lo consulta solo para Admin o Super Admin. El selector admite
perfiles activos compatibles con soporte y excluye `operations_readonly`.

### Asignacion De Ticket

`POST /api/v1/admin/support/tickets/{ticket_id}/assign`

46D2 conserva el payload, RBAC, motivo, idempotencia, auditoria y errores
definidos por 20B. No cambia el contrato publico.

El Builder puede inspeccionar endpoints existentes de Admin, Soporte, Ordenes,
Negocios, Clientes, Intake, Audit y Notificaciones para mapear que capacidades
existen hoy. Esa inspeccion debe ser read-only.

## Si El Reporte Propone Nuevos Endpoints

Cada endpoint propuesto debe venir como mini-slice independiente e incluir:

- objetivo exacto;
- rol autorizado;
- datos permitidos y prohibidos;
- respuesta allowlist;
- auditoria;
- rate limit;
- `Cache-Control`;
- errores;
- pruebas;
- rollback.

## Reglas Prohibidas

No se permite proponer endpoints que:

- devuelvan cuerpos de chats o tickets por defecto;
- expongan datos bancarios completos, wallets completas o instrucciones de
  pago completas en pantallas generales;
- devuelvan `storage_path`, signed URLs o IDs internos de storage sin accion
  explicita y auditada;
- mezclen lectura de caso con cambio de estado;
- decidan culpabilidad, fraude, pago valido o recuperacion;
- permitan acciones destructivas sin un contrato separado.

## Endpoints Existentes A Considerar

El reporte debe revisar, como minimo:

- busqueda operativa 46A;
- ficha de investigacion 46B;
- filtros avanzados 46C;
- visor de chat de orden 44B;
- soporte 20B;
- detalle Admin de orden;
- detalle Admin de negocio;
- intake de negocio;
- audit y notificaciones operativas.
