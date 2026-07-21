# QA.md

## Contract tests

- DTO publico no contiene `risk_level` ni `trust_level`.
- DTO propio contiene metricas pero no permite mutarlas.
- DTO admin puede incluir campos internos.
- `reputation_tier` se calcula sin modificar `trust_level`.
- Todos los minimos de tier son obligatorios.
- Success rate se calcula en backend y no en frontend.
- Migracion up/down es reversible y no borra columnas existentes.
- Tabla `ratings` no contiene comentario, titulo ni texto de resena.

## Comandos

```powershell
python -m pytest apps/api/tests -q
python -m ruff check apps/api scripts
python -m compileall apps/api apps/web/src scripts
pnpm --filter @nodo/web build
git diff --check
```

Ejecutar tambien scan del diff y fuentes tocadas por secretos, campos internos y
texto libre prohibido.
