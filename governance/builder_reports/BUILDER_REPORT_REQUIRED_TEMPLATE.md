# BUILDER_REPORT_REQUIRED_TEMPLATE.md

Builder debe usar este formato al finalizar cada slice.

## Slice

- Slice:
- Estado final:
- Fecha:
- Builder/agente:

## Scope construido

- Incluido:
- Excluido:
- Que NO toque:

## Archivos y lineas

Por cada archivo:

```txt
archivo:
lineas:
motivo:
contrato cumplido:
```

## Dependencias

Por cada dependencia nueva o modificada:

```txt
paquete:
version:
archivo donde quedo registrado:
motivo:
contrato que la permite:
```

## Contratos cumplidos

- Governance:
- Data:
- API:
- Security:
- UI/UX:
- QA:

## Comandos ejecutados

```txt
comando:
resultado:
evidencia:
```

## Tests

- Tests ejecutados:
- Tests no ejecutados:
- Razon de tests no ejecutados:

## Evidencia

- Archivos de evidencia:
- Resultados JSON/logs:
- Capturas si aplica:

## Riesgos residuales

- Riesgo:
- Impacto:
- Cuando se retoma:

## Auto-verificacion de Builder

Confirmar:

- No toque scope prohibido.
- No cambie reglas de negocio.
- No cambie estados/enums sin contrato.
- No cambie disclaimers.
- No expuse secretos.
- No use rutas/endpoints no aprobados.
- No cree tablas fuera del contrato.
- No deje tests fallando.
- No declare `READY_FOR_REAL_USE`.

## Estado final permitido

Usar solo uno:

```txt
READY_FOR_OWNER_REVIEW
BLOCKED_BY_MISSING_CONTRACT
BLOCKED_BY_CONTRACT_CONFLICT
BLOCKED_BY_SECURITY_GAP
BLOCKED_BY_UI_CONTRACT_GAP
BLOCKED_BY_SCOPE_EXPANSION
```

