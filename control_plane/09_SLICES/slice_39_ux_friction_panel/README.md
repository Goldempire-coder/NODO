# slice_39_ux_friction_panel

Estado: `READY_FOR_VALIDATION`

## Objetivo

Mostrar en Admin donde cliente y negocio se traban mas dentro de las Mini Apps, usando eventos UX seguros y agregados.

## Alcance

- Persistir eventos frontend observability redacted.
- Resumir friccion por superficie, pantalla, accion y ruta API.
- Agregar panel Admin `UX`.
- Enviar eventos seguros de pantalla, acciones, lentitud y errores cuando la ingesta esta activada.

## Fuera De Alcance

- No graba sesiones de usuario.
- No guarda IP address.
- No guarda wallet completa, Zelle completo, PIN, token, comprobantes ni signed URLs.
- No cambia reglas financieras.
- No cambia Base USDC.
- No cambia notificaciones.
- No hace deploy.
- No declara `READY_FOR_REAL_USE`.

## Flags Requeridos

- Backend: `OBSERVABILITY_INGEST_ENABLED=1`
- Frontend: `NEXT_PUBLIC_OBSERVABILITY_INGEST_ENABLED=1`

Si estos flags estan apagados, el panel existe pero no acumula eventos nuevos.

## Criterio De Salida

- Admin puede ver `UX` con pantallas, acciones y errores mas repetidos.
- Usuarios no admin no pueden acceder.
- Tests validan que no se exponen valores sensibles.
- Build y pruebas completas pasan.
