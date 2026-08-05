# API Contract

Las superficies publicas y de negocio devuelven una de estas proyecciones:

```json
{"publication_status":"withheld_pending_snapshot","label":"Reputacion aun no publicada"}
```

```json
{
  "publication_status":"published_snapshot",
  "label":"4.8 ★ · 12 opiniones",
  "rating_avg":"4.80",
  "ratings_count":12,
  "published_at":"timestamp"
}
```

Los valores publicados proceden de `business_public_reputation_snapshots`, no
de las columnas vivas de `businesses`. No se devuelve tier publico ni rating
individual. El mismo DTO agregado se usa para marketplace, perfil publico y
negocio propio. Admin conserva el DTO interno ya contratado; Support no recibe
ratings individuales.
