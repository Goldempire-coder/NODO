# CHANGE_MANAGEMENT

Estado: OFFICIAL
Ultima actualizacion: 2026-07-11

## Regla

Ningun cambio se considera listo solo porque compila. Debe tener evidencia de build, tests, seguridad, migraciones si aplica, rollback y operacion.

## Antes de cambiar staging

1. Confirmar slice o ticket.
2. Revisar `control_plane/00_GOVERNANCE/ENGINEERING_GUARDRAILS.md`.
3. Ejecutar:
   ```powershell
   python -m pytest apps\api\tests -q
   python -m ruff check apps\api scripts
   python -m compileall apps\api apps\web\src scripts
   corepack pnpm --filter @nodo/web build
   ```
4. Si toca dependencias frontend:
   ```powershell
   corepack pnpm audit --prod
   ```
5. Si toca DB staging, usar solo scripts con guardrails.

## Deploy

No existe script de deploy versionado en repo para Railway o Cloudflare Pages. El procedimiento de deploy queda `PARTIALLY VALIDATED` hasta documentar comandos exactos o provider workflow.

## Rollback

Rollback provider no esta automatizado en repo. Debe documentarse antes de produccion.
