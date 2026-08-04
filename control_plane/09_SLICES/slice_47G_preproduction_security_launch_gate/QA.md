# Slice 47G QA

Estado: CONTRACTS_DRAFT_READY_FOR_OWNER_REVIEW

## Pruebas Esperadas

- Secret scan del diff, repo e historial sin valores reales.
- Bundle frontend sin tokens, DB URLs, Redis URLs, service role, JWT secrets,
  bot tokens, private keys ni webhook secrets.
- Railway/Cloudflare/Supabase variables revisadas por nombre y entorno, sin
  imprimir valores.
- Supabase `db advisors` contra staging/produccion objetivo con
  `security_findings = 0`.
- SQL catalog check confirma:
  - `rls_disabled_tables = 0`;
  - `anon_table_grants = 0`;
  - `auth_table_grants = 0`;
  - `anon/authenticated` sin `USAGE` del schema public.
- Telegram auth rechaza `initData` ausente, firma invalida, fecha vieja y
  `userId` manipulado.
- IDOR rechaza acceso cruzado a:
  - orden ajena;
  - chat ajeno;
  - adjunto ajeno;
  - payment instructions ajenas;
  - Pago Movil ajeno;
  - soporte ajeno;
  - admin sin rol.
- CORS solo permite origenes aprobados.
- CSP/headers de seguridad presentes en frontend y backend.
- File upload rechaza tipo invalido, tamano excesivo y recurso ajeno.
- Errores no exponen stack trace, SQL, storage path ni secretos.
- Rate limits activos en auth, ordenes, chat, soporte, adjuntos y webhooks.
- Dependency audit triageado sin fixes forzados.

## Smoke Manual

- Abrir Mini App Cliente en Telegram y navegador externo.
- Abrir Mini App Negocio en Telegram y navegador externo.
- Confirmar que fuera de Telegram no se puede operar sin auth valida.
- Crear orden de prueba, chat, adjunto y cierre sin fuga de datos en consola.
- Revisar Supabase Advisor despues de aplicar migraciones.
- Revisar paneles Railway/Cloudflare/Supabase por variables de entorno.

## Criterio De Paso

- Cero hallazgos criticos o altos sin mitigacion.
- Cero secretos reales en repo, historial, bundle o logs revisados.
- Cero hallazgos de seguridad en Supabase Advisor.
- Todos los endpoints sensibles tienen pruebas de ownership/RBAC.
- El Owner aprueba explicitamente cualquier secreto pendiente de rotacion.

## Criterio De Bloqueo

- Cualquier llave backend-only en frontend.
- Cualquier tabla publica sin RLS o con grant directo a `anon/authenticated`.
- Cualquier endpoint que permita IDOR en ordenes, chat, adjuntos, soporte,
  Pago Movil, payment instructions o admin.
- Cualquier bot token, DB URL, Redis URL, JWT secret o service role filtrado.
- Cualquier dependencia critica/alta alcanzable sin plan de mitigacion.
