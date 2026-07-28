# Slice 46C - Admin Investigation Advanced Filters

Estado: STAGING_DEPLOYED_PENDING_OWNER_SMOKE

## Objetivo

Agregar una busqueda avanzada de investigacion para casos donde Admin o Soporte
no tienen un ID exacto, pero si tienen pistas operativas:

- cliente o telefono aproximado;
- monto enviado;
- fecha o ventana horaria;
- negocio posible;
- estado de orden o ticket;
- codigo publico parcial.

46A resuelve busqueda simple por texto. 46B abre una ficha desde un anchor
exacto. 46C debe encontrar candidatos cuando el caso empieza incompleto.

## Problemas Que Cubre

- Cliente dice que envio dinero, pero no recuerda a que negocio.
- Cliente cerro la app y no sabe volver a la conversacion.
- Cliente recuerda monto y fecha, pero no codigo de orden.
- Negocio dice que no reconoce un pago y soporte necesita comparar ordenes
  recientes.
- Ticket viejo se archivo y el cliente solo recuerda telefono, monto o dia.
- Admin necesita reducir una lista grande de ordenes sin abrir negocio por
  negocio.

## Resultado Esperado

Admin Web debe mostrar una vista de filtros compacta:

- cliente o telefono;
- negocio o codigo de referencia;
- monto minimo y maximo;
- fecha desde y hasta;
- estado de orden;
- estado de soporte;
- boton para abrir ficha 46B del candidato.

El resultado debe devolver candidatos con razones factuales, no por juicio:

- monto dentro del rango;
- fecha dentro de la ventana;
- cliente relacionado;
- negocio relacionado;
- ticket relacionado;
- reporte de pago existente.

El orden inicial del MVP es deterministico y simple: ordenes mas recientes
primero (`created_at DESC`, `order_id DESC`). No hay `score` oculto, ranking de
riesgo ni conclusion automatica.

No debe declarar culpa, fraude, pago valido ni recuperacion.

## Que No Construye

- No busca texto dentro de chats privados.
- No descarga adjuntos.
- No abre signed URLs.
- No fusiona tickets.
- No cambia estados.
- No crea expediente persistente.
- No exporta datos.
- No toca pagos, creditos, USDC, Zelle, reputacion, bots ni capacidad.
- No ejecuta migraciones salvo que el Builder demuestre que un indice es
  necesario y el Owner lo apruebe.

## Decision Inicial

Crear endpoint dedicado y liviano:

```txt
GET /api/v1/admin/investigation/order-candidates
```

No se debe meter todo en `GET /api/v1/admin/investigation/search`, porque 46A
es una lupa rapida y 46C necesita filtros estructurados, limites de ventana y
reglas de costo distintas.

## Criterios De Aceptacion

- Admin puede buscar candidatos por cliente + monto + fecha.
- Admin puede buscar candidatos por negocio + fecha.
- Si faltan filtros suficientes, el backend rechaza la busqueda.
- Rangos de monto y fecha son pares completos; no se acepta un solo extremo.
- `support_status_group=active|archived` filtra candidatos, no solo contadores.
- Support activo ve solo lo que sus permisos y alcance permiten, aplicado antes
  del limite de resultados.
- Cursores son opacos, firmados y no reutilizables con otros filtros.
- La respuesta no contiene cuerpos de mensajes ni datos de pago completos.
- Cada candidato tiene ruta para abrir ficha 46B.
- La pantalla es compacta, scrollable y no bloquea el resto del dashboard.
- La busqueda audita filtros seguros y conteos, nunca texto crudo sensible.
- El backend aplica limites antes de devolver resultados.

## Relacion Con Otros Slices

- Usa 46A como entrada rapida.
- Usa 46B para abrir la ficha final del candidato.
- No reemplaza 44B; si se necesita chat completo, Admin debe abrir el visor
  auditado de chat.
- No reemplaza soporte; solo ayuda a encontrar el caso correcto.
