# Observability Contract

## Objetivo

Hacer visibles los fallos temporales sin exponer datos sensibles.

## Eventos esperados

Registrar o preservar evidencia segura para:

- fallo de refresh de credit wallet;
- fallo de polling de admin unread-count;
- fallo de Clipboard API al copiar business id;
- transicion lenta real entre vistas de Mini App Negocio.

## Datos prohibidos en logs/breadcrumbs

No registrar:

- wallet completa;
- Zelle completo;
- PIN;
- token;
- `tx_hash` completo;
- `storage_path`;
- signed URL;
- cuerpo privado de soporte;
- metadata interna de riesgo.

## Resultado esperado

Si un owner dice "el boton no hizo nada" o "desaparecieron mis creditos", debe
existir una pista segura para saber si fue frontend, backend, red o refresh
fallido.
