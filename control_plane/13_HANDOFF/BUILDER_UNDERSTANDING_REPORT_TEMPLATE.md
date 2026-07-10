# BUILDER_UNDERSTANDING_REPORT_TEMPLATE.md

Builder debe entregar este reporte antes de editar archivos.

## Identificacion

- Slice asignado:
- Estado solicitado:
- Fecha:
- Builder/agente:

## Lectura obligatoria

- Documentos globales leidos:
- Documentos de seguridad leidos:
- Documentos UI/UX leidos:
- Documento del slice leidos:
- Pantallas afectadas leidas:

## Entendimiento del slice

- Objetivo del slice:
- Scope incluido:
- Scope excluido:
- Que NO voy a tocar:
- Dependencias de slices anteriores:

## Contratos afectados

- Tablas/modelos:
- Estados/enums:
- State machines:
- Endpoints:
- Payloads/errores:
- RBAC/permisos:
- Audit events:
- Jobs/workers:
- Notificaciones:
- UI/screens:
- Motion/interacciones:

## Seguridad

- Auth requerida:
- Ownership rules:
- RBAC checks:
- Rate limits:
- Idempotencia:
- Datos sensibles:
- Secrets/env:
- Audit logs:
- Security tests planificados:

## UI/UX

- Pantallas a construir/modificar:
- Componentes base:
- Uso de `@telegram-apps/telegram-ui`:
- Uso de Telegram SDK/MainButton/themeParams:
- Motion requerido:
- Reduced motion:
- Loading/empty/error/offline states:
- Disclaimer/copy requerido:

## Plan de implementacion

- Archivos o carpetas esperadas:
- Orden de trabajo:
- Tests a crear/ejecutar:
- Evidencia a entregar:

## Riesgos y bloqueos

- Huecos detectados:
- Contradicciones detectadas:
- Decisiones necesarias del owner:
- Estado:

Estados validos antes de construir:

```txt
READY_FOR_OWNER_APPROVAL_TO_BUILD
BLOCKED_BY_MISSING_CONTRACT
BLOCKED_BY_CONTRACT_CONFLICT
BLOCKED_BY_SECURITY_GAP
BLOCKED_BY_UI_CONTRACT_GAP
BLOCKED_BY_SCOPE_EXPANSION
```

Builder no puede usar:

```txt
READY_FOR_REAL_USE
```

