# QA Contract

42D0 no ejecuta pruebas funcionales. Los siguientes casos son gates de los
slices de implementacion.

## 42D1

- rating 1 y rating 5 crean la misma pausa de 15 minutos;
- replay del mismo rating no vuelve a extenderla;
- ratings distintos concurrentes conservan el mayor `paused_until`;
- rating invalido o no autorizado no crea pausa;
- Memory y PostgreSQL mantienen paridad;
- migracion nullable aplica y revierte sin invalidar negocios existentes;
- el campo no aparece en DTO publico, marketplace, chat ni notificaciones;
- no cambia estado de anuncios, creditos, capacidad ni reputacion publica.

## 42D2

- pausa bloquea crear/reactivar/republicar Zelle y USDT;
- anuncios activos no cambian de estado, pero marketplace no los ofrece;
- pausa invalida la proyeccion cacheada y una respuesta stale no autoriza orden;
- creacion directa de orden falla con error neutral;
- `now == paused_until` permite publicar si no existe otra restriccion;
- bloqueo Admin domina despues del vencimiento;
- negocio no recibe rating, orden origen, causa, chat, attention ni Telegram.

## 42E1

- cliente selecciona una orden propia y backend deriva `business_id`;
- missing y foreign order responden `ORDER_NOT_FOUND`;
- los seis estados reportables son aceptados;
- `waiting_payment`, `payment_reported` y `expired` son rechazados neutralmente;
- payload con `business_id` o campos extra es rechazado;
- no existe entrada desde chat;
- ticket generico no crea hold;
- respuesta cliente no expone si existe pausa o hold;
- mismo replay devuelve el reporte existente y otra llave no lo duplica;
- rate limits por cliente y orden se aplican.

## 42F1

- reporte con `database_now < paused_until` crea ticket y hold atomicamente;
- reporte con `database_now >= paused_until` crea ticket sin hold;
- cerrar o resolver ticket no libera hold;
- cliente no puede liberar;
- Admin/Super Admin liberan con reason e idempotencia;
- Support sin permiso falla; Support autorizado y dentro de scope puede liberar;
- varios holds requieren liberar todos;
- PostgreSQL concurrente no crea duplicados;
- hold bloquea marketplace, publicacion y creacion directa de orden;
- hold y liberacion invalidan la proyeccion cacheada aplicable;
- la liberacion no salta bloqueo Admin, capacidad, creditos ni limites.

## 42F2

- se crea un job por destinatario Admin/Super Admin activo y vinculado;
- no se crea job role-only;
- texto y metadata no contienen datos sensibles;
- fallo o falta de destinatario no revierte ticket/hold;
- retry idempotente no duplica alerta;
- se registran queued, sent/failed y error interno observable.

## Validacion documental 42D0

- buscar contradicciones legacy en contratos de rating, soporte, anuncios,
  ordenes, negocios, Admin, notificaciones y RBAC;
- `git diff --check`;
- Secret Guard sobre documentos tocados;
- no ejecutar suite funcional por un cambio exclusivamente documental.
