# SEVERITY_MATRIX

Estado: OFFICIAL
Ultima actualizacion: 2026-07-11

## SEV-1 Critico

Activar si existe cualquiera de estos sintomas:

- Duplicacion de creditos.
- Creditos no autorizados.
- Usuario ve datos de otro usuario o negocio.
- Admin/support accede con permisos indebidos.
- Compromiso o exposicion de secretos.
- Corrupcion de datos de ordenes, creditos, pagos, access links o staff.
- API completamente caida para cliente/negocio/admin.
- Base de datos no responde.

Actualizaciones: cada 15 minutos.
Incident Commander: DECISION REQUERIDA.
Canal: DECISION REQUERIDA.
Escalamiento: owner tecnico + owner operativo + seguridad.

## SEV-2 Alto

- Funcion principal no disponible para muchos usuarios.
- API p95 alto sostenido.
- Telegram bot no responde.
- Watcher de creditos detenido.
- Storage privado no firma URLs o no permite subir evidencia.
- Job critico falla repetidamente.

Actualizaciones: cada 30 minutos.

## SEV-3 Medio

- Funcion secundaria afectada con workaround.
- Panel admin parcialmente lento.
- Soporte no puede adjuntar archivos, pero puede responder texto.
- Un proveedor externo degradado sin impacto financiero inmediato.

Actualizaciones: cada 60 minutos.

## SEV-4 Bajo

- Defecto cosmetico.
- Error aislado sin reproduccion.
- Consulta operativa no urgente.

Actualizaciones: al cierre o siguiente horario laboral.

## Release gate

Si un componente Tier 0 o Tier 1 carece de owner, alerta, recovery o evidencia de validacion, produccion queda bloqueada.
