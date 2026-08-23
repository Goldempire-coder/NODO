# SECURITY_CONTRACT.md

## Activos A Proteger

- fondos recibidos por NODO;
- saldo de creditos publicitarios;
- ledger de creditos;
- configuracion de contrato/token/red;
- wallet/tesoreria receptora;
- RPC keys;
- Admin/Super Admin;
- negocio que compra creditos.

## Amenazas Principales

### Hash Publico Reclamado Por Otro Negocio

Mitigacion:

- acreditar solo eventos del contrato oficial;
- evento debe incluir `purchase_ref`;
- `purchase_ref` debe existir en una compra del negocio;
- tx hash sin evento oficial no acredita.
- el backend deriva la compra desde `purchase_ref`, no desde quien presenta el
  hash ni desde `payer`.

### Front-running Del Purchase Ref

Mitigacion:

- ref aleatorio de 32 bytes, no enumerable;
- solo se entrega al negocio autenticado de la compra;
- el contrato exige autorizacion EIP-712 firmada por NODO;
- la autorizacion amarra `purchase_ref`, `payer`, `amount`, `chain_id`,
  `verifying_contract`, `contract_version` y `valid_until`;
- un tercero que vea el ref no puede pagar desde otra wallet ni cambiar monto,
  red, contrato o expiracion sin invalidar la firma;
- si la wallet autorizada esta comprometida, el contrato no puede distinguir al
  atacante del dueno real; ese caso queda como seguridad de la wallet del
  negocio y proceso de soporte.

### Cambio Malicioso De Wallet

Mitigacion:

- `treasury` immutable en contrato;
- cambiar destino requiere desplegar contrato nuevo;
- backend solo acepta contratos allowlisted por entorno;
- release debe alertar a Telegram Admin con fingerprint enmascarado.
- `authorizedSigner` puede rotarse, pero no puede cambiar tesoreria ni mover
  fondos.

### Contrato Falso

Mitigacion:

- backend valida direccion exacta del contrato por chain;
- no aceptar eventos por firma solamente;
- no aceptar token por simbolo;
- no aceptar datos enviados por frontend como autoridad.

### Phishing De Direccion O Red

Mitigacion:

- UI toma chain, token y contrato solo del snapshot backend;
- mostrar nombre de red y fingerprints abreviados, nunca una direccion copiada
  desde texto libre, chat o Telegram;
- wallet debe confirmar chain id y contrato antes de firmar;
- backend rechaza cualquier evento fuera de allowlist aunque la UI haya sido
  manipulada;
- cambios de contrato/treasury requieren release auditado y alerta.

### Token Incorrecto

Mitigacion:

- un contrato por token;
- token immutable;
- backend valida token address del evento;
- no mezclar USDT manual TRC20 con Base/BSC EVM.

### Pago Parcial O Sobrepago

Mitigacion:

- el amount firmado debe coincidir con el monto esperado del paquete;
- el usuario no puede bajar o subir el monto sin romper la firma;
- cualquier diferencia entre evento, Transfer ERC20 y snapshot backend queda
  `under_review`, sin credito automatico;
- no sumar pagos parciales en MVP;
- `purchase_ref` single-use.

### Reentrancy / Token No Estandar

Mitigacion:

- `nonReentrant`;
- `SafeERC20`;
- checks-effects-interactions;
- pruebas con mock token que devuelve false, revierte y no devuelve boolean.

### Admin Comprometido

Mitigacion:

- owner preferido: multisig o cuenta dedicada, no wallet personal diaria;
- owner no puede cambiar token ni treasury;
- owner solo pausa/despausa y barre hacia treasury immutable;
- eventos de pausa/sweep;
- alertas Admin fuera de la misma wallet.

### Frontend Manipulado

Mitigacion:

- backend recalcula package, amount, token, chain, contrato y expiry;
- frontend solo muestra instrucciones;
- cualquier parametro de usuario se valida contra snapshot durable.

### Watcher, RPC Y Redis Caidos

Mitigacion:

- no acreditar si receipt, confirmaciones o logs no pueden verificarse;
- Redis solo coordina costo/locks y nunca autoriza creditos;
- PostgreSQL constraints y transaccion exact-once siguen siendo autoridad;
- reintentos con backoff, limites por rango de bloques y checkpoint durable;
- una caida conserva el estado anterior y genera alerta, sin marcar pago como
  rechazado ni acreditado por inferencia.

### Treasury Comprometida

Mitigacion:

- backend no guarda llaves ni mueve fondos;
- treasury preferida: multisig separada del owner operativo del vault;
- pausa detiene cobros nuevos, pero no recupera fondos ya extraidos;
- rotacion exige contrato nuevo, allowlist nueva, aviso visible y runbook;
- nunca cambiar silenciosamente una direccion mostrada al usuario.

### Token Del Emisor O Proxy Comprometido

`acceptedToken` immutable fija la direccion, no el comportamiento futuro de un
token controlado mediante proxy por su emisor. La seleccion de token conserva
riesgo de emisor, blacklist, pausa y upgrades. Este riesgo debe aceptarse por
Owner y revisarse antes de cada despliegue.

## Secretos

Nunca guardar ni imprimir:

- private key;
- seed phrase;
- mnemonic;
- RPC URL con key;
- admin token;
- raw provider response.

El contrato no requiere private key de NODO para cobrar. El despliegue si
requiere una wallet de deploy, fuera del backend y fuera del repo.

El diseno firmado introduce un secreto operativo nuevo: la private key del
`authorizedSigner`. Esa llave solo firma autorizaciones; no debe ser treasury,
owner, admin personal ni wallet diaria. Debe poder rotarse y cada rotacion debe
generar auditoria y alerta Admin.

## Gates Antes De Dinero Real

- contrato probado localmente;
- testnet deploy probado;
- address verificada en explorer;
- source publicado/verificado;
- firma EIP-712 probada contra backend y contrato;
- review independiente;
- backend watcher probado con PostgreSQL real;
- staging con wallet temporal y monto pequeno;
- exact-once probado;
- alerta Telegram probada;
- rollback documentado;
- Owner aprueba red/token/contrato.

## No Declarar

- no `READY_FOR_REAL_USE`;
- no `READY_FOR_PRODUCTION`;
- no wallet oficial;
- no fondos reales.
