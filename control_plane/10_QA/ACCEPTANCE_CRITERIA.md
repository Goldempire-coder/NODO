# ACCEPTANCE_CRITERIA.md

NODO no puede declararse READY_FOR_OWNER_REVIEW si falla cualquiera de estos criterios.

## Producto

- Remitente puede abrir Telegram Mini App, autenticarse, buscar negocio, ver detalle, crear orden, ver instrucciones, reportar pago, chatear, confirmar recibido, calificar y ver historial.
- Negocio puede registrarse, enviar verificacion, comprar creditos, crear anuncio, recibir orden, confirmar pago, marcar entrega, responder chat/disputa y ver historial.
- Admin puede aprobar/rechazar negocios, revisar pagos manuales de creditos, ajustar creditos, suspender negocio, revisar disputas, ver metricas, usuarios y audit logs.

## Confianza y disclaimers

- Todas las pantallas de pago, orden, negocio y disputa muestran copy correcto: NODO registra perfiles y evidencia, pero no guarda fondos ni garantiza entrega.
- No existe texto prohibido: escrow, fondos garantizados, dinero protegido, transaccion garantizada, entrega garantizada, liberamos fondos.
- El copy publico usa `Perfil registrado`; `Identidad validada` solo aplica cuando existe evidencia de revision documental del titular.

## Seguridad

- Telegram initData validado en backend.
- RBAC aplicado en backend.
- Secrets fuera del frontend y fuera del repo.
- Rate limits activos por usuario, IP, negocio y endpoint sensible.
- Audit log para transiciones, admin, creditos, pagos, disputas y cambios de metodos.
- Storage privado para evidencias con URLs firmadas.

## Datos y estados

- Migraciones reproducibles desde cero.
- Constraints e indices aplicados.
- State machines impiden transiciones invalidas.
- Idempotencia en crear orden, reportar pago, webhooks Stripe y aprobaciones manuales.
- Ledger de creditos append-only y balance no negativo.

## UI

- UI respeta VISUAL_REFERENCE y SCREEN_LAYOUT_MASTER.
- UI respeta MOTION_AND_INTERACTION.
- Mobile first para Telegram Mini App.
- Bottom nav, header NODO, cards oscuras, CTA verde/azul y estados compactos implementados.
- Entry/home incluye AnimatedLogo y microinteracciones controladas.
- Botones, tabs, cards, segmented controls e inputs tienen feedback visual.
- Animaciones respetan reduced motion.
- Animaciones no causan layout shift ni bloquean navegacion.
- Pantallas tienen loading, empty, error, unauthorized y success.
- No se entrega landing page en lugar de app.

## Operacion

- Frontend, backend, worker y DB desplegados en entornos separados.
- Webhooks Telegram y Stripe configurados.
- Monitoreo y alertas activos.
- Backup/restore probado.
- Runbook admin disponible.

## Pruebas minimas

- Unit tests de services, state machines y policies.
- Integration tests de APIs principales.
- Contract tests de payloads y errores.
- E2E happy path remitente, negocio y admin.
- Security tests de RBAC y auth.
- Concurrency tests de 2,000 ordenes activas simuladas.
