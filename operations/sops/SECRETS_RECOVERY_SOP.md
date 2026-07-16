# SOP: Secrets Recovery

SOP_ID: SOP-SECRETS-RECOVERY-001
Estado de validacion: NOT VALIDATED
Ultima actualizacion: 2026-07-11

## Proposito

Recuperar o rotar secrets/env vars de NODO sin imprimirlos, filtrarlos al frontend ni romper sesiones validas mas de lo necesario.

## Alcance

- Railway backend env.
- Cloudflare Pages public env.
- Supabase service role.
- Database URL.
- Redis URL.
- JWT secrets.
- Telegram bot tokens.
- Base RPC keys.
- Stripe legacy/test secrets si estan activos.

## Cuando usar

- Secret perdido.
- Secret comprometido.
- Provider env inconsistente.
- Restore de entorno requiere reconfigurar secrets.

## Cuando no usar

- Como troubleshooting generico.
- Durante SEV-1 sin Incident Commander.
- Para copiar secrets por chat, capturas o evidencia.

## Permisos requeridos

- Owner approval.
- Acceso provider minimo necesario.
- Dos personas para cambios Tier 0 cuando owner lo requiera.

## Comandos reales

COMMAND NOT AVAILABLE para recuperar secrets provider.

Comando seguro local para verificar ausencia en frontend:

```powershell
rg -n "SUPABASE_SERVICE_ROLE_KEY|DATABASE_URL|REDIS_URL|BOT_TOKEN|BUSINESS_INTAKE_BOT_TOKEN|JWT_SECRET|PRIVATE_KEY|BASE_RPC_API_KEY" apps/web
```

## Riesgos

- Invalidar sesiones activas al rotar JWT secrets.
- Romper bots al rotar tokens sin actualizar webhook.
- Romper storage si service role queda mal configurado.
- Filtrar secrets en evidencia.

## Criterio de exito

- Secret recuperado/rotado solo en provider correcto.
- Frontend no contiene backend secrets.
- `/health`, `/ready`, `/version` OK.
- Smoke Telegram/storage segun secret afectado.
- Evidencia solo muestra presente/ausente, nunca valor.

## Criterio de aborto

- No se puede confirmar entorno.
- Aparece un valor secreto en output.
- Falta owner approval.
- Rotacion JWT sin plan de logout/re-auth.

## Evidencia requerida

- Secret name, no value.
- Provider.
- Entorno.
- Actor autorizado.
- Validacion posterior.

## Estado

BLOCKED para produccion hasta validar con provider.
