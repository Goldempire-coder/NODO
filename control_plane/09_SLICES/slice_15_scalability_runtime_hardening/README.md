# slice_15_scalability_runtime_hardening

## Objetivo

Preparar NODO para escalar lecturas calientes del marketplace y trafico concurrente sin tumbar PostgreSQL ni debilitar operaciones sensibles.

Este slice existe porque las pruebas locales mostraron:

- Marketplace reads c100/c200 no rompieron reglas ni invariantes.
- La latencia p95 sigue alta bajo usuarios unicos simultaneos.
- El query de marketplace esta indexado y no es el cuello principal.
- Auth por usuario unico + threadpool + pool de DB generan cola.
- Multi-worker sin presupuesto de conexiones rompe PostgreSQL con `too many clients already`.

## Dependencias

- slices 00-14D2.
- Reporte: `governance/owner_reviews/performance_runtime_capacity_report_02_20260710.md`.

## Estado

READY_FOR_OWNER_APPROVAL_TO_BUILD_15

