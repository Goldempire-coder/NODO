# SECURITY_CONTRACT_INDEX.md

Indice maestro de contratos de seguridad para Builder.

## Regla de autoridad

Si un slice toca auth, usuarios, negocios, anuncios, ordenes, creditos, pagos, evidencias, chat, admin, jobs o webhooks, debe cumplir los contratos de esta carpeta.

Si un contrato requerido falta o no puede cumplirse, Builder debe detenerse con:

```txt
BLOCKED_BY_SECURITY_GAP
```

## Contratos obligatorios

### 1. Auth contract

Documento:

```txt
AUTH_TELEGRAM.md
```

Debe cubrir:

- validacion backend de Telegram initData
- rechazo de hash invalido
- rechazo de initData expirado
- JWT corto
- refresh controlado
- usuario suspendido bloqueado
- bot token nunca en frontend

### 2. RBAC contract

Documento:

```txt
RBAC_PERMISSION_MATRIX.md
```

Debe cubrir:

- actor
- accion
- recurso
- ownership
- estado requerido
- audit event
- permitido/no permitido

Regla: si una accion no esta en la matriz, esta prohibida.

### 3. Sensitive data contract

Documento:

```txt
SENSITIVE_DATA_POLICY.md
```

Debe cubrir:

- enmascaramiento
- signed URLs
- storage privado
- no leakage en logs
- sanitizacion de campos libres
- acceso minimo necesario

### 4. Secrets contract

Documento:

```txt
SECRETS_POLICY.md
```

Debe cubrir:

- secretos fuera de repo
- secretos fuera de frontend
- secretos fuera de logs
- variables por ambiente
- rotacion si se exponen

### 5. Rate limit contract

Documento:

```txt
RATE_LIMIT_POLICY.md
```

Debe cubrir:

- auth
- create order
- report payment
- upload evidence
- chat
- create ad
- checkout
- admin actions

### 6. Audit contract

Documento:

```txt
AUDIT_LOG_POLICY.md
```

Debe cubrir:

- append-only logs
- request_id
- actor
- resource
- old/new values
- reason
- provider event ids
- no secretos/datos completos

### 7. Admin security contract

Documento:

```txt
ADMIN_SECURITY.md
```

Debe cubrir:

- admin real, no whitelist informal
- roles activos
- permisos por accion
- reason obligatorio
- audit log
- exportaciones sensibles bloqueadas por defecto

### 8. API security contract

Documento:

```txt
../06_API_CONTRACTS/API_OVERVIEW.md
../06_API_CONTRACTS/ERROR_CONTRACT.md
```

Debe cubrir:

- auth middleware
- policy layer
- errores seguros
- no stack traces
- idempotencia en mutaciones criticas
- webhooks firmados

## Backlog avanzado no bloqueante

Documento:

```txt
ADVANCED_SECURITY_BACKLOG.md
```

Debe usarse como recordatorio post-staging para controles enterprise que no estan activos todavia:

- Zero Trust
- API gateway / WAF
- mTLS
- credenciales de corta duracion para infraestructura
- HMAC/Ed25519 donde aplique
- HSM/KMS
- rotacion automatica de secretos
- runtime secret injection
- RASP
- canary tokens
- eBPF
- service mesh
- firma de codigo

Este backlog no debe usarse para bloquear retroactivamente slices ya aceptados. Solo se vuelve obligatorio cuando el owner apruebe un slice futuro de seguridad avanzada, deploy final o produccion publica con estos controles como requisito.

### 9. Data consistency contract

Documentos:

```txt
../04_DATA/DATABASE_CONSTRAINTS.md
../04_DATA/INDEXES.md
../10_QA/CONCURRENCY_TESTS.md
```

Debe cubrir:

- constraints
- unique keys
- locks
- transacciones
- no doble toma de anuncio
- no doble acreditacion de creditos
- no doble consumo/liberacion de creditos

### 10. Slice security contract

Documento por slice:

```txt
../09_SLICES/<slice>/SECURITY_CONTRACT.md
```

Debe cubrir la seguridad especifica del slice asignado.

## Security release gate

Ningun slice sensible puede pasar a `READY_FOR_OWNER_REVIEW` sin pruebas de:

- auth valida/invalida
- RBAC
- ownership
- rate limit
- idempotencia
- audit log
- errores seguros
- datos sensibles protegidos
- pruebas de concurrencia cuando aplique

## Superficies criticas por prioridad

P0:

- auth Telegram
- admin panel
- creditos
- Stripe webhook
- ordenes/anuncios
- evidencias de pago

P1:

- chat
- disputas
- jobs
- notificaciones
- metricas/admin reads

P2:

- UI masking
- empty/error states
- observabilidad no sensible
