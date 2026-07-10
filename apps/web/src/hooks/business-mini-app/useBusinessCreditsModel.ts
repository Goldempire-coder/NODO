import { useCallback, useState } from "react";
import type { AuthenticatedRequest } from "../../api/client";
import {
  applyBusinessReferral,
  getBusinessCreditWallet,
  getBusinessReferrals,
  listBusinessCreditLedger,
  startBusinessStripeCheckout,
  submitBusinessManualCreditPayment
} from "../../api/credits";
import type { BusinessMiniAppView } from "../../constants/businessViews";
import type { CreditLedgerEntry, CreditPurchase, CreditWallet, ReferralData } from "../../types/credits";
import { idempotencyKey } from "./helpers";

export function useBusinessCreditsModel({
  request,
  setBusy,
  setNotice,
  setView
}: {
  request: AuthenticatedRequest;
  setBusy: (busy: boolean) => void;
  setNotice: (notice: string) => void;
  setView: (view: BusinessMiniAppView) => void;
}) {
  const [creditWallet, setCreditWallet] = useState<CreditWallet | null>(null);
  const [creditLedger, setCreditLedger] = useState<CreditLedgerEntry[]>([]);
  const [selectedCreditPurchase, setSelectedCreditPurchase] = useState<CreditPurchase | null>(null);
  const [creditPackage, setCreditPackage] = useState("starter");
  const [manualPaymentMethod, setManualPaymentMethod] = useState<"zelle_manual_admin_approved" | "usdt_manual_admin_approved">("zelle_manual_admin_approved");
  const [manualPaymentReference, setManualPaymentReference] = useState("");
  const [manualTxHash, setManualTxHash] = useState("");
  const [referralData, setReferralData] = useState<ReferralData | null>(null);
  const [referralCodeInput, setReferralCodeInput] = useState("");

  const loadCreditDashboard = useCallback(async () => {
    setBusy(true);
    try {
      const data = await getBusinessCreditWallet<{ wallet: CreditWallet; disclaimer?: string }>(request);
      setCreditWallet(data.wallet);
      setView("credits-dashboard");
      setNotice(data.disclaimer || "Creditos para publicar y operar anuncios.");
    } catch (error) {
      setView("credits-dashboard");
      setNotice(error instanceof Error ? error.message : "No logramos cargar tus creditos.");
    } finally {
      setBusy(false);
    }
  }, [request, setBusy, setNotice, setView]);

  const loadCreditLedger = useCallback(async () => {
    setBusy(true);
    try {
      const data = await listBusinessCreditLedger<{ items: CreditLedgerEntry[]; disclaimer?: string }>(request);
      setCreditLedger(data.items);
      setView("credits-ledger");
      setNotice(data.disclaimer || "Movimientos de creditos cargados.");
    } catch (error) {
      setCreditLedger([]);
      setView("credits-ledger");
      setNotice(error instanceof Error ? error.message : "No pudimos cargar tus movimientos.");
    } finally {
      setBusy(false);
    }
  }, [request, setBusy, setNotice, setView]);

  const startStripeCheckout = useCallback(async () => {
    setBusy(true);
    try {
      const data = await startBusinessStripeCheckout<{ purchase: CreditPurchase; disclaimer?: string }>(request, creditPackage, idempotencyKey("stripe_checkout"));
      setSelectedCreditPurchase(data.purchase);
      setView("credit-payment-pending");
      setNotice(data.disclaimer || "Pago con tarjeta iniciado. Completa el proceso en la ventana segura.");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "No logramos iniciar el pago.");
    } finally {
      setBusy(false);
    }
  }, [creditPackage, request, setBusy, setNotice, setView]);

  const submitManualCreditPayment = useCallback(async (file: File | null) => {
    if (!file) {
      setNotice("Selecciona el comprobante privado.");
      return;
    }
    setBusy(true);
    try {
      const data = await submitBusinessManualCreditPayment<{ purchase: CreditPurchase; disclaimer?: string }>(
        request,
        {
          packageCode: creditPackage,
          paymentMethod: manualPaymentMethod,
          manualPaymentReference,
          manualTxHash,
          file
        },
        idempotencyKey("manual_credit")
      );
      setSelectedCreditPurchase(data.purchase);
      setView("credit-payment-pending");
      setNotice(data.disclaimer || "Comprobante enviado a revision.");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "No pudimos enviar el comprobante.");
    } finally {
      setBusy(false);
    }
  }, [creditPackage, manualPaymentMethod, manualPaymentReference, manualTxHash, request, setBusy, setNotice, setView]);

  const loadReferrals = useCallback(async () => {
    setBusy(true);
    try {
      const data = await getBusinessReferrals<ReferralData>(request);
      setReferralData(data);
      setView("referrals");
      setNotice(data.disclaimer || "Programa de referidos cargado.");
    } catch (error) {
      setReferralData(null);
      setView("referrals");
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
    creditLedger,
    creditPackage,
    creditWallet,
    loadCreditDashboard,
    loadCreditLedger,
    loadReferrals,
    manualPaymentMethod,
    manualPaymentReference,
    manualTxHash,
    referralCodeInput,
    referralData,
    selectedCreditPurchase,
    setCreditPackage,
    setManualPaymentMethod,
    setManualPaymentReference,
    setManualTxHash,
    setReferralCodeInput,
    startStripeCheckout,
    submitManualCreditPayment
  };
}
