import { useCallback, useEffect, useRef, useState } from "react";
import { ApiClientError, type AuthenticatedRequest } from "../../api/client";
import {
  createBusinessCreditHandoff,
  dismissBusinessContractCreditPurchase,
  getBusinessCreditHandoff,
  getBusinessPendingContractCreditPurchase,
  getBusinessCreditPurchase,
  getBusinessCreditWallet,
  getBusinessReferrals,
  startBusinessBaseUsdcPayment
} from "../../api/credits";
import type { BusinessMiniAppView } from "../../constants/businessViews";
import type { BusinessSummary } from "../../types/business";
import type { ContractCreditPayment, CreditPurchase, CreditWallet, ReferralData } from "../../types/credits";
import { actionStartedAt, recordBusinessActionCompleted, recordBusinessActionFailed, recordBusinessActionStarted } from "../actionTelemetry";
import { useStableIdempotencyKeys } from "../useStableIdempotencyKeys";
import { openMetaMaskCreditHandoff as launchMetaMaskCreditHandoff } from "../../lib/wallet/metamaskHandoff";
import { BASE_SEPOLIA_WALLET_NETWORK } from "../../lib/wallet/eip1193";
import { useInjectedWallet } from "./useInjectedWallet";
import { handleBusinessPinError as routeBusinessPinError, requireUnlockedBusinessPin } from "./businessPinGuards";
import {
  BASE_USDC_PAYABLE_PENDING_STATUS,
  DEFAULT_CREDIT_PACKAGE,
  isDismissableBaseUsdcPurchase,
  isPendingBaseUsdcPurchaseForBusiness,
} from "./businessCreditPaymentRules";
import {
  clearRememberedBaseUsdcPurchase,
  clearRememberedCreditHandoffId,
  creditHandoffStorageKey,
  pendingBaseUsdcPurchaseStorageKey,
  readRememberedBaseUsdcPurchaseId,
  readRememberedCreditHandoffId,
  rememberCreditHandoffId,
  rememberPendingBaseUsdcPurchase,
} from "./businessCreditPaymentStorage";

const BASE_USDC_CREDIT_NOTICE = "Modo de prueba: NODO prepara compras de creditos en USDC sobre Base Sepolia.";
const BASE_USDC_PAYMENT_UNAVAILABLE_MESSAGE = "La compra de creditos no esta disponible en este momento.";

type PrepareCreditHandoffOptions = {
  silent?: boolean;
};

type RefreshSelectedCreditPurchaseOptions = {
  silent?: boolean;
};

function baseUsdcPaymentErrorMessage(error: unknown) {
  if (error instanceof ApiClientError) {
    if (error.code === "VALIDATION_ERROR") {
      return "Revisa la wallet pagadora e intenta de nuevo.";
    }
    if (
      error.code === "CRYPTO_CONTRACT_PAYMENT_NOT_CONFIGURED" ||
      error.code === "CRYPTO_PAYMENT_SIGNER_UNAVAILABLE" ||
      error.code === "CRYPTO_PAYMENT_CONTRACT_PAUSED"
    ) {
      return BASE_USDC_PAYMENT_UNAVAILABLE_MESSAGE;
    }
    if (error.code === "CRYPTO_PAYMENT_PENDING_PURCHASE_EXISTS") {
      return "Tienes un pago Base USDC pendiente. Continua ese pago antes de abrir otro.";
    }
    return error.message;
  }
  return "No logramos iniciar el pago en red Base.";
}

