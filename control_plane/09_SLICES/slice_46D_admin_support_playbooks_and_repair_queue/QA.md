# Slice 46D QA

Estado: IMPLEMENTATION_46D1_46D2_READY_FOR_OWNER_REVIEW

## Regresiones 46D1

- El panel muestra checks neutrales para orden, reporte de pago, ticket, chat,
  evidencia e intake.
- El panel propone solo una pantalla existente que se puede abrir.
- No contiene composer, fetch propio, campos de storage ni lenguaje de culpa o
  validacion de pago.

## Regresiones 46D2

- La UI reutiliza el endpoint de asignacion existente.
- Los candidatos vienen de perfiles Staff activos.
- `operations_readonly` queda fuera del selector.
- No hay entrada manual de user ID.
- Motivo e idempotencia se conservan.
- La accion tiene loading propio y no agrega polling.

## Casos Que Debe Mapear El Reporte

### Cliente Pago Pero No Recuerda El Negocio

- Pistas posibles: telefono, Telegram, monto, dia, captura, nombre parcial.
- Debe indicar si 46C puede encontrar candidatos.
- Debe indicar como abrir 46B del candidato.
- Debe indicar si falta accion para enlazar ticket con orden.

### Cliente Cerro La App Y Perdio La Conversacion

- Pistas posibles: usuario, ticket, orden, ultimo mensaje, fecha aproximada.
- Debe indicar si Admin puede encontrar ticket activo o archivado.
- Debe indicar si el cliente puede volver a su ticket desde la app.

### Orden Expiro Despues De Pago Reportado

- Debe indicar que evidencia existe: orden, reporte, timeline, ticket.
- No debe validar el pago.
- Debe indicar si falta playbook para escalar o revisar manualmente.

### Negocio No Reconoce Pago

- Debe indicar como comparar negocio, monto, fecha, reporte y tickets.
- Debe indicar si falta accion para pedir evidencia adicional.

### Negocio Entro Con Codigo De Recomendacion

- Debe indicar donde se ve el codigo en intake, negocio y ficha.
- Debe indicar si falta mostrarlo en Dashboard.

### Ticket Cerrado O Archivado

- Debe indicar donde queda archivado.
- Debe indicar si usuario puede verlo.
- Debe indicar si Admin puede investigar sin reabrir.

### Adjuntos En Soporte

- Debe indicar si Admin puede ver metadata y abrir/descargar con accion segura.
- Debe indicar si falta endpoint o boton auditado.

### Alerta De Chat Fuera De Plataforma

- Debe indicar como llega la alerta.
- Debe indicar como abrir la orden y evidencia 44B.
- No debe bloquear mensajes ni decidir fraude.

## Calidad Del Reporte

- Cada caso debe tener estado: `cubierto`, `parcial`, `no_cubierto` o
  `no_aplica`.
- Cada brecha debe tener severidad: `critical`, `high`, `medium`, `low`.
- Cada reparacion debe indicar mini-slice sugerido.
- Cada reparacion debe decir que pruebas la demostrarian.
- Las recomendaciones deben ser pequenas y revisables.

## Validacion Esperada

```powershell
python -m pytest apps/api/tests/test_admin_investigation_case_file.py apps/api/tests/test_support_ticket_center.py -q --tb=short
python -m pytest apps/api/tests/test_auth_lifecycle_static.py -q --tb=short
python -m ruff check apps/api scripts
python -m compileall apps/api apps/web/src scripts
pnpm --filter @nodo/web build
git diff --check
```
