# ACCEPTANCE_CRITERIA.md

- Contratos de superficie creados y enlazados desde masters.
- Data model define business intake y soporte.
- API contracts definen endpoints, payloads, errores, RBAC y audit.
- Security contracts definen surface access, bot security y support security.
- UI contracts separan cliente, negocio, admin web y bot.
- QA cubre separacion, intake, soporte y no claims prohibidos.
- Mini App Negocio tiene contrato para selector seguro de metodos aprobados.
- B-08_CREATE_AD no usa input manual de `payment_method_id`.
- B-16_PAYMENT_METHODS queda read-only/placeholder gobernado en 14B.
- No se toca backend/frontend/migraciones durante CONTRACT_FIX_ONLY.
