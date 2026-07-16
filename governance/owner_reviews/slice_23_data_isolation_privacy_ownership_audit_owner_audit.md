# SLICE_23_DATA_ISOLATION_PRIVACY_OWNERSHIP_AUDIT_OWNER_AUDIT

Fecha: 2026-07-11
Estado: PASSED_OWNER_AUDIT_WITH_LIMITS
Decision: DATA ISOLATION VERIFIED WITH LIMITS

## Alcance auditado

Se reviso el resultado del builder para `slice_23_data_isolation_privacy_ownership_audit`.

Areas revisadas:

- Fix de visibilidad de tickets de soporte de negocio.
- Regresion agregada en soporte.
- Patrones similares de acceso por `requester_user_id`.
- Signed URL y storage path en soporte.
- Cache y frontend storage a nivel de scan dirigido.
- Validaciones backend focales y suite completa.

No se ejecuto DAST, staging real, navegador multi-cuenta ni pruebas reales multi-tab/offline.

## Hallazgo critico confirmado

### DATA_EXPOSURE_CRITICAL_FINDING - Ticket de soporte de negocio visible tras access link revocado

El hallazgo del builder es valido.

Causa:

- `SupportService._ticket_visible_to_user` permitia el acceso por `ticket.requester_user_id == user.id`.
- Para tickets de negocio, eso permitia que el creador del ticket siguiera leyendo el ticket aunque su `business_access_link` ya estuviera revocado.

Fix validado:

- Si el usuario es `business_owner` y el ticket tiene `business_id`, ahora se evalua primero `_active_business_for_user`.
- `_active_business_for_user` llama `evaluate_business_access`.
- Si el link esta suspendido, bloqueado o revocado, el ticket no es visible.

Archivos clave:

- `apps/api/app/modules/support/service.py`
- `apps/api/tests/test_support_ticket_center.py`

## Revision adicional

Se revisaron llamadas de visibilidad:

- `user_ticket_detail`
- `create_user_message`
- `upload_attachment`
- `list_user_tickets`

Todas pasan por `_ticket_visible_to_user` para usuarios no admin.

Se reviso `attachment_view_url`:

- Solo Admin Web/support autorizado.
- Usa `view_support_attachment`.
- Verifica que el `file_id` pertenezca al ticket o a mensajes del ticket.

No se encontro otro shortcut equivalente confirmado en soporte.

## Validaciones ejecutadas

```text
python -m pytest apps\api\tests\test_support_ticket_center.py apps\api\tests\test_business_access_control.py apps\api\tests\test_internal_staff_roles.py -q --tb=short
17 passed, 1 warning

python -m pytest apps\api\tests -q --tb=short
210 passed, 1 warning

python -m ruff check apps\api scripts
All checks passed!

python -m compileall apps\api apps\web\src scripts
OK

corepack pnpm --filter @nodo/web build
OK
```

Scans:

```text
FRONTEND_SENSITIVE_SCAN_CLEAN
```

El scan sobre evidencia/reports encontro menciones descriptivas y comandos que contienen `storage_path`, `account_value` y nombres de secretos. No encontro valores sensibles reales.

## Riesgos residuales

- No hubo DAST ni fuzzing externo.
- No hubo pruebas reales multi-cuenta en navegador.
- No hubo staging/cloud real.
- Los caches frontend por hook no son persistentes, pero requieren prueba E2E de cambio rapido de cuenta para cerrar ese riesgo visual.
- El scan de patrones no reemplaza una revision formal de cada query SQL contra datos reales.

## Veredicto

DATA ISOLATION VERIFIED WITH LIMITS.

El hallazgo critico fue real y quedo corregido con regresion. No se encontraron otros leaks confirmados en la revision dirigida, pero no corresponde declarar `DATA ISOLATION VERIFIED` sin DAST, staging real y pruebas multi-cuenta en navegador.
