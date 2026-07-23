# ACCEPTANCE_COPY.md

Estado: `DRAFT LEGAL_REVIEW_REQUIRED`

Fecha de borrador: 2026-07-21

Textos cortos propuestos para casillas, botones y pantallas de aceptacion en Telegram Mini Apps. No implementar hasta revision legal y aprobacion del owner.

## Cliente - pantalla de aceptacion

### Titulo

Antes de usar NODO

### Texto corto

NODO conecta clientes con negocios aprobados y registra evidencia. NODO no recibe, retiene, mueve ni garantiza fondos. El pago y la entrega ocurren directamente entre cliente y negocio, bajo riesgo propio.

### Checkbox

He leido y acepto los Terminos de NODO y el Acuerdo de Riesgo del Cliente. Entiendo que NODO no custodia fondos ni garantiza pagos, entregas, tasas, tiempos o recuperacion.

### Boton primario

Acepto y continuar

### Boton secundario

No aceptar

### Texto de bloqueo si no acepta

Para usar NODO debes aceptar los terminos vigentes y el acuerdo de riesgo.

## Negocio - pantalla de aceptacion

### Titulo

Acuerdo para operar como negocio

### Texto corto

NODO publica negocios aprobados, registra ordenes y conserva evidencia. Tu negocio opera directamente con el cliente. NODO no recibe, retiene, mueve ni garantiza fondos, pagos, entregas, tasas, disponibilidad o solvencia.

### Checkbox

He leido y acepto los Terminos de NODO y el Acuerdo de Participacion del Negocio. Confirmo que mi negocio es responsable de sus datos, pagos externos, entregas, evidencia, limites y cumplimiento.

### Boton primario

Acepto como negocio

### Boton secundario

No aceptar

### Texto de bloqueo si no acepta

Para operar como negocio en NODO debes aceptar los terminos vigentes y el acuerdo de participacion.

## Re-aceptacion por nueva version

### Cliente

Actualizamos los terminos de NODO. Para continuar, acepta la version vigente. NODO sigue sin custodiar fondos ni garantizar pagos o entregas.

### Negocio

Actualizamos los terminos para negocios. Para seguir operando, acepta la version vigente. Tu negocio sigue siendo responsable de pagos externos, entregas, evidencia y cumplimiento.

## Evidencia minima de aceptacion que debe guardar backend

Guardar un evento inmutable o auditable con:

- `user_id`
- `business_id` si aplica
- `terms_version`
- `client_risk_agreement_version` si aplica
- `business_participation_agreement_version` si aplica
- `accepted_at`
- `ip_hash` si existe y es legalmente permitido
- `user_agent_hash` si existe y es legalmente permitido
- `surface`
- `locale`
- `telegram_user_id_hash` si aplica y es permitido por politica de privacidad
- `acceptance_action`
- `document_set`

Valores sugeridos:

- `surface`: `client_mini_app`, `business_mini_app`, `admin_web`, `business_intake_bot`
- `acceptance_action`: `initial_acceptance`, `version_reacceptance`
- `document_set`: `terms_of_service`, `client_risk_agreement`, `business_participation_agreement`

## Copy que NODO no debe usar

- Fondos garantizados.
- Dinero protegido.
- Transaccion garantizada.
- Entrega garantizada.
- Pago garantizado.
- Solvencia garantizada.
- Recuperacion garantizada.
- Liberamos fondos.
- Retenemos fondos.
- Fondos en custodia.
- Escrow.
- Somos banco.
- Somos casa de cambio.
- Procesamos remesas.
- Aseguramos tu dinero.

