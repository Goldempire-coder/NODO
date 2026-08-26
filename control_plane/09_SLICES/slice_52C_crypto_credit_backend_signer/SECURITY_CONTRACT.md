# SECURITY_CONTRACT.md

## Activos

- signer private key;
- signer public address/version;
- purchase ref;
- autorizacion EIP-712;
- configuracion de contrato/token/red/treasury;
- credit wallet;
- credits ledger;
- fondos recibidos por NODO;
- negocio comprador.

## Custodia Del Signer

### Produccion

Produccion no debe custodiar la private key del signer como variable plana en
Railway/env. La opcion preferida es un servicio de firma separado o KMS/HSM con:

- allowlist de operacion unica: firmar `PaymentAuthorization`;
- acceso desde backend por identidad de servicio;
- auditoria de cada firma;
- rate limit;
- rotacion;
- alertas Admin;
- sin capacidad de mover fondos.

Si no existe KMS/HSM en el MVP, se requiere decision Owner explicita y gate de
riesgo antes de fondos reales. Esa excepcion no puede declararse produccion
segura sin auditoria separada.

### Staging/Testnet

Staging/testnet puede usar signer temporal si:

- no se usa wallet oficial;
- no se usan fondos reales relevantes;
- la key no se imprime ni se guarda en repo;
- se marca como temporal;
- se rota antes de produccion;
- se valida con montos pequenos;
- existe alerta de firma y de rotacion.

## Prohibido

- signer key en frontend;
- signer key en repo;
- signer key en logs/audit/evidencia;
- signer key en screenshots;
- signer key reutilizada como treasury;
- signer key reutilizada como owner/multisig;
- endpoint que firme typed data arbitraria enviada por frontend/admin;
- aceptar amount, token, chain, treasury, contrato, version, expiry o ref desde
  frontend como autoridad.

## Firmas

El backend solo solicita firma sobre snapshots creados internamente:

- negocio derivado de sesion;
- paquete oficial;
- monto oficial;
- payer wallet validada;
- chain/token/contrato/treasury allowlisted;
- expiracion corta;
- purchase ref aleatorio;
- contract version esperada.

El digest/fingerprint puede guardarse para auditoria. La private key nunca.

## Rate Limits Y Costos

Crear autorizaciones es una superficie de costo y abuso. Debe tener limites por:

- usuario;
- negocio;
- IP hasheada;
- compras pendientes por negocio;
- idempotency key.

Politica minima antes de habilitar 52C fuera de pruebas:

- 5 creaciones/reemisiones por usuario cada 10 minutos;
- 5 creaciones/reemisiones por negocio cada 10 minutos;
- 20 creaciones/reemisiones por IP hasheada cada 10 minutos;
- maximo 3 compras `base_usdc_contract` no terminales por negocio;
- el replay idempotente no crea otra compra ni consume otro cupo pendiente;
- staging/produccion usa limitador compartido;
- si el limitador compartido falla, crear/reemitir falla cerrado y no firma.

Las IP solo se usan como clave hasheada de limitacion; no se agregan en claro a
audit metadata. Los limites se aplican en backend, nunca solo en frontend.

No debe haber polling de blockchain por compras sin transaccion. No debe firmar
repetidamente si existe una autorizacion vigente para la misma compra.

La lectura de reanudacion es bajo demanda, privada y `no-store`. No reemite ni
firma como efecto lateral. El frontend normal no solicita ni envia `tx_hash`.

Para `base_usdc_contract`, un hash presentado por usuario se rechaza y no se
persiste. El watcher solo confia en el evento del contrato oficial ligado al
`purchase_ref` esperado.

## Rotacion

Rotar signer invalida autorizaciones pendientes firmadas por el signer anterior.
El backend debe:

- registrar evento de rotacion;
- alertar Admin;
- permitir reemision controlada para compras pendientes no vencidas/no pagadas;
- bloquear pagos nuevos si la configuracion signer/contrato diverge.

## Failure Mode

Ante signer ausente, contrato pausado, configuracion incompleta, RPC requerido
caido para comprobar pausa o divergencia de contrato:

- fallar cerrado;
- no crear compra pagable o dejarla no pagable;
- no acreditar;
- mensaje neutral;
- audit/alerta segura.

## Wallet Handoff Efimero

- JWT, refresh token, cookie, PIN y Telegram `initData` nunca viajan a MetaMask.
- Deeplink contiene solo token opaco en fragmento; la pagina lo elimina con
  `history.replaceState` y lo conserva solo en memoria.
- Backend persiste SHA-256 del token con TTL cinco minutos y una gracia corta
  exclusivamente para informar expiracion neutral.
- Challenge incluye origen backend, handoff, nonce, Base chain ID y expiracion.
- `personal_sign` prueba control; no autoriza pago ni transfiere fondos.
- Creacion limita usuario, negocio e IP. Challenge/claim limitan IP y handoff.
- Redis compartido es obligatorio en staging/produccion.
- Claim revalida usuario activo, negocio aprobado, owner link activo y PIN.
- Replay identico devuelve el mismo resultado; otro claim no reutiliza la
  capacidad.
- Auditoria usa handoff ID y wallet enmascarada, nunca token o firma completos.

## Ejecucion Testnet En Wallet

- Solo Base Sepolia `84532` y snapshots backend con `is_testnet = true` son
  pagables en 52C2F-S1; mainnet falla cerrado en frontend.
- Token, vault, monto, payer, referencia, version, expiracion y firma provienen
  del snapshot backend. La UI no acepta campos editables equivalentes.
- `approve` usa exactamente `expected_amount_units`; no existe aprobacion
  ilimitada.
- `pay` envia valor nativo cero y calldata del contrato firmado. La wallet
  muestra y autoriza cada transaccion.
- Cambio de cuenta/red o expiracion estricta borra o bloquea el estado pagable.
- Respuestas del provider, firmas y hashes de transaccion no se registran ni se
  envian al backend por este flujo.
- No hay polling. La confirmacion y acreditacion pertenecen al watcher
  contractual exact-once.
