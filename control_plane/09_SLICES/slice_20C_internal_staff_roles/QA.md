# QA.md

Tests obligatorios:

- Staff sin permiso no ve cola.
- Staff solo ve tickets asignados cuando el scope es `assigned_only`.
- `support_agent` responde ticket asignado pero no bloquea usuario.
- `support_agent` no resuelve disputa formal.
- `support_agent` no aprueba credito.
- `support_lead` asigna tickets solo con permiso activo.
- Staff revocado pierde acceso inmediatamente.
- Permisos frontend no sustituyen backend.
- Mutaciones staff requieren reason e `Idempotency-Key`.
- Audit completo para invitacion, activacion, suspension, revocacion y permisos.
- Masking correcto.
- Scans sin secretos, `storage_path`, `account_value` ni signed URLs persistidas.
