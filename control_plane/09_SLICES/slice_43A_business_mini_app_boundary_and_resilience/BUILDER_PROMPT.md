# Builder Prompt

SKILLS A USAR

- security-and-hardening
- code-review-and-quality
- test-driven-development
- frontend-ui-engineering
- observability-and-instrumentation
- api-and-interface-design
- debugging-and-error-recovery
- git-workflow-and-versioning

AFOS es la autoridad principal. Este slice gobierna el alcance.

ESTADO ESPERADO

`READY_FOR_OWNER_REVIEW` o `BLOCKED_BY_EXPLICIT_EVIDENCE`.

OBJETIVO

Implementa `slice_43A_business_mini_app_boundary_and_resilience`.

Corrige el primer paquete de riesgos de la Mini App Negocio:

1. No exponer `risk_level` ni senales internas al negocio.
2. Evitar que creditos/contadores desaparezcan por fallos temporales.
3. Corregir medicion falsa de transiciones.
4. Manejar error de copiar identificacion del negocio.

ANTES DE TOCAR ARCHIVOS

1. Confirma:
   - `Get-Location`
   - `git status --short --branch`
   - rama actual
   - archivos modificados/no rastreados
2. Lee todos los documentos de:
   `control_plane/09_SLICES/slice_43A_business_mini_app_boundary_and_resilience/`
3. Reporta brevemente:
   - archivos que vas a tocar
   - pruebas que vas a agregar o actualizar
   - riesgos de alcance

CONSTRUIR

- Remover `risk_level` del DTO de sesion/surface de negocio.
- Revisar `trust_level` contra contrato vigente. Si esta prohibido para negocio,
  removerlo; si hay conflicto, bloquear y explicar.
- Agregar prueba negativa para que el DTO no-admin no incluya campos internos.
- En creditos, conservar ultimo wallet/saldo valido ante error temporal y
  mostrar estado degradado.
- En admin notifications unread count, conservar ultimo contador valido ante
  error temporal y mostrar estado degradado.
- En Mini App Negocio, medir transicion desde accion de navegar hasta render de
  la vista nueva.
- En perfil negocio, mostrar feedback si falla copiar la identificacion.

NO TOCAR

- No deploy.
- No produccion.
- No migraciones.
- No reset DB.
- No pagos reales.
- No Base USDC lifecycle.
- No precios.
- No paginacion completa.
- No cambio de auth/token storage.
- No rediseño grande de soporte.
- No tocar los cinco borradores legales no rastreados.
- No declarar `READY_FOR_REAL_USE`.

QA OBLIGATORIO

Ejecuta:

```powershell
python -m pytest apps/api/tests/test_auth_lifecycle_static.py -q --tb=short
python -m pytest apps/api/tests/test_business_access_control.py -q --tb=short
python -m pytest apps/api/tests/test_admin_operational_notifications.py -q --tb=short
python -m pytest apps/api/tests -q
python -m ruff check apps/api scripts
python -m compileall apps/api apps/web/src scripts
pnpm --filter @nodo/web build
git diff --check
```

Si `pnpm` falla porque falta Node en PATH, usa:

```powershell
$env:PATH="C:\Users\carlo\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin;$env:PATH"
pnpm --filter @nodo/web build
```

SALIDA FINAL

Entrega:

1. ESTADO
2. RESUMEN SIN TECNICISMOS
3. ARCHIVOS TOCADOS
4. QUE CAMBIO
5. QUE NO TOCASTE
6. VALIDACION EJECUTADA
7. RIESGOS PENDIENTES
8. CONFIRMACION DE NO DEPLOY / NO PRODUCCION / NO SECRETOS
