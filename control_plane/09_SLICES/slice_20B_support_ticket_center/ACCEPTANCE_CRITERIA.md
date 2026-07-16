# ACCEPTANCE_CRITERIA.md

20B queda listo para owner review solo si:

- tablas y migraciones de soporte se crean segun contrato;
- endpoints cliente/negocio/admin cumplen `SUPPORT_API.md`;
- support no puede cambiar ordenes, creditos, anuncios, disputas, usuarios ni access links;
- adjuntos son privados y nunca exponen `storage_path`;
- Admin Web soporte es desktop-first;
- Mini Apps mantienen separacion de superficies;
- audit events estan completos;
- tests y scans pasan;
- no se declara READY_FOR_REAL_USE.
