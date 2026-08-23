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

No ejecutar deploy desde este paquete sin una aprobacion Owner separada.
