# Slice 46C Security Contract

Estado: IMPLEMENTED_LOCAL - PENDING_VALIDATOR

## Principio

La busqueda avanzada reduce incertidumbre operativa, pero no convierte NODO en
juez automatico ni en exportador de datos privados.

## Permitido

- Buscar candidatos por filtros estructurados.
- Mostrar datos minimos para comparar:
  - codigo publico de orden;
  - monto;
  - fecha;
  - estado;
  - negocio;
  - cliente enmascarado;
  - existencia de ticket o reporte.
- Abrir ficha 46B desde el candidato.
- Auditar la busqueda sin guardar valores crudos sensibles.

## Prohibido

- Buscar cuerpos de mensajes.
- Exponer comprobantes o adjuntos.
- Exponer signed URLs.
- Exponer `storage_path`.
- Exponer `file_asset_id`.
- Exponer wallets, bancos o instrucciones completas.
- Usar `score`, `risk_level`, `trust_level`, `severity_hint` o
  `suggested_next_step`.
- Decir que un candidato es culpable, fraude, pago valido o recuperable.
- Cambiar estados desde esta pantalla.
- Crear tickets, cerrar tickets, aprobar negocios o resolver disputas.

## Controles De Abuso

- Requiere autenticacion Admin.
- Requiere filtros suficientes.
- Rechaza rangos incompletos de monto o fecha.
- Limita ventana de fecha.
- Limita resultados.
- Ordena de forma deterministica por fecha e ID, sin score oculto.
- Usa cursor opaco firmado ligado a filtros, rol y alcance.
- Rate limit por actor.
- `Cache-Control: private, no-store`.
- Audit log obligatorio.
- Respuesta allowlist.

## Support

`support` activo no hereda acceso completo de Admin. Solo puede usar la busqueda
si sus permisos vigentes lo permiten. La respuesta debe permanecer enmascarada
y de solo lectura.

Reglas minimas:

- `support` activo con `view_orders_masked` puede buscar candidatos enmascarados.
- `support` activo sin `view_orders_masked` solo puede ver ordenes ligadas a
  tickets dentro de su cola visible o asignacion vigente.
- Los filtros de alcance de `support` se aplican antes de `ORDER BY`, cursor y
  `LIMIT`.
- `support` sin permiso aplicable recibe `FORBIDDEN`.

## Hints En Query String

`client_hint` y `business_hint` no se guardan crudos en audit, logs de app ni
telemetria. El operador no debe pegar cuerpos de mensajes, bancos completos,
wallets, PIN, tokens ni datos de pago completos en estos campos. Como son query
params de `GET`, pueden aparecer en logs de infraestructura fuera del control
del backend; si el flujo exige pistas sensibles, debe abrirse un slice nuevo
para evaluar un endpoint `POST` con cuerpo protegido.

## Evidencia Insuficiente

- Captura visual sin request id.
- Endpoint 200 sin demostrar ausencia de datos prohibidos.
- Test que busca solo por un filtro amplio.
- Test que no verifica actor `support`.
- Test que no prueba rangos invalidos.
- Test que no prueba cursor alterado o reutilizado con otros filtros.
- Test donde el alcance de `support` se filtra despues del `LIMIT`.
