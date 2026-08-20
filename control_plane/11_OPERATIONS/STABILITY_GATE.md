# STABILITY_GATE.md

Gate operativo obligatorio para evitar que un arreglo rompa otra parte de NODO.

Este documento gobierna cambios antes de staging, smoke y uso real controlado. No
reemplaza `DEPLOY_READINESS_GATE.md`; lo complementa con los flujos sagrados de
Cliente, Negocio y Admin.

## Objetivo

Antes de subir cualquier candidato, demostrar que el cambio:

- arreglo el problema reportado;
- no cambio logica fuera del scope aprobado;
- no rompio Cliente, Negocio, Admin, soporte, creditos, anuncios ni disputas;
- no aumento riesgo de costo, extraccion de datos o errores silenciosos.

## Cuando aplica

Este gate aplica si el cambio toca o puede afectar cualquiera de estas areas:

- acceso, login, sesiones, PIN, roles o business access links;
- Admin Web, Cliente Mini App o Negocio Mini App;
- anuncios, marketplace, ordenes, chat, soporte o disputas;
- creditos, referidos, ledger, pagos manuales u on-chain;
- uploads, storage, URLs firmadas, Telegram, webhooks o notificaciones;
- polling, paginacion, rate limits, cache o performance;
- copy legal/confianza donde pueda parecer custodia, escrow o garantia.

Si el cambio es solo documental, el builder debe decirlo y aun asi pasar el
gate documental: diff limpio, scope claro, contradicciones revisadas y no
declarar readiness de runtime.

## Reglas no negociables

- No mezclar feature nueva con fix de bug.
- No tocar archivos fuera del mapa aprobado.
- No cambiar pagos, creditos, ordenes, acceso o estados si el slice no lo pide.
- No "limpiar" codigo no relacionado.
- No desplegar con worktree sucio o candidato sin commits logicos.
- No declarar `READY_FOR_REAL_USE` ni `READY_FOR_PRODUCTION`.
- No usar staging como prueba si frontend y backend no reportan el mismo SHA.
- No usar datos reales sensibles en evidencia: tokens, telefonos completos,
  documentos, comprobantes, wallets privadas, cookies o `initData`.

## Responsabilidades

### Builder

Antes de editar:

- Entrega un mapa de archivos permitidos.
- Entrega una lista de archivos prohibidos.
- Nombra logica que no puede cambiar.
- Define la prueba roja o evidencia que reproduce el bug.

Al terminar:

- Reporta archivos tocados y por que.
- Reporta pruebas ejecutadas y no ejecutadas.
- Reporta riesgos pendientes.
- Confirma explicitamente lo que no toco.

### Validator

- Repite pruebas criticas del slice.
- Ejecuta smoke local o staging segun corresponda.
- Revisa consola, network, scroll, mobile y datos antes/despues.
- Marca `BLOCKED` si falta evidencia real.

### Owner

- Decide si el resultado pasa a staging o uso real controlado.
- Autoriza cualquier mutacion de staging, migracion, deploy o prueba con fondos.

## Flujo de candidato limpio

Un candidato estable debe cumplir:

1. `git status --short --branch` sin cambios no explicados.
2. Commits logicos, pequenos y revisables.
3. `git diff --check` PASS.
4. Secret scan PASS sobre diff y archivos tocados.
5. Backend tests dirigidos PASS.
6. Frontend build PASS si se toca web.
7. Suite API completa PASS si se toca backend compartido, estado, auth, pagos,
   creditos, ordenes, soporte o seguridad.
8. Staging solo si Railway/Cloudflare/Supabase/Redis estan sanos y el deploy
   puede probar el candidato exacto.

## Flujos sagrados

Estos flujos no pueden romperse por cambios laterales. Si un slice toca una
superficie cercana, debe probar el subconjunto afectado.

### Admin: negocio y acceso

