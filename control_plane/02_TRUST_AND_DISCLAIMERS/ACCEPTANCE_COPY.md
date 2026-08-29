# ACCEPTANCE_COPY.md

Estado: `DRAFT LEGAL_REVIEW_REQUIRED`

Fecha de borrador: 2026-08-29

Textos cortos propuestos para casillas, botones y pantallas de aceptacion en Telegram Mini Apps. No implementar hasta revision legal y aprobacion del owner.

## Cliente - pantalla de aceptacion

### Titulo

Antes de usar NODO

### Texto corto

NODO conecta clientes con negocios registrados y registra evidencia. NODO no recibe, retiene, mueve ni garantiza fondos. El pago y la entrega ocurren directamente entre cliente y negocio, bajo riesgo propio.

### Checkbox

He leido y acepto los Terminos de NODO y el Acuerdo de Riesgo del Cliente. Entiendo que NODO no custodia fondos ni garantiza pagos, entregas, tasas, tiempos o recuperacion.

### Boton primario

Acepto y continuar

### Boton secundario

No aceptar

### Texto de bloqueo si no acepta

Para usar NODO debes aceptar los terminos vigentes y el acuerdo de riesgo.

## Negocio - pantalla de aceptacion general

### Titulo

Terminos para operar como negocio

### Texto corto

NODO permite registrar tu negocio, publicar anuncios, operar servicios disponibles y comprar creditos internos para usar la plataforma. Tu negocio sigue siendo responsable de sus datos, anuncios, clientes, pagos externos, entregas y cumplimiento.

### Checkbox

He leido y acepto los Terminos de NODO y los Terminos de Negocio NODO. Confirmo que mi negocio es responsable de sus datos, anuncios, pagos externos, entregas, evidencia, limites y cumplimiento.

### Boton primario

Acepto como negocio

### Boton secundario

No aceptar

### Texto de bloqueo si no acepta

Para operar como negocio en NODO debes aceptar los terminos vigentes para negocios.

## Negocio - compra de creditos

### Titulo

Antes de comprar creditos

### Texto corto

Los creditos NODO son internos de la plataforma y sirven para publicar u operar anuncios y otros servicios habilitados. No son dinero, no son saldo custodiado, no son retirables y no son transferibles.

### Checkbox

Acepto los Terminos de Negocio NODO. Entiendo que compro creditos internos para usar servicios de la plataforma, que los creditos no son dinero, no son retirables ni transferibles, y que los pagos digitales se acreditan cuando NODO los confirma.

### Boton primario

Aceptar y comprar

### Texto de bloqueo si no acepta

Para comprar creditos debes aceptar los terminos vigentes de negocio y creditos.

## Re-aceptacion por nueva version

### Cliente

Actualizamos los terminos de NODO. Para continuar, acepta la version vigente. NODO sigue sin custodiar fondos ni garantizar pagos o entregas.

### Negocio

Actualizamos los terminos para negocios. Para seguir operando o comprar creditos, acepta la version vigente. Tu negocio sigue siendo responsable de sus datos, anuncios, pagos externos, entregas, evidencia y cumplimiento.

## Evidencia minima de aceptacion que debe guardar backend

Guardar un evento inmutable o auditable con:

- `user_id`
- `business_id` si aplica
- `terms_version`
- `client_risk_agreement_version` si aplica
- `business_participation_agreement_version` si aplica
- `business_credit_terms_version` si aplica
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
- `document_set`: `terms_of_service`, `client_risk_agreement`, `business_terms`, `business_credit_terms`

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
