# QA.md

## Pruebas automaticas

```powershell
python -m pytest apps/api/tests/test_chat_disputes.py -q --tb=short
python -m pytest apps/api/tests/test_admin_operational_notifications.py::test_admin_operational_notifications_frontend_and_migration_contracts -q --tb=short
```

Cobertura obligatoria adicional:

- la alerta conserva solo la senal canonica y elimina texto sensible circundante;
- una falla de `admin_notifications` no bloquea el mensaje ya validado;
- usos neutrales como `por fuera del borde` no crean alerta.

## Casos manuales staging

1. Abrir una orden con chat permitido.
2. Enviar como negocio: `La proxima vez por fuera te doy mejor tasa fuera de la app.`
3. Confirmar que el cliente ve el mensaje.
4. Confirmar que el admin ve notificacion operativa.
5. Abrir la notificacion y confirmar que carga detalle de orden.
6. Enviar como cliente la misma frase y confirmar que no crea alerta de negocio.
7. Enviar como negocio una frase con WhatsApp y telefono; confirmar que el telefono aparece redactado en la alerta.

## Criterio PASS

- No se duplican alertas al repetir el mismo request idempotente.
- Audit log no contiene el cuerpo completo.
- Admin notification no contiene secretos ni storage path.
- Una caida de la bandeja admin deja log operativo seguro y no bloquea el chat.
- Chat sigue abierto durante el periodo vigente de la orden.
