# QA 42E1

- cliente crea reporte para orden propia en cada estado reportable;
- orden ajena e inexistente responden `ORDER_NOT_FOUND`;
- estados no reportables responden `OPERATION_REPORT_NOT_ALLOWED`;
- payload con `business_id` o campos extra falla validacion;
- replay con misma llave no duplica;
- misma llave con payload distinto falla;
- otra llave no duplica un reporte activo;
- ticket persiste `order_id`, `business_id` derivado y `report_kind`;
- negocio no ve el ticket ni su mensaje;
- respuesta privada usa `Cache-Control: private, no-store`;
- UI existe en detalle de orden y no en chat;
- fallo conserva seleccion y mensaje para reintento;
- no cambia orden, anuncio, credito, capacidad ni disputa;
- migracion `0051` aplica y revierte en PostgreSQL local desechable.
