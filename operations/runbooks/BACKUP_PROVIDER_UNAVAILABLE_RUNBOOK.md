# RUNBOOK: Backup provider unavailable

Estado de validacion: NOT VALIDATED
Ultima actualizacion: 2026-07-11

## Sintoma

- Supabase/Railway/Cloudflare/Upstash no permite acceder a backups, restore UI/API o deploy history.
- Backup programado falla.
- Restore solicitado no puede iniciarse.

## Severidad inicial

SEV-1 si afecta Tier 0.
SEV-2 si afecta Tier 1/Tier 2 sin perdida actual.

## Primeros cinco minutos

1. Confirmar provider status.
2. Confirmar si es dashboard/API/permisos o servicio caido.
3. No crear backups improvisados con datos reales.
4. Escalar a owner.

## Diagnostico

PROVIDER_ACCESS_REQUIRED.

## Mitigacion

- Mantener sistema en modo conservador.
- Congelar cambios destructivos o migraciones.
- Preparar entorno alterno solo con aprobacion.

## Recuperacion

Depende del provider. COMMAND NOT AVAILABLE en repo.

## Prohibiciones

- No asumir que backup existe sin verlo.
- No descargar dumps reales sin aprobacion privacy/owner.
