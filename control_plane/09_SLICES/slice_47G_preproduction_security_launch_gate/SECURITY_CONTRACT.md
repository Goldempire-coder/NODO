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

## Slice 47G2 - Upload hardening documental

- Comprobantes manuales de creditos, documentos de Business Intake y el camino
  legacy interno de verificacion aceptan solo JPG, PNG, WebP y PDF, maximo 5 MB.
- El backend valida los bytes antes de storage. No confia en nombre, extension o
  MIME declarado como prueba del tipo real.
- JPG, PNG y WebP deben decodificar correctamente y coincidir con el MIME
  declarado. PDF requiere encabezado PDF valido y marcador final `%%EOF`; no se
  ejecuta, renderiza ni interpreta contenido activo.
- Storage y metadata usan MIME y extension canonicos.
- Un rechazo ocurre antes de crear compra, documento, `file_asset`, evento,
  audit, notificacion Admin u objeto en storage.
- El error publico es neutral y no expone parser, bytes, rutas ni metadata
  interna.

## Gate 8 - Salida

El slice solo puede cerrar como `READY_FOR_OWNER_REVIEW` si entrega:

- evidencia de comandos;
- resultados de advisor;
- lista de secretos rotados o pendientes;
- blockers;
- riesgos residuales;
- decision explicita de no declarar `READY_FOR_REAL_USE`.

## Slice 47G1 - Data/cost protection

- Observability aplica cuotas compartidas por actor+surface y por IP hasheada.
- Marketplace usa una cuota Redis compartida de `30` busquedas por usuario y
  `120` por IP hasheada cada `60` segundos; conserva `429 RATE_LIMITED` y los
  filtros existentes.
- Ambas rutas fallan cerradas si Redis queda no disponible. El fallback local
  sigue permitido para rutas existentes no incluidas en 47G1, pero no es
  autoridad para estas rutas costosas.
- Los rechazos no persisten eventos ni registran payloads, IPs crudas, tokens o
  datos privados.
- Redis no autoriza pagos, permisos, ownership ni estado financiero.
