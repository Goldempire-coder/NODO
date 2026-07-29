# Slice 46D Security Contract

Estado: IMPLEMENTATION_46D1_46D2_READY_FOR_OWNER_REVIEW

## Principio

46D organiza trabajo operativo, pero no convierte a NODO en juez automatico, no
exporta datos privados y no amplifica el acceso de Soporte.

## Permitido En El Reporte

- Describir pantallas, endpoints, modelos y acciones existentes.
- Usar datos sinteticos o ejemplos inventados.
- Citar nombres de campos, rutas y eventos.
- Indicar si una evidencia existe o falta.
- Proponer reparaciones con alcance claro.

## Prohibido En El Reporte

- Copiar cuerpos reales de mensajes, tickets o chats.
- Copiar datos bancarios reales, wallets completas, PIN, tokens o secrets.
- Copiar URLs firmadas, `storage_path` o IDs internos de archivos como
  evidencia visual.
- Afirmar que un cliente o negocio mintio, hizo fraude o pago correctamente.
- Recomendar recuperar dinero sin validacion humana y legal.
- Proponer que Soporte vea mas de lo que permite su RBAC actual sin contrato.

## Lenguaje Permitido

Usar lenguaje factual:

- "orden relacionada encontrada";
- "reporte de pago presente";
- "ticket archivado relacionado";
- "evidencia no revisada";
- "requiere abrir visor auditado";
- "no hay accion disponible en Dashboard".

## Lenguaje Prohibido

- "fraude confirmado";
- "cliente culpable";
- "negocio culpable";
- "pago valido";
- "pago falso";
- "recuperacion garantizada";
- "este caso esta resuelto" si no hay accion auditada que lo demuestre.

## Privacidad Y Costo

- No buscar full-text en mensajes privados como parte del reporte.
- No descargar adjuntos para construir el mapa.
- No ejecutar consultas amplias sin limite.
- No usar datos reales de produccion.
- No guardar pistas crudas sensibles en nuevos documentos.
- No proponer polling adicional sin analizar costo.

## Auditoria Futura

Si una reparacion futura crea accion operativa, debe auditar:

- actor;
- rol;
- entidad afectada;
- accion;
- resultado;
- request id;
- sin cuerpos privados ni datos sensibles completos.

## Controles Aplicados En 46D1 Y 46D2

- El playbook se deriva en frontend de la ficha allowlist 46B.
- El playbook no hace fetch adicional, no descarga adjuntos y no cambia estado.
- La asignacion solo aparece para Admin y Super Admin, porque son los roles que
  pueden consultar la lista Staff existente.
- No se amplian permisos de Support para listar personal.
- El selector usa `user_id` del perfil Staff recibido; no admite entrada manual
  de IDs.
- La asignacion exige motivo y usa `Idempotency-Key`.
- `operations_readonly` no aparece como responsable seleccionable.
