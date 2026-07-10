# Slice Start Protocol

Este protocolo se ejecuta antes de construir cualquier slice.

## 1. Confirmar slice asignado

El owner debe indicar un solo slice:

```txt
slice_00_foundation
slice_01_auth_telegram
slice_02_business_verification
slice_03_ads_marketplace
slice_04_order_creation
slice_05_payment_instructions_reports
slice_06_business_order_ops
slice_07_chat_disputes
slice_08_credits_referrals
slice_09_admin_console
slice_10_jobs_notifications
slice_11_hardening_deploy
```

Sin slice asignado, no se construye.

## 2. Lectura obligatoria

Leer el orden definido en:

```txt
control_plane/README.md
control_plane/13_HANDOFF/BUILDER_START_PROMPT.md
```

## 3. Reporte antes de editar

Antes de tocar archivos, Builder debe entregar un `BUILDER_UNDERSTANDING_REPORT` con:

- slice asignado
- objetivo
- documentos leidos
- pantallas afectadas
- tablas afectadas
- endpoints afectados
- estados afectados
- permisos RBAC afectados
- audit events afectados
- tests planificados
- limites de scope
- huecos o contradicciones

## 4. Aprobacion

El owner debe aprobar el reporte.

Sin aprobacion, no hay implementacion.

## 5. Construccion

Construir solo el slice asignado y guardar evidencia en:

```txt
evidence/slice_runs/
governance/builder_reports/
```

