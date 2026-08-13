# 47G4 - Infraestructura Real Security Mapping

Fecha de inspeccion: 2026-08-13

Modo ejecutado: `INSPECTION_ONLY / READ_ONLY`

## Estado

`BLOCKED`

Bloqueo operativo: `BLOCKED_FOR_STAGING_SMOKE`.

La API de staging identifica el mismo commit que el HEAD local. El runtime local
47G4.1 ya genera `/version.json` con una identidad frontend publica y allowlist,
pero el artefacto aun no fue desplegado ni verificado en Cloudflare. Ademas, sin
acceso read-only autorizado a Supabase, Railway, Upstash y Cloudflare no se puede
demostrar el estado real de RLS, grants, buckets, variables, ACL/TLS ni permisos
de proveedor. No se autoriza wallet temporal ni oficial con estas brechas de
evidencia.

## Resumen para Owner

- La API de staging esta disponible, reporta ambiente `staging` y build
  `811bded341dd0a2bae40dc32c3a459333785db65`, igual al HEAD local.
- `/ready` reporta PostgreSQL y Redis disponibles. Esto prueba conectividad en
  ese instante, no RLS, grants, TLS, ACL, backups ni configuracion del proveedor.
- Cliente y Negocio en Cloudflare responden `200`, HTML con `no-store`, CSP y
  assets inmutables cacheables.
- El frontend desplegado aun no publica SHA/build ID. 47G4.1 corrige el artefacto
  local, pero la identidad de staging seguira `NOT_VERIFIED` hasta un deploy
  autorizado y una comparacion HTTP posterior.
- Las rutas privadas consultadas sin token respondieron `401` con
  `Cache-Control: private, no-store`.
- El scan de los chunks iniciales desplegados no encontro nombres de variables
  privadas ni formas de secreto de alta confianza. Esto no cubre todos los
  chunks lazy ni la configuracion privada del proyecto Cloudflare.
- La migracion local `0046` revoca acceso publico y activa RLS, pero su
  aplicacion real en Supabase queda `NOT_VERIFIED`.
- El flujo actual de credito on-chain sigue bloqueado para una wallet oficial:
  exact-once evita doble credito, pero no demuestra que quien reclama un hash
  publico sea quien origino la transferencia.

Conclusion: la infraestructura tiene buenas defensas locales y evidencia HTTP
parcial, pero todavia no esta demostrada para un smoke financiero controlado.

## Preflight y evidencia segura

| Control | Resultado | Evidencia segura |
| --- | --- | --- |
| Repo | VERIFICADO | Rama `codex/intake-admin-review-v2`; HEAD `811bded...`; worktree sucio preexistente preservado. |
| API build | VERIFICADO | `/health`, `/version` y `/api/v1/version` reportaron `staging-811bded` y el HEAD completo. |
| API dependencies | PARCIAL | `/ready` reporto database y Redis `ok`; no prueba seguridad del proveedor. |
| Frontend availability | VERIFICADO | `/` y `/business/` respondieron `200` desde Cloudflare. |
| Frontend build identity | LOCAL_IMPLEMENTED / STAGING_NOT_VERIFIED | 47G4.1 genera `/version.json`; staging no fue mutado ni consultado de nuevo. |
| Private no-store | VERIFICADO | `/api/v1/users/me` y `/api/v1/admin/dashboard` sin token: `401` y `private, no-store`. |
| Static caching | VERIFICADO | HTML `no-store`; JS hasheado `public, max-age=31536000, immutable`. |
| Supabase RLS/grants | NOT_VERIFIED | Solo se inspecciono la migracion local `0046`; no hubo acceso real. |
| Supabase Storage | NOT_VERIFIED | No se consultaron buckets/policies ni se genero URL firmada real. |
| Railway variables/roles | NOT_VERIFIED | No hay CLI/sesion read-only autorizada en este entorno. |
| Redis TLS/ACL | NOT_VERIFIED | La aplicacion conecta, pero no se inspecciono scheme, ACL, IP controls o provider settings. |
| Cloudflare env/roles | NOT_VERIFIED | Solo se inspeccionaron respuestas publicas y chunks iniciales. |
| Semgrep | NOT_TESTED | No esta instalado; no se instalo nada. |
| Secret Guard | PARCIAL/PASS | Sin secreto confirmado; hallazgos fueron nombres/placeholders o identificadores de codigo. |
| Env lint | LOCAL_ONLY | `.env.local` tiene drift respecto a su example; no demuestra staging. |

## Hallazgos

### HIGH - Identidad frontend/backend pendiente de evidencia en staging

