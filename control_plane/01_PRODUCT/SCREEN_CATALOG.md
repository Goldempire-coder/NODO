# SCREEN_CATALOG.md

## Slice 14 - Catalogo por superficie

Mini App Cliente:
- R-01 a R-09, R-12 y R-13 segun contratos existentes, excluyendo completion/rating si pertenecen a slice futuro.
- Soporte general cliente y soporte por orden segun `control_plane/08_SCREENS/support/SUPPORT_SURFACES.md`.

Mini App Negocio:
- Pantallas operativas de negocio, creditos, anuncios, ordenes entrantes, chat de negocio, perfil e historial.
- Acceso solo con negocio aprobado/asociado.

Panel Admin Web Desktop:
- Pantallas admin A-01 a A-13 y nuevas vistas de intake/soporte admin segun `ADMIN_WEB_SURFACE.md`.
- No vive dentro de Mini App Cliente.
- Las pantallas A-01 a A-13 se renderizan como Admin Web Desktop con sidebar/top bar/tablas/filtros; no como Telegram Mini App.

Bot Registro Negocios:
- `business_intake_bot/BUSINESS_INTAKE_BOT_FLOW.md`.

Superficies de soporte:
- `support/SUPPORT_SURFACES.md`.
- Cliente:
  - `client/C-20_CLIENT_SUPPORT_CENTER.md`
- Mini App Negocio:
  - `business_app/BAPP-20_BUSINESS_SUPPORT_CENTER.md`
- Admin Web:
  - `admin_web/AW-20_SUPPORT_TICKET_CENTER.md`

Los archivos historicos en `remitter/`, `business/` y `admin/` siguen como contratos de pantalla existentes; slice 14 redefine ownership por superficie sin mover implementacion.

## Remitente

- R-01_WELCOME_ENTRY
- R-02_HOME_SEARCH
- R-03_SEARCH_RESULTS
- R-04_BUSINESS_DETAIL
- R-05_CREATE_ORDER
- R-06_ORDER_SUMMARY
- R-07_PAYMENT_INSTRUCTIONS
- R-08_REPORT_PAYMENT
- R-09_ORDER_TRACKING_CHAT
- R-10_CONFIRM_RECEIVED
- R-11_RATING
- R-12_MY_ORDERS
- R-13_PROFILE

## Negocio

- B-01_BUSINESS_ONBOARDING
- B-02_BUSINESS_VERIFICATION_FORM
- B-03_VERIFICATION_PENDING
- B-04_BUSINESS_DASHBOARD
- B-05_BUY_CREDITS
- B-06_CREDIT_PAYMENT_PENDING
- B-07_MY_CREDITS_LEDGER
- B-08_CREATE_AD
- B-09_MY_ADS
- B-10_ARCHIVED_ADS
- B-11_INCOMING_ORDERS
- B-12_BUSINESS_ORDER_DETAIL
- B-13_BUSINESS_CHAT
- B-14_BUSINESS_RATINGS
- B-15_REFERRAL_PROGRAM
- B-16_PAYMENT_METHODS
- B-17_BUSINESS_SETTINGS

Notas 14B:
- B-08_CREATE_AD usa selector visual desde `GET /api/v1/business/payment-methods`; no input manual de `payment_method_id`.
- B-16_PAYMENT_METHODS es solo lectura o placeholder gobernado en 14B; no hay gestion self-service de metodos.

## Admin

- A-01_ADMIN_DASHBOARD
- A-02_PENDING_BUSINESSES
- A-03_BUSINESS_VERIFICATION_DETAIL
- A-04_PENDING_CREDIT_PAYMENTS
- A-05_CREDIT_PAYMENT_DETAIL
- A-06_DISPUTES_LIST
- A-07_DISPUTE_DETAIL
- A-08_EVASION_REPORTS
- A-09_BUSINESS_RISK_DETAIL
- A-10_USERS_REMITTERS
- A-11_AUDIT_LOGS
- A-12_SYSTEM_METRICS
- A-13_MANUAL_ADJUSTMENTS

Notas 14C:
- A-01, A-02, A-03, A-06, A-07, A-08, A-09, A-10, A-11 y A-12 son ownership de Admin Web.
- A-04, A-05 y A-13 pertenecen a slice 08, pero Admin Web puede componerlas/enlazarlas sin cambiar reglas de creditos.
- Admin Web no usa Telegram bottom nav, Telegram MainButton, shell Mini App ni `themeParams`.

Notas 20A:
- A-10_USERS_REMITTERS se convierte en control operativo Admin Web para usuarios y `business_access_links`.
- Support ve A-10 solo masked/read-only.
- Mutaciones de usuario/access link usan backend RBAC, reason, idempotencia y audit.

Notas 20B:
- El soporte real vive en pantallas separadas por superficie; no reutiliza chat operativo como ticket.
- Admin Web muestra soporte en layout desktop con cola, filtros, split detail, eventos, adjuntos, asignacion y cierre.
- Mini App Cliente y Mini App Negocio solo muestran tickets propios o recursos propios autorizados por backend.

Notas 20C:
- Admin Web agrega Staff Center, Staff Detail e Invite Staff:
  - `AW-21_STAFF_CENTER`
  - `AW-22_STAFF_DETAIL`
  - `AW-23_STAFF_INVITE`
- Estas pantallas administran `staff_profiles`, `staff_permissions` y `staff_invites`.
- No viven dentro de Mini App Cliente ni Mini App Negocio.
