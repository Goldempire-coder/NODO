# AFOS Three-App Predeploy Audit

Estado: `THREE_APP_AUDIT_READY_FOR_OWNER_REVIEW`

Fecha: 2026-07-17

Auditor: Codex

Ambiente evaluado: worktree local `C:\Users\carlo\Documents\Playground\NODO`

## 1. Veredicto

| Superficie | Estado AFOS | Veredicto |
| --- | --- | --- |
| Admin Web | `IN_PROGRESS` | Tiene consola operativa, modo emergencia, incidentes, UX friction y auditoria, pero falta deploy candidate limpio y prueba staging real. |
| Business Mini App | `IN_PROGRESS` | Tiene PIN, Zelle/USDT TRC20, anuncios, creditos Base USDC, ordenes y soporte, pero falta prueba real Telegram tras deploy. |
| Client Mini App | `IN_PROGRESS` | Tiene terminos, marketplace, ordenes, pago, chat, soporte y deep links, pero falta prueba real Telegram contra staging. |
| Backend compartido | `IN_PROGRESS` | Autoridad central fuerte, idempotencia y ledger; faltan restore provider, alertas reales, scheduler/operacion completa y release inmutable. |
| Produccion | `NOT_READY` | No hay Production Gate ni release candidate limpio con evidencia de staging. |

## 2. Evidencia ejecutada en este audit

### 2.1 Smoke local de tres superficies

Comando:

```powershell
$env:PYTHONPATH='apps/api'; python scripts/local_surface_cross_smoke.py --output evidence/slice_runs/slice_41_local_surface_cross_smoke.json
```

Resultado: `PASS`.

Evidencia:

- `evidence/slice_runs/slice_41_local_surface_cross_smoke.json`

Cobertura observada:

- Cliente acepta terminos, guarda perfil, busca negocio y crea orden.
- Negocio aprobado configura PIN, crea anuncio, ve orden y confirma pago.
- Admin ve dashboard, orden y audit logs.
- Intake bot crea solicitud y admin la ve.
- Soporte crea, asigna, responde, resuelve y cierra ticket.
- Compra Base USDC se crea como `pending_payment`, con red `base_mainnet`, token `USDC`, wallet destino presente y sin acreditar por pantalla.
- Respuestas revisadas no exponen `storage_path`.
- Respuesta admin de orden no expone cuenta completa usada en fixture.

### 2.2 Tests focales

Comando:

```powershell
python -m pytest apps/api/tests/test_frontend_observability_ingest.py apps/api/tests/test_admin_console.py apps/api/tests/test_credits_referrals.py -q --tb=short
```

Resultado: `37 passed, 1 warning`.

### 2.3 Diff hygiene

Comando:

```powershell
git diff --check
```

Resultado: `PASS` con warnings de normalizacion CRLF/LF en archivos frontend.

### 2.4 Scan sensible focal

Comando ejecutado con patrones focales para API/RPC, wallet exacta, private keys y AWS keys. El valor exacto no se copia en este reporte para no repetir el dato sensible.

Resultado: `FAIL documental`.

Hallazgo:

- `control_plane/09_SLICES/slice_36_business_mini_app_afos_release_hardening/QA.md:14` contiene un comando con fragmento de API/RPC y wallet publica exacta.

Impacto:

- No es codigo ejecutable de producto.
- No prueba exposicion de private key.
- Si bloquea una politica fuerte de "no dejar rastros sensibles en repo/GitHub".

## 3. Controles AFOS evaluados

### 3.1 Arquitectura y responsabilidad

Estado: `IN_PROGRESS`

Evidencia:

- Admin Web esta separado en `apps/web/src/hooks/admin-web/*` y `apps/web/src/screens/admin-web/*`.
- Business Mini App esta separada en `apps/web/src/hooks/business-mini-app/*` y `apps/web/src/screens/business-app/*`.
- Client Mini App esta separada en `apps/web/src/hooks/workspace/*` y `apps/web/src/screens/client/*`.
- Admin CSS fue separado hacia `apps/web/src/app/admin-web.css`.
- `control_plane/09_SLICES/slice_40A_commit_boundary_and_evidence_pack/COMMIT_BOUNDARIES.md` ya define paquetes A-G para no desplegar todo mezclado.

