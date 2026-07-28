# Slice 46C Security Contract

Estado: DRAFT

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
- Limita ventana de fecha.
- Limita resultados.
- Rate limit por actor.
- `Cache-Control: private, no-store`.
- Audit log obligatorio.
- Respuesta allowlist.

## Support

`support` activo no hereda acceso completo de Admin. Solo puede usar la busqueda
si sus permisos vigentes lo permiten. La respuesta debe permanecer enmascarada
y de solo lectura.

## Evidencia Insuficiente

- Captura visual sin request id.
- Endpoint 200 sin demostrar ausencia de datos prohibidos.
- Test que busca solo por un filtro amplio.
- Test que no verifica actor `support`.
- Test que no prueba rangos invalidos.
