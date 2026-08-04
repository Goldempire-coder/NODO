# Builder Prompt - Slice 47G

Actua como Builder senior de NODO bajo AFOS.

Objetivo: preparar el gate de seguridad preproduccion. Este slice no es una
feature; es la revision final para que NODO no llegue a produccion con secretos
viejos, llaves expuestas, Telegram mal validado, Supabase abierto, storage
publico, IDOR, CORS laxo, headers faltantes o dependencias vulnerables.

Skills a usar:

- security-and-hardening
- secret-guard
- deps-doctor
- source-driven-development
- supabase-postgres-best-practices
- browser-testing-with-devtools
- api-and-interface-design
- ci-cd-and-automation
- test-driven-development

Trabajo inicial obligatorio:

1. Lee este slice completo y los slices 47A-47F.
2. Lee `SECRETS_POLICY.md`, `AUTH_TELEGRAM.md`, `SURFACE_ACCESS_POLICY.md`,
   `RBAC_PERMISSION_MATRIX.md`, `ENVIRONMENT_VARIABLES.md`,
   `REAL_SERVICES_STAGING_SETUP.md` y contratos activos de orden/chat/pagos.
3. No modifiques archivos en la primera respuesta.
4. Entrega `BUILDER_UNDERSTANDING_REPORT` con:
   - mapa de secretos por entorno usando solo nombres;
   - que variables son backend-only y cuales pueden ser publicas;
   - estado actual de Telegram auth/initData;
   - estado actual de Supabase RLS/advisor/grants;
   - estado actual de storage y signed URLs;
   - endpoints sensibles y matriz IDOR;
   - CORS/CSP/headers actuales;
   - dependency/supply-chain status;
   - riesgos criticos/altos/medios;
   - plan de implementacion por mini-fixes;
   - pruebas automaticas y manuales;
   - archivos probables;
   - que NO vas a tocar.

Reglas duras:

- No imprimir secretos.
- No usar comandos que listen variables con valores crudos.
- No rotar secretos reales sin aprobacion explicita del Owner.
- No tocar produccion.
- No borrar datos.
- No abrir RLS ni crear policies permisivas.
- No relajar CORS/CSP/auth/RBAC por conveniencia.
- No cambiar reglas financieras, estados, creditos, Zelle, USDT o reputacion.
- No declarar `READY_FOR_REAL_USE`.

Validacion minima esperada despues de implementar, si el Owner aprueba:

- secret scan de diff/repo/historial;
- bundle frontend scan;
- Supabase Advisor con `security_findings = 0`;
- SQL catalog check de RLS/grants;
- tests de Telegram auth manipulada;
- tests IDOR de orden/chat/adjuntos/pagos/soporte/admin;
- CORS/CSP/headers verificados;
- dependency audit triageado;
- smoke autenticado Cliente, Negocio y Admin en staging.
