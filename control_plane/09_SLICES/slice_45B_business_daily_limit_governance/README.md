# slice_45B_business_daily_limit_governance

Estado contractual: `STAGING_SCHEMA_APPLIED_PENDING_OWNER_SMOKE`

## Objetivo

Formalizar como NODO sabe que un negocio llego a su limite diario de USD y como evita que siga recibiendo ordenes cuando ya no debe operar mas ese dia.

La pregunta que responde este slice es:

```txt
Si un negocio tiene limite diario de 1000.00 USD, como sabe el sistema
cuanto lleva usado, cuanto tiene reservado y cuanto puede aceptar todavia?
```

## Relacion con slice 45A

El slice 45A ya agrego capacidad disponible declarada, reservas por orden y matching por monto. Este slice no debe reescribir eso.

45B debe revisar y cerrar el contrato de limite diario sobre esa base:

- que se cuenta contra el limite diario;
- cuando se libera;
- cuando se consume definitivamente;
- que ve el negocio;
- que ve Admin;
- que nunca debe ver el cliente;
- que pruebas prueban el caso de USD 1000 diarios.

## Que construye este slice

- Contrato formal de limite diario operativo.
- Reglas de conteo diario para reservas, consumos, cancelaciones y disputas.
- Definicion de campos visibles para Negocio y Admin.
- Contrato de privacidad para que Cliente no vea numeros internos.
- Plan de pruebas para casos de limite diario, carreras y cambio de dia.
- Prompt de mapeo para Builder antes de tocar codigo.

## Implementacion local

- UTC se mantiene como dia operativo.
- Reservas abiertas cuentan sin depender de `created_at`.
- Consumos cuentan por `consumed_at` dentro del dia UTC.
- Marketplace y creacion de orden revalidan reservado mas consumido.
- Negocio y Admin reciben el desglose; Cliente no recibe montos internos.
- No se creo migracion nueva dentro de 45B. El indice por `consumed_at` quedo
  separado en 45C para no mezclar regla de negocio con ajuste de consulta.

## Que no construye todavia

- No cambia pagos, USDC, Zelle ni creditos.
- No cambia soporte, intake, reputacion ni bots Telegram.
- No cambia el lifecycle de anuncios.
- No declara que el flujo esta validado por smoke del Owner.
- No permite multiples ordenes sobre un mismo anuncio.

## Resultado permitido

- `PLAN_READY_FOR_OWNER_REVIEW`
- `INSPECTION_COMPLETE_READY_FOR_OWNER_REVIEW`
- `READY_FOR_VALIDATOR_REVIEW` solo si despues se aprueba implementacion
- `STAGING_SCHEMA_APPLIED_PENDING_OWNER_SMOKE` cuando staging tenga migraciones y deploy, pero falte smoke funcional
- `BLOCKED_BY_EXPLICIT_EVIDENCE`

## Resultado no permitido

- `READY_FOR_REAL_USE`
- `PRODUCTION_READY`
- `APPROVED_FOR_PRODUCTION`

## Decisiones iniciales

1. El limite diario es una regla operativa de seguridad, no un saldo financiero.
2. El backend es la unica autoridad para aceptar o rechazar una orden.
3. El cliente no debe ver cuanto cupo diario exacto le queda a un negocio.
4. El negocio si debe ver suficiente informacion para saber por que no puede recibir mas ordenes.
5. Admin si debe ver los numeros y las ordenes que explican el limite.
6. 45A usa dia UTC; 45B debe validar si se mantiene UTC o si Owner aprueba otra zona.

## Reconciliacion 2026-07-28

Staging reporto sin migraciones pendientes y con `0035_business_available_capacity_matching`
y `0036_business_daily_limit_query_indexes` aplicadas. Esto confirma que las tablas
e indices necesarios para 45A/45B/45C existen en staging, pero no reemplaza el
smoke funcional ni el perfil `EXPLAIN` de 45C.

## Documentos del slice

- `DOMAIN_CONTRACT.md`
- `API_CONTRACT.md`
- `SECURITY_CONTRACT.md`
- `QA.md`
- `DO_NOT_BUILD.md`
- `BUILDER_PROMPT.md`