- Admin ve negocios con lista scrolleable y paginada.
- Admin filtra por ID o nombre cuando aplique.
- Admin aprueba negocio desde Intake.
- Admin puede bloquear y desbloquear negocio con razon.
- Admin puede bloquear y desbloquear cliente con razon.
- Admin puede ver diagnostico de acceso del negocio sin exponer secretos.
- El diagnostico backend manda: negocio, dueno, rol, vinculo owner y Telegram.
- Reactivar negocio no debe crear duplicados inconsistentes.
- Accion exitosa con refresh fallido muestra exito local y pide actualizar.

### Negocio Mini App

- Dueno aprobado entra a la Mini App Negocio.
- Negocio puede ponerse online/offline y el estado visual coincide con backend.
- Negocio crea anuncio si tiene credito, capacidad, metodo activo y no hay hold.
- Negocio ve anuncios propios, ordenes abiertas, por verificar e historial sin
  cargas automaticas pesadas.
- Listas largas tienen scroll y `Cargar mas`.
- Confirmar pago consume el credito correcto una sola vez.
- Si el cliente reporto pago, negocio no puede rechazar/cerrar directo; debe
  reportar problema/disputa.

### Cliente Mini App

- Cliente entra por Telegram, completa perfil y no vuelve a onboarding tras
  recargar.
- Cliente ve marketplace solo con negocios elegibles.
- Cliente busca, abre detalle, crea orden y ve instrucciones.
- Cliente reporta pago, chatea, confirma recibido, califica y ve historial.
- Listas largas tienen scroll y paginacion.
- Copy no promete custodia, escrow, garantia, recuperacion ni entrega segura.

### Ordenes, pagos y disputas

- Crear orden es idempotente.
- Reportar pago es idempotente.
- Confirmar pago consume credito exactamente una vez.
- Resolver disputa a favor de cliente/negocio/cancelacion mueve credito,
  capacidad y anuncio segun contrato vigente.
- Orden `payment_rejected` historica puede resolverse por Admin sin dejar
  anuncio ocupado ni credito perdido.
- Chat queda investigable cuando hay disputa.

### Creditos y referidos

- Comprar creditos no acredita hasta verificacion/aprobacion backend.
- Wallet/ledger no quedan negativos.
- Compra manual requiere revision Admin.
- On-chain valida red, token, wallet destino, monto, expiracion y tx/log usado.
- Replays no duplican ledger ni wallet.
- Referido no permite self-referral.
- Un negocio referido solo genera un bonus valido.
- Bonus de referido se acredita una sola vez y aparece en ledger.
- Admin puede auditar quien refirio a quien cuando exista la pantalla/report.

### Soporte

- Lista de tickets activa/archivada tiene scroll y `Cargar mas`.
- Detalle de ticket mantiene chat con scroll interno.
- Adjuntos se descargan solo por accion explicita.
- Soporte no cambia ordenes, creditos ni anuncios salvo endpoints contratados.
- Reporte estructurado de operacion crea ticket/hold sin exponer negocio al
  cliente.
- Cerrar ticket no libera hold operativo.

### Seguridad y costo

- Rutas privadas responden `Cache-Control: private, no-store`, incluso errores.
- Rate limit activo en auth, marketplace, observability, chat/soporte segun
  contrato.
- Polling solo corre con pantalla visible y sin requests solapadas.
- Uploads validan bytes reales antes de storage.
- Paginacion usa limite duro y cursor estable en listas criticas.
- No hay `storage_path`, signed URL, token, wallet privada ni telefono completo
  en listas publicas o respuestas no autorizadas.

### UI y accesibilidad

- Desktop 1440x900 sin overflow horizontal.
- Tablet 1024x768 sin contenido atrapado.
- Mobile 390x844 sin botones fuera de pantalla.
- Paneles con listas largas tienen scroll interno.
- Detalles con conversaciones tienen header compacto y chat scrolleable.
- Botones criticos tienen razon obligatoria, confirmacion clara y foco manejado.
- Texto largo no rompe layout ni desplaza la app hacia un lado.

## Comandos minimos

