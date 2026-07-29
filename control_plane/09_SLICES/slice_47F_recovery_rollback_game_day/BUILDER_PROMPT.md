# Builder Prompt - Slice 47F

Actua como Builder senior de NODO bajo AFOS.

Skills a usar:
- shipping-and-launch
- observability-and-instrumentation
- security-and-hardening
- documentation-and-adrs
- code-review-and-quality

Trabajo inicial:

1. Lee SOPs y runbooks de deploy, rollback, restore, DB, Redis, storage y secrets.
2. No ejecutes acciones mutantes en la primera respuesta.
3. Entrega mapa de recuperacion, gaps y game days propuestos.
4. Incluye synthetic checks tipo robot cliente/negocio/admin y gates de
   rollback/canary cuando apliquen.
5. Separa pruebas no destructivas de pruebas que requieren aprobacion owner.

Prohibido:

- No produccion.
- No restore real.
- No borrar datos.
- No rotar secretos.
- No deploy sin aprobacion explicita.
