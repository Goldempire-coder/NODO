# SOP: Environment Configuration

SOP_ID: SOP-ENV-001
Estado de validacion: PARTIALLY VALIDATED

## Proposito

Configurar variables sin filtrar secretos al frontend.

## Variables backend Railway

Ver `control_plane/11_OPERATIONS/ENVIRONMENT_VARIABLES.md`.

Minimas:

- APP_ENV
- APP_VERSION
- NODO_BUILD_ID
- DATABASE_URL
- REDIS_URL
- JWT_SECRET
- JWT_REFRESH_SECRET
- BOT_TOKEN
- BUSINESS_INTAKE_BOT_TOKEN
- PRIVATE_STORAGE_MODE
- SUPABASE_URL
- SUPABASE_SERVICE_ROLE_KEY
- BASE_RPC_URL
- NODO_CREDIT_RECEIVING_WALLET_BASE

## Variables Cloudflare Pages

Solo publicas:

- NEXT_PUBLIC_API_BASE_URL
- NEXT_PUBLIC_TELEGRAM_BOT_USERNAME
- NEXT_PUBLIC_APP_ENV

## Procedimiento

1. Copiar desde plantilla, nunca desde chat con secretos.
2. Validar que Cloudflare no tenga secretos backend.
3. Ejecutar build local:
   ```powershell
   corepack pnpm --filter @nodo/web build
   ```
4. Escanear:
   ```powershell
   rg -n "SUPABASE_SERVICE_ROLE_KEY|DATABASE_URL|REDIS_URL|BOT_TOKEN|BUSINESS_INTAKE_BOT_TOKEN|JWT_SECRET|PRIVATE_KEY|BASE_RPC_API_KEY" apps/web
   ```

## Criterio de exito

No hay secretos backend en frontend ni repo.
