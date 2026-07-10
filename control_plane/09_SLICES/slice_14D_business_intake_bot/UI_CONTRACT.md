# UI_CONTRACT.md

## Bot flow

- Bienvenida para negocio referido/interesado.
- Solicitar compartir contacto de Telegram.
- Formulario guiado:
  - nombre del negocio
  - responsable
  - ciudad
  - telefono del negocio
  - operacion
  - bancos
  - metodos
  - rango minimo/maximo
  - horario
  - referencias/redes
- Solicitar documentos/imagenes/PDF permitidos.
- Confirmacion exacta: "Solicitud recibida. Revisaremos tu informacion y te avisaremos el siguiente paso."

## Estados

- draft: continuar formulario.
- submitted: solicitud recibida.
- accepted: puede notificar solo si backend/admin ya acepto.
- rejected: mensaje seguro sin detalles sensibles.

## Prohibido

- Prometer aprobacion.
- Mostrar boton de Mini App Negocio antes de aprobacion y link activo confirmado.
- Pedir videos en MVP.
- Mostrar `storage_path`.
