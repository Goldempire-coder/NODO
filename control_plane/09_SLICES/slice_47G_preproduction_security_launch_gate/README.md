# Slice 47G - Preproduction Security Launch Gate

Estado: CONTRACTS_DRAFT_READY_FOR_OWNER_REVIEW

## Objetivo

Convertir la preocupacion de seguridad preproduccion en un gate obligatorio:
antes de uso real, NODO debe demostrar que secretos, Telegram Web, Supabase,
storage, API, chat, adjuntos, webhooks, dependencias y permisos no dejan puertas
abiertas.

Este slice existe porque la Mini App corre como web dentro de Telegram y tambien
puede abrirse desde navegador. Todo codigo cliente debe considerarse visible y
manipulable. La seguridad real vive en backend, base de datos, storage privado,
validacion de Telegram y controles de proveedor.

## Problema Que Cubre

- Llaves usadas en desarrollo/staging podrian haberse filtrado o copiado.
- Un bundle web puede exponer variables si se usa una key incorrecta.
- Telegram `initData` puede ser falsificado si el backend no lo valida.
- Chats y adjuntos son entrada de usuario y pueden ser usados para abuso,
  spam, XSS, archivos maliciosos o IDOR.
- Supabase puede quedar abierto aunque el codigo de backend parezca correcto.
- Un deploy puede pasar tests locales pero fallar en configuracion real de
  Railway, Cloudflare, Supabase, Redis, storage o Telegram.

## Resultado Esperado

- Inventario de secretos por entorno sin imprimir valores.
- Runbook de rotacion preproduccion para Telegram, JWT, DB, Redis, Supabase,
  storage, webhooks, Cloudflare, Railway y proveedores activos.
- Confirmacion de que produccion usa secretos nuevos, separados de staging/dev.
- Escaneo de repo, historial, staged diff y bundle frontend.
- Supabase Security Advisor con `security_findings = 0`.
- Verificacion SQL de RLS y privilegios publicos en staging/produccion objetivo.
- Validacion de Telegram `initData` y `auth_date` en rutas sensibles.
- Matriz IDOR para ordenes, chats, adjuntos, soporte, Pago Movil, payment
  instructions, ratings, admin y negocio.
- Revision de CORS, CSP, headers, errores seguros y rate limits.
- Pruebas de archivos: tipo, tamano, ownership, URL temporal y no exposicion de
  `storage_path`.
- Dependency audit y supply-chain review sin aplicar fixes forzados.
- Reporte final con blockers, riesgos residuales y decision explicita del
  Owner antes de cualquier `READY_FOR_REAL_USE`.

## Dependencias

- 31B backup/restore contracts.
- 47A observabilidad.
- 47B alertas.
- 47C jobs/retries/reconciliation.
- 47D cost/noise control.
- 47E auditoria forense.
- 47F recovery/rollback/game day.
- Slices de P2P activos: 42C, 45A-45C, 48B, 49A, 50A-50C.
- Hardening Supabase aplicado en `0046` y `0047`.

## No Construir Todavia

- No rotar secretos reales sin runbook aprobado y ventana definida.
- No imprimir, copiar ni guardar valores secretos en reportes.
- No tocar produccion sin autorizacion explicita del Owner.
- No borrar datos.
- No cambiar reglas financieras, creditos, pagos, USDT/Zelle o estados.
- No relajar RLS, CORS, CSP, auth, RBAC ni storage privado por conveniencia.
- No declarar `READY_FOR_REAL_USE`.
