# RUNBOOK: Business intake bot stuck

Estado de validacion: NOT VALIDATED

## SINTOMA

Bot pide datos pero no avanza, `finalizar` no responde, documentos se repiten.

## SEVERIDAD INICIAL

SEV-2/3.

## DIAGNOSTICO

Revisar:

- `business_intake_requests.last_step`.
- `business_intake_requests.last_update_id`.
- Documentos en `file_assets.resource_type = business_intake`.
- Logs del webhook.

## MITIGACION

- Si flujo quedo mal, admin puede delete/reject intake si endpoint esta disponible.
- Pedir al negocio reiniciar con nuevo registro solo despues de limpiar evidencia.

## PROHIBICIONES

- No crear negocio activo desde bot.
- No crear access link desde bot.
