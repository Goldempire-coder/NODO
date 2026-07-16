# SECURITY_CONTRACT.md

## Principio

El backend manda. El frontend ayuda al usuario, pero no decide seguridad, dinero, ownership, permisos, creditos ni disponibilidad de anuncios.

## Acciones sensibles

El builder debe crear o actualizar una matriz con estas acciones:

- crear Zelle;
- editar Zelle;
- borrar Zelle;
- crear USDT TRC20;
- editar USDT TRC20;
- borrar USDT TRC20;
- poner negocio online/offline;
- crear anuncio;
- editar anuncio;
- pausar anuncio;
- reactivar anuncio;
- borrar/archivar anuncio;
- republicar anuncio;
- generar compra Base USDC;
- pegar/verificar tx hash;
- confirmar pago de orden;
- rechazar reporte de pago;
- marcar pago movil enviado;
- abrir disputa o chat operativo cuando aplique.

Para cada accion:

- requiere PIN: si/no;
- endpoint backend;
- idempotency key;
- audit event;
- test backend;
- test frontend/static;
- datos prohibidos en logs.

## Datos prohibidos en cliente/logs

No exponer ni registrar:

- token;
- refresh token;
- PIN;
- OTP;
- API keys;
- wallet privada;
- seed phrase;
- tx hash completo en logs;
- Zelle completo en logs;
- wallet USDT completa en logs;
- correo completo en logs;
- telefono completo en logs;
- storage path privado;
- signed URL;
- evidencia completa.

## Backend checks requeridos

El slice debe verificar, no asumir:

- ownership de negocio;
- negocio aprobado;
- negocio no restringido;
- PIN desbloqueado cuando aplique;
- metodo de cobro activo/aprobado y propio;
- anuncio propio;
- rango autorizado del negocio;
- credito disponible antes de publicar/republicar;
- idempotencia en mutaciones sensibles;
- negocio online antes de crear orden;
- orden propia antes de operar desde negocio.

## Evidencia aceptable

- tests backend directos;
- tests de manipulacion de IDs;
- tests de doble click/retry/idempotencia;
- scan de secretos;
- auditoria de breadcrumbs sin datos sensibles.
