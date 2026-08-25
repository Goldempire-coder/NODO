import { useCallback, useState } from "react";
import { ApiClientError, type AuthenticatedRequest } from "../../api/client";
import {
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
import { openMetaMaskWalletProbe as launchMetaMaskWalletProbe } from "../../lib/wallet/metamaskHandoff";
import { useInjectedWallet } from "./useInjectedWallet";
import { handleBusinessPinError as routeBusinessPinError, requireUnlockedBusinessPin } from "./businessPinGuards";

const BASE_USDC_CREDIT_NOTICE = "NODO prepara compras de creditos en USDC sobre red Base.";
const BASE_USDC_PENDING_PURCHASE_LEGACY_KEY = "nodo_base_usdc_pending_purchase_id";
const BASE_USDC_PENDING_PURCHASE_KEY_PREFIX = "nodo_base_usdc_pending_purchase_id";
const BASE_USDC_PAYMENT_UNAVAILABLE_MESSAGE = "La compra de creditos no esta disponible en este momento.";
const BASE_USDC_PENDING_STATUSES = new Set(["pending_payment", "pending_onchain_confirmation", "detected", "under_review"]);

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
    return error.message;
  }
  return "No logramos iniciar el pago en red Base.";
}

function pendingBaseUsdcPurchaseStorageKey(businessId: string | null | undefined) {
  return businessId ? `${BASE_USDC_PENDING_PURCHASE_KEY_PREFIX}:${businessId}` : null;
}

function isPendingBaseUsdcPurchaseForBusiness(purchase: CreditPurchase, businessId: string | null | undefined) {
  return Boolean(
    businessId &&
    purchase.business_id === businessId &&
    purchase.payment_method === "base_usdc_contract" &&
    BASE_USDC_PENDING_STATUSES.has(purchase.status)
  );
}

function rememberPendingBaseUsdcPurchase(purchase: CreditPurchase, storageKey: string | null) {
  if (typeof window === "undefined") {
    return;
  }
  const legacyPurchaseId = window.localStorage.getItem(BASE_USDC_PENDING_PURCHASE_LEGACY_KEY);
  if (legacyPurchaseId === purchase.id) {
    window.localStorage.removeItem(BASE_USDC_PENDING_PURCHASE_LEGACY_KEY);
  }
  if (!storageKey) {
    return;
  }
  if (purchase.payment_method === "base_usdc_contract" && BASE_USDC_PENDING_STATUSES.has(purchase.status)) {
    window.localStorage.setItem(storageKey, purchase.id);
    return;
  }
  const rememberedPurchaseId = window.localStorage.getItem(storageKey);
  if (rememberedPurchaseId === purchase.id) {
    window.localStorage.removeItem(storageKey);
  }
}

function readRememberedBaseUsdcPurchaseId(storageKey: string | null) {
  if (typeof window === "undefined") {
    return null;
  }
  return (storageKey ? window.localStorage.getItem(storageKey) : null) || window.localStorage.getItem(BASE_USDC_PENDING_PURCHASE_LEGACY_KEY);
}

