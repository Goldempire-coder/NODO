# slice_37_client_mini_app_afos_hardening evidence

## Estado

`READY_FOR_OWNER_REVIEW`

## Evidencia de alcance

- `apps/web/src/hooks/actionTelemetry.ts`
- `apps/web/src/hooks/useClientWorkspaceModel.ts`
- `apps/web/src/hooks/workspace/useClientWorkspaceState.ts`
- `apps/web/src/hooks/workspace/useClientMarketplaceModel.ts`
- `apps/web/src/hooks/workspace/useRemitterOrdersModel.ts`
- `apps/web/src/hooks/workspace/usePaymentReportModel.ts`
- `apps/web/src/hooks/workspace/useClientChatDisputesModel.ts`
- `apps/web/src/hooks/useSurfaceSupportModel.ts`
- `apps/web/src/screens/client/*`
- `control_plane/09_SLICES/slice_37_client_mini_app_afos_hardening/*`

## Pruebas

```text
python -m pytest apps/api/tests/test_auth_lifecycle_static.py -q --tb=short
8 passed

pnpm --filter @nodo/web build
passed

python -m pytest apps/api/tests/test_order_creation.py apps/api/tests/test_payment_instructions_reports.py apps/api/tests/test_chat_disputes.py apps/api/tests/test_support_ticket_center.py apps/api/tests/test_jobs_notifications.py -q --tb=short
53 passed, 1 warning

python -m ruff check apps/api scripts
All checks passed

python -m compileall apps/api apps/web/src scripts
passed

python -m pytest apps/api/tests -q
369 passed, 1 warning
```

## Observacion AFOS

El backend sigue siendo la autoridad para identidad, ownership, estado de orden, idempotencia, adjuntos privados, pagos y disputas.

El frontend quedo limitado a UI, navegacion, formularios y llamadas API con breadcrumbs seguros.
