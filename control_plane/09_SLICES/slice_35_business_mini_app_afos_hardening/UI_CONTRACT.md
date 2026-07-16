# UI_CONTRACT.md

## Principio

La Mini App Negocio debe sentirse rapida, limpia y operable. Las pantallas no deben explicar todo; deben permitir hacer el trabajo.

## Pantallas principales

- Inicio
- Anuncios
- Ordenes
- Creditos
- Perfil
- Metodos de cobro
- PIN
- Soporte

## Reglas UX

- No mostrar textos largos de reglas en Inicio, Anuncios o Creditos.
- Reglas y terminos van en Perfil/Reglas.
- Botones sensibles deben mostrar estado claro: guardando, borrando, reactivando, generando.
- Botones no deben titilar ni parecer tocables si estan bloqueados.
- Cada accion fallida debe dejar mensaje accionable.
- Metodos de cobro debe permitir agregar varios Zelle y USDT TRC20, editar, borrar y seleccionar uno por anuncio.
- Un anuncio atado a un metodo borrado debe mostrar ruta clara: editar y escoger un metodo activo.
- Ordenes deben mostrar `public_order_code`.
- Historial debe separar completadas/canceladas/entregadas de abiertas.
- Online/offline debe ser visible en Inicio y afectar anuncios.
- Creditos debe mostrar solo balance util y compra; no ledger crudo para negocio.

## Medicion de fluidez

El builder debe medir o testear:

- Inicio -> Anuncios;
- Anuncios -> detalle de anuncio;
- Anuncios -> Metodos;
- Inicio -> Creditos;
- Creditos -> Comprar;
- Ordenes -> Detalle;
- Perfil -> PIN/Reglas.

Evidencia minima:

- no hay loading global innecesario entre tabs ya cargados;
- acciones independientes no bloquean toda la pantalla;
- no hay pantalla "Load failed" silenciosa sin boton de recuperacion.