PASS parcial:

- Las responsabilidades ya no estan concentradas en una sola pantalla gigante.
- Las tres apps tienen modelos/hooks propios.

FAIL / pendiente:

- El worktree sigue mezclando admin, negocio, cliente, observabilidad, emergencia, terminos y limpieza.
- No hay todavia release candidate unico, inmutable y desplegable.

### 3.2 Backend como autoridad

Estado: `PASS parcial`

Evidencia:

- Cliente no crea orden sin terminos vigentes: `require_current_user_with_terms` en `apps/api/app/modules/orders/remitter_routes.py`.
- Crear orden se bloquea con modo emergencia: `require_platform_operational(..., operation="order_create")`.
- Crear/reactivar/republicar anuncio exige backend + PIN + idempotencia.
- Comprar creditos Base USDC exige backend + PIN + idempotencia.
- El pago Base USDC no acredita por pegar tx hash; usa verifier backend y ledger.
- Negocio online/offline se valida en backend con PIN e idempotencia.

PASS parcial:

- Las reglas sensibles viven en backend.
- La app no es fuente de verdad para dinero, ordenes, estados ni aprobaciones.

FAIL / pendiente:

- No se probo todavia en staging real que la UI de Telegram no se quede en botones titilando o sin respuesta.

### 3.3 Identidad, autorizacion y aislamiento

Estado: `PASS parcial`

Evidencia:

- Admin usa `require_current_user` y policy de admin en servicio.
- Mutaciones admin requieren razon e idempotency key.
- Business usa `require_active_business_access` para acceso propio.
- Credit wallet/ledger son propios del negocio y tienen tests de acceso.
- Smoke local confirma que negocio no puede listar credit purchases admin.

PASS parcial:

- Hay denegacion backend para roles equivocados.
- Hay audit de acciones admin.

FAIL / pendiente:

- MFA/admin real fuera de repo no validado.
- No hay prueba staging real de sesiones revocadas o rol cambiado en vivo.

### 3.4 Dinero, creditos, wallets y ledger

Estado: `IN_PROGRESS`

Evidencia:

- Base USDC crea compra `pending_payment`.
- Wallet destino sale de config backend.
- `submit_base_usdc_tx_hash` verifica tx contra monto, destino y confirmaciones.
- Creditos se agregan por ledger cuando verification pasa.
- Tests focales de creditos/referrals pasan.

PASS parcial:

- No hay acreditacion por pantalla.
- Ledger y wallet se prueban localmente.
- Admin adjustment no puede saltar autorizacion normal.

FAIL / pendiente:

- Falta staging real controlado para confirmar acreditacion automatica de creditos con dinero falso/test tx/verifier controlado.
- Falta reconciliacion provider real y alertas operativas de creditos atascados.

### 3.5 Notificaciones y jobs

Estado: `IN_PROGRESS`

Evidencia:

- Jobs/notificaciones aparecen en incident console.
- El sender Telegram ya fue limitado a notificaciones inmediatas de orden segun el trabajo previo.
- Tests de jobs/notificaciones existen.

PASS parcial:

- Existe outbox y dedupe para notificaciones.

FAIL / pendiente:

- No hay evidencia de envio real Telegram staging.
- Scheduler/ejecucion automatica del sender no queda demostrado como operacion continua.

### 3.6 Observabilidad, logs y UX friction

Estado: `PASS parcial`

Evidencia:

- `clientTelemetry.ts` registra screen views, acciones, errores API, acciones lentas y transiciones lentas.
- Backend observability redacts metadata sensible.
- Admin tiene endpoint `GET /api/v1/admin/ux-friction`.
- Admin tiene incident console.

PASS parcial:

- El panel admin puede decir donde se traban usuarios si los flags de ingest estan activos.
- No graba sesiones ni IP address en el contrato del slice 39.

FAIL / pendiente:

- Falta verificar flags reales de staging.
- Falta recorrido real de una operacion con request_id/correlation_id desde Telegram hasta logs provider.

### 3.7 Seguridad y secretos

