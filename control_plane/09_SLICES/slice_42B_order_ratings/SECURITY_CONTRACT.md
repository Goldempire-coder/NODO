# SECURITY_CONTRACT.md

- Solo un `remitter` activo y propietario de la orden puede calificar.
- La orden debe estar `completed`.
- Una orden completada por `admin_resolved` solo es elegible si no existe
  disputa `open` o `in_review`.
- `business_id` y `rater_user_id` se derivan en backend; nunca del payload.
- El owner del negocio no puede calificarse a si mismo.
- El unique de `ratings.order_id` y la operacion transaccional protegen carreras.
- `Idempotency-Key` es obligatorio y distingue replay de payload mismatch.
- Rating y agregados de reputacion se persisten juntos o ninguno se persiste.
- Audit solo registra IDs del rating, orden y negocio; no registra payload libre.
- No existen comentarios, titulo, cuerpo de resena ni endpoint business/admin.
- Ningun DTO publico expone `risk_level`, `trust_level`, senales antifraude,
  notas admin o contadores internos.