La API identifica el HEAD local, pero el deployment actual de Cloudflare Pages
no expone SHA, deployment ID correlacionable ni un `version.json`. El runtime
47G4.1 ya genera el archivo en el export local; falta publicarlo con autorizacion
y comprobarlo contra el backend de staging.

Escenario: se valida un backend nuevo contra un frontend anterior o posterior y
se atribuye un fallo o una proteccion al candidato equivocado.

Gate implementado localmente:

1. `frontend.commit_sha` debe coincidir exactamente con
   `backend.data.build_id` de `/api/v1/version`.
2. `frontend.environment` debe coincidir con `backend.data.environment`.
3. En el script de despliegue controlado, `frontend.commit_sha` tambien debe
   coincidir con el HEAD Git local aprobado.
4. Cualquier valor `unknown`, conflicto de fuentes o mismatch bloquea el smoke.
5. `/version.json` contiene solo `service`, `environment`, `commit_sha`,
   `build_id` y `source`; no publica el entorno completo.
6. Cloudflare Pages usa `CF_PAGES_COMMIT_SHA`; un build manual controlado puede
   usar `NODO_RELEASE_COMMIT_SHA`. Si ambas existen y difieren, la identidad se
   publica como desconocida y el gate falla cerrado.

Pendiente: deploy autorizado y comparacion HTTP de ambos documentos publicos.

No requiere migracion ni cambio financiero.

### HIGH - Seguridad real de Supabase y storage no demostrada

`database/migrations/0046_supabase_public_schema_rls_lockdown.up.sql:3-77`
revoca privileges, habilita RLS y crea un event trigger para tablas nuevas. No
se pudo comprobar que `0046` este en `nodo_schema_migrations`, que todas las
tablas tengan RLS, que `anon/authenticated/public` carezcan de grants, ni que los
buckets sean privados.

Escenario: una tabla o bucket queda accesible por Data API/Storage aunque el
backend aplique ownership correctamente.

Fix minimo: ejecutar las consultas read-only de este documento con una cuenta
Supabase autorizada y guardar solo resultados booleanos/nombres no sensibles.
Un solo grant publico inesperado o bucket `public=true` mantiene el gate
bloqueado.

### HIGH - Hash publico on-chain no prueba ownership del pago

`apps/api/app/modules/credits/schemas.py:21-22` acepta un `tx_hash` enviado por
el negocio. `apps/api/app/modules/credits/onchain.py:212-223` valida el Transfer
hacia la wallet receptora, pero no vincula `tx_from_address` a una identidad o
intencion unica emitida para esa compra. La unique en
`apps/api/app/modules/credits/postgres_onchain.py:236` evita doble uso, pero el
primer reclamante aun podria usar un hash publico ajeno compatible.

Impacto: acreditacion incorrecta de creditos publicitarios. Bloquea wallet
oficial y auto-credito real. 47G4 no cambia este flujo.

Fix minimo futuro: disenar prueba de intencion/ownership no reutilizable por
compra antes de habilitar fondos reales. Requiere contrato separado, threat
model y pruebas PostgreSQL/concurrencia.

### MEDIUM - TLS/ACL de Redis no verificados ni forzados por config

`apps/api/app/shared/rate_limit/redis.py:30-40` usa Redis compartido y permite
modo deny. `apps/api/app/main.py:107` aplica deny a rutas caras. Sin embargo,
`apps/api/app/core/config.py:164` exige presencia de `REDIS_URL`, no scheme TLS,
y las rutas generales conservan fallback local si Redis falla.

Lo correcto que debe conservarse: marketplace y observability fallan cerrados
cuando Redis esta configurado pero no disponible.

Pendiente real: confirmar `rediss://`/TLS, autenticacion, ACL o control
equivalente, rotacion, limites del plan y alertas de disponibilidad en Upstash.

### MEDIUM - CSP permite inline y HSTS no fue observado

`apps/web/public/_headers:5` define CSP, pero permite `script-src 'unsafe-inline'`
y `style-src 'unsafe-inline'`. Las respuestas inspeccionadas de Cloudflare y
Railway no incluyeron `Strict-Transport-Security`.

No es evidencia de bypass actual, pero reduce defensa ante XSS/downgrade. Debe
revisarse con Telegram WebView antes de retirar inline; HSTS puede activarse en
edge solo despues de confirmar todos los subdominios requeridos.

### MEDIUM - No hay alertas agregadas demostradas

El runtime genera senales utiles:

