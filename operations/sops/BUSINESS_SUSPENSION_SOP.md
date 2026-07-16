# SOP: Business Suspension

SOP_ID: SOP-BUSINESS-002
Estado de validacion: NOT VALIDATED

## Proposito

Suspender negocio o acceso sin borrar datos.

## Opciones reales

- Suspender/bloquear usuario admin endpoints 20A.
- Suspender/revocar/bloquear `business_access_links`.
- Cambiar business verification status segun endpoints existentes/admin flow.

## Procedimiento

1. Identificar si el problema es usuario, negocio o access link.
2. Preservar evidencia.
3. Usar Admin Web/API con reason.
4. Validar que `/surface/session` deniega acceso.
5. Revisar audit logs.

## Prohibiciones

- No borrar negocio.
- No borrar usuario.
- No borrar ordenes.
