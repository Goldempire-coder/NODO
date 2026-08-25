"use client";

import { Text, Title } from "@telegram-apps/telegram-ui";
import { useInjectedWallet } from "../../../hooks/business-mini-app/useInjectedWallet";

export default function BusinessWalletProbePage() {
  const {
    connectWallet,
    connectedWalletAddress,
    connectedWalletAddressMasked,
    connectingWallet,
    switchWalletToBase,
    switchingWalletNetwork,
    walletChainId,
    walletError,
    walletIsBase,
    walletProviderStatus,
  } = useInjectedWallet(() => undefined);
  const walletReadyForTelegram = Boolean(connectedWalletAddress) && walletIsBase;

  return (
    <main className="app-shell">
      <section className="business-shell" aria-labelledby="wallet-probe-title">
        <div className="business-card">
          <Text className="business-card__label">Prueba de conexión</Text>
          <Title id="wallet-probe-title" level="2" className="business-shell__title">
            Wallet en MetaMask
          </Title>
          <Text>Esta prueba no cobra, no firma pagos y no mueve fondos.</Text>
          <div className="business-status-panel" role="status">
            <div>
              <span className="status-dot" aria-hidden="true" />
              <div>
                <strong>
                  {walletProviderStatus === "checking"
                    ? "Buscando wallet"
                    : walletProviderStatus === "available"
                      ? "Wallet compatible detectada"
                      : "No detectamos una wallet compatible"}
                </strong>
                <Text>
                  {connectedWalletAddress
                    ? `Cuenta: ${connectedWalletAddressMasked}`
                    : "Abre esta página dentro del navegador de MetaMask e intenta conectar."}
                </Text>
              </div>
            </div>
          </div>
          {connectedWalletAddress ? (
            <div className="business-status-panel" role="status">
              <div>
                <span className="status-dot" aria-hidden="true" />
                <div>
                  <strong>{walletIsBase ? "Base conectada" : "Red distinta de Base"}</strong>
                  <Text>Chain ID: {walletChainId ?? "desconocido"}</Text>
                  {!walletIsBase ? <small>Cambia la red de tu wallet a Base (8453).</small> : null}
                </div>
              </div>
            </div>
          ) : null}
          {walletError ? <Text role="alert">{walletError}</Text> : null}
          {walletReadyForTelegram ? (
            <div className="business-status-panel" role="status">
              <div>
                <span className="status-dot" aria-hidden="true" />
                <div>
                  <strong>Listo para volver a Telegram</strong>
                  <Text>MetaMask ya está en Base. Usa el botón Telegram de arriba para regresar a NODO.</Text>
                  <small>Esta prueba terminó; todavía no prepara compras ni pagos.</small>
                </div>
              </div>
            </div>
          ) : (
            <button
              className="mini-action-button mini-action-button--filled mini-action-button--full"
              type="button"
              disabled={connectingWallet || switchingWalletNetwork || walletProviderStatus === "checking"}
              onClick={() => {
                if (connectedWalletAddress && !walletIsBase) {
                  void switchWalletToBase();
                  return;
                }
                void connectWallet();
              }}
            >
              {connectingWallet
                ? "Conectando..."
                : switchingWalletNetwork
                  ? "Abriendo Base..."
                  : connectedWalletAddress
                    ? "Cambiar a Base"
                    : "Conectar wallet"}
            </button>
          )}
        </div>
      </section>
    </main>
  );
}