- `backend_request_completed` con ruta, status, latencia y error code;
- `rate_limiter_redis_unavailable`;
- audits de apertura de disputa y acceso a signed URLs;
- `onchain_payment_verification_failed` y configuracion wallet invalida.

No se demostro que Railway/Sentry/otro proveedor agregue y alerte por bursts de
401/403/429, scraping, URLs firmadas, uploads rechazados, Redis caido o fallos
on-chain. Esto es el alcance recomendado para 47G6.

### MEDIUM - Hostname de Railway induce confusion de entorno

El host publico contiene la palabra `production`, pero `/version` reporta
`environment=staging` y el frontend de staging lo usa. No es un fallo tecnico,
pero aumenta el riesgo de ejecutar smoke, variables o runbooks contra el
entorno incorrecto. Toda evidencia debe validar `/version` antes de actuar.

### LOW - Drift local de env example

Env-lint encontro claves nuevas ausentes en `.env.local` y `BASE_RPC_URL` vacia.
Es evidencia local solamente; los defaults cubren varias claves y no demuestra
el estado de Railway. No debe mezclarse con la validacion real de staging.

## Controles correctos que deben conservarse

- Backend como unica autoridad para DB, storage, rate limit y credito.
- `SUPABASE_SERVICE_ROLE_KEY`, `DATABASE_URL`, `REDIS_URL` y RPC solo backend.
- `next.config.mjs` exporta una allowlist de variables `NEXT_PUBLIC_*`.
- No hay private key, mnemonic, seed phrase o signing key en el flujo de credito.
- Rutas privadas usan `Cache-Control: private, no-store`, incluidos errores.
- HTML no se cachea; assets hasheados si se cachean de forma inmutable.
- Signed URLs requieren endpoint autorizado, ownership/RBAC, audit y TTL maximo
  de 300 segundos; no se persisten en DTOs normales.
- Logging y frontend observability redaccionan tokens, wallets, tx hashes,
  storage paths y signed URLs.
- Redis no es autoridad de dinero, permisos, ownership ni estado de orden.
- Marketplace/observability usan el limiter compartido fail-closed.
- `0046` es fail-closed incluso en down: no reabre grants ni desactiva RLS.

## Consultas Supabase requeridas

Ejecutar solo en SQL Editor read-only/autorizado. No incluir filas de negocio,
PII, secretos ni connection strings en la evidencia.

### Ledger de migracion 0046

```sql
select filename,
       checksum_sha256 is not null as checksum_recorded,
       applied_at is not null as applied
from public.nodo_schema_migrations
where filename = '0046_supabase_public_schema_rls_lockdown.up.sql';
```

Esperado: exactamente una fila, checksum presente.

### RLS en todas las tablas publicas

```sql
select n.nspname as schema_name,
       c.relname as table_name,
       c.relrowsecurity as rls_enabled,
       c.relforcerowsecurity as rls_forced
from pg_catalog.pg_class c
join pg_catalog.pg_namespace n on n.oid = c.relnamespace
where n.nspname = 'public'
  and c.relkind in ('r', 'p')
order by c.relname;
```

Esperado: `rls_enabled=true` en todas. `rls_forced` se inventaria, pero 0046 no
lo exige como sustituto de grants revocados.

### Grants directos y defaults

```sql
select grantee, table_schema, table_name, privilege_type
from information_schema.role_table_grants
where table_schema = 'public'
  and grantee in ('PUBLIC', 'anon', 'authenticated')
order by grantee, table_name, privilege_type;

select defaclrole::regrole as owner_role,
       defaclnamespace::regnamespace as schema_name,
       defaclobjtype,
       defaclacl
from pg_catalog.pg_default_acl
where defaclnamespace = 'public'::regnamespace;
```

Esperado: ninguna capacidad de lectura/escritura para esos roles. El segundo
resultado requiere revision humana de ACL; no publicar valores sensibles.

### Trigger para tablas futuras

```sql
select evtname, evtenabled
from pg_catalog.pg_event_trigger
where evtname = 'nodo_enable_rls_on_public_table_create';
```

Esperado: una fila habilitada.

### Buckets y policies de storage

```sql
select id,
       public,
       file_size_limit is not null as has_size_limit,
       allowed_mime_types is not null as has_mime_allowlist
from storage.buckets
order by id;

select policyname, roles, cmd
from pg_catalog.pg_policies
where schemaname = 'storage'
order by tablename, policyname;
```

Esperado: todos los buckets NODO privados. Ninguna policy debe permitir lectura
anonima de evidencias, documentos, comprobantes, chat, soporte o intake.

## Checklist Railway/backend

Verificar desde acceso read-only y registrar solo `present/missing`, nunca valor:

