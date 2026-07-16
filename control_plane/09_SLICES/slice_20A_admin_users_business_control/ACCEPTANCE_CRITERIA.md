# ACCEPTANCE_CRITERIA.md

El build de 20A solo puede quedar `READY_FOR_OWNER_REVIEW` si:

- endpoints admin de usuarios implementan contratos de API;
- acciones de usuario son reason/idempotency/audit;
- support queda read-only;
- masking cumple `SENSITIVE_DATA_POLICY.md`;
- A-10 funciona como Admin Web desktop;
- access links pueden verse por usuario y negocio;
- mutaciones de access links conservan reglas de 14B1;
- usuarios/links bloqueados suspenden acceso a superficies correspondientes;
- tests y scans pasan;
- no se toca deploy;
- no se declara READY_FOR_REAL_USE.
