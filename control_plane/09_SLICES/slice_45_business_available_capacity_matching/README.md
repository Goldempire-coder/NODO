# slice_45_business_available_capacity_matching

Estado contractual: `STAGING_SCHEMA_APPLIED_PENDING_OWNER_SMOKE`

## Objetivo

Permitir que el negocio declare cuanto USD tiene disponible para operar ahora, y que el cliente solo vea o pueda abrir ordenes con negocios que pueden cubrir el monto solicitado.

El problema que resuelve es simple: si un negocio solo tiene `40.00 USD` disponibles, ningun cliente debe poder abrir una orden de `80.00 USD` contra ese negocio.

## Por que existe

El rango base del negocio puede ser `$20-$100`, pero ese rango no significa que el negocio tenga siempre `$100` disponibles. El sistema necesita distinguir:

- limite permitido por operacion;
- limite diario del negocio;
- negocio online/offline;
- monto realmente disponible ahora;
- monto ya reservado por ordenes abiertas.

Sin esta separacion, el marketplace puede mostrar negocios que no pueden cumplir, abrir ordenes imposibles o permitir que varios clientes compitan por la misma liquidez declarada.

## Resultado permitido

- `PLAN_READY_FOR_OWNER_REVIEW`
- `LOCAL_VALIDATED_READY_FOR_OWNER_REVIEW` cuando pase pruebas locales sin deploy
- `STAGING_SCHEMA_APPLIED_PENDING_OWNER_SMOKE` cuando migracion y schema existan en staging, pero falte smoke funcional
- `BLOCKED_BY_EXPLICIT_EVIDENCE`

## Resultado no permitido

- `READY_FOR_REAL_USE`
- `PRODUCTION_READY`
- `APPROVED_FOR_PRODUCTION`

## Que construye este slice

- Migracion reversible `0035_business_available_capacity_matching`.
- Modulo backend de capacidad operativa declarada.
- Endpoints de negocio y admin para ver/ajustar capacidad.
- Filtro de marketplace por monto solicitado y capacidad efectiva.
- Reserva transaccional al crear orden.
- Liberacion o consumo idempotente al cancelar, expirar, completar o resolver disputa.
- UI minima en Mini App Negocio y Admin Web.
- Contratos y pruebas de privacidad, idempotencia y reglas de ordenes.

## Que no construye todavia

- No habilita multiples ordenes simultaneas sobre el mismo anuncio.
- No cambia creditos de publicacion ni lifecycle de anuncios mas alla de validar capacidad al crear orden.
- No modifica pagos, USDC, Zelle ni Base.
- No cambia produccion.
- No declara uso real ni flujo validado por el Owner.

## Decisiones iniciales

1. La capacidad disponible no es custodia de NODO.
2. La capacidad disponible es una declaracion operativa del negocio.
3. El backend es la autoridad que valida, reserva y libera capacidad.
4. El cliente no puede confiar solo en lo que vio en pantalla; crear orden revalida todo en servidor.
5. El publico no necesita ver el monto exacto disponible salvo que el Owner lo apruebe. El sistema puede mostrar "Disponible para tu monto".
6. Admin si debe ver declarado, reservado y restante para poder operar soporte.

## Reconciliacion 2026-07-28

Staging reporto `0035_business_available_capacity_matching.up.sql` aplicado y
sin migraciones pendientes. El codigo del slice esta incluido en el backend
staging actual, pero falta smoke funcional Cliente/Negocio/Admin antes de mover
pantallas o declarar el flujo validado.

## Decision arquitectonica vigente

Este slice conserva la regla actual de una orden por anuncio: al crear la orden,
el anuncio sigue moviendose `active -> in_order`. La capacidad declarada evita
que el cliente abra una orden mayor a lo disponible, pero no reparte un mismo
anuncio entre multiples clientes.

Permitir varias ordenes sobre el mismo anuncio requiere otro slice porque toca
creditos de publicacion, lifecycle del anuncio y reconciliacion operativa.

## Documentos del slice

- `DOMAIN_CONTRACT.md`
- `API_CONTRACT.md`
- `SECURITY_CONTRACT.md`
- `QA.md`
- `DO_NOT_BUILD.md`
- `BUILDER_PROMPT.md`
