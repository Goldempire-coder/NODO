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
- El rating individual no aparece en ordenes del negocio, chat, attention,
  Telegram, marketplace ni `/businesses/me`.
- Tier, promedio, conteo y bandas derivados son internos. Publico y negocio
  reciben una etiqueta estable hasta que exista snapshot durable.
- El orden del marketplace no usa rating, tier, confianza, conteos, completions
  ni velocidad vivos. Los aliases legacy se resuelven por tasa/fecha.
- La cache del marketplace usa un namespace de proyeccion versionado para no
  reutilizar respuestas creadas antes de esta politica.
- Admin y Support no reciben ratings individuales en este slice.
- Ningun DTO publico expone `risk_level`, `trust_level`, senales antifraude,
  notas admin o contadores internos.
