import { useCallback, useRef, useState } from "react";
import { listAdminCreditPurchases, reviewAdminCreditPurchase } from "../../api/admin";
import type { AuthenticatedRequest } from "../../api/client";
import type { CreditPurchase } from "../../types/credits";
import { appendUniqueById } from "../pagination";
import { idempotencyKey } from "./helpers";
import type { CreditsView, QueueCriticalAction } from "./adminCreditsTypes";

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
  const [creditPurchasesNextCursor, setCreditPurchasesNextCursor] = useState<string | null>(null);
  const [creditPurchasesLoadingMore, setCreditPurchasesLoadingMore] = useState(false);
  const [selectedCreditPurchase, setSelectedCreditPurchase] = useState<CreditPurchase | null>(null);
  const [creditFilter, setCreditFilter] = useState("pending_manual_review");
  const creditPurchasesRequestEpoch = useRef(0);
  const creditPurchasesQueryRef = useRef("pending_manual_review");

  const loadCreditPurchases = useCallback(async (status = creditFilter) => {
    const requestEpoch = ++creditPurchasesRequestEpoch.current;
    setCreditPurchasesLoadingMore(false);
    setBusy(true);
    try {
      const data = await listAdminCreditPurchases(request, status);
      if (requestEpoch !== creditPurchasesRequestEpoch.current) {
        return;
      }
      setCreditPurchases(data.items);
      setCreditPurchasesNextCursor(data.next_cursor);
      setCreditFilter(status);
      creditPurchasesQueryRef.current = status;
      setView("credit-purchases");
      setNotice(data.items.length ? "Compras de creditos cargadas." : "No hay compras para ese filtro.");
    } catch (error) {
      if (requestEpoch === creditPurchasesRequestEpoch.current) {
        setCreditPurchases([]);
        setCreditPurchasesNextCursor(null);
        setNotice(error instanceof Error ? error.message : "No se pudo cargar compras de creditos.");
      }
    } finally {
      if (requestEpoch === creditPurchasesRequestEpoch.current) {
        setBusy(false);
      }
    }
  }, [creditFilter, request, setBusy, setNotice, setView]);

  const loadMoreCreditPurchases = useCallback(async () => {
    const cursor = creditPurchasesNextCursor;
    if (!cursor || creditPurchasesLoadingMore) {
      return;
    }
    const requestEpoch = ++creditPurchasesRequestEpoch.current;
    const requestedStatus = creditPurchasesQueryRef.current;
    setCreditPurchasesLoadingMore(true);
    try {
      const data = await listAdminCreditPurchases(request, requestedStatus, cursor);
      if (requestEpoch !== creditPurchasesRequestEpoch.current) {
        return;
      }
      setCreditPurchases((current) => appendUniqueById(current, data.items));
      setCreditPurchasesNextCursor(data.next_cursor);
    } catch (error) {
      if (requestEpoch === creditPurchasesRequestEpoch.current) {
        setNotice(error instanceof Error ? error.message : "No se pudieron cargar mas compras de creditos.");
      }
    } finally {
      if (requestEpoch === creditPurchasesRequestEpoch.current) {
        setCreditPurchasesLoadingMore(false);
      }
    }
  }, [creditPurchasesLoadingMore, creditPurchasesNextCursor, request, setNotice]);

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
    creditPurchasesLoadingMore,
    creditPurchasesNextCursor,
    loadMoreCreditPurchases,
    loadCreditPurchases,
    reviewCreditPurchase,
    selectedCreditPurchase,
    setCreditFilter,
    setSelectedCreditPurchase
  };
}
