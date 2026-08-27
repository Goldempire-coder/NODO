# Base Sepolia Credit Vault Deployment SOP

Estado: `DRY_RUN_ONLY_AWAITING_OWNER_APPROVAL`

## Objetivo Y Limites

Preparar un deploy reproducible de `NODOCreditPaymentVaultSigned` V2 en Base
Sepolia. Este SOP no autoriza ejecutar el deploy, configurar Railway, activar el
watcher, firmar compras, hacer `approve`/`pay` ni mover fondos.

Fuentes oficiales:

- Base: Base Sepolia usa chain ID `84532`.
  https://docs.base.org/base-chain/quickstart/connecting-to-base
- Circle: USDC de Base Sepolia es
  `0x036CbD53842c5426634e7929541eC2318f3dCF7e`.
  https://developers.circle.com/stablecoins/usdc-contract-addresses
- Hardhat 3: las redes HTTP pueden fijar `chainId` y resolver configuracion de
  forma diferida. Los secretos deben administrarse fuera del repo.
  https://hardhat.org/docs/reference/configuration
  https://hardhat.org/docs/guides/configuration-variables

## Entradas Publicas Requeridas

Definir solo direcciones Base Sepolia verificadas por Owner:

```powershell
$env:NODO_BASE_SEPOLIA_VAULT_TREASURY="<public-testnet-address>"
$env:NODO_BASE_SEPOLIA_VAULT_OWNER="<public-testnet-address>"
$env:NODO_BASE_SEPOLIA_VAULT_AUTHORIZED_SIGNER="<public-testnet-address>"
```

Las tres direcciones deben ser no cero. Treasury, owner y signer deben ser
cuentas de prueba controladas y, preferiblemente, separadas. No reutilizar una
wallet o signer de produccion.

## Plan Offline

Este comando no resuelve RPC, no abre una red y no crea una transaccion:

```powershell
pnpm --filter @nodo/contracts run plan:base-sepolia-vault
```

Revisar que la salida diga:

- `DRY_RUN_ONLY_NO_TRANSACTION`;
- Base Sepolia `84532`;
- version `2`;
- pausa esperada `false` al terminar el constructor;
- direcciones publicas enmascaradas.

## Gate Antes Del Deploy Real

No continuar hasta obtener aprobacion Owner separada que confirme las tres
direcciones publicas, el origen del USDC, la cuenta que pagara gas de testnet y
la ventana de cambio.

Hardhat resuelve `NODO_BASE_SEPOLIA_DEPLOY_RPC_URL` y
`NODO_BASE_SEPOLIA_DEPLOYER_KEY` fuera del script. No pasar ninguno por
argumentos, no escribirlos en el repo y no mostrarlos en terminal, evidencia o
capturas. El script no lee ni imprime esos valores. La cuenta debe contener
solo ETH de prueba suficiente para el deploy.

Inmediatamente antes del comando aprobado, definir el gate no secreto:

```powershell
$env:NODO_BASE_SEPOLIA_VAULT_DEPLOY_APPROVAL="OWNER_APPROVED_BASE_SEPOLIA_VAULT_DEPLOY"
```

Comando reservado para la ejecucion aprobada; **no ejecutarlo en este slice**:

```powershell
pnpm --filter @nodo/contracts run deploy:base-sepolia-vault
```

## Verificacion Automatica

El script aborta antes del deploy si el nombre de red no es `baseSepolia`, el
chain ID no es `84532`, falta la aprobacion o no existe exactamente una cuenta
configurada. Despues de minar con dos confirmaciones, exige:

- bytecode no vacio;
- `CONTRACT_VERSION = 2`;
- `acceptedToken` igual al USDC oficial de Base Sepolia;
- treasury, owner y authorized signer iguales al plan;
- `paused = false`, estado inicial del contrato actual.

Despues de minar imprime la direccion publica con estado
`MINED_PENDING_VERIFICATION`; esto permite recuperar un deploy aunque una lectura
posterior falle. Solo `deploymentStatus: VERIFIED` confirma que todas las
comprobaciones pasaron. Registrar la direccion en evidencia gobernada antes de
cualquier cambio backend. No activar backend, signer ni watcher en el mismo
paso.

## Contencion, Pausa Y Rollback

Un contrato desplegado no puede borrarse ni revertirse. Si alguna comprobacion
falla:

1. no registrar el contrato en backend ni Railway;
2. no firmar autorizaciones y no iniciar watcher;
3. registrar el incidente con direcciones y hashes enmascarados;
4. si el contrato correcto requiere contencion, Owner puede ejecutar `pause()`
   desde su wallet en una accion separada y aprobada;
5. verificar `paused = true` mediante lectura RPC;
6. si token o treasury son incorrectos, abandonar ese deploy y preparar uno
   nuevo, porque ambos campos son immutable;
7. si el signer fue comprometido, pausar primero y luego rotarlo mediante una
   accion Owner separada.

No enviar USDC de prueba hasta completar el deploy, la verificacion, la pausa o
habilitacion deliberada, la configuracion backend y el smoke aprobado.

## Aprobacion Pendiente

Antes del deploy real, Owner debe proporcionar y aprobar las direcciones
publicas de treasury, owner y authorized signer de Base Sepolia. La existencia
de este SOP y del tooling no constituye esa aprobacion.
