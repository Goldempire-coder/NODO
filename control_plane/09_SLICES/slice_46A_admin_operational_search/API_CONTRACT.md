# Slice 46A API Contract

## GET /api/v1/admin/investigation/search

Headers:

- `Authorization: Bearer <admin session>`

Query:

- `q`: string, 3 a 120 caracteres despues de trim.
- `limit`: entero 1 a 20. Aplica por grupo.

Respuesta:

```json
{
  "data": {
    "groups": {
      "users": [],
      "businesses": [],
      "business_intakes": [],
      "orders": [],
      "support_tickets": []
    },
    "result_counts": {
      "users": 0,
      "businesses": 0,
      "business_intakes": 0,
      "orders": 0,
      "support_tickets": 0
    },
    "disclaimer": "..."
  },
  "request_id": "..."
}
```

Cada resultado usa:

```json
{
  "type": "user|business|business_intake|order|support_ticket",
  "id": "uuid",
  "title": "string",
  "subtitle": "string",
  "matched_on": ["codigo_orden"],
  "action_route": "admin://order/{id}",
  "status": "string|null",
  "reference": "string|null",
  "created_at": "iso|null",
  "context": {}
}
```

## Reglas

- Solo `admin`, `super_admin` y `support` activo pueden leer.
- La respuesta debe usar `Cache-Control: private, no-store`.
- El endpoint no busca cuerpos de chat.
- El endpoint no devuelve `storage_path`, signed URLs, `file_asset_id`,
  valores bancarios completos, tokens, secretos ni payloads privados.
- Buscar por cliente/negocio/orden puede devolver entidades relacionadas.
- Buscar por orden debe poder mostrar tickets ligados a esa orden.
- Buscar por codigo de referencia debe poder mostrar negocio o intake.
- La busqueda no ejecuta mutaciones.

## Errores

- `ADMIN_OPERATIONAL_SEARCH_QUERY_TOO_SHORT`: `q` tiene menos de 3 caracteres.
- `FORBIDDEN`: actor sin permiso admin/support.
- `RATE_LIMITED`: exceso de busquedas.