Estado: `FAIL documental / PASS parcial producto`

PASS parcial:

- No se encontro private key, AWS key ni Coinbase RPC endpoint completo en codigo de producto con el scan focal.
- La politica de redaccion incluye `account_value`, `storage_path`, `signed_url`, `wallet`, `zelle`, `pin`, `tx_hash`, tokens y secretos.

FAIL:

- Hay una linea documental con fragmento de API/RPC y wallet exacta en `slice_36.../QA.md`.

Accion requerida:

- Limpiar esa linea antes de commit/deploy/GitHub.
- Ejecutar scan completo de historia Git antes de release.

### 3.8 Backups, restore, rollback y operacion

Estado: `IN_PROGRESS`

Evidencia:

- Existen contratos y SOPs de backup/restore.
- Hay pruebas sinteticas locales historicas.

FAIL / pendiente:

- No hay restore provider/staging real validado en este audit.
- No hay rollback real de artefacto desplegado.
- No hay alertas disparadas y recibidas de extremo a extremo.

### 3.9 Experiencia real en Telegram

Estado: `IN_PROGRESS`

Evidencia:

- Smoke local une backend de cliente, negocio y admin.

FAIL / pendiente:

- No se ejecuto walkthrough real dentro de Telegram para:
  - Botones de negocio.
  - Botones de cliente.
  - Compra de creditos.
  - Crear orden.
  - Notificaciones fuera/dentro de la app.
  - Admin panel contra staging.

Este punto sigue siendo clave porque el usuario ha observado fallos reales de botones que los tests locales no detectaban.

## 4. Bloqueantes antes de deploy

1. `MIXED_WORKTREE_RELEASE_BOUNDARY`
   - El repo sigue mezclando multiples paquetes.
   - No hacer deploy como una sola masa.

2. `SENSITIVE_DOC_TRACE_FOUND`
   - Limpiar `control_plane/09_SLICES/slice_36_business_mini_app_afos_release_hardening/QA.md:14`.

3. `REAL_TELEGRAM_WALKTHROUGH_NOT_EXECUTED`
   - Falta prueba staging real en Telegram para cliente y negocio.

4. `AUTO_CREDIT_STAGING_FLOW_NOT_PROVEN`
   - Falta prueba controlada de acreditacion automatica de creditos.

5. `NOTIFICATION_DELIVERY_REAL_NOT_PROVEN`
   - Falta probar Telegram real y operacion automatica del sender.

6. `RESTORE_ROLLBACK_ALERTS_NOT_PROVEN`
   - Falta restore provider, rollback y alertas end-to-end.

## 5. Siguiente plan recomendado

### 41A - Clean candidate boundary

- Seleccionar paquetes del `COMMIT_BOUNDARIES.md`.
- Limpiar el hallazgo sensible documental.
- Re-ejecutar scan completo.
- Commit por frontera.

### 41B - Staging three-app deploy candidate

- Desplegar solo el paquete candidato.
- Confirmar variables/flags de observabilidad.
- Smoke post-deploy.

### 41C - Real Telegram walkthrough, fake money

- Cliente: terminos, perfil, marketplace, orden, pago reportado, chat, soporte.
- Negocio: PIN, online/offline, Zelle/USDT TRC20, anuncio, orden, confirmacion, notificaciones.
- Admin: incidentes, UX, orden, audit, soporte, creditos.

### 41D - Credit auto-accrual proof

- Probar Base USDC en staging con verifier controlado o test transaction permitida.
- Confirmar que credito se acredita una sola vez.
- Confirmar ledger, wallet y admin audit.

### 41E - Ops hardening gate

- Restore staging.
- Rollback de artefacto.
- Alertas criticas disparadas/recibidas.
- Cost/budget review.

## 6. Conclusion

NODO esta mas cerca de un staging serio que de una demo suelta. La arquitectura ya va en buena direccion: backend manda, las apps estan separadas, admin observa, negocio tiene PIN, cliente tiene terminos, y el smoke local une las tres superficies.

Pero AFOS no permite pasar a produccion todavia. El proximo movimiento debe ser limpiar el candidato, desplegar staging y probar en Telegram con dinero falso.
