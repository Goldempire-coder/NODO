import { useCallback, useState } from "react";
import { ApiClientError, type AuthenticatedRequest } from "../../api/client";
import {
  applyBusinessReferral,
  getBusinessCreditPurchase,
  getBusinessCreditWallet,
  getBusinessReferrals,
  startBusinessBaseUsdcPayment,
  submitBusinessBaseUsdcTxHash
} from "../../api/credits";
import type { BusinessMiniAppView } from "../../constants/businessViews";
import type { BusinessSummary } from "../../types/business";
import type { CreditPurchase, CreditWallet, ReferralData } from "../../types/credits";
import { actionStartedAt, recordBusinessActionCompleted, recordBusinessActionFailed, recordBusinessActionStarted } from "../actionTelemetry";
import { useStableIdempotencyKeys } from "../useStableIdempotencyKeys";
import { handleBusinessPinError as routeBusinessPinError, requireUnlockedBusinessPin } from "./businessPinGuards";

const BASE_USDC_CREDIT_NOTICE = "Asegurate de usar la red Base para comprar tus creditos.";
const BASE_USDC_PENDING_PURCHASE_LEGACY_KEY = "nodo_base_usdc_pending_purchase_id";
const BASE_USDC_PENDING_PURCHASE_KEY_PREFIX = "nodo_base_usdc_pending_purchase_id";
const BASE_USDC_WALLET_MISSING_MESSAGE = "Compra de creditos no disponible todavia. Falta configurar la wallet Base de NODO.";
const BASE_USDC_PENDING_STATUSES = new Set(["pending_payment", "pending_onchain_confirmation", "detected", "under_review"]);

function baseUsdcPaymentErrorMessage(error: unknown) {
  if (error instanceof ApiClientError) {
    if (error.code === "ONCHAIN_RECEIVING_WALLET_NOT_CONFIGURED" || error.code === "VALIDATION_ERROR") {
      return BASE_USDC_WALLET_MISSING_MESSAGE;
    }
    return error.message;
  }
  return "No logramos iniciar el pago en red Base.";
}

function pendingBaseUsdcPurchaseStorageKey(businessId: string | null | undefined) {
  return businessId ? `${BASE_USDC_PENDING_PURCHASE_KEY_PREFIX}:${businessId}` : null;
}

