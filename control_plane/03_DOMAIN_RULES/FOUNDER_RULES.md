# FOUNDER_RULES.md

Contrato canonico del retiro de founder access en NODO.

## Decision canonica

Decision del Owner, 2026-09-29: retirar la exencion Founder. Carlos asigna
manualmente creditos a los negocios iniciales mediante el ajuste administrativo
existente. No hay publicaciones gratuitas automaticas ni periodo de 30 dias.

Los campos siguientes se conservan exclusivamente como historial compatible:

- `businesses.founder_status`
- `businesses.founder_started_at`
- `businesses.founder_expires_at`

No existe tabla activa `founder_access` en slice 08. Si aparece en documentos
anteriores, queda como nombre legacy/no valido para MVP.

## Reglas

- Toda publicacion nueva o republicacion requiere saldo suficiente y un `hold`
  transaccional, independientemente del estado o fechas Founder historicos.
- La asignacion administrativa usa creditos normales, con permiso, reason,
  idempotencia, ledger `admin_adjustment` y auditoria existentes.
- Se mantienen verificacion, limites, riesgo, rate limit y RBAC.
- La confirmacion usa el hold correspondiente y consume una sola vez.
- Un anuncio historico sin `credit_hold_ledger_id` no admite ordenes nuevas:
  `AD_NOT_AVAILABLE` (409), sin fabricar reservas ni usar las de otros anuncios.
- No se generan nuevos movimientos `founder_free_use`.
- No se borran balances, campos, movimientos ni auditoria historicos.

## Estados

`founder_status` historico conservado, sin privilegios:

- active
- expired
- revoked

`null` significa que no existe marca Founder historica.

## Expiracion

- Leer los campos historicos de wallet/credits no concede exenciones.
- El job ya no expira Founder ni crea notificaciones de ese beneficio retirado.
- Toda publicacion requiere creditos disponibles, sin depender de fechas Founder.

## Auditoria

Eventos conservados solo para interpretar historial:

- founder_access_granted
- founder_access_expired
- founder_access_revoked
- founder_free_use

Los ajustes administrativos nuevos requieren reason y conservan su auditoria.

## Transicion y limites

No se aplica migracion ni ajuste retroactivo. Antes de desplegar, un inventario
autorizado debe determinar si existen anuncios u ordenes previas sin hold y
notificaciones Founder pendientes. Este cambio no los repara ni los elimina.
No convierte `founder_free_use` en una reserva real ni cambia confirmaciones de
ordenes ya creadas. Toda remediacion de datos requiere autorizacion separada.

## Prohibido

- Saltar business verification.
- Saltar risk limits.
- Generar balance negativo.
- Prometer fondos protegidos, escrow, garantia de entrega o garantia de pago.
- Usar tabla `founder_access` como modelo activo en MVP.
