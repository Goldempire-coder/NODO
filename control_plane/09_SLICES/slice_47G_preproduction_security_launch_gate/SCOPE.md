# Slice 47G Scope

Estado: CONTRACTS_DRAFT_READY_FOR_OWNER_REVIEW

## Dentro Del Alcance

- Mapear todos los secretos y variables por entorno usando solo nombres.
- Definir rotacion preproduccion y orden seguro de cambio/revocacion.
- Validar que frontend no incluya secretos ni keys backend-only.
- Validar Telegram Web como superficie no confiable.
- Confirmar Supabase/Postgres cerrado: RLS, grants, Advisor y storage privado.
- Revisar autorizacion backend en endpoints sensibles.
- Revisar chat y adjuntos como entrada hostil.
- Revisar CORS, CSP, headers y errores seguros.
- Revisar rate limits, replay/idempotencia y abuso basico.
- Revisar dependencias y lockfiles.
- Definir smoke autenticado Cliente, Negocio y Admin antes de produccion.
- Producir reporte de blockers y plan de mitigacion.

## Fuera Del Alcance

- Crear features nuevas.
- Cambiar UX del flujo P2P.
- Cambiar reglas de pago, credito, capacidad o reputacion.
- Migrar proveedores.
- Borrar historial o limpiar datos reales.
- Ejecutar rotacion de produccion sin aprobacion separada.
- Hacer pruebas destructivas contra produccion.

## Regla Madre

Una Mini App de Telegram es una web visible para el usuario. Ningun secreto,
permiso o decision financiera puede depender de que el cliente "no vea" o "no
modifique" el codigo frontend.
