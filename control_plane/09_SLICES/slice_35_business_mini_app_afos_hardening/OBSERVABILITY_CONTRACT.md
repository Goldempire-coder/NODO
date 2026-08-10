# OBSERVABILITY_CONTRACT.md

## Objetivo

Detectar errores de la Mini App Negocio antes de que el usuario tenga que explicar por captura que un boton "no hace nada".

## Eventos minimos

Frontend breadcrumbs:

- screen_view;
- action_started;
- action_completed;
- action_failed;
- api_failure;
- slow_screen_transition;
- slow_sensitive_action.

Acciones criticas:

- zelle_add;
- zelle_edit;
- zelle_delete;
- usdt_wallet_add;
- usdt_wallet_edit;
- usdt_wallet_delete;
- business_availability_update;
- ad_create;
- ad_edit;
- ad_pause;
- ad_reactivate;
- ad_delete;
- ad_republish;
- credit_payment_create;
- credit_tx_submit;
- business_order_confirm_payment;
- business_order_dispute_open;
- business_order_mark_delivered.

## Campos permitidos

- screen;
- previous_screen;
- action;
- status;
- route_template;
- duration_ms;
- status_code;
- error_code;
- request_id;
- correlation_id;
- operation_id;
- surface;
- counts no sensibles.

## Campos prohibidos

- wallet completa;
- wallet USDT completa;
- Zelle completo;
- email completo;
- telefono completo;
- PIN;
- token;
- tx hash completo;
- storage path;
- signed URL;
- evidencia de comprobante.

## Backend

La ingesta puede seguir apagada por defecto, pero el slice debe documentar:

- como activarla en staging;
- que limites tiene;
- que evento prueba que funciona;
- que evento prueba redaccion;
- como apagarla.

No persistir eventos en DB sin contrato nuevo.
