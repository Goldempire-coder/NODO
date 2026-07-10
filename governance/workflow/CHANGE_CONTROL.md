# Change Control

Este documento evita que NODO se convierta en software improvisado.

## Cambios permitidos sin aprobacion especial

- Crear archivos dentro del slice asignado.
- Agregar tests del slice asignado.
- Agregar evidencia del slice asignado.
- Ajustar implementacion para cumplir contratos existentes.

## Cambios que requieren aprobacion del owner

- Cambiar reglas de creditos.
- Cambiar ciclo de vida de anuncios.
- Cambiar ciclo de vida de ordenes.
- Cambiar disclaimers.
- Cambiar roles o permisos.
- Cambiar estados/enums.
- Cambiar arquitectura base.
- Cambiar stack.
- Cambiar estilo visual principal.
- Agregar features fuera del slice.

## Cambios bloqueados

Si el builder encuentra una contradiccion real, no debe corregirla por cuenta propia.

Debe reportar:

```txt
BLOCKED_BY_CONTRACT_CONFLICT
```

Y explicar:

- documentos en conflicto
- lineas o secciones afectadas
- impacto tecnico
- decision necesaria del owner

## Registro

Toda decision aprobada debe terminar registrada en:

```txt
control_plane/00_GOVERNANCE/DECISION_LOG.md
governance/owner_reviews/
```

