# SCOPE.md

## Incluye

- Crear purchase on-chain Base USDC para paquetes de creditos.
- Verificar tx on-chain por watcher y por tx hash submitido.
- Acreditar creditos exactamente una vez.
- Admin review read/reject para casos `under_review`.
- Bot/admin privado solo como notificador.
- Tests de seguridad, idempotencia y watcher.

## No incluye

- USDT Base en MVP.
- USDT TRC20 manual como flujo Base.
- Custodia o pagos de remesas.
- Private keys, seed phrases o signing backend.
- Refunds automaticos.
- Reembolsos on-chain.
- Override manual de acreditacion sin verifier.
- Cambios a lifecycle de anuncios, ordenes o disputas.
- Nuevas pantallas fuera de creditos negocio/admin.
- Deploy.
- READY_FOR_REAL_USE.
