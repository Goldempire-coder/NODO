# UI Resilience Contract

## Principio

Un fallo temporal no debe hacer que la app muestre una verdad falsa. Si el
backend no responde, la UI debe conservar el ultimo dato conocido y marcar que
esta desactualizado o en modo degradado.

## Creditos negocio

Cuando falle el refresh de wallet/creditos:

- no reemplazar el ultimo saldo valido por `null`;
- no mostrar cero si no fue confirmado por backend;
- mostrar mensaje corto de estado degradado;
- permitir reintento manual;
- no iniciar compra ni verificacion por error.

## Notificaciones admin relacionadas con soporte

Cuando falle el polling de unread-count:

- conservar el ultimo contador valido;
- no convertirlo a cero falso;
- mostrar que la informacion puede estar desactualizada;
- registrar breadcrumb/log seguro si existe mecanismo local para hacerlo.

## Copiar identificacion del negocio

Cuando el portapapeles funciona:

- mostrar confirmacion clara.

Cuando el portapapeles falla:

- mostrar feedback de error seguro;
- no romper la pantalla;
- no ocultar la identificacion.

## Transiciones de pantalla

La metrica de transicion debe medir navegacion real, no tiempo de permanencia
en la pantalla anterior.

La medicion debe comenzar cuando se solicita el cambio de vista y terminar
cuando la nueva vista renderiza.
