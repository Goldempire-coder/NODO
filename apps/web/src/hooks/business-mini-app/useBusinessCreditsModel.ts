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
import { actionStartedAt, recordBusinessActionCompleted, recordBusinessActionFailed, recordBusinessActionStarted } from "./actionTelemetry";
import { handleBusinessPinError as routeBusinessPinError, requireUnlockedBusinessPin } from "./businessPinGuards";
import { idempotencyKey } from "./helpers";

const BASE_USDC_CREDIT_NOTICE = "Asegurate de usar la red Base para comprar tus creditos.";
const BASE_USDC_PENDING_PURCHASE_KEY = "nodo_base_usdc_pending_purchase_id";
const BASE_USDC_WALLET_MISSING_MESSAGE = "Compra de creditos no disponible todavia. Falta configurar la wallet Base de NODO.";
const BASE_USDC_PENDING_STATUSES = new Set(["pending_payment", "pending_onchain_confirmation", "detected", "verified", "under_review"]);

function baseUsdcPaymentErrorMessage(error: unknown) {
  if (error instanceof ApiClientError) {
    if (error.code === "ONCHAIN_RECEIVING_WALLET_NOT_CONFIGURED" || error.code === "VALIDATION_ERROR") {
      return BASE_USDC_WALLET_MISSING_MESSAGE;
    }
    return error.message;
  }
  return "No logramos iniciar el pago en red Base.";
}

function rememberPendingBaseUsdcPurchase(purchase: CreditPurchase) {
  if (typeof window === "undefined") {
    return;
  }
  if (BASE_USDC_PENDING_STATUSES.has(purchase.status)) {
    window.localStorage.setItem(BASE_USDC_PENDING_PURCHASE_KEY, purchase.id);
    return;
  }
  window.localStorage.removeItem(BASE_USDC_PENDING_PURCHASE_KEY);
}

function readRememberedBaseUsdcPurchaseId() {
  if (typeof window === "undefined") {
    return null;
  }
  return window.localStorage.getItem(BASE_USDC_PENDING_PURCHASE_KEY);
}

function clearRememberedBaseUsdcPurchase() {
  if (typeof window === "undefined") {
    return;
  }
  window.localStorage.removeItem(BASE_USDC_PENDING_PURCHASE_KEY);
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
  const [creditPackage, setCreditPackage] = useState("starter");
  const [baseUsdcTxHash, setBaseUsdcTxHash] = useState("");
  const [referralData, setReferralData] = useState<ReferralData | null>(null);
  const [referralCodeInput, setReferralCodeInput] = useState("");
  const [generatingCreditPayment, setGeneratingCreditPayment] = useState(false);
  const [refreshingCreditPurchase, setRefreshingCreditPurchase] = useState(false);
  const [verifyingCreditTx, setVerifyingCreditTx] = useState(false);

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
    const rememberedPurchaseId = readRememberedBaseUsdcPurchaseId();
    if (rememberedPurchaseId) {
      setBusy(true);
      try {
        const data = await getBusinessCreditPurchase<{ purchase: CreditPurchase }>(request, rememberedPurchaseId);
        if (BASE_USDC_PENDING_STATUSES.has(data.purchase.status)) {
          setSelectedCreditPurchase(data.purchase);
          setView("credit-payment-pending");
          setNotice("Tienes una compra Base USDC pendiente.");
          return;
        }
        clearRememberedBaseUsdcPurchase();
      } catch {
        clearRememberedBaseUsdcPurchase();
      } finally {
        setBusy(false);
      }
    }
  }, [request, setBusy, setNotice, setView]);

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
    const action = "comprar creditos";
    if (!requireBusinessPinFor(action)) {
      return;
    }
    setGeneratingCreditPayment(true);
    const startedAt = actionStartedAt();
    recordBusinessActionStarted("credit_payment_create", "buy-credits");
    try {
      const data = await startBusinessBaseUsdcPayment<{
        purchase: CreditPurchase;
        payment: { expected_amount_display?: string; network?: string; expires_at?: string | null };
        disclaimer?: string;
      }>(request, creditPackage, idempotencyKey("base_usdc_payment"));
      setSelectedCreditPurchase(data.purchase);
      setBaseUsdcTxHash("");
      rememberPendingBaseUsdcPurchase(data.purchase);
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
  }, [creditPackage, handleBusinessPinError, request, requireBusinessPinFor, setNotice, setView]);

  const refreshSelectedCreditPurchase = useCallback(async () => {
    if (!selectedCreditPurchase) {
      return;
    }
    setRefreshingCreditPurchase(true);
    try {
      const data = await getBusinessCreditPurchase<{ purchase: CreditPurchase }>(request, selectedCreditPurchase.id);
      setSelectedCreditPurchase(data.purchase);
      rememberPendingBaseUsdcPurchase(data.purchase);
      setNotice("Estado de compra actualizado.");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "No pudimos actualizar la compra.");
    } finally {
      setRefreshingCreditPurchase(false);
    }
  }, [request, selectedCreditPurchase, setNotice]);

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
    try {
      const data = await submitBusinessBaseUsdcTxHash<{ purchase: CreditPurchase; credited: boolean }>(
        request,
        selectedCreditPurchase.id,
        baseUsdcTxHash.trim(),
        idempotencyKey("base_usdc_tx")
      );
      setSelectedCreditPurchase(data.purchase);
      rememberPendingBaseUsdcPurchase(data.purchase);
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
  }, [baseUsdcTxHash, handleBusinessPinError, refreshCreditWallet, request, requireBusinessPinFor, selectedCreditPurchase, setNotice]);

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
    try {
      await applyBusinessReferral(request, referralCodeInput, idempotencyKey("apply_referral"));
      await loadReferrals();
      setNotice("Codigo referido registrado. El bono se evalua con la primera compra aprobada.");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "No pudimos aplicar el codigo.");
    } finally {
      setBusy(false);
    }
  }, [loadReferrals, referralCodeInput, request, setBusy, setNotice]);

  return {
    applyReferral,
    baseUsdcTxHash,
    creditPackage,
    creditWallet,
    generatingCreditPayment,
    loadCreditDashboard,
    loadReferrals,
    openBuyCredits,
    referralCodeInput,
    referralData,
    refreshCreditWallet,
    refreshingCreditPurchase,
    refreshSelectedCreditPurchase,
    selectedCreditPurchase,
    setBaseUsdcTxHash,
    setCreditPackage,
    setReferralCodeInput,
    startBaseUsdcPayment,
    submitBaseUsdcTxHash,
    verifyingCreditTx,
  };
}
