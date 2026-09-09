# PILOT_CONTROLLED_GATE

Estado: OFFICIAL - OWNER REVIEW REQUIRED
Ultima actualizacion: 2026-09-09

Este gate separa dos cosas que no deben mezclarse:

- piloto controlado con pocos negocios/clientes conocidos;
- produccion abierta o uso masivo.

El piloto puede avanzar solo si el Owner acepta los riesgos residuales por escrito en la evidencia del corte. Este documento no declara `READY_FOR_REAL_USE` ni reemplaza revision legal.

## Alcance permitido del piloto

- Negocios conocidos, registrados y aprobados manualmente.
- Clientes limitados por invitacion o acceso controlado.
- Montos bajos y operacion supervisada.
- Creditos asignados manualmente por Owner si las compras USDC reales siguen fuera de alcance.
- Base Sepolia/testnet para cualquier prueba crypto on-chain.
- Admin Web disponible para bloquear, pausar, revisar alertas y activar modo emergencia.

## Fuera de alcance del piloto

- Produccion abierta.
- Marketing publico masivo.
- Base mainnet/USDC real para creditos sin aprobacion Owner separada.
- Wallet, signer o treasury production-ready.
- Garantias de pago, entrega, recuperacion, escrow o custodia.
- Operaciones en jurisdicciones no revisadas.
- Restaurar datos reales para demostrar backup.

## Gate minimo antes de invitar usuarios

| Area | Minimo piloto | Estado si falta |
|---|---|---|
| Release identity | Backend y web staging reportan el mismo SHA | BLOCKED |
| Rollback codigo | Procedimiento para redeploy de SHA anterior documentado | BLOCKED |
| Backup/restore | Riesgo aceptado o restore drill aislado validado | OWNER_RISK_ACCEPTANCE_REQUIRED |
| Alertas | Telegram Admin Alerts probado y eventos criticos documentados | BLOCKED |
| Emergencia | Kill switch visible, probado y con mensaje al usuario | BLOCKED |
| Lenguaje legal | Cliente, Negocio, Admin y website sin claims de custodia/garantia | BLOCKED |
| Costos | Listas pesadas con paginacion o carga explicita | BLOCKED |
| Produccion separada | Variables, dominios, bots, DB, Redis y storage definidos por ambiente | OWNER_DECISION_REQUIRED |

## Evidencia requerida por corte

- commit SHA backend/web;
- URL publica staging;
- resultado de `/health`, `/ready`, `/api/v1/version` y `/version.json`;
- pruebas automatizadas ejecutadas;
- smoke manual Owner en Telegram para Cliente y Negocio;
- screenshot o confirmacion del bloque Admin de emergencia;
- confirmacion de Telegram Admin Alerts;
- lista de riesgos aceptados y riesgos bloqueantes;
- declaracion explicita de que USDC real queda fuera del piloto si aplica.

## Resultado permitido

- `BLOCKED`: falta una condicion minima.
- `OWNER_RISK_ACCEPTANCE_REQUIRED`: el piloto podria operar, pero con un riesgo documentado que solo el Owner puede aceptar.
- `READY_FOR_OWNER_REVIEW`: evidencia tecnica lista para decision Owner.

Resultado prohibido para builders:

- `READY_FOR_REAL_USE`
- `READY_FOR_PRODUCTION`

## Frase operativa oficial

NODO registra negocios, ofertas, ordenes, chat, evidencia, reputacion y creditos internos. El pago y la entrega entre cliente y negocio ocurren directamente entre las partes. NODO no recibe, retiene, mueve, transmite, libera ni garantiza fondos entre cliente y negocio.
