"use client";

import { Text, Title } from "@telegram-apps/telegram-ui";
import { useEffect, useState } from "react";
import { claimCreditHandoff, getCreditHandoffChallenge } from "../../../api/credits";
import { useInjectedWallet } from "../../../hooks/business-mini-app/useInjectedWallet";
import { getInjectedEthereumProvider, resolveWalletNetworkProfile } from "../../../lib/wallet/eip1193";
import {
  approveExactTestUsdc,
  payTestCreditPurchase,
  paymentAuthorizationExpired,
  readTestUsdcAllowance,
  testnetPaymentErrorMessage,
} from "../../../lib/wallet/testnetCreditPayment";
import type { ContractCreditPayment, CreditHandoffChallenge, CreditHandoffStatus } from "../../../types/credits";

type PaymentStep = "wallet" | "checking" | "review" | "approval" | "pay" | "sent";


function extractCreditHandoffToken(search: string, fragment: string): string | null {
  const token = new URLSearchParams(search).get("handoff")
    || new URLSearchParams(fragment.replace(/^#/, "")).get("handoff");
  return token && /^[A-Za-z0-9_-]{43}$/.test(token) ? token : null;
}


export default function BusinessCreditPaymentHandoffPage() {
  const [handoffToken, setHandoffToken] = useState<string | null>(null);
  const [challenge, setChallenge] = useState<CreditHandoffChallenge | null>(null);
  const [loadingChallenge, setLoadingChallenge] = useState(true);
  const [claiming, setClaiming] = useState(false);
  const [paymentDetail, setPaymentDetail] = useState<CreditHandoffStatus | null>(null);
  const [paymentStep, setPaymentStep] = useState<PaymentStep>("wallet");
  const [paymentActionBusy, setPaymentActionBusy] = useState(false);
  const [pageError, setPageError] = useState<string | null>(null);
  const expectedNetwork = challenge
    ? resolveWalletNetworkProfile(challenge.network, challenge.chain_id)
    : null;
  const {
    connectWallet,
    connectedWalletAddress,
    connectedWalletAddressMasked,
    connectingWallet,
    signWalletChallenge,
    switchWalletToExpectedNetwork,
    switchingWalletNetwork,
    walletChainId,
    walletError,
    walletIsExpectedNetwork,
    walletProviderStatus,
  } = useInjectedWallet(() => {
    setPaymentDetail(null);
    setPaymentStep("wallet");
    setPageError("La cuenta o red cambio. Revisa la wallet antes de continuar.");
  }, expectedNetwork);

  const payment = paymentDetail?.payment || null;
  const paymentExpired = payment ? paymentAuthorizationExpired(payment) : false;

  useEffect(() => {
    const token = extractCreditHandoffToken(window.location.search, window.location.hash);
    window.history.replaceState(null, "", window.location.pathname);
    if (!token) {
      setPageError("Este enlace no es valido. Inicia de nuevo desde Telegram.");
      setLoadingChallenge(false);
      return;
    }
    setHandoffToken(token);
    void getCreditHandoffChallenge(token)
      .then((data) => {
        const network = resolveWalletNetworkProfile(data.network, data.chain_id);
        if (!network || !data.is_testnet || data.network !== "base_sepolia") {
          throw new Error("La red de prueba no esta configurada correctamente.");
        }
        setChallenge(data);
      })
      .catch((error: unknown) => {
        setPageError(error instanceof Error ? error.message : "No pudimos abrir esta preparacion.");
      })
      .finally(() => setLoadingChallenge(false));
  }, []);

  const checkTestUsdcPermission = async (currentPayment: ContractCreditPayment | null = payment) => {
    if (!currentPayment || !connectedWalletAddress || walletChainId === null) {
      setPaymentStep("review");
      setPageError("Prepara la compra antes de revisar el permiso de USDC.");
      return;
    }
    const provider = getInjectedEthereumProvider();
    if (!provider) {
      setPaymentStep("review");
      setPageError("No detectamos una wallet compatible.");
      return;
    }
    setPaymentActionBusy(true);
    setPaymentStep("checking");
    setPageError(null);
    try {
      const allowance = await readTestUsdcAllowance(
        provider,
        currentPayment,
        connectedWalletAddress,
        walletChainId,
      );
      const requiredAmount = BigInt(currentPayment.expected_amount_units || "0");
      setPaymentStep(allowance >= requiredAmount ? "pay" : "approval");
    } catch (error) {
      setPaymentStep("review");
      setPageError(testnetPaymentErrorMessage(error));
    } finally {
      setPaymentActionBusy(false);
    }
  };

  const confirmWallet = async () => {
    if (!handoffToken || !challenge || !connectedWalletAddress || !walletIsExpectedNetwork) {
      setPageError("Conecta una wallet en Base Sepolia antes de continuar.");
      return;
    }
    setClaiming(true);
    setPageError(null);
    try {
      const signature = await signWalletChallenge(challenge.challenge);
      const data = await claimCreditHandoff({
        handoffToken,
        walletAddress: connectedWalletAddress,
        chainId: walletChainId ?? 0,
        signature,
      });
      if (!data.payment || !data.purchase) {
        throw new Error("La compra no quedo preparada. Inicia de nuevo desde Telegram.");
      }
      setPaymentDetail(data);
      await checkTestUsdcPermission(data.payment);
    } catch (error) {
      const safeLocalMessage = error instanceof Error && (
        error.message === "La compra no quedo preparada. Inicia de nuevo desde Telegram."
      ) ? error.message : null;
      setPageError(safeLocalMessage || testnetPaymentErrorMessage(error));
    } finally {
      setClaiming(false);
    }
  };

  const approveTestUsdc = async () => {
    if (!payment || !connectedWalletAddress || walletChainId === null) {
      setPageError("Prepara la compra antes de autorizar USDC de prueba.");
      return;
    }
    const provider = getInjectedEthereumProvider();
    if (!provider) {
      setPageError("No detectamos una wallet compatible.");
      return;
    }
    setPaymentActionBusy(true);
    setPageError(null);
    try {
      await approveExactTestUsdc(provider, payment, connectedWalletAddress, walletChainId);
      setPaymentStep("pay");
    } catch (error) {
      setPageError(testnetPaymentErrorMessage(error));
    } finally {
      setPaymentActionBusy(false);
    }
  };

  const submitTestPayment = async () => {
    if (!payment || !connectedWalletAddress || walletChainId === null) {
      setPageError("Prepara la compra antes de pagar.");
      return;
    }
    const provider = getInjectedEthereumProvider();
    if (!provider) {
      setPageError("No detectamos una wallet compatible.");
      return;
    }
    setPaymentActionBusy(true);
    setPageError(null);
    try {
      await payTestCreditPurchase(provider, payment, connectedWalletAddress, walletChainId);
      setPaymentStep("sent");
    } catch (error) {
      setPageError(testnetPaymentErrorMessage(error));
    } finally {
      setPaymentActionBusy(false);
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
          <Text>Este flujo usa USDC y ETH de prueba, sin valor real, en Base Sepolia.</Text>
          <Text>NODO no ve ni guarda tu clave privada.</Text>

          <div className="business-status-panel" role="status">
            <div>
              <span className="status-dot" aria-hidden="true" />
              <div>
                <strong>
                  {loadingChallenge
                    ? "Validando enlace"
                    : connectedWalletAddress
                      ? "Wallet conectada"
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

          {connectedWalletAddress && challenge ? (
            <div className="business-status-panel" role="status">
              <div>
                <span className="status-dot" aria-hidden="true" />
                <div>
                  <strong>{walletIsExpectedNetwork ? "Base Sepolia conectada" : "Red distinta de Base Sepolia"}</strong>
                  <Text>Chain ID: {walletChainId ?? "desconocido"}</Text>
                </div>
              </div>
            </div>
          ) : null}

          {pageError || walletError ? <Text role="alert">{pageError || walletError}</Text> : null}

          {paymentDetail ? (
            <div className="business-status-panel" role="status">
              <div>
                <span className="status-dot" aria-hidden="true" />
                <div>
                  <strong>
                    {paymentStep === "sent"
                      ? "Pago enviado. Vuelve a Telegram y toca Actualizar"
                      : `Pagaras ${payment?.expected_amount_display || paymentDetail.purchase.price_usd} USDC de prueba en Base Sepolia`}
                  </strong>
                  <Text>
                    {paymentStep === "approval"
                      ? "MetaMask pedira permiso solo por el monto exacto de esta compra."
                        : paymentStep === "pay"
                          ? "Autorizacion enviada. Si MetaMask aun la confirma, espera unos segundos antes de pagar."
                          : paymentStep === "sent"
                            ? "El watcher de prueba confirmara el evento; NODO no usa hashes pegados."
                            : paymentStep === "review"
                              ? "Puedes revisar el permiso sin crear otra compra."
                              : "Revisando el permiso de USDC de prueba."}
                  </Text>
                </div>
              </div>
            </div>
          ) : null}

          {!paymentDetail && (loadingChallenge || challenge) ? (
            <button
              className="mini-action-button mini-action-button--filled mini-action-button--full"
              type="button"
              disabled={loadingChallenge || connectingWallet || switchingWalletNetwork || claiming}
              onClick={() => {
                if (!connectedWalletAddress) {
                  void connectWallet();
                } else if (!walletIsExpectedNetwork) {
                  void switchWalletToExpectedNetwork();
                } else {
                  void confirmWallet();
                }
              }}
            >
              {connectingWallet
                ? "Conectando..."
                : switchingWalletNetwork
                  ? "Abriendo Base Sepolia..."
                  : claiming
                    ? "Comprobando wallet..."
                    : !connectedWalletAddress
                      ? "Conectar wallet"
                      : !walletIsExpectedNetwork
                        ? "Cambiar a Base Sepolia"
                        : "Confirmar esta wallet"}
            </button>
          ) : paymentStep === "review" || paymentStep === "checking" ? (
            <button
              className="mini-action-button mini-action-button--filled mini-action-button--full"
              type="button"
              disabled={paymentActionBusy || claiming || paymentExpired}
              onClick={() => void checkTestUsdcPermission()}
            >
              {paymentActionBusy || paymentStep === "checking"
                ? "Revisando permiso..."
                : "Revisar permiso de USDC"}
            </button>
          ) : paymentStep === "approval" ? (
            <button
              className="mini-action-button mini-action-button--filled mini-action-button--full"
              type="button"
              disabled={paymentActionBusy || paymentExpired}
              onClick={() => void approveTestUsdc()}
            >
              {paymentActionBusy ? "Abriendo MetaMask..." : "Autorizar USDC de prueba"}
            </button>
          ) : paymentStep === "pay" ? (
            <button
              className="mini-action-button mini-action-button--filled mini-action-button--full"
              type="button"
              disabled={paymentActionBusy || paymentExpired}
              onClick={() => void submitTestPayment()}
            >
              {paymentActionBusy ? "Enviando..." : "Pagar creditos de prueba"}
            </button>
          ) : null}

          {paymentExpired && paymentStep !== "sent" ? (
            <Text role="alert">La autorizacion vencio. Inicia una compra nueva desde Telegram.</Text>
          ) : null}
        </div>
      </section>
    </main>
  );
}
