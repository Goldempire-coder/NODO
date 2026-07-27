# Slice 46B QA

Estado: DRAFT

## Casos Obligatorios

### Cliente No Recuerda El Negocio

Entrada:

- telefono, Telegram, user id o ticket del cliente.

Resultado:

- ficha muestra ordenes recientes del cliente;
- muestra negocios asociados;
- muestra tickets activos y archivados relacionados;
- no muestra chats completos sin abrir visor autorizado.

### Negocio Entro Con Codigo De Referencia

Entrada:

- codigo de referencia o negocio creado desde intake.

Resultado:

- ficha muestra intake;
- codigo de referencia;
- negocio creado, si existe;
- owner vinculado;
- documentos solo como metadata segura.

### Ticket Cerrado O Archivado

Entrada:

- soporte busca un ticket cerrado.

Resultado:

- ficha lo incluye aunque no este en Activos;
- muestra estado final;
- muestra links para abrir ticket y entidades relacionadas;
- no permite responder desde la ficha.

### Alerta Por Fuera De Plataforma

Entrada:

- notificacion que apunta a una orden y `message_id`.

Resultado:

- ficha abre orden;
- muestra que hay evidencia de chat disponible;
- no pone el cuerpo completo del mensaje en la ficha inicial;
- permite abrir visor autorizado si ya existe.

### Pago Reportado Sin Orden Clara

Entrada:

- monto aproximado, fecha aproximada o cliente.

Resultado:

- ficha muestra ordenes compatibles;
- timeline ayuda a comparar tiempos;
- no declara que el pago fue correcto;
- no promete recuperacion.

### Varios Tickets Del Mismo Caso

Entrada:

- cliente o negocio con varios tickets.

Resultado:

- ficha agrupa activos y archivados;
- ordena por ultima actividad;
- indica si hay mas resultados que cargar.

## Pruebas De Seguridad

- Cliente, negocio y usuario sin sesion reciben rechazo.
- Staff inactivo recibe rechazo.
- Respuesta no contiene:
  - `storage_path`;
  - signed URLs;
  - PIN;
  - tokens;
  - wallets completas;
  - datos bancarios completos;
  - cuerpos completos de mensajes;
  - texto crudo de busqueda 46A en audit.
- Audit log contiene anchor, conteos y request id, no cuerpos.
- La ficha usa `Cache-Control: private, no-store`.

## Pruebas De UX

- Pantalla Admin es scrollable.
- Secciones son compactas y separadas.
- Un error en una seccion permite reintentar esa seccion o ver las demas.
- Abrir desde 46A no rompe rutas existentes.
- Links internos abren orden, ticket, negocio, cliente o intake correcto.

## Comandos Esperados

Builder debe proponer comandos exactos tras el mapeo. Base esperada:

```powershell
python -m pytest apps/api/tests/test_admin_console.py -q --tb=short
python -m pytest apps/api/tests/test_admin_operational_search.py -q --tb=short
python -m pytest apps/api/tests -q
python -m ruff check apps/api scripts
python -m compileall apps/api apps/web/src scripts
pnpm --filter @nodo/web build
git diff --check
```

## Evidencia Insuficiente

- "La ficha se ve bien".
- "El endpoint respondio 200".
- Captura sin usuario, ambiente, commit ni pasos.
- No probar archivados.
- No probar permisos.
- No probar que no se filtran datos privados.
