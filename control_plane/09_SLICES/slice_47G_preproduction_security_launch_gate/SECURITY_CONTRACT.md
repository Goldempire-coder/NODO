# Slice 47G Security Contract

Estado: CONTRACTS_DRAFT_READY_FOR_OWNER_REVIEW

## Limites De Confianza

| Superficie | Tratamiento |
|---|---|
| Telegram Web / Mini App | No confiable. Puede inspeccionarse y manipularse. |
| Frontend Cloudflare | Publico. Nunca contiene secretos backend-only. |
| Backend Railway | Boundary de autorizacion, validacion y reglas de negocio. |
| Supabase/Postgres | Fuente canonica. Cerrado por RLS y privilegios minimos. |
| Supabase/R2 Storage | Privado. Acceso solo por URLs temporales auditadas. |
| Redis/Upstash | Cache/locks/rate limit. Nunca fuente canonica de dinero. |
| Webhooks Telegram/proveedores | Entrada externa firmada/secreta y rate limited. |

## Gate 1 - Secretos

- Produccion debe usar secretos nuevos, no heredados de staging/dev.
- Rotar antes de uso real: Telegram bot tokens, JWT secrets, DB, Redis,
  Supabase service role, storage, webhook secrets, Cloudflare/Railway tokens y
  cualquier proveedor activo.
- El reporte solo muestra nombres, estado y fecha de rotacion; nunca valores.
- Si un secreto estuvo en GitHub o en un log, se asume comprometido y se revoca.

## Gate 2 - Frontend Expuesto

- El bundle no puede contener `DATABASE_URL`, `REDIS_URL`, service role,
  bot token, JWT secret, private keys, webhook secrets ni storage credentials.
- `NEXT_PUBLIC_*` no reemplaza auth, RBAC, RLS ni validacion backend.
- Cualquier dato sensible mostrado al cliente debe venir de un endpoint
  autorizado y con allowlist.

## Gate 3 - Telegram

- Backend valida `initData`, firma, `auth_date` y usuario.
- El frontend no puede mandar un `userId` como autoridad.
- Bot tokens y webhook secrets son backend-only.
- Webhooks responden genericamente ante errores y no imprimen payload sensible.

## Gate 4 - Supabase/Postgres

- Todas las tablas en `public` tienen RLS activo.
- `anon` y `authenticated` no tienen permisos directos sobre tablas,
  secuencias, funciones ni schema public de datos canonicos.
- Supabase Security Advisor debe reportar `security_findings = 0`.
- Cualquier tabla nueva debe nacer cerrada o tener migracion que lo demuestre.

## Gate 5 - API/RBAC

- Cada endpoint sensible valida actor, rol, ownership y estado.
- Recursos ajenos responden con error generico cuando aplique, sin filtrar
  existencia.
- No hay stack traces ni errores internos visibles.
- Mutaciones criticas usan idempotencia, rate limit y transiciones validas.

## Gate 6 - Chat Y Adjuntos

- Mensajes se tratan como texto, no HTML.
- Adjuntos validan tamano, tipo, ownership, recurso y estado.
- `storage_path`, hashes completos, signed URLs y metadata cruda no aparecen en
  respuestas publicas ni logs.
- Admin/Support solo ven evidencia por rutas auditadas y acciones explicitas.

## Gate 7 - Supply Chain

- El lockfile canonico debe estar comprometido.
- Audits de dependencias se triagean por severidad y alcanzabilidad.
- No se permite `audit fix --force` sin revision humana.
- Nuevas dependencias requieren revision de mantenimiento, origen y scripts.

## Gate 8 - Salida

El slice solo puede cerrar como `READY_FOR_OWNER_REVIEW` si entrega:

- evidencia de comandos;
- resultados de advisor;
- lista de secretos rotados o pendientes;
- blockers;
- riesgos residuales;
- decision explicita de no declarar `READY_FOR_REAL_USE`.
