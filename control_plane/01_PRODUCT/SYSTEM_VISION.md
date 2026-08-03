# SYSTEM_VISION.md

NODO es una Telegram Mini App tipo directorio de negocios registrados.

Conecta remitentes fuera de Venezuela con negocios registrados que reciben Zelle o USDT TRC20 y pagan bolivares por pago movil en Venezuela.

NODO registra ordenes, evidencia, estados, chat, reputacion, auditoria, creditos publicitarios y reglas de riesgo.

NODO no toca fondos, no hace escrow, no procesa pagos de remesas, no garantiza entrega y no actua como banco.

## Vision operativa

El sistema debe nacer con arquitectura profesional:

- frontend mobile-first para Telegram Mini App
- backend modular
- DB con constraints e indices
- Redis para locks/rate limits/jobs
- webhooks para Telegram y Stripe
- admin panel funcional
- observabilidad y auditoria

## Principio de confianza

NODO cuida la confianza verificando datos basicos, mostrando reputacion y dejando evidencia. La responsabilidad del pago y la entrega sigue siendo entre remitente y negocio.
