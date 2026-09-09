# SOURCE_OF_TRUTH.md
# NODO - Orden de autoridad documental

## 1. Autoridad maxima

Este documento define que archivo manda cuando exista conflicto.

## 2. Orden de autoridad

1. 00_GOVERNANCE/SOURCE_OF_TRUTH.md
2. operations/PILOT_CONTROLLED_GATE.md
3. operations/README.md
4. 00_GOVERNANCE/ENGINEERING_GUARDRAILS.md
5. 00_GOVERNANCE/CODE_ARCHITECTURE_MASTER.md
6. 02_TRUST_AND_DISCLAIMERS/*.md
7. 04_DATA/ENUMS_AND_STATUS_MASTER.md
8. 04_DATA/DATA_MODEL_MASTER.md
9. 03_DOMAIN_RULES/*_MASTER.md
10. 05_SECURITY/RBAC_PERMISSION_MATRIX.md
11. 06_API_CONTRACTS/*.md
12. 01_PRODUCT/SPEC_MASTER.md
13. 01_PRODUCT/SCREEN_CATALOG.md
14. 08_SCREENS/**/*.md
15. 09_SLICES/**/slice contracts
16. 07_UI_UX/VISUAL_REFERENCE.md
17. 07_UI_UX/SCREEN_LAYOUT_MASTER.md
18. 07_UI_UX/UI_UX_MASTER.md
19. 10_QA/*.md

## 3. Reglas de conflicto

- Si SPEC_MASTER dice algo general y ENUMS_AND_STATUS_MASTER dice un enum exacto, manda ENUMS_AND_STATUS_MASTER.
- Si SCREEN_CATALOG lista una pantalla, debe existir su screen spec.
- Si API_CONTRACT contradice una pantalla, se pausa y se resuelve antes de construir.
- Si UI_UX contradice producto, seguridad, data, operaciones de piloto o disclaimers, manda producto/seguridad/data/operaciones/disclaimers.
- Si un cambio compila pero viola ENGINEERING_GUARDRAILS, se rechaza hasta tener evidencia o rediseno.
- Si falta contrato, no se inventa.

## 4. Valores oficiales MVP

payment_method:
- zelle
- usdt_trc20

delivery_method:
- pago_movil_ve

order.status:
- created
- waiting_payment
- payment_reported
- payment_rejected
- payment_confirmed
- delivered
- completed
- cancelled
- disputed

completion_reason:
- manual_confirmed
- auto_completed_after_24h
- admin_resolved

completed_auto NO es estado valido.

## 5. Posicion oficial NODO

NODO registra y organiza perfiles, ordenes y evidencia.

Cuando el proceso aplicable incluye revision documental, NODO registra ese
resultado sin convertirlo en garantia, recomendacion ni certificacion del
negocio.

Las partes coordinan y cumplen directamente entre ellas.

NODO no recibe, retiene, transfiere ni procesa fondos.

NODO no garantiza entrega, solvencia ni cumplimiento futuro.

## 6. Superficies oficiales

La separacion de superficies queda gobernada por:
- `control_plane/01_PRODUCT/SURFACE_ARCHITECTURE_MASTER.md`
- `control_plane/02_ARCHITECTURE/SURFACE_BOUNDARIES.md`
- `control_plane/05_SECURITY/SURFACE_ACCESS_POLICY.md`
- `control_plane/09_SLICES/slice_14_surface_separation_support_intake/`

Superficies canonicas:
- Mini App Cliente: solo clientes.
- Mini App Negocio: solo negocios aprobados y asociados a Telegram ID.
- Panel Admin Web Desktop: owner/admin/super_admin/support, fuera de Mini App Cliente.
- Bot Registro Negocios: capta solicitudes, no activa negocios automaticamente.
- Backend unico compartido: autoridad de auth, RBAC, datos, audit, storage, ordenes, creditos, soporte y jobs.

## 7. Regla de piloto controlado

NODO puede preparar un piloto controlado, no produccion abierta, solo bajo `operations/PILOT_CONTROLLED_GATE.md`.

Para piloto:
- alcance pequeno;
- negocios conocidos;
- clientes limitados;
- creditos manuales si el Owner mantiene USDC real fuera de alcance;
- Base Sepolia/testnet para cualquier prueba crypto;
- evidencia actual antes de cada corte.

Base mainnet/USDC real requiere aprobacion Owner separada de crypto production go-live.

Nombres tecnicos heredados como `remitter`, `payment_reported` o `payment_instructions` pueden existir por compatibilidad, pero no autorizan copy publico de remesa, envio de dinero, custodia, escrow, procesamiento financiero o garantia.