- `APP_ENV` es staging.
- build SHA coincide con el candidato.
- `DATABASE_URL`, `REDIS_URL`, JWT, Telegram y storage secrets presentes.
- `PRIVATE_STORAGE_MODE=supabase` si ese es el proveedor aprobado.
- `BASE_RPC_URL` y cualquier key RPC solo backend.
- `NODO_CREDIT_RECEIVING_WALLET_BASE` es solo direccion publica backend.
- `ONCHAIN_CREDIT_WATCHER_ENABLED` permanece deshabilitado para fondos reales
  hasta cerrar el riesgo de hash publico.
- ausencia de private keys, mnemonics, seed phrases y signing keys.
- usuarios/proyecto aplican minimo privilegio y MFA segun proveedor.

La evidencia HTTP actual confirma `APP_ENV=staging`, SHA, DB y Redis conectados;
no confirma el resto.

## Checklist Upstash/Redis

- Conexion TLS (`rediss://` o mecanismo equivalente del proveedor).
- Autenticacion activa; endpoint no anonimo.
- ACL/IP restriction cuando el plan lo soporte; documentar si no existe.
- Credencial dedicada a staging y rotacion definida.
- No usar Redis como fuente canonica de dinero, sesiones revocadas, permisos o
  audit durable.
- Marketplace/observability deny durante outage.
- Alertas por errores de conexion, 429 y consumo/cuota.
- Probar `PING`, rate limit e idempotencia solo con autorizacion de staging y
  sin imprimir URL/credencial.

## Checklist Cloudflare/frontend

- Deployment commit coincide con Railway/HEAD aprobado.
- Solo variables publicas permitidas en Pages.
- Ningun secret en deployment variables, source maps o artefactos.
- HTML `no-store`; assets hasheados inmutables.
- CSP revisada para reducir `unsafe-inline` sin romper Telegram WebView.
- HSTS evaluado y activado con alcance seguro.
- Roles del proyecto con minimo privilegio/MFA.
- El hostname Railway llamado `production` se etiqueta explicitamente como
  staging en runbooks y validaciones automaticas.

## Secret scanning

Secret Guard se ejecuto sobre archivos de infraestructura relevantes y sobre
todos los archivos modificados/no rastreados. Los hallazgos fueron revisados sin
imprimir valores:

- placeholders sinteticos en `.env.*.example`;
- nombres canonicos de buckets;
- identificadores `debounce_seconds` y `token_symbol`;
- referencias de rutas documentales en tests/contratos.

No se confirmo un secreto real. El scan en memoria de los chunks iniciales
desplegados no encontro PEM private key, JWT, Stripe live key, Telegram bot
token ni URL con credenciales. Chunks lazy completos, historial Git y variables
reales de proveedores quedan fuera de esta evidencia.

## Cobertura actual de deteccion

| Senal | Existe en runtime | Alerta real demostrada |
| --- | --- | --- |
| Muchos 401/403/429 | Logs por ruta/status/error | NO |
| Scraping/bursts | Rate limits y logs 429 | NO |
| Abuso signed URLs | Rate limit + audit por accion | NO |
| Upload rechazado | 4xx/error code en request log | NO |
| Redis caido | `rate_limiter_redis_unavailable` | NO |
| Cambio de wallet | Proceso documental; no endpoint | NO |
| Disputa abierta | Audit + notificacion Admin interna | Telegram/externa NO DEMOSTRADA |
| Verificador on-chain caido | Audit seguro y estado fail-closed | Alerta sostenida NO |

## Mini-slices recomendados

1. `47G4.1 Build identity`: implementado localmente; falta deploy autorizado y
   evidencia HTTP de `/version.json` frente a `/api/v1/version`.
2. `47G4.2 Provider read-only evidence`: ejecutar SQL/grants/buckets y revisar
   Railway/Upstash/Cloudflare con acceso autorizado.
3. `47G4.3 Edge hardening`: evaluar HSTS y CSP sin romper Telegram WebView.
4. `47G6 Security alerts`: agregar alertas agregadas, deduplicadas y redacted.
5. `47G7 On-chain claim binding`: contrato y runtime separado antes de wallet
   oficial; no resolverlo como parche de infraestructura.
6. `47G8 Controlled staging smoke`: wallet temporal, monto pequeno, rollback y
   evidencia exact-once solo despues de cerrar 47G7 y los gates anteriores.

## Checklist antes de wallet temporal

