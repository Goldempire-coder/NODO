# BUILDER_PROMPT.md

> Prompt historico, no autoridad normativa despues de 52C-S0. Las decisiones
> vigentes estan en `CREDITS_API.md` y los API contracts 52A/52C.

Usa estos skills:

- `$gstack-lite-careful`
- `$gstack-lite-spec`
- `$gstack-lite-security`
- `$api-and-interface-design`
- `$source-driven-development`
- `$test-driven-development` solo si Owner autoriza implementacion

Modo inicial:

```txt
MAPPING_ONLY_THEN_OWNER_APPROVAL
```

Objetivo:

Disenar, no implementar todavia, el contrato crypto para pagos de paquetes de
creditos publicitarios NODO. El objetivo es cerrar el riesgo de reclamar hashes
publicos ajenos y preparar una ruta segura hacia un contrato EVM.

Archivos permitidos en mapping:

- `control_plane/09_SLICES/slice_52A_crypto_credit_payment_contract/*`
- `control_plane/03_DOMAIN_RULES/ONCHAIN_CREDIT_TOPUPS_MASTER.md`
- `control_plane/06_API_CONTRACTS/CREDITS_API.md`
- `control_plane/04_DATA/DATA_MODEL_MASTER.md`
- `control_plane/04_DATA/DATABASE_CONSTRAINTS.md`
- `control_plane/04_DATA/ENUMS_AND_STATUS_MASTER.md`

Archivos prohibidos sin aprobacion Owner separada:

- `apps/api/**`
- `apps/web/**`
- `database/migrations/**`
- Solidity/runtime nuevo
- Railway/Cloudflare/Supabase/Upstash
- `.env*`
- scripts de deploy

No hacer:

- no deploy;
- no commit;
- no migracion;
- no instalar dependencias;
- no configurar wallet;
- no mover fondos;
- no tocar staging/produccion;
- no cambiar creditos, ordenes, disputas, marketplace o P2P.

Tareas:

1. Mapear el flujo actual `base_usdc_onchain`.
2. Confirmar fuentes oficiales de Base, USDC Base, BSC y tokens candidatos.
3. Explicar por que wallet directa no prueba intencion.
4. Proponer contrato `NODOCreditPaymentVaultSigned` minimalista:
   - token immutable;
   - treasury immutable;
   - authorized signer rotatable;
   - purchase ref single-use;
   - autorizacion EIP-712 firmada por NODO;
   - payer, monto, chain, contrato, version y expiracion amarrados por firma;
   - evento canonico;
   - pausa;
   - sweep solo hacia treasury;
   - no native token;
   - no upgradeable.
5. Definir cambios API/data necesarios para `purchase_ref` y contrato oficial.
   La API debe incluir `payer_wallet_address` para poder firmar una
   autorizacion segura. El frontend no puede imponer monto, red, token,
   contrato, treasury ni expiracion.
6. Definir matriz de amenazas y pruebas.
7. Identificar decisiones Owner pendientes:
   - Base primero o BSC primero;
   - token MVP;
   - toolkit Solidity;
   - auditoria externa;
   - wallet temporal;
   - quien controla owner/multisig.

Validacion:

- `git diff --check`
- Secret Guard sobre docs tocados
- busqueda de contradicciones:
  - `rg -n "base_usdc_onchain|base_usdc_contract|USDT|BSC|purchase_ref|escrow|garantia|custodia" control_plane`

Salida esperada:

- `READY_FOR_OWNER_REVIEW` si solo hubo mapping documental.
- `BLOCKED_BY_OWNER_DECISION` si falta decision de red/token/toolkit.
- Nunca declarar `READY_FOR_REAL_USE`.
