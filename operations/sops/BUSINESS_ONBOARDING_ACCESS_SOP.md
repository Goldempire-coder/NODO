# SOP: Business Onboarding and Access

SOP_ID: SOP-BUSINESS-001
Estado de validacion: NOT VALIDATED

## Proposito

Crear/vincular acceso de negocio sin self-onboarding inseguro.

## Procedimiento operativo

1. Revisar intake en Admin Web o API `/api/v1/admin/business-intake`.
2. Verificar documentos y datos.
3. Crear o aprobar negocio segun flujo admin existente.
4. Crear `business_access_links` desde endpoint admin.
5. Validar que Mini App Negocio use `/api/v1/surface/session`.

## Verificacion

- Usuario tiene rol `business_owner`.
- Negocio esta `approved`.
- Access link esta `active`.
- `surface/session` permite `business_mini_app`.

## Prohibiciones

- No cambiar role manualmente en DB.
- No aprobar solo por Telegram ID.
- No crear access link sin reason/audit.