- [ ] Frontend y backend identifican el mismo SHA aprobado.
- [ ] `0046` aplicada con checksum correcto.
- [ ] Todas las tablas publicas tienen RLS y no grants anon/authenticated/public.
- [ ] Buckets privados y policies revisadas.
- [ ] Railway confirma staging y ausencia de material de firma.
- [ ] Redis TLS/auth/ACL y fail-closed verificados.
- [ ] Cloudflare solo contiene env publicas y no secrets en todos los chunks.
- [ ] Signed URL real: ownership, TTL, no-store y audit comprobados.
- [ ] Alertas 47G6 probadas con payload redacted.
- [ ] Riesgo de reclamar hash publico cerrado por contrato/runtime.
- [ ] Wallet temporal dedicada y monto pequeno aprobados por Owner.
- [ ] Watcher/auto-credito deshabilitado hasta el momento exacto del smoke.
- [ ] Rollback/rotacion documentados y responsables identificados.

## Prompt recomendado para 47G6

```md
# NODO 47G6 - Security And Cost Alerts

Modo inicial: MAPPING_ONLY_THEN_OWNER_APPROVAL.

Objetivo: convertir senales existentes en alertas agregadas, accionables,
deduplicadas y sin PII/secrets. No cambiar pagos, wallet, creditos, auth,
ownership ni estados de negocio.

Mapear y proponer alertas para:
- bursts de 401/403/429 por ruta/surface/IP hasheada;
- scraping de marketplace, soporte e historial;
- abuso de endpoints de signed URL;
- uploads rechazados por contenido;
- `rate_limiter_redis_unavailable` y degradacion Redis;
- cambio/missing/invalid de wallet por proceso de release;
- disputa abierta que requiere revision;
- `onchain_payment_verification_failed` y RPC caido sostenido.

Reglas:
- usar route template y ventanas agregadas, nunca URL cruda;
- no incluir token, cookie, telefono, banco, wallet completa, tx hash completo,
  storage_path, signed URL, mensaje/evidencia ni raw provider response;
- IDs/IPs solo hasheados o public IDs allowlisted;
- dedupe/idempotencia y cooldown para evitar alert storms/costo;
- fallo de alerta no cambia orden, ticket, disputa, credito o wallet;
- separar page vs ticket y enlazar runbook;
- Telegram Admin es salida posible, no autoridad de seguridad;
- primero pruebas rojas y provider adapter local/fake; staging solo con permiso.

Entregar contrato, umbrales iniciales justificados, eventos fuente, RBAC,
redaction, retry/dedupe, pruebas, costo estimado, runbook y plan de smoke. No
deploy, no produccion, no wallet real y no READY_FOR_REAL_USE.
```

## Validacion ejecutada

- `git status --short --branch` y HEAD.
- `git diff --check` antes del documento: PASS, solo warnings CRLF preexistentes.
- HTTP read-only: `/health`, `/ready`, `/version`, `/api/v1/version`, Cliente,
  Negocio y errores privados sin token.
- Headers Cloudflare/Railway y cache de un asset hasheado.
- Scan en memoria de chunks iniciales desplegados, sin guardar artefactos.
- Env-lint local sin imprimir valores.
- Secret Guard redacted sobre infraestructura y worktree modificado.
- Inspeccion local de migracion 0046, storage, rate limit, logging, redaction,
  signed URLs, frontend env allowlist y credit verifier.

## NOT_VERIFIED

- Supabase real: ledger 0046, RLS, grants, default ACL, triggers, buckets,
  policies, backups y roles.
- Railway: inventario de variables, usuarios, MFA, service permissions, logs y
  watcher real.
- Upstash: TLS, auth, ACL/IP controls, plan, cuotas y alertas.
- Cloudflare: commit del deployment, variables reales, roles/MFA y todos los
  chunks lazy/source maps.
- Storage real: upload privado y signed URL autorizada.
- Alert delivery real, Supabase/Railway/Cloudflare/Redis consoles, Telegram
  WebView autenticado y smoke financiero.

## Confirmaciones

- 47G4.1 agrego runtime frontend minimo y publico para identidad de build:
  `/version.json`, la metadata allowlist del frontend y el guard que compara
  frontend, backend y HEAD antes de aceptar un candidato. No se modifico runtime
  backend financiero.
- No se hizo deploy, commit, push, restart ni cambio de variables.
- No se ejecutaron migraciones ni SQL real.
- No se tocaron staging/produccion de forma mutante.
- No se configuro wallet, no se movieron fondos y no se activo auto-credito.
- No se imprimieron secretos, credenciales, URLs privadas ni valores de env.
- No se declara `READY_FOR_REAL_USE` ni `READY_FOR_PRODUCTION`.
