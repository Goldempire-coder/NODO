# FOUNDER_RULES.md

Contrato canonico para founder access en NODO.

## Decision canonica

Founder access usa campos en `businesses` como fuente canonica MVP:

- `businesses.founder_status`
- `businesses.founder_started_at`
- `businesses.founder_expires_at`

No existe tabla activa `founder_access` en slice 08. Si aparece en documentos
anteriores, queda como nombre legacy/no valido para MVP.

## Reglas

- Un negocio founder debe estar verificado/aprobado.
- Founder access dura 30 dias desde `founder_started_at`.
- Founder access permite publicar anuncios sin debitar creditos durante la ventana.
- Founder access no salta limites de monto, riesgo, negocio aprobado, rate limit ni RBAC.
- Founder access no elimina auditoria.
- Founder access no convierte a NODO en garante de fondos.
- Al publicar con founder access se escribe ledger `founder_free_use`.
- `founder_free_use` debe incluir:
  - business_id
  - amount = credits that would have been blocked
  - related_ad_id
  - reason = founder_access_ad_publish
  - source = ads
  - reference_type = ad
  - reference_id = ads.id
  - created_by = business owner id

## Estados

`founder_status` permitido:

- active
- expired
- revoked

`null` significa que el negocio no tiene founder access.

## Expiracion

- Slice 08 puede validar founder access al leer wallet/credits.
- La expiracion masiva/notificaciones quedan para `slice_10_jobs_notifications`.
- Si founder access expiro, nuevas publicaciones requieren creditos disponibles.

## Auditoria

Eventos:

- founder_access_granted
- founder_access_expired
- founder_access_revoked
- founder_free_use

Los eventos admin requieren reason.

## Prohibido

- Saltar business verification.
- Saltar risk limits.
- Generar balance negativo.
- Prometer fondos protegidos, escrow, garantia de entrega o garantia de pago.
- Usar tabla `founder_access` como modelo activo en MVP.
