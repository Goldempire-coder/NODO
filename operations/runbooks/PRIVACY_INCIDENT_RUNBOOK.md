# RUNBOOK: Privacy incident

Estado de validacion: NOT VALIDATED

## SINTOMA

Datos personales, documentos, signed URLs, storage paths o tokens expuestos.

## SEVERIDAD INICIAL

SEV-1.

## PRIMEROS CINCO MINUTOS

1. Detener exposicion.
2. Preservar evidencia redacted.
3. Identificar tipo de dato.
4. Identificar usuarios afectados.
5. Escalar a owner/security.

## DIAGNOSTICO

- Buscar `storage_path`, `account_value`, tokens o signed URLs en logs/responses.
- Revisar endpoints recientes.
- Revisar deploy reciente.

## MITIGACION

- Revocar signed URLs si el proveedor lo permite.
- Rotar secreto especifico si se filtro.
- Bloquear descarga publica.

## PROHIBICIONES

- No compartir datos completos en postmortem.
- No borrar logs sin preservar evidencia.