Usar los comandos equivalentes del repo si cambian los scripts. Reportar salida
resumida, no logs enormes.

```text
git status --short --branch
git diff --check
python -m compileall apps/api/app apps/api/tests
ruff check apps/api
pnpm --filter @nodo/web build
pytest -q apps/api/tests/<tests dirigidos>
pytest -q apps/api/tests
```

Si un comando no aplica, reportar `NOT_APPLICABLE` y la razon. Si no se pudo
ejecutar, reportar `NOT_TESTED` y la causa.

## Smoke local recomendado

Antes de staging, con datos sinteticos:

1. Admin login y dashboard.
2. Admin lista/detalle de negocios, clientes, ordenes, disputas, creditos,
   audit, intake, soporte y notificaciones.
3. Cliente onboarding, marketplace, orden, pago reportado, chat e historial.
4. Negocio acceso, online/offline, metodo, capacidad, anuncio, orden, pago y
   soporte.
5. Scroll y responsive en 1440x900, 1024x768 y 390x844.
6. Consola del navegador sin errores.
7. Network sin loops, 401/403 inesperados o requests infinitas.

## Smoke staging recomendado

Solo despues de candidato limpio y deploy sano:

1. Confirmar frontend `/version.json`.
2. Confirmar backend `/api/v1/version`.
3. Confirmar mismo SHA que HEAD aprobado.
4. Confirmar `/health` y `/ready`.
5. Probar Admin con sesion real autorizada.
6. Probar Cliente y Negocio en Telegram/WebView real.
7. Registrar antes/despues de creditos, ordenes, anuncios, capacidad, holds y
   disputas cuando haya mutaciones.

Si Railway, Cloudflare, Supabase, Redis o Telegram estan degradados, el smoke
queda `BLOCKED_BY_PROVIDER` y no se reemplaza por una conclusion falsa.

## Evidencia requerida

Cada reporte final debe incluir:

```text
Estado:
Objetivo:
Archivos tocados:
Archivos no tocados importantes:
Prueba roja:
Validacion automatica:
Smoke local:
Smoke staging:
Datos antes/despues si hubo mutacion:
Riesgos pendientes:
No acciones:
Readiness permitido:
```

## Estados permitidos

- `BLOCKED`: falta decision, acceso, proveedor, datos o evidencia.
- `CHANGES_REQUIRED`: hay hallazgos que deben corregirse.
- `READY_FOR_VALIDATOR_REVIEW`: localmente coherente, espera validacion.
- `READY_FOR_OWNER_REVIEW`: validado y listo para decision owner.

Prohibido para builders:

- `READY_FOR_REAL_USE`
- `READY_FOR_PRODUCTION`

## Builder prompt obligatorio

Todo prompt de fix debe incluir esta seccion:

```text
Usa estos skills: gstack-lite-careful, gstack-lite-spec, test-driven-development,
gstack-lite-review, ponytail-lite-review, security-and-hardening si toca datos,
auth, pagos, uploads o Admin.

Antes de editar:
- Mapea archivos permitidos y prohibidos.
- Explica la logica que NO vas a cambiar.
- Crea prueba roja o evidencia reproducible.

Durante el fix:
- Cambia solo lo necesario.
- No hagas refactors no relacionados.
- No toques pagos/creditos/ordenes/acceso si no estan en scope.

Validacion:
- Ejecuta pruebas dirigidas.
- Ejecuta build si toca frontend.
- Ejecuta suite amplia si toca backend compartido.
- Ejecuta smoke visual si toca UI.
- Reporta NOT_TESTED con razon cuando aplique.
```

## Relacion con otros gates

- `DEPLOY_READINESS_GATE.md`: gate productivo y de deploy.
- `ACCEPTANCE_CRITERIA.md`: criterios de aceptacion de producto.
- `MONITORING_ALERTS.md`: senales operativas.
- `REAL_SERVICES_STAGING_SETUP.md`: staging real.

Este gate debe ejecutarse antes de pedir deploy y antes de cualquier smoke real.
