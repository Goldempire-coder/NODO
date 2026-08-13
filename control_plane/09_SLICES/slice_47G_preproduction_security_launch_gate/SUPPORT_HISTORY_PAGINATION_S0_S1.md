# S0/S1 Support History Pagination

## Estado

`IMPLEMENTED_LOCALLY_PENDING_VALIDATOR`

## Decision

El detalle de Soporte conserva sus endpoints y permisos, pero deja de devolver
todo el historial. Cliente, Negocio y Admin reciben por defecto los 25 mensajes
mas recientes. Admin recibe ademas los 25 eventos mas recientes.

Los cursores de mensajes y eventos son opacos y estables por
`(created_at, id)`. Cada pagina se presenta en orden cronologico. El historial
anterior se solicita de forma explicita y se combina por ID, sin duplicados.

El polling visible de Cliente, Negocio y Admin solo refresca la pagina reciente.
Las paginas anteriores que el operador ya cargo permanecen en memoria, pero no
se vuelven a descargar en cada intervalo.

Los adjuntos solo aparecen con el mensaje incluido en la pagina. Crear una URL
firmada sigue exigiendo permiso, razon y auditoria; la pertenencia del archivo se
valida con una consulta acotada por ticket y archivo.

## Compatibilidad

Se mantienen `attachments`, `messages`, `events`, `disclaimer` y todos los
campos resumen existentes. Se agregan:

- `messages_next_cursor`;
- `events_next_cursor` para detalle Admin;
- query `messages_cursor`, `messages_limit`, `events_cursor`, `events_limit`.

Admin Web navega mensajes anteriores en este slice. Aunque el backend pagina
eventos y expone `events_next_cursor`, la UI actual no muestra eventos del
ticket; agregar esa superficie queda fuera de S0/S1.

## Fuera De Alcance

- Marketplace/Ads quedo fuera de S0/S1. El mini-slice posterior de cursor
  compuesto usa `rate_bs_per_usd`, `created_at` e `id`, sin un parche parcial
  solo por fecha.
- Los otros listados legacy quedan para mini-slices posteriores.
- No se agregan indices sin `EXPLAIN` con PostgreSQL representativo.
- No se agrega cache privada.
- No cambian soporte, ownership, RBAC, signed URLs, pagos, ordenes ni reglas
  financieras.

## Evidencia Requerida

- 120 o mas mensajes: primera pagina acotada y recorrido completo sin perdida.
- Empates de `created_at`: cero duplicados y cero omisiones.
- Adjuntos fuera de pagina ausentes del payload inicial.
- URL firmada valida sin escanear mensajes.
- Paridad Memory/PostgreSQL.
- Polling visible-only, no-overlap y sin reemplazar paginas historicas cargadas.

## Validacion Local

- Suite API completa: `911 passed, 29 skipped`.
- Regresiones dirigidas de Soporte: `42 passed`.
- Regresiones dirigidas de Chat y cursor estable: `72 passed, 1 skipped`.
- Build web de produccion: PASS.
- Memory: PASS para 125 mensajes y 123 eventos con timestamps empatados.
- PostgreSQL 16 desechable: PASS. Se aplicaron las 53 migraciones desde cero y
  la prueba opt-in paso para Soporte participante, Admin Soporte, eventos Admin
  y Chat con timestamps empatados. El contenedor local se elimino al terminar.
