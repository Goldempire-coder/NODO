# Slice 47H Scope

Estado: CONTRACTS_DRAFT_READY_FOR_OWNER_REVIEW

## Dentro Del Alcance

- Adaptar el Prompt Maestro a NODO como auditoria brownfield, no como
  arquitectura greenfield.
- Leer contratos activos antes de opinar:
  - `SOURCE_OF_TRUTH.md`
  - `DO_NOT_INVENT.md`
  - `SPEC_MASTER.md`
  - `CODE_ARCHITECTURE_MASTER.md`
  - `ENGINEERING_GUARDRAILS.md`
  - `SLICE_EXECUTION_MATRIX.md`
  - `SLICE_CONTRACTS_MASTER.md`
  - contratos de ordenes, chat, pagos, soporte, reputacion, notificaciones,
    seguridad y operaciones.
- Mapear los modulos reales de NODO y sus responsabilidades.
- Comparar reglas de negocio contra implementacion, pruebas y evidencia.
- Identificar drift entre documentos, runtime y staging.
- Revisar separacion UI / casos de uso / dominio / repositorios / adaptadores.
- Revisar concurrencia, idempotencia, estados terminales y migraciones
  criticas.
- Revisar modelo de carga disponible y marcar entradas desconocidas.
- Revisar costos, polling, Redis, storage, logs y workers desde los datos
  existentes.
- Revisar observabilidad, alertas, runbooks, backups y restore contra evidencia.
- Producir una matriz de puntuacion 0-10 por categoria con bloqueadores.
- Producir un plan de slices de reparacion, sin implementar.

## Fuera Del Alcance

- Escribir runtime.
- Redisenar flujos aprobados sin decision del Owner.
- Crear features nuevas.
- Cambiar reglas financieras, creditos, pagos, capacidad, Zelle, USDT, Pago
  Movil, reputacion o estados de orden.
- Ejecutar migraciones.
- Hacer deploy.
- Tocar produccion.
- Rotar secretos.
- Borrar datos.
- Cambiar proveedores.
- Declarar `READY_FOR_REAL_USE`.

## Estados Obligatorios

- `DECISION_REQUIRED`: falta decision del Owner.
- `UNKNOWN_INPUT`: falta un dato de carga, costo, volumen, presupuesto o
  objetivo.
- `UNVERIFIED`: existe afirmacion sin comprobacion actual.
- `NOT_TESTED`: no se ejecuto la prueba necesaria.
- `BLOCKED_BY_CONTRACT_CONFLICT`: dos fuentes de autoridad se contradicen.

## No Aceptado

- "Escala" sin carga, limite, metrica y prueba.
- "Seguro" sin threat model, controles y evidencia.
- "Listo" sin staging, smoke autenticado y production gate.
- "Bug corregido" sin reproduccion roja y regresion.
- "Costo bajo" sin medicion o supuestos marcados.
