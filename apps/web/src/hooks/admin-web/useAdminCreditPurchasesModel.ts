import { useCallback, useState } from "react";
import { listAdminCreditPurchases, reviewAdminCreditPurchase } from "../../api/admin";
import type { AuthenticatedRequest } from "../../api/client";
import type { CreditPurchase } from "../../types/credits";
import { idempotencyKey } from "./helpers";
import type { CreditsView, ListResponse, QueueCriticalAction } from "./adminCreditsTypes";

export function useAdminCreditPurchasesModel({
  adminMutable,
  queueCriticalAction,
  reason,
  request,
  setBusy,
  setNotice,
  setReason,
  setView
}: {
  adminMutable: boolean;
  queueCriticalAction: QueueCriticalAction;
  reason: string;
  request: AuthenticatedRequest;
  setBusy: (busy: boolean) => void;
  setNotice: (notice: string) => void;
  setReason: (reason: string) => void;
  setView: (view: CreditsView) => void;
}) {
  const [creditPurchases, setCreditPurchases] = useState<CreditPurchase[]>([]);
  const [selectedCreditPurchase, setSelectedCreditPurchase] = useState<CreditPurchase | null>(null);
  const [creditFilter, setCreditFilter] = useState("pending_manual_review");

  const loadCreditPurchases = useCallback(async (status = creditFilter) => {
    setBusy(true);
    try {
      const data = await listAdminCreditPurchases<ListResponse<CreditPurchase>>(request, status);
      setCreditPurchases(data.items);
      setCreditFilter(status);
      setView("credit-purchases");
      setNotice(data.items.length ? "Compras de creditos cargadas." : "No hay compras para ese filtro.");
    } catch (error) {
      setCreditPurchases([]);
      setNotice(error instanceof Error ? error.message : "No se pudo cargar compras de creditos.");
    } finally {
      setBusy(false);
    }
  }, [creditFilter, request, setBusy, setNotice, setView]);

  const reviewCreditPurchase = useCallback((action: "approve" | "reject") => {
    if (!selectedCreditPurchase || !adminMutable) {
      setNotice("Accion no permitida para este rol.");
      return;
    }
    queueCriticalAction(action === "approve" ? "Aprobar pago manual" : "Rechazar pago manual", "La revision mantiene ownership de slice 08.", async () => {
      const data = await reviewAdminCreditPurchase<{ purchase: CreditPurchase }>(
        request,
        selectedCreditPurchase.id,
        action,
        reason,
        idempotencyKey(`credit_${action}`)
      );
      setSelectedCreditPurchase(data.purchase);
      setReason("");
      setNotice(action === "approve" ? "Pago aprobado y acreditado por backend." : "Pago rechazado sin acreditar.");
      await loadCreditPurchases();
    });
  }, [adminMutable, loadCreditPurchases, queueCriticalAction, reason, request, selectedCreditPurchase, setNotice, setReason]);

  return {
    creditFilter,
    creditPurchases,
    loadCreditPurchases,
    reviewCreditPurchase,
    selectedCreditPurchase,
    setCreditFilter,
    setSelectedCreditPurchase
  };
}
