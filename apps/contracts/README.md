# NODO Contracts

Paquete local para contratos de cobro de creditos publicitarios.

Estado actual: `52A1_LOCAL_ONLY_NOT_FOR_DEPLOYMENT`.

Incluye:

- `NODOCreditPaymentVaultSigned`: contrato V2 con autorizacion EIP-712 firmada
  por NODO.
- mocks ERC20 para pruebas locales.
- pruebas Hardhat locales sin backend, sin staging, sin wallet real y sin fondos.

Comandos:

```powershell
pnpm --filter @nodo/contracts build
pnpm --filter @nodo/contracts test
```

Plan offline Base Sepolia, sin RPC ni transaccion:

```powershell
$env:NODO_BASE_SEPOLIA_VAULT_TREASURY="<public-testnet-address>"
$env:NODO_BASE_SEPOLIA_VAULT_OWNER="<public-testnet-address>"
$env:NODO_BASE_SEPOLIA_VAULT_AUTHORIZED_SIGNER="<public-testnet-address>"
pnpm --filter @nodo/contracts run plan:base-sepolia-vault
```

El procedimiento completo y el gate Owner viven en
`operations/sops/BASE_SEPOLIA_VAULT_DEPLOYMENT_SOP.md`. El script de deploy no
acepta private keys por argumentos y no debe ejecutarse sin aprobacion Owner
explicita.

No ejecutar deploy desde este paquete sin una aprobacion Owner separada.