function clearRememberedBaseUsdcPurchase(storageKey: string | null, purchaseId?: string | null) {
  if (typeof window === "undefined") {
    return;
  }
  const legacyPurchaseId = window.localStorage.getItem(BASE_USDC_PENDING_PURCHASE_LEGACY_KEY);
  if (!purchaseId || legacyPurchaseId === purchaseId) {
    window.localStorage.removeItem(BASE_USDC_PENDING_PURCHASE_LEGACY_KEY);
  }
  if (!storageKey) {
    return;
  }
  const scopedPurchaseId = window.localStorage.getItem(storageKey);
  if (!purchaseId || scopedPurchaseId === purchaseId) {
    window.localStorage.removeItem(storageKey);
  }
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
  const [refreshingCreditPurchase, setRefreshingCreditPurchase] = useState(false);
  const { clearIdempotencyKey, getIdempotencyKey } = useStableIdempotencyKeys();
  const pendingPurchaseStorageKey = pendingBaseUsdcPurchaseStorageKey(business?.id);

  const invalidatePreparedCreditPayment = useCallback(() => {
    const hadPreparedPayment = Boolean(selectedCreditPurchase || selectedCreditPayment || pendingCreditPurchase);
    setSelectedCreditPurchase(null);
    setSelectedCreditPayment(null);
    setPendingCreditPurchase(null);
    clearRememberedBaseUsdcPurchase(pendingPurchaseStorageKey);
    if (hadPreparedPayment) {
      setView("buy-credits");
      setNotice("La cuenta o red cambió. Prepara la autorización de nuevo.");
    }
  }, [pendingCreditPurchase, pendingPurchaseStorageKey, selectedCreditPayment, selectedCreditPurchase, setNotice, setView]);

  const {
    connectWallet,
    connectingWallet,
    connectedWalletAddress,
    connectedWalletAddressMasked,
    getConnectedWalletSnapshot,
    switchWalletToBase,
    switchingWalletNetwork,
    walletChainId,
    walletError,
    walletIsBase,
    walletProviderStatus,
  } = useInjectedWallet(invalidatePreparedCreditPayment);

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

  const openBuyCredits = useCallback(async () => {
    setNotice(BASE_USDC_CREDIT_NOTICE);
    setView("buy-credits");
    setSelectedCreditPurchase(null);
    setSelectedCreditPayment(null);
    setPendingCreditPurchase(null);
    const rememberedPurchaseId = readRememberedBaseUsdcPurchaseId(pendingPurchaseStorageKey);
    if (rememberedPurchaseId) {
      setLoadingPendingPurchase(true);
      try {
        const data = await getBusinessCreditPurchase(request, rememberedPurchaseId);
        if (isPendingBaseUsdcPurchaseForBusiness(data.purchase, business?.id)) {
          setPendingCreditPurchase(data.purchase);
          setNotice("Tienes un pago Base USDC pendiente. Puedes continuarlo cuando quieras.");
          return;
        }
        setPendingCreditPurchase(null);
        clearRememberedBaseUsdcPurchase(pendingPurchaseStorageKey, rememberedPurchaseId);
      } catch {
        setPendingCreditPurchase(null);
        clearRememberedBaseUsdcPurchase(pendingPurchaseStorageKey, rememberedPurchaseId);
      } finally {
        setLoadingPendingPurchase(false);
      }
    }
  }, [business?.id, pendingPurchaseStorageKey, request, setNotice, setView]);

  const continuePendingBaseUsdcPayment = useCallback(async () => {
    const rememberedPurchaseId = pendingCreditPurchase?.id || readRememberedBaseUsdcPurchaseId(pendingPurchaseStorageKey);
    if (!rememberedPurchaseId) {
      setNotice("No hay un pago Base USDC pendiente.");
      return;
    }
    if (walletProviderStatus !== "available") {
      setNotice("No detectamos una wallet compatible en este navegador. NODO no puede conectar tu wallet desde aqui.");
      return;
    }
    if (!connectedWalletAddress) {
      setNotice("Conecta la wallet desde donde pagaras.");
      return;
    }
    if (!walletIsBase) {
      setNotice("Cambia tu wallet a Base para continuar el pago.");
      return;
    }
    const preparedWallet = getConnectedWalletSnapshot();
    if (preparedWallet.address !== connectedWalletAddress || preparedWallet.chainId !== walletChainId) {
      setNotice("La cuenta o red cambio. Revisa tu wallet e intenta de nuevo.");
      return;
    }
    setLoadingPendingPurchase(true);
    try {
      const data = await getBusinessCreditPurchase(request, rememberedPurchaseId);
      if (!isPendingBaseUsdcPurchaseForBusiness(data.purchase, business?.id)) {
        setPendingCreditPurchase(null);
        clearRememberedBaseUsdcPurchase(pendingPurchaseStorageKey, rememberedPurchaseId);
        setNotice("Ese pago ya no esta pendiente.");
        return;
      }
      const currentWallet = getConnectedWalletSnapshot();
      if (
        currentWallet.address !== preparedWallet.address ||
        currentWallet.chainId !== preparedWallet.chainId
      ) {
        setPendingCreditPurchase(null);
        clearRememberedBaseUsdcPurchase(pendingPurchaseStorageKey, rememberedPurchaseId);
        setNotice("La cuenta o red cambio. Prepara la autorizacion de nuevo.");
        return;
      }
      const paymentWallet = data.payment?.payer_wallet_address?.toLowerCase() || null;
      if (!paymentWallet || paymentWallet !== preparedWallet.address) {
        setPendingCreditPurchase(null);
        clearRememberedBaseUsdcPurchase(pendingPurchaseStorageKey, rememberedPurchaseId);
        setNotice("Ese pago pendiente pertenece a otra wallet. Prepara una nueva autorizacion.");
        return;
      }
      setSelectedCreditPurchase(data.purchase);
      setSelectedCreditPayment(data.payment || null);
      setPendingCreditPurchase(data.purchase);
      rememberPendingBaseUsdcPurchase(data.purchase, pendingPurchaseStorageKey);
      setView("credit-payment-pending");
      setNotice("Revisa la autorizacion Base USDC pendiente.");
    } catch (error) {
      setPendingCreditPurchase(null);
      clearRememberedBaseUsdcPurchase(pendingPurchaseStorageKey, rememberedPurchaseId);
      setNotice(error instanceof Error ? error.message : "No pudimos abrir el pago pendiente.");
    } finally {
      setLoadingPendingPurchase(false);
    }
  }, [business?.id, connectedWalletAddress, getConnectedWalletSnapshot, pendingCreditPurchase, pendingPurchaseStorageKey, request, setNotice, setView, walletChainId, walletIsBase, walletProviderStatus]);

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

  const openMetaMaskWalletProbe = useCallback(() => {
    try {
      launchMetaMaskWalletProbe();
    } catch {
      setNotice("No pudimos abrir MetaMask desde este navegador.");
    }
  }, [setNotice]);

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
    if (!walletIsBase) {
      setNotice("Cambia tu wallet a Base para preparar el pago.");
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
      clearIdempotencyKey(idempotencyScope);
      const currentWallet = getConnectedWalletSnapshot();
      if (
        currentWallet.address !== preparedWallet.address ||
        currentWallet.chainId !== preparedWallet.chainId
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
  }, [clearIdempotencyKey, connectedWalletAddress, creditPackage, getConnectedWalletSnapshot, getIdempotencyKey, handleBusinessPinError, pendingPurchaseStorageKey, request, requireBusinessPinFor, setNotice, setView, walletChainId, walletIsBase, walletProviderStatus]);

  const refreshSelectedCreditPurchase = useCallback(async () => {
    if (!selectedCreditPurchase) {
      return;
    }
    setRefreshingCreditPurchase(true);
    try {
      const data = await getBusinessCreditPurchase(request, selectedCreditPurchase.id);
      setSelectedCreditPurchase(data.purchase);
      setSelectedCreditPayment(data.payment || null);
      setPendingCreditPurchase(BASE_USDC_PENDING_STATUSES.has(data.purchase.status) ? data.purchase : null);
      rememberPendingBaseUsdcPurchase(data.purchase, pendingPurchaseStorageKey);
      if (data.purchase.status === "credited") {
        await refreshCreditWallet();
      }
      setNotice("Estado de compra actualizado.");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "No pudimos actualizar la compra.");
    } finally {
      setRefreshingCreditPurchase(false);
    }
  }, [pendingPurchaseStorageKey, refreshCreditWallet, request, selectedCreditPurchase, setNotice]);

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
    creditPackage,
    creditWallet,
    creditWalletRefreshState,
    generatingCreditPayment,
    loadingPendingPurchase,
    loadCreditDashboard,
    loadReferrals,
    openBuyCredits,
    openMetaMaskWalletProbe,
    referralData,
    refreshCreditWallet,
    refreshingCreditPurchase,
    refreshSelectedCreditPurchase,
    pendingCreditPurchase,
    selectedCreditPayment,
    selectedCreditPurchase,
    setCreditPackage,
    startBaseUsdcPayment,
    switchWalletToBase,
    switchingWalletNetwork,
    walletChainId,
    walletError,
    walletIsBase,
    walletProviderStatus,
  };
}
