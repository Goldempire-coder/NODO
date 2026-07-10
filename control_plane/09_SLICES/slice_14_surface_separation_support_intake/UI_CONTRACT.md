# UI_CONTRACT.md

## Superficies UI

- `client/CLIENT_MINI_APP_SURFACE.md`
- `business_app/BUSINESS_MINI_APP_SURFACE.md`
- `admin_web/ADMIN_WEB_SURFACE.md`
- `business_intake_bot/BUSINESS_INTAKE_BOT_FLOW.md`
- `support/SUPPORT_SURFACES.md`

## Reglas

- Cliente no muestra negocio/admin.
- Negocio no muestra admin ni marketplace de admin.
- Admin web es desktop-first.
- Bot es flujo conversacional separado.
- Mantener copy aprobado y disclaimers NODO.
- B-08_CREATE_AD usa selector visual de metodos aprobados desde `GET /api/v1/business/payment-methods`; prohibido input manual de `payment_method_id`.
- B-16_PAYMENT_METHODS en 14B es solo lectura o placeholder gobernado; no contiene gestion self-service.
- Empty state de metodos: "Aun no tienes metodos aprobados. Contacta a NODO para activar tus metodos de operacion."
