# QA.md

## Pruebas Smart Contract

Con mock ERC20:

- constructor rechaza direcciones cero;
- `pay` rechaza `purchaseRef = 0` dentro de la autorizacion;
- `pay` rechaza `amount = 0` dentro de la autorizacion;
- `pay` rechaza firma invalida;
- `pay` rechaza signer incorrecto;
- `pay` rechaza payer distinto a `msg.sender`;
- `pay` rechaza monto alterado;
- `pay` rechaza chain incorrecta;
- `pay` rechaza contrato incorrecto;
- `pay` rechaza version incorrecta;
- `pay` rechaza autorizacion expirada;
- `pay` rechaza autorizacion cuando `block.timestamp == validUntil`;
- `pay` acepta autorizacion en `validUntil - 1` y la rechaza despues del limite;
- `pay` transfiere token del pagador a treasury;
- `pay` emite `NodoCreditPaymentReceived` con datos exactos;
- receipt contiene Transfer del token desde payer hacia treasury por el monto;
- `purchaseRef` queda single-use;
- segundo `pay` con mismo ref revierte;
- si transfer falla, la transaccion revierte y ref no queda usado;
- pause bloquea `pay`;
- unpause restaura `pay`;
- receive/fallback rechazan ETH/BNB nativo;
- sweep envia balance atrapado a treasury;
- sweep requiere owner, rechaza balance cero y no emite
  `NodoCreditPaymentReceived`;
- allowance o balance insuficiente revierten sin consumir `purchaseRef` ni
  transferir fondos a treasury;
- owner no puede cambiar treasury/token porque no existen setters.
- transferencia de ownership requiere aceptacion en dos pasos;
- un pago parcial consume el ref y no permite sumar otro pago al mismo ref;
- un tercero que observa el ref no puede acreditar otra compra con ese ref;
- owner puede rotar `authorizedSigner`;
- no-owner no puede rotar `authorizedSigner`;
- `renounceOwnership` revierte;

## Pruebas Backend

- create purchase genera `purchase_ref` unico;
- replay de create purchase devuelve mismo `purchase_ref`;
- create purchase exige `payer_wallet_address` EVM valido;
- backend firma autorizacion EIP-712 con payer, monto, chain, contrato, version
  y expiracion del snapshot;
- tx sin evento de contrato responde `ONCHAIN_PAYMENT_NOT_CONTRACT_BOUND`;
- evento NODO sin Transfer ERC20 canonico coincidente se rechaza;
- evento de contrato falso se rechaza;
- chain incorrecta se rechaza;
- token incorrecto se rechaza;
- treasury incorrecto se rechaza;
- purchase_ref mismatch se rechaza;
- payer mismatch se rechaza;
- monto insuficiente queda `under_review`;
- sobrepago queda segun politica contratada, sin credito extra automatico;
- autorizacion expirada no acredita;
- evento duplicado no duplica ledger;
- dos compras intentando usar el mismo evento: una sola acredita;
- compra expirada queda `under_review`;
- RPC caido no acredita;
- Redis caido no acredita ni elimina el guard exact-once PostgreSQL;
- frontend alterando chain/token/contract/treasury/amount no cambia el snapshot;
- wallet directa con hash publico nunca auto-acredita;
- PostgreSQL exact-once con concurrencia real.

## Pruebas De Fuente Y Configuracion

- Base 8453 y USDC Base coinciden con fuentes oficiales;
- BSC 56 coincide con BNB Chain oficial;
- no existe configuracion BSC activa sin fuente oficial del emisor para token y
  direccion exacta;
- contrato falso, token falso, chain incorrecta y treasury incorrecta fallan
  cerrados;
- configuracion faltante no inicia watcher ni acepta compras.

## Pruebas UI

- Negocio ve red, token, contrato, monto y expiracion.
- Copy no promete escrow, proteccion de fondos, garantia de pago ni remesa.
- UI no pide ni guarda seed/private key.
- UI no permite elegir token/red fuera del contrato activo.
- Si wallet no esta disponible, muestra camino manual seguro o instruccion clara.
- Error de red/token equivocado es tranquilo y accionable.

## Smoke Staging

Solo con aprobacion Owner:

1. deploy testnet o staging contract;
2. configurar backend staging con contrato temporal;
3. crear negocio sintetico;
4. crear compra Starter;
5. pagar monto pequeno exacto;
6. verificar un ledger y un saldo;
7. reintentar submit/watcher y confirmar cero duplicados;
8. probar tx directa a wallet y confirmar cero credito;
9. pausar contrato y confirmar que `pay` falla;
10. registrar evidencia enmascarada.

No se ejecuta smoke con fondos reales. Antes de staging se usa testnet y luego,
solo con aprobacion Owner, wallet temporal y monto pequeno.

## Gate De Deploy Base Sepolia 52C2G-S0

- plan offline no conecta RPC ni crea transacciones;
- chain queda fijada a `84532`;
- token queda fijado al USDC oficial de Base Sepolia;
- treasury, owner y authorized signer rechazan valores faltantes, invalidos o
  cero;
- deploy exige aprobacion Owner literal antes de abrir la conexion de red;
- post-deploy comprueba bytecode, version 2, token, treasury, owner, signer y
  estado de pausa;
- errores del tooling son neutrales y no imprimen RPC ni secretos;
- contrato, wallet y variables backend siguen sin activarse hasta un slice
  separado.

## Evidencia Requerida

- commit SHA frontend/backend;
- chain id;
- contrato enmascarado;
- token enmascarado;
- purchase id publico o interno enmascarado;
- tx hash enmascarado;
- ledger id;
- saldo antes/despues;
- logs sin secretos;
- Secret Guard PASS;
- build/test PASS.
