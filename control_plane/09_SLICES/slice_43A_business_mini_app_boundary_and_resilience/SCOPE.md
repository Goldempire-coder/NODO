# Scope

## Construir

1. Remover `risk_level` de la respuesta de sesion/surface usada por la Mini App
   Negocio.
2. Agregar regresion que falle si `risk_level` u otra senal antifraude interna
   aparece en el DTO de negocio no-admin.
3. Auditar `trust_level` en el DTO de sesion de negocio:
   - si el contrato vigente lo prohibe para negocio, removerlo tambien;
   - si el contrato no es claro, reportar `BLOCKED_BY_EXPLICIT_EVIDENCE` antes
     de cambiarlo.
4. Preservar el ultimo saldo/estado de creditos conocido ante un fallo temporal
   de refresh, mostrando estado degradado en vez de borrar la informacion.
5. Preservar el ultimo contador admin de notificaciones soporte ante un fallo
   temporal de polling, mostrando estado degradado en vez de convertirlo en
   cero falso.
6. Corregir la medicion de transiciones de pantalla de la Mini App Negocio para
   medir desde el inicio real de navegacion hasta el render de la nueva vista.
7. Agregar manejo de error cuando el negocio intenta copiar su identificacion y
   el portapapeles falla.
8. Actualizar tests y evidencia del slice.

## No construir en este slice

- No paginacion/cargar mas para soporte, anuncios u ordenes.
- No cambio de storage de tokens.
- No rediseño grande de chat.
- No cambio de flujos Base USDC.
- No cambio de precios, creditos, ledger ni acreditacion on-chain.
- No nuevas migraciones.
- No nuevos endpoints salvo que la evidencia demuestre que no hay forma segura
  de cumplir el contrato actual.
- No deploy.

## Archivos esperados

El Builder debe identificar los archivos exactos antes de editar, pero el scope
probable incluye:

- `apps/api/app/modules/businesses/access_control.py`
- tests API relacionados con surface/session o access control
- `apps/web/src/hooks/business-mini-app/useBusinessCreditsModel.ts`
- `apps/web/src/hooks/admin-web/useAdminNotificationsModel.ts`
- `apps/web/src/screens/business-app/BusinessMiniAppShell.tsx`
- `apps/web/src/screens/business-app/BusinessSettingsScreen.tsx`
- tests estaticos existentes o nuevos bajo `apps/api/tests/`
