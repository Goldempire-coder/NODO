# SCOPE - slice_31B_backup_restore_contracts_and_sops

## Construir en este slice

- Documentacion oficial de backup/restore/DR.
- Matriz Tier/RTO/RPO/ownership/backup/restore.
- SOPs y runbooks operativos.
- Acceptance criteria de readiness para futuros drills.

## No construir en este slice

- Scripts de backup.
- Scripts de restore.
- Migraciones.
- Backend.
- Frontend.
- Integraciones provider.
- Export de datos reales.
- Restore drill real.
- Deploy.
- `READY_FOR_REAL_USE`.

## Componentes cubiertos

- Supabase PostgreSQL.
- Supabase Storage privado.
- Redis/Upstash.
- Railway backend.
- Cloudflare frontend.
- Secrets/env vars.
- Telegram bots/webhooks.
- Base RPC/on-chain watcher.
- Audit logs.
- `file_assets`.
- `notification_jobs`.
