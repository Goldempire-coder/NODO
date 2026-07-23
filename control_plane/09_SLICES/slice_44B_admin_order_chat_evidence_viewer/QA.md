# QA.md

## Pruebas automaticas esperadas

```powershell
python -m pytest apps/api/tests/test_admin_order_chat_evidence.py -q --tb=short
python -m pytest apps/api/tests/test_chat_disputes.py apps/api/tests/test_admin_operational_notifications.py apps/api/tests/test_admin_console.py -q --tb=short
python -m pytest apps/api/tests -q
python -m ruff check apps/api scripts
python -m compileall apps/api apps/web/src scripts
pnpm --filter @nodo/web build
git diff --check
```

## Casos obligatorios

- Admin autorizado abre detalle de orden y ve mensajes cronologicos.
- Actor no autorizado no puede leer mensajes de una orden.
- Abrir notificacion anti-evasion carga la orden correcta.
- `message_id` de alerta queda destacado si el contrato lo permite.
- La notificacion conserva solo senal canonica y no cuerpo completo.
- El payload admin no contiene `storage_path`, signed URLs, PIN, tokens ni `account_value`.
- Si la carga del chat falla, el detalle de orden sigue usable y muestra retry.
- El panel de chat es scrollable y no agranda infinitamente el dashboard.
- Adjuntos aparecen como metadata segura; abrir/descargar requiere accion separada.

## Prueba manual staging

1. Crear una orden de prueba cliente-negocio.
2. Enviar como negocio una frase de evasion: `La proxima vez por fuera te doy mejor tasa fuera de la app.`
3. Confirmar que el mensaje llega al cliente.
4. Confirmar que Admin recibe notificacion.
5. Abrir la notificacion.
6. Confirmar que abre la orden correcta.
7. Confirmar que el panel muestra la conversacion completa con scroll.
8. Confirmar que la alerta no muestra el cuerpo completo fuera del panel autorizado.
9. Revisar network payload: no debe incluir paths internos ni signed URLs iniciales.
10. Revisar logs/audit: no debe incluir cuerpo completo del mensaje.

## Criterio PASS

- Admin puede revisar evidencia real sin guardar datos sensibles en la notificacion.
- La UI queda operativa y liviana.
- La autorizacion y auditoria quedan probadas.
- No hay cambios de dinero, pagos, ordenes ni cierre de chat.
