# API_CONTRACT.md

## Principio

NODO separa trafico liviano de trafico sensible.

Lecturas no sensibles del marketplace pueden usar un camino mas rapido. Mutaciones y datos sensibles mantienen validacion fuerte contra backend/DB.

## Endpoints afectados

### GET /api/v1/ads/search

Permitido optimizar.

Reglas:

- Debe seguir validando JWT firmado y expiracion.
- Debe permitir solo actor `remitter` con claim activo compatible.
- Puede usar cache de usuario/sesion para evitar DB por request.
- Si usa claims del JWT, solo aplica para lectura de marketplace.
- El riesgo de usuario recien bloqueado debe quedar acotado por TTL corto o invalidacion.
- No expone datos privados ni `account_value`.
- No audita cada busqueda individual para evitar saturar audit logs.

### GET /api/v1/ads/{id}

Permitido optimizar parcialmente.

Reglas:

- Puede usar cache de anuncio/negocio publico.
- No debe revelar instrucciones completas de pago.
- Crear orden sigue siendo el gate fuerte.

## Endpoints que NO pueden usar auth liviana

- `POST /api/v1/orders`
- `GET /api/v1/orders/{id}/payment-instructions`
- `POST /api/v1/orders/{id}/payment-report`
- `POST /api/v1/orders/{id}/payment-evidence`
- `GET/POST /api/v1/orders/{id}/messages`
- `POST /api/v1/orders/{id}/disputes`
- Todos los endpoints `/api/v1/business/*`
- Todos los endpoints `/api/v1/admin/*`
- Todos los endpoints de creditos/referrals.
- Todos los endpoints de bot intake.

## Nuevos contratos internos permitidos

El builder puede crear interfaces internas, sin exponer nueva API publica:

- `MarketplaceReadAuthenticator`
- `MarketplaceReadCache`
- `RuntimeCapacityConfig`
- `CapacityGuard`

Si se crea endpoint admin/ops nuevo para diagnostico, debe estar bajo:

```txt
GET /api/v1/admin/ops/runtime-capacity
```

Y requiere `admin` o `super_admin`.

