# Slice 46D Scope

Estado: IMPLEMENTATION_46D1_46D2_READY_FOR_OWNER_REVIEW

## Autorizacion Acotada Del Owner

- Panel read-only de revision guiada en la ficha de investigacion 46B.
- Selector de perfiles Staff activos para asignar tickets activos.
- Reutilizacion exclusiva de endpoints existentes.
- Pruebas estaticas y regresiones de backend existentes.

## Dentro Del Alcance

- Inspeccion read-only del Dashboard, soporte, ordenes, intake, negocios,
  clientes, audit y notificaciones.
- Inventario de flujos reales que Admin necesita resolver.
- Mapa de pantallas existentes y acciones disponibles.
- Identificacion de brechas operativas.
- Priorizacion de reparaciones por severidad, frecuencia probable y costo.
- Separacion de reparaciones en mini-slices seguros.
- Definicion de pruebas esperadas por caso.
- Recomendaciones de copy operativo neutral.

## Fuera Del Alcance

- Nuevos endpoints.
- Migraciones.
- Cambios de permisos.
- Cambios de estados.
- Descarga de archivos o URLs firmadas.
- Validacion de pagos.
- Automatizacion de decisiones.
- Produccion, deploy, reset DB o borrado de datos.
- `repair_queue`.
- Relaciones nuevas entre tickets o entre ticket y orden.

## Reglas De Paquete

- 46D es report-first.
- Si una reparacion requiere codigo, se debe crear un mini-slice separado.
- Cada mini-slice debe tener alcance, pruebas y rollback propios.
- No se permite mezclar reparaciones visuales con cambios de reglas de negocio.

## Entrega Minima

El reporte debe incluir:

- estado del repo;
- archivos y modulos inspeccionados;
- matriz de casos;
- brechas encontradas;
- reparaciones propuestas;
- dependencias entre reparaciones;
- riesgos y datos sensibles;
- que no se toco;
- validaciones ejecutadas o no ejecutadas.
