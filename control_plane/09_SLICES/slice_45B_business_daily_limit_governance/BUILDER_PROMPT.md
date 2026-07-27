# BUILDER_PROMPT.md

Usa estos skills antes de trabajar:

- `spec-driven-development`
- `api-and-interface-design`
- `security-and-hardening`
- `supabase-postgres-best-practices`
- `performance-optimization`
- `observability-and-instrumentation`
- `test-driven-development`
- `code-review-and-quality`
- `git-workflow-and-versioning`

Actua como Builder, pero esta primera tarea es SOLO MAPEO Y PLAN. No escribas codigo. No hagas deploy. No ejecutes migraciones. No borres datos.

## Autoridad

AFOS y los documentos del slice son autoridad. El slice es:

```txt
control_plane/09_SLICES/slice_45B_business_daily_limit_governance/
```

Tambien debes leer el slice anterior:

```txt
control_plane/09_SLICES/slice_45_business_available_capacity_matching/
```

## Objetivo

Mapear como NODO sabe actualmente que un negocio llego al limite diario de `1000.00 USD`, que ya quedo cubierto por 45A y que falta para cerrar 45B.

La pregunta del Owner es:

```txt
Como sabe el sistema cuando el negocio llego al limite de 1000 diarios?
```

## Revisa archivos probables

- `apps/api/app/modules/business_capacity/`
- `apps/api/app/modules/businesses/`
- `apps/api/app/modules/ads/`
- `apps/api/app/modules/orders/`
- `apps/api/tests/test_business_capacity_matching.py`
- `apps/web/src/hooks/business-mini-app/`
- `apps/web/src/screens/business-app/`
- `apps/web/src/screens/admin-web/`
- `control_plane/06_API_CONTRACTS/`
- `database/migrations/0035_business_available_capacity_matching.*.sql`

## Preguntas que debes responder

1. Que parte del limite diario ya esta implementada por 45A?
2. El calculo usa UTC? En que archivo y linea?
3. El sistema separa reservado hoy y consumido hoy, o los mezcla?
4. Cancelar antes de pago libera cupo diario?
5. Completar una orden consume cupo diario?
6. Una disputa mantiene cupo retenido?
7. El negocio puede ver limite diario, usado y restante?
8. Admin puede ver limite diario, usado, restante y ordenes que explican el calculo?
9. Cliente recibe algun numero interno que no debe ver?
10. El matching filtra por limite diario antes de `LIMIT`?
11. Crear orden revalida limite diario dentro de la transaccion?
12. Que pasa si dos clientes intentan usar el ultimo cupo al mismo tiempo?
13. Hace falta una migracion nueva o se puede usar la tabla de reservas existente?
14. Que pruebas faltan?
15. Que riesgos de performance tiene el calculo diario a escala?

## Entrega esperada

Devuelve:

```txt
1. ESTADO
2. MAPA ACTUAL
3. QUE YA CUMPLE 45A
4. BRECHAS PARA 45B
5. DECISIONES QUE NECESITAN OWNER
6. PLAN MINIMO DE IMPLEMENTACION
7. ARCHIVOS PROBABLES
8. TESTS PROPUESTOS
9. RIESGOS Y ROLLBACK
10. CONFIRMACIONES DE NO CAMBIO
```

## Reglas

- No tocar codigo.
- No modificar documentos.
- No ejecutar migraciones.
- No hacer deploy.
- No tocar pagos, USDC, Zelle, creditos, soporte, intake, reputacion ni bots.
- No declarar `READY_FOR_REAL_USE`.
- Reporta si el repo ya esta sucio antes de empezar.