function isPendingBaseUsdcPurchaseForBusiness(purchase: CreditPurchase, businessId: string | null | undefined) {
  return Boolean(businessId && purchase.business_id === businessId && BASE_USDC_PENDING_STATUSES.has(purchase.status));
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
  if (BASE_USDC_PENDING_STATUSES.has(purchase.status)) {
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
  const [selectedCreditPurchase, setSelectedCreditPurchase] = useState<CreditPurchase | null>(null);
  const [pendingCreditPurchase, setPendingCreditPurchase] = useState<CreditPurchase | null>(null);
  const [creditPackage, setCreditPackage] = useState<string | null>(null);
  const [baseUsdcTxHash, setBaseUsdcTxHash] = useState("");
  const [referralData, setReferralData] = useState<ReferralData | null>(null);
  const [referralCodeInput, setReferralCodeInput] = useState("");
  const [generatingCreditPayment, setGeneratingCreditPayment] = useState(false);
  const [loadingPendingPurchase, setLoadingPendingPurchase] = useState(false);
  const [refreshingCreditPurchase, setRefreshingCreditPurchase] = useState(false);
  const [verifyingCreditTx, setVerifyingCreditTx] = useState(false);
  const { clearIdempotencyKey, getIdempotencyKey } = useStableIdempotencyKeys();
  const pendingPurchaseStorageKey = pendingBaseUsdcPurchaseStorageKey(business?.id);

  const requireBusinessPinFor = useCallback((action: string) => {
    return requireUnlockedBusinessPin({ action, business, setNotice, setView });
  }, [business?.access_link, setNotice, setView]);

  const handleBusinessPinError = useCallback((error: unknown, action: string) => {
    return routeBusinessPinError({ action, error, setNotice, setView });
  }, [setNotice, setView]);

  const refreshCreditWallet = useCallback(async () => {
    try {
      const data = await getBusinessCreditWallet<{ wallet: CreditWallet; disclaimer?: string }>(request);
      setCreditWallet(data.wallet);
      return data.wallet;
    } catch {
      setCreditWallet(null);
      return null;
    }
  }, [request]);

  const openBuyCredits = useCallback(async () => {
    setNotice(BASE_USDC_CREDIT_NOTICE);
    setView("buy-credits");
    setPendingCreditPurchase(null);
    const rememberedPurchaseId = readRememberedBaseUsdcPurchaseId(pendingPurchaseStorageKey);
    if (rememberedPurchaseId) {
      setLoadingPendingPurchase(true);
      try {
        const data = await getBusinessCreditPurchase<{ purchase: CreditPurchase }>(request, rememberedPurchaseId);
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
    setLoadingPendingPurchase(true);
    try {
      const data = await getBusinessCreditPurchase<{ purchase: CreditPurchase }>(request, rememberedPurchaseId);
      if (!isPendingBaseUsdcPurchaseForBusiness(data.purchase, business?.id)) {
        setPendingCreditPurchase(null);
        clearRememberedBaseUsdcPurchase(pendingPurchaseStorageKey, rememberedPurchaseId);
        setNotice("Ese pago ya no esta pendiente.");
        return;
      }
      setSelectedCreditPurchase(data.purchase);
      setPendingCreditPurchase(data.purchase);
      rememberPendingBaseUsdcPurchase(data.purchase, pendingPurchaseStorageKey);
      setView("credit-payment-pending");
      setNotice("Continua el pago Base USDC pendiente.");
    } catch (error) {
      setPendingCreditPurchase(null);
      clearRememberedBaseUsdcPurchase(pendingPurchaseStorageKey, rememberedPurchaseId);
      setNotice(error instanceof Error ? error.message : "No pudimos abrir el pago pendiente.");
    } finally {
      setLoadingPendingPurchase(false);
    }
  }, [business?.id, pendingCreditPurchase, pendingPurchaseStorageKey, request, setNotice, setView]);

  const loadCreditDashboard = useCallback(async () => {
    setView("credits-dashboard");
    setNotice(BASE_USDC_CREDIT_NOTICE);
    setBusy(true);
    try {
      const data = await getBusinessCreditWallet<{ wallet: CreditWallet; disclaimer?: string }>(request);
      setCreditWallet(data.wallet);
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "No logramos cargar tus creditos.");
    } finally {
      setBusy(false);
    }
  }, [request, setBusy, setNotice, setView]);

  const startBaseUsdcPayment = useCallback(async () => {
    if (!creditPackage) {
      setNotice("Elige un paquete para generar el pago.");
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
      const data = await startBusinessBaseUsdcPayment<{
        purchase: CreditPurchase;
        payment: { expected_amount_display?: string; network?: string; expires_at?: string | null };
        disclaimer?: string;
      }>(request, creditPackage, getIdempotencyKey(idempotencyScope, { creditPackage }));
      clearIdempotencyKey(idempotencyScope);
      setSelectedCreditPurchase(data.purchase);
      setPendingCreditPurchase(data.purchase);
      setBaseUsdcTxHash("");
      rememberPendingBaseUsdcPurchase(data.purchase, pendingPurchaseStorageKey);
      setView("credit-payment-pending");
      setNotice(`Pago creado: envia ${data.payment.expected_amount_display || data.purchase.price_usd} USDC en red Base y luego pega el tx hash.`);
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
  }, [clearIdempotencyKey, creditPackage, getIdempotencyKey, handleBusinessPinError, pendingPurchaseStorageKey, request, requireBusinessPinFor, setNotice, setView]);

  const refreshSelectedCreditPurchase = useCallback(async () => {
    if (!selectedCreditPurchase) {
      return;
    }
    setRefreshingCreditPurchase(true);
    try {
      const data = await getBusinessCreditPurchase<{ purchase: CreditPurchase }>(request, selectedCreditPurchase.id);
      setSelectedCreditPurchase(data.purchase);
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

  const submitBaseUsdcTxHash = useCallback(async () => {
    if (!selectedCreditPurchase || !baseUsdcTxHash.trim()) {
      setNotice("Registra el tx hash de Base USDC.");
      return;
    }
    const action = "verificar tx hash";
    if (!requireBusinessPinFor(action)) {
      return;
    }
    setVerifyingCreditTx(true);
    const startedAt = actionStartedAt();
    recordBusinessActionStarted("credit_tx_submit", "credit-payment-pending");
    const idempotencyScope = `base_usdc_tx_${selectedCreditPurchase.id}`;
    try {
      const data = await submitBusinessBaseUsdcTxHash<{ purchase: CreditPurchase; credited: boolean }>(
        request,
        selectedCreditPurchase.id,
        baseUsdcTxHash.trim(),
        getIdempotencyKey(idempotencyScope, { purchaseId: selectedCreditPurchase.id, txHash: baseUsdcTxHash.trim() })
      );
      clearIdempotencyKey(idempotencyScope);
      setSelectedCreditPurchase(data.purchase);
      setPendingCreditPurchase(BASE_USDC_PENDING_STATUSES.has(data.purchase.status) ? data.purchase : null);
      rememberPendingBaseUsdcPurchase(data.purchase, pendingPurchaseStorageKey);
      if (data.credited) {
        await refreshCreditWallet();
      }
      setNotice(data.credited ? "Pago verificado. Creditos acreditados." : "Tx hash recibido. NODO seguira verificando confirmaciones en Base.");
      recordBusinessActionCompleted("credit_tx_submit", "credit-payment-pending", startedAt);
    } catch (error) {
      if (handleBusinessPinError(error, action)) {
        recordBusinessActionFailed("credit_tx_submit", "credit-payment-pending", startedAt, "BUSINESS_PIN_REQUIRED");
        return;
      }
      setNotice(error instanceof Error ? error.message : "No pudimos verificar el tx hash.");
      recordBusinessActionFailed("credit_tx_submit", "credit-payment-pending", startedAt, error instanceof ApiClientError ? error.code : undefined);
    } finally {
      setVerifyingCreditTx(false);
    }
  }, [baseUsdcTxHash, clearIdempotencyKey, getIdempotencyKey, handleBusinessPinError, pendingPurchaseStorageKey, refreshCreditWallet, request, requireBusinessPinFor, selectedCreditPurchase, setNotice]);

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

  const applyReferral = useCallback(async () => {
    setBusy(true);
    const idempotencyScope = `apply_referral_${referralCodeInput.trim()}`;
    try {
      await applyBusinessReferral(request, referralCodeInput, getIdempotencyKey(idempotencyScope, { referralCodeInput: referralCodeInput.trim() }));
      clearIdempotencyKey(idempotencyScope);
      await loadReferrals();
      setNotice("Codigo referido registrado. El bono se evalua con la primera compra aprobada.");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "No pudimos aplicar el codigo.");
    } finally {
      setBusy(false);
    }
  }, [clearIdempotencyKey, getIdempotencyKey, loadReferrals, referralCodeInput, request, setBusy, setNotice]);

  return {
    applyReferral,
    baseUsdcTxHash,
    continuePendingBaseUsdcPayment,
    creditPackage,
    creditWallet,
    generatingCreditPayment,
    loadingPendingPurchase,
    loadCreditDashboard,
    loadReferrals,
    openBuyCredits,
    referralCodeInput,
    referralData,
    refreshCreditWallet,
    refreshingCreditPurchase,
    refreshSelectedCreditPurchase,
    pendingCreditPurchase,
    selectedCreditPurchase,
    setBaseUsdcTxHash,
    setCreditPackage,
    setReferralCodeInput,
    startBaseUsdcPayment,
    submitBaseUsdcTxHash,
    verifyingCreditTx,
  };
}
