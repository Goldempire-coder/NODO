# SECURITY_CONTRACT.md

## Datos permitidos en admin notification

- `order_id`
- `message_id`
- `rule_id`
- `severity`
- `matched_phrase` limitada a senales canonicas de deteccion y sin texto circundante del mensaje
- `sender_role`

## Datos prohibidos

- cuerpo completo sin redaccion
- `storage_path`
- signed URLs
- `account_value`
- instrucciones completas de pago
- tokens
- secretos
- PIN
- wallet privada

## Reglas de deteccion iniciales

- `off_platform_platform_bypass`: frases como `por fuera`, `fuera de la app`, `fuera de NODO`, `sin NODO`, `directo conmigo`.
- `off_platform_external_contact`: frases con canal/contacto externo como WhatsApp, Telegram, Instagram, email, telefono o usuario externo cuando el contexto indica contacto directo.
- Contextos fisicos neutrales como `por fuera del borde` no deben crear alerta.

## Comportamiento seguro

- La deteccion no autoriza acciones admin.
- La deteccion no bloquea el mensaje.
- La deteccion no declara fraude confirmado.
- La deteccion solo crea una alerta operativa para revision.
- Si falla la persistencia de la alerta, el mensaje ya validado no se bloquea; se registra un error operativo seguro sin cuerpo del mensaje.
