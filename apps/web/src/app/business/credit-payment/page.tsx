"use client";

import { Text, Title } from "@telegram-apps/telegram-ui";
import { useEffect, useState } from "react";
import { claimCreditHandoff, getCreditHandoffChallenge } from "../../../api/credits";
import { useInjectedWallet } from "../../../hooks/business-mini-app/useInjectedWallet";
import type { CreditHandoffChallenge } from "../../../types/credits";


function extractCreditHandoffToken(fragment: string): string | null {
  const token = new URLSearchParams(fragment.replace(/^#/, "")).get("handoff");
  return token && /^[A-Za-z0-9_-]{43}$/.test(token) ? token : null;
}


export default function BusinessCreditPaymentHandoffPage() {
  const [handoffToken, setHandoffToken] = useState<string | null>(null);
  const [challenge, setChallenge] = useState<CreditHandoffChallenge | null>(null);
  const [loadingChallenge, setLoadingChallenge] = useState(true);
  const [claiming, setClaiming] = useState(false);
  const [completed, setCompleted] = useState(false);
  const [pageError, setPageError] = useState<string | null>(null);
  const {
    connectWallet,
    connectedWalletAddress,
    connectedWalletAddressMasked,
    connectingWallet,
    signWalletChallenge,
    switchWalletToBase,
    switchingWalletNetwork,
    walletChainId,
    walletError,
    walletIsBase,
    walletProviderStatus,
  } = useInjectedWallet(() => {
    setCompleted(false);
    setPageError("La cuenta o red cambio. Revisa la wallet antes de continuar.");
  });

  useEffect(() => {
    const token = extractCreditHandoffToken(window.location.hash);
    window.history.replaceState(null, "", `${window.location.pathname}${window.location.search}`);
    if (!token) {
      setPageError("Este enlace no es valido. Inicia de nuevo desde Telegram.");
      setLoadingChallenge(false);
      return;
    }
    setHandoffToken(token);
    void getCreditHandoffChallenge(token)
      .then(setChallenge)
      .catch((error: unknown) => {
        setPageError(error instanceof Error ? error.message : "No pudimos abrir esta preparacion.");
      })
      .finally(() => setLoadingChallenge(false));
  }, []);

  const confirmWallet = async () => {
    if (!handoffToken || !challenge || !connectedWalletAddress || !walletIsBase) {
      setPageError("Conecta una wallet en Base antes de continuar.");
      return;
    }
    setClaiming(true);
    setPageError(null);
    try {
      const signature = await signWalletChallenge(challenge.challenge);
      await claimCreditHandoff({
        handoffToken,
        walletAddress: connectedWalletAddress,
        chainId: walletChainId ?? 0,
        signature,
      });
      setCompleted(true);
    } catch (error) {
      setPageError(error instanceof Error ? error.message : "No pudimos comprobar esta wallet.");
    } finally {
      setClaiming(false);
    }
  };

  return (
    <main className="app-shell">
      <section className="business-shell" aria-labelledby="credit-handoff-title">
        <div className="business-card">
          <Text className="business-card__label">Preparacion segura</Text>
          <Title id="credit-handoff-title" level="2" className="business-shell__title">
            Wallet para creditos NODO
          </Title>
          <Text>Esto no cobra, no aprueba pagos y no mueve fondos.</Text>
          <Text>NODO no ve ni guarda tu clave privada.</Text>

          <div className="business-status-panel" role="status">
            <div>
              <span className="status-dot" aria-hidden="true" />
              <div>
                <strong>
                  {loadingChallenge
                    ? "Validando enlace"
                    : walletProviderStatus === "available"
                      ? "Wallet compatible detectada"
                      : "No detectamos una wallet compatible"}
                </strong>
                <Text>
                  {connectedWalletAddress
                    ? `Cuenta: ${connectedWalletAddressMasked}`
                    : "Abre esta pagina dentro del navegador de MetaMask."}
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
                </div>
              </div>
            </div>
          ) : null}

          {pageError || walletError ? <Text role="alert">{pageError || walletError}</Text> : null}

          {completed ? (
            <div className="business-status-panel" role="status">
              <div>
                <span className="status-dot" aria-hidden="true" />
                <div>
                  <strong>Listo. Vuelve a Telegram</strong>
                  <Text>En NODO pulsa Actualizar para recuperar la compra preparada.</Text>
                </div>
              </div>
            </div>
          ) : (
            <button
              className="mini-action-button mini-action-button--filled mini-action-button--full"
              type="button"
              disabled={loadingChallenge || connectingWallet || switchingWalletNetwork || claiming}
              onClick={() => {
                if (!connectedWalletAddress) {
                  void connectWallet();
                } else if (!walletIsBase) {
                  void switchWalletToBase();
                } else {
                  void confirmWallet();
                }
              }}
            >
              {connectingWallet
                ? "Conectando..."
                : switchingWalletNetwork
                  ? "Abriendo Base..."
                  : claiming
                    ? "Comprobando wallet..."
                    : !connectedWalletAddress
                      ? "Conectar wallet"
                      : !walletIsBase
                        ? "Cambiar a Base"
                        : "Confirmar esta wallet"}
            </button>
          )}
        </div>
      </section>
    </main>
  );
}
