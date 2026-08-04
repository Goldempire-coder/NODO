# API Contract

Las superficies publicas y de negocio devuelven una de estas proyecciones:

```json
{"publication_status":"withheld_pending_snapshot","label":"Reputacion aun no publicada"}
```

```json
{
  "publication_status":"published_snapshot",
  "label":"4.60 de 5 (5 calificaciones)",
  "rating_avg":"4.60",
  "ratings_count":5,
  "published_at":"timestamp"
}
```

Los valores publicados proceden de `business_public_reputation_snapshots`, no
de las columnas vivas de `businesses`. No se devuelve tier publico ni rating
individual. Admin conserva el DTO interno ya contratado.