export function useBusinessCreditsModel({
  business,
  request,
  setBusy,
  setNotice,
  setView
}: {
  business: BusinessSummary | null;
  request: AuthenticatedRequest;
  setBusy: (busy: boolean) => void;
  setNotice: (notice: string) => void;
  setView: (view: BusinessMiniAppView) => void;
}) {
  const [creditWallet, setCreditWallet] = useState<CreditWallet | null>(null);
  const [creditWalletRefreshState, setCreditWalletRefreshState] = useState<"idle" | "ready" | "stale">("idle");
  const [selectedCreditPurchase, setSelectedCreditPurchase] = useState<CreditPurchase | null>(null);
  const [selectedCreditPayment, setSelectedCreditPayment] = useState<ContractCreditPayment | null>(null);
  const [pendingCreditPurchase, setPendingCreditPurchase] = useState<CreditPurchase | null>(null);
  const [creditPackage, setCreditPackage] = useState<string | null>(null);
  const [referralData, setReferralData] = useState<ReferralData | null>(null);
  const [generatingCreditPayment, setGeneratingCreditPayment] = useState(false);
  const [loadingPendingPurchase, setLoadingPendingPurchase] = useState(false);
  const [dismissingPendingCreditPurchase, setDismissingPendingCreditPurchase] = useState(false);
  const [pendingDismissConfirmationRequested, setPendingDismissConfirmationRequested] = useState(false);
  const [refreshingCreditPurchase, setRefreshingCreditPurchase] = useState(false);
  const [creditHandoffId, setCreditHandoffId] = useState<string | null>(null);
  const [creditHandoffLaunchToken, setCreditHandoffLaunchToken] = useState<string | null>(null);
  const [creditHandoffOpened, setCreditHandoffOpened] = useState(false);
  const [creditHandoffError, setCreditHandoffError] = useState<string | null>(null);
  const [preparingCreditHandoff, setPreparingCreditHandoff] = useState(false);
  const [refreshingCreditHandoff, setRefreshingCreditHandoff] = useState(false);
  const creditPackageRef = useRef<string | null>(null);
  const refreshingCreditPurchaseRef = useRef(false);
  const { clearIdempotencyKey, getIdempotencyKey } = useStableIdempotencyKeys();
  const pendingPurchaseStorageKey = pendingBaseUsdcPurchaseStorageKey(business?.id);
  const handoffStorageKey = creditHandoffStorageKey(business?.id);
  const accessLink = business?.access_link;
  const canPrepareCreditHandoffSilently = !accessLink?.pin_required
    || Boolean(accessLink.pin_configured && accessLink.pin_unlocked);

  useEffect(() => {
    creditPackageRef.current = creditPackage;
  }, [creditPackage]);

  const invalidatePreparedCreditPayment = useCallback(() => {
    const hadPreparedPayment = Boolean(selectedCreditPurchase || selectedCreditPayment || pendingCreditPurchase);
    setSelectedCreditPurchase(null);
    setSelectedCreditPayment(null);
    setPendingCreditPurchase(null);
    setPendingDismissConfirmationRequested(false);
    clearRememberedBaseUsdcPurchase(pendingPurchaseStorageKey);
    setCreditHandoffId(null);
    setCreditHandoffLaunchToken(null);
    setCreditHandoffOpened(false);
    setCreditHandoffError(null);
    clearRememberedCreditHandoffId(handoffStorageKey);
    if (hadPreparedPayment) {
      setView("buy-credits");
      setNotice("La cuenta o red cambió. Prepara la autorización de nuevo.");
    }
  }, [handoffStorageKey, pendingCreditPurchase, pendingPurchaseStorageKey, selectedCreditPayment, selectedCreditPurchase, setNotice, setView]);

  const {
    connectWallet,
    connectingWallet,
    connectedWalletAddress,
    connectedWalletAddressMasked,
    getConnectedWalletSnapshot,
    switchWalletToExpectedNetwork,
    switchingWalletNetwork,
    walletChainId,
    walletError,
    walletIsExpectedNetwork,
    walletProviderStatus,
  } = useInjectedWallet(invalidatePreparedCreditPayment, BASE_SEPOLIA_WALLET_NETWORK);

  const requireBusinessPinFor = useCallback((action: string) => {
    return requireUnlockedBusinessPin({ action, business, setNotice, setView });
  }, [business?.access_link, setNotice, setView]);

  const handleBusinessPinError = useCallback((error: unknown, action: string) => {
    return routeBusinessPinError({ action, error, setNotice, setView });
  }, [setNotice, setView]);

  const refreshCreditWallet = useCallback(async () => {
    const startedAt = actionStartedAt();
    try {
      const data = await getBusinessCreditWallet<{ wallet: CreditWallet; disclaimer?: string }>(request);
      setCreditWallet(data.wallet);
      setCreditWalletRefreshState("ready");
      return data.wallet;
    } catch (error) {
      setCreditWalletRefreshState("stale");
      recordBusinessActionFailed("credit_balance_refresh", "credits", startedAt, error instanceof ApiClientError ? error.code : undefined);
      return null;
    }
  }, [request]);

  const loadBackendPendingBaseUsdcPurchase = useCallback(async () => {
    const data = await getBusinessPendingContractCreditPurchase(request);
    if (data.purchase && isPendingBaseUsdcPurchaseForBusiness(data.purchase, business?.id)) {
      setPendingCreditPurchase(data.purchase);
      rememberPendingBaseUsdcPurchase(data.purchase, pendingPurchaseStorageKey);
      return data;
    }
    setPendingCreditPurchase(null);
    setPendingDismissConfirmationRequested(false);
    if (data.purchase) {
      clearRememberedBaseUsdcPurchase(pendingPurchaseStorageKey, data.purchase.id);
    } else {
      clearRememberedBaseUsdcPurchase(pendingPurchaseStorageKey);
    }
    return null;
  }, [business?.id, pendingPurchaseStorageKey, request]);

  const openBuyCredits = useCallback(async () => {
    setNotice(BASE_USDC_CREDIT_NOTICE);
    setView("buy-credits");
    setSelectedCreditPurchase(null);
    setSelectedCreditPayment(null);
    setPendingCreditPurchase(null);
    setCreditPackage((current) => current || DEFAULT_CREDIT_PACKAGE);
    setCreditHandoffError(null);
    if (!creditHandoffLaunchToken) {
      const rememberedHandoffId = readRememberedCreditHandoffId(handoffStorageKey);
      setCreditHandoffId(rememberedHandoffId);
      setCreditHandoffOpened(Boolean(rememberedHandoffId));
    }
    const rememberedPurchaseId = readRememberedBaseUsdcPurchaseId(pendingPurchaseStorageKey);
    setLoadingPendingPurchase(true);
    try {
      if (rememberedPurchaseId) {
        const data = await getBusinessCreditPurchase(request, rememberedPurchaseId);
        if (isPendingBaseUsdcPurchaseForBusiness(data.purchase, business?.id)) {
          setPendingCreditPurchase(data.purchase);
          setPendingDismissConfirmationRequested(false);
          setCreditHandoffId(null);
          setCreditHandoffLaunchToken(null);
          setCreditHandoffOpened(false);
          clearRememberedCreditHandoffId(handoffStorageKey);
          setNotice("Tienes un pago Base USDC pendiente. Puedes continuarlo cuando quieras.");
          return;
        }
        setPendingCreditPurchase(null);
        clearRememberedBaseUsdcPurchase(pendingPurchaseStorageKey, rememberedPurchaseId);
      }
      const backendPending = await loadBackendPendingBaseUsdcPurchase();
      if (backendPending?.purchase) {
        setPendingDismissConfirmationRequested(false);
        setCreditHandoffId(null);
        setCreditHandoffLaunchToken(null);
        setCreditHandoffOpened(false);
        clearRememberedCreditHandoffId(handoffStorageKey);
        setNotice("Tienes un pago Base USDC pendiente. Puedes continuarlo cuando quieras.");
      }
    } catch {
      setPendingCreditPurchase(null);
      if (rememberedPurchaseId) {
        clearRememberedBaseUsdcPurchase(pendingPurchaseStorageKey, rememberedPurchaseId);
      }
    } finally {
      setLoadingPendingPurchase(false);
    }
  }, [business?.id, creditHandoffLaunchToken, handoffStorageKey, loadBackendPendingBaseUsdcPurchase, pendingPurchaseStorageKey, request, setNotice, setView]);

  const selectCreditPackage = useCallback((packageCode: string) => {
    if (packageCode !== creditPackage) {
      setCreditHandoffId(null);
      setCreditHandoffLaunchToken(null);
      setCreditHandoffOpened(false);
      setCreditHandoffError(null);
      setPendingDismissConfirmationRequested(false);
      clearRememberedCreditHandoffId(handoffStorageKey);
    }
    setCreditPackage(packageCode);
  }, [creditPackage, handoffStorageKey]);

  const prepareMetaMaskCreditHandoff = useCallback(async (options: PrepareCreditHandoffOptions = {}) => {
    const requestedPackage = creditPackage;
    const silent = options.silent === true;
    setCreditHandoffError(null);
    if (!requestedPackage) {
      if (!silent) {
        setNotice("Elige un paquete antes de abrir MetaMask.");
      }
      return false;
    }
    if (creditHandoffLaunchToken) {
      return true;
    }
    if (preparingCreditHandoff) {
      return false;
    }
    try {
      const backendPending = await loadBackendPendingBaseUsdcPurchase();
      if (backendPending?.purchase) {
        setCreditHandoffLaunchToken(null);
        setCreditHandoffOpened(false);
        clearRememberedCreditHandoffId(handoffStorageKey);
        if (!silent) {
          setNotice("Tienes un pago Base USDC pendiente. Continua ese pago antes de abrir otro.");
        }
        return false;
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : "No pudimos revisar pagos pendientes.";
      setCreditHandoffError(message);
      if (!silent) {
        setNotice(message);
      }
      return false;
    }
    const action = "preparar compra de creditos";
    if (!requireBusinessPinFor(action)) {
      return false;
    }
    setPreparingCreditHandoff(true);
    try {
      const data = await createBusinessCreditHandoff(request, requestedPackage);
      if (creditPackageRef.current !== requestedPackage) {
        return false;
      }
      setCreditHandoffId(data.handoff.id);
      setCreditHandoffLaunchToken(data.handoff.token);
      setCreditHandoffOpened(false);
      rememberCreditHandoffId(handoffStorageKey, data.handoff.id);
      if (!silent) {
        setNotice("Enlace listo. Toca Abrir MetaMask para continuar.");
      }
      return true;
    } catch (error) {
      if (handleBusinessPinError(error, action)) {
        return false;
      }
      const message = error instanceof ApiClientError && error.code === "RATE_LIMITED"
        ? "Demasiados intentos. Espera unos minutos y vuelve a intentar."
        : error instanceof Error
          ? error.message
          : "No pudimos preparar MetaMask desde este navegador.";
      setCreditHandoffError(message);
      if (!silent) {
        setNotice(message);
      }
      return false;
    } finally {
      setPreparingCreditHandoff(false);
    }
  }, [creditHandoffLaunchToken, creditPackage, handleBusinessPinError, handoffStorageKey, loadBackendPendingBaseUsdcPurchase, preparingCreditHandoff, request, requireBusinessPinFor, setNotice]);

  const continuePendingBaseUsdcPayment = useCallback(async () => {
    if (creditHandoffLaunchToken && pendingCreditPurchase) {
      try {
        launchMetaMaskCreditHandoff(creditHandoffLaunchToken);
        setCreditHandoffOpened(true);
        setNotice("Intentamos abrir MetaMask. Termina el pago pendiente y vuelve a Telegram.");
      } catch (error) {
        const message = error instanceof Error ? error.message : "No pudimos abrir MetaMask desde este navegador.";
        setCreditHandoffError(message);
        setNotice(message);
      }
      return;
    }
    const rememberedPurchaseId = pendingCreditPurchase?.id || readRememberedBaseUsdcPurchaseId(pendingPurchaseStorageKey);
    if (!rememberedPurchaseId && !pendingCreditPurchase) {
      setNotice("No hay un pago Base USDC pendiente.");
      return;
    }
    setCreditHandoffError(null);
    setLoadingPendingPurchase(true);
    try {
      const data = await getBusinessCreditPurchase(
        request,
        (pendingCreditPurchase?.id || rememberedPurchaseId) as string
      );
      if (!isPendingBaseUsdcPurchaseForBusiness(data.purchase, business?.id)) {
        setPendingCreditPurchase(null);
        setPendingDismissConfirmationRequested(false);
        clearRememberedBaseUsdcPurchase(pendingPurchaseStorageKey, rememberedPurchaseId);
        setNotice("Ese pago ya no esta pendiente.");
        return;
      }
      if (data.purchase.status === BASE_USDC_PAYABLE_PENDING_STATUS && !data.payment?.payer_wallet_address) {
        setCreditHandoffError("No pudimos confirmar la wallet de ese pago pendiente.");
        setNotice("No pudimos confirmar la wallet de ese pago pendiente.");
        return;
      }
      setSelectedCreditPurchase(data.purchase);
      setSelectedCreditPayment(data.payment || null);
      setPendingCreditPurchase(data.purchase);
      setCreditPackage(data.purchase.package_code);
      rememberPendingBaseUsdcPurchase(data.purchase, pendingPurchaseStorageKey);
      setPendingDismissConfirmationRequested(false);
      if (data.purchase.status !== BASE_USDC_PAYABLE_PENDING_STATUS) {
        const detail = await getBusinessCreditPurchase(request, data.purchase.id);
        setSelectedCreditPurchase(detail.purchase);
        setSelectedCreditPayment(detail.payment || null);
        setView("credit-payment-pending");
        setNotice("NODO esta revisando ese pago. Actualiza el estado en unos segundos.");
        return;
      }
      const handoff = await createBusinessCreditHandoff(request, data.purchase.package_code);
      setCreditHandoffId(handoff.handoff.id);
      setCreditHandoffLaunchToken(handoff.handoff.token);
      setCreditHandoffOpened(false);
      rememberCreditHandoffId(handoffStorageKey, handoff.handoff.id);
      setNotice("Enlace listo. Toca Continuar en MetaMask para terminar el pago pendiente.");
    } catch (error) {
      const message = error instanceof ApiClientError && error.code === "RATE_LIMITED"
        ? "Demasiados intentos. Espera unos minutos y vuelve a intentar."
        : error instanceof Error
          ? error.message
          : "No pudimos preparar el pago pendiente.";
      setCreditHandoffError(message);
      setNotice(message);
    } finally {
      setLoadingPendingPurchase(false);
    }
  }, [business?.id, creditHandoffLaunchToken, handoffStorageKey, pendingCreditPurchase, pendingPurchaseStorageKey, request, setNotice]);

  const requestPendingCreditPurchaseDismiss = useCallback(() => {
    if (!isDismissableBaseUsdcPurchase(pendingCreditPurchase, business?.id)) {
      setNotice("Este intento ya no se puede descartar desde la app. Actualiza el estado.");
      return;
    }
    setCreditHandoffError(null);
    setPendingDismissConfirmationRequested(true);
    setNotice("Confirma solo si no enviaste el pago en MetaMask.");
  }, [business?.id, pendingCreditPurchase, setNotice]);

  const resetPendingCreditPurchaseDismiss = useCallback(() => {
    setPendingDismissConfirmationRequested(false);
  }, []);

  const dismissPendingBaseUsdcPayment = useCallback(async () => {
    const purchase = pendingCreditPurchase;
    if (!purchase || !isDismissableBaseUsdcPurchase(purchase, business?.id)) {
      setNotice("Este intento ya no se puede descartar desde la app. Actualiza el estado.");
      return;
    }
    const action = "descartar intento de pago";
    if (!requireBusinessPinFor(action)) {
      return;
    }
    setDismissingPendingCreditPurchase(true);
    setCreditHandoffError(null);
    try {
      await dismissBusinessContractCreditPurchase(request, purchase.id);
      clearRememberedBaseUsdcPurchase(pendingPurchaseStorageKey, purchase.id);
      clearRememberedCreditHandoffId(handoffStorageKey);
      setPendingCreditPurchase(null);
      setSelectedCreditPurchase(null);
      setSelectedCreditPayment(null);
      setCreditHandoffId(null);
      setCreditHandoffLaunchToken(null);
      setCreditHandoffOpened(false);
      setPendingDismissConfirmationRequested(false);
      setView("buy-credits");
      setNotice("Listo. Este intento no seguira bloqueando. Si enviaste el pago, NODO todavia lo verificara.");
    } catch (error) {
      if (handleBusinessPinError(error, action)) {
        return;
      }
      const message = error instanceof Error ? error.message : "No pudimos descartar este intento.";
      setCreditHandoffError(message);
      setNotice(message);
    } finally {
      setDismissingPendingCreditPurchase(false);
    }
  }, [
    business?.id,
    handoffStorageKey,
    handleBusinessPinError,
    pendingCreditPurchase,
    pendingPurchaseStorageKey,
    request,
    requireBusinessPinFor,
    setNotice,
    setView,
  ]);

  const loadCreditDashboard = useCallback(async () => {
    setView("credits-dashboard");
    setNotice(BASE_USDC_CREDIT_NOTICE);
    setBusy(true);
    try {
      const wallet = await refreshCreditWallet();
      if (!wallet) {
        setNotice("No pudimos actualizar tus creditos. Reintenta en un momento.");
      }
    } finally {
      setBusy(false);
    }
  }, [refreshCreditWallet, setBusy, setNotice, setView]);

  const openMetaMaskCreditHandoff = useCallback(async () => {
    setCreditHandoffError(null);
    if (creditHandoffLaunchToken) {
      try {
        launchMetaMaskCreditHandoff(creditHandoffLaunchToken);
        setCreditHandoffOpened(true);
        setNotice("Intentamos abrir MetaMask. Luego vuelve a Telegram y pulsa Actualizar.");
      } catch (error) {
        const message = error instanceof Error ? error.message : "No pudimos abrir MetaMask desde este navegador.";
        setCreditHandoffError(message);
        setNotice(message);
      }
      return;
    }
    await prepareMetaMaskCreditHandoff();
  }, [creditHandoffLaunchToken, prepareMetaMaskCreditHandoff, setNotice]);

  const refreshCreditHandoff = useCallback(async () => {
    const handoffId = creditHandoffId || readRememberedCreditHandoffId(handoffStorageKey);
    if (!handoffId) {
      setNotice("No hay una preparacion de MetaMask pendiente.");
      return;
    }
    setRefreshingCreditHandoff(true);
    try {
      const data = await getBusinessCreditHandoff(request, handoffId);
      if (data.handoff.status === "prepared" && data.purchase && data.payment) {
        setSelectedCreditPurchase(data.purchase);
        setSelectedCreditPayment(data.payment);
        setPendingCreditPurchase(data.purchase);
        rememberPendingBaseUsdcPurchase(data.purchase, pendingPurchaseStorageKey);
        clearRememberedCreditHandoffId(handoffStorageKey);
        setCreditHandoffId(null);
        setCreditHandoffLaunchToken(null);
        setCreditHandoffOpened(false);
        setView("credit-payment-pending");
        setNotice("Wallet comprobada y autorizacion preparada.");
        return;
      }
      if (data.handoff.status === "expired") {
        clearRememberedCreditHandoffId(handoffStorageKey);
        setCreditHandoffId(null);
        setCreditHandoffLaunchToken(null);
        setCreditHandoffOpened(false);
        setNotice("La preparacion vencio. Abre MetaMask de nuevo.");
        return;
      }
      setCreditHandoffId(handoffId);
      setCreditHandoffLaunchToken(null);
      setCreditHandoffOpened(true);
      setNotice("La wallet aun no esta confirmada. Completa la prueba en MetaMask.");
    } catch (error) {
      if (
        error instanceof ApiClientError &&
        (error.code === "CREDIT_HANDOFF_NOT_FOUND" || error.code === "CREDIT_HANDOFF_EXPIRED")
      ) {
        clearRememberedCreditHandoffId(handoffStorageKey);
        setCreditHandoffId(null);
        setCreditHandoffLaunchToken(null);
        setCreditHandoffOpened(false);
      }
      setNotice(error instanceof Error ? error.message : "No pudimos actualizar la preparacion de wallet.");
    } finally {
      setRefreshingCreditHandoff(false);
    }
  }, [creditHandoffId, handoffStorageKey, pendingPurchaseStorageKey, request, setNotice, setView]);

  const startBaseUsdcPayment = useCallback(async () => {
    if (!creditPackage) {
      setNotice("Elige un paquete para generar el pago.");
      return;
    }
    if (walletProviderStatus !== "available") {
      setNotice("No detectamos una wallet compatible en este navegador. NODO no puede conectar tu wallet desde aqui.");
      return;
    }
    if (!connectedWalletAddress) {
      setNotice("Conecta la wallet desde donde pagarás.");
      return;
    }
    if (!walletIsExpectedNetwork) {
      setNotice("Cambia tu wallet a Base Sepolia para preparar la prueba.");
      return;
    }
    const preparedWallet = getConnectedWalletSnapshot();
    if (preparedWallet.address !== connectedWalletAddress || preparedWallet.chainId !== walletChainId) {
      setNotice("La cuenta o red cambió. Revisa tu wallet e intenta de nuevo.");
      return;
    }
    const action = "comprar creditos";
    if (!requireBusinessPinFor(action)) {
      return;
    }
    setGeneratingCreditPayment(true);
    const startedAt = actionStartedAt();
    recordBusinessActionStarted("credit_payment_create", "buy-credits");
    const idempotencyScope = `base_usdc_payment_${creditPackage}`;
    try {
      const data = await startBusinessBaseUsdcPayment(
        request,
        creditPackage,
        connectedWalletAddress,
        getIdempotencyKey(idempotencyScope, {
          creditPackage,
          connectedWalletAddress
        })
      );
      if (
        data.payment?.network !== BASE_SEPOLIA_WALLET_NETWORK.network
        || data.payment.chain_id !== BASE_SEPOLIA_WALLET_NETWORK.chainId
        || data.payment.is_testnet !== true
      ) {
        setNotice("La red de prueba no coincide con la configuracion del backend.");
        return;
      }
      clearIdempotencyKey(idempotencyScope);
      const currentWallet = getConnectedWalletSnapshot();
      if (
        currentWallet.address !== preparedWallet.address
        || currentWallet.chainId !== preparedWallet.chainId
      ) {
        setNotice("La cuenta o red cambió. Prepara la autorización de nuevo.");
        return;
      }
      setSelectedCreditPurchase(data.purchase);
      setSelectedCreditPayment(data.payment || null);
      setPendingCreditPurchase(data.purchase);
      rememberPendingBaseUsdcPurchase(data.purchase, pendingPurchaseStorageKey);
      setView("credit-payment-pending");
      setNotice("Autorizacion preparada. Revisa el estado antes de continuar.");
      recordBusinessActionCompleted("credit_payment_create", "buy-credits", startedAt);
    } catch (error) {
      if (handleBusinessPinError(error, action)) {
        recordBusinessActionFailed("credit_payment_create", "buy-credits", startedAt, "BUSINESS_PIN_REQUIRED");
        return;
      }
      setNotice(baseUsdcPaymentErrorMessage(error));
      recordBusinessActionFailed("credit_payment_create", "buy-credits", startedAt, error instanceof ApiClientError ? error.code : undefined);
    } finally {
      setGeneratingCreditPayment(false);
    }
  }, [clearIdempotencyKey, connectedWalletAddress, creditPackage, getConnectedWalletSnapshot, getIdempotencyKey, handleBusinessPinError, pendingPurchaseStorageKey, request, requireBusinessPinFor, setNotice, setView, walletChainId, walletIsExpectedNetwork, walletProviderStatus]);

  const refreshSelectedCreditPurchase = useCallback(async (options: RefreshSelectedCreditPurchaseOptions = {}) => {
    if (!selectedCreditPurchase) {
      return;
    }
    const silent = options.silent === true;
    const showManualRefreshLoading = !silent;
    if (refreshingCreditPurchaseRef.current) {
      return;
    }
    refreshingCreditPurchaseRef.current = true;
    if (showManualRefreshLoading) {
      setRefreshingCreditPurchase(true);
    }
    try {
      const data = await getBusinessCreditPurchase(request, selectedCreditPurchase.id);
      setSelectedCreditPurchase(data.purchase);
      setSelectedCreditPayment(data.payment || null);
      const purchaseIsPending = isPendingBaseUsdcPurchaseForBusiness(data.purchase, business?.id);
      setPendingCreditPurchase(purchaseIsPending ? data.purchase : null);
      if (!purchaseIsPending || !isDismissableBaseUsdcPurchase(data.purchase, business?.id)) {
        setPendingDismissConfirmationRequested(false);
      }
      rememberPendingBaseUsdcPurchase(data.purchase, pendingPurchaseStorageKey);
      if (data.purchase.status === "credited") {
        await refreshCreditWallet();
        setNotice("Pago exitoso. Tus creditos ya estan disponibles.");
        return;
      }
      if (!silent) {
        setNotice("Estado de compra actualizado.");
      }
    } catch (error) {
      if (!silent) {
        setNotice(error instanceof Error ? error.message : "No pudimos actualizar la compra.");
      }
    } finally {
      refreshingCreditPurchaseRef.current = false;
      if (showManualRefreshLoading) {
        setRefreshingCreditPurchase(false);
      }
    }
  }, [business?.id, pendingPurchaseStorageKey, refreshCreditWallet, request, selectedCreditPurchase, setNotice]);

  const loadReferrals = useCallback(async () => {
    setView("referrals");
    setBusy(true);
    try {
      const data = await getBusinessReferrals<ReferralData>(request);
      setReferralData(data);
      setNotice("Programa de referidos cargado.");
    } catch (error) {
      setReferralData(null);
      setNotice(error instanceof Error ? error.message : "No pudimos cargar referidos.");
    } finally {
      setBusy(false);
    }
  }, [request, setBusy, setNotice, setView]);

  return {
    continuePendingBaseUsdcPayment,
    connectWallet,
    connectingWallet,
    connectedWalletAddress,
    connectedWalletAddressMasked,
    canDismissPendingCreditPurchase: isDismissableBaseUsdcPurchase(pendingCreditPurchase, business?.id),
    canPrepareCreditHandoffSilently,
    creditHandoffError,
    creditPackage,
    creditHandoffId,
    creditHandoffLaunchReady: Boolean(creditHandoffLaunchToken),
    creditHandoffOpened,
    creditWallet,
    creditWalletRefreshState,
    dismissPendingBaseUsdcPayment,
    dismissingPendingCreditPurchase,
    generatingCreditPayment,
    loadingPendingPurchase,
    loadCreditDashboard,
    loadReferrals,
    openBuyCredits,
    openMetaMaskCreditHandoff,
    pendingDismissConfirmationRequested,
    prepareMetaMaskCreditHandoff,
    preparingCreditHandoff,
    referralData,
    requestPendingCreditPurchaseDismiss,
    resetPendingCreditPurchaseDismiss,
    refreshCreditWallet,
    refreshCreditHandoff,
    refreshingCreditHandoff,
    refreshingCreditPurchase,
    refreshSelectedCreditPurchase,
    pendingCreditPurchase,
    selectedCreditPayment,
    selectedCreditPurchase,
    setCreditPackage: selectCreditPackage,
    startBaseUsdcPayment,
    switchWalletToExpectedNetwork,
    switchingWalletNetwork,
    walletChainId,
    walletError,
    walletIsExpectedNetwork,
    walletProviderStatus,
  };
}
