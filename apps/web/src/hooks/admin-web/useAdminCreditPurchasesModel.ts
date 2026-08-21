import { useCallback, useRef, useState } from "react";
import { getAdminCreditPurchaseDetail, listAdminCreditPurchases, reviewAdminCreditPurchase } from "../../api/admin";
import type { AuthenticatedRequest } from "../../api/client";
import type { AdminCreditPurchaseDetail, AdminCreditPurchaseSummary } from "../../types/credits";
import { appendUniqueById } from "../pagination";
import { idempotencyKey } from "./helpers";
import type { CreditsView, QueueCriticalAction } from "./adminCreditsTypes";

function purchaseMatchesStatusFilter(status: string, filter: string) {
  const normalizedFilter = filter.trim().toLowerCase();
  return !normalizedFilter || status === normalizedFilter;
}

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
  const [creditPurchases, setCreditPurchases] = useState<AdminCreditPurchaseSummary[]>([]);
  const [creditPurchasesNextCursor, setCreditPurchasesNextCursor] = useState<string | null>(null);
  const [creditPurchasesLoadingMore, setCreditPurchasesLoadingMore] = useState(false);
  const [selectedCreditPurchase, setSelectedCreditPurchaseDetail] = useState<AdminCreditPurchaseDetail | null>(null);
  const [creditFilter, setCreditFilter] = useState("pending_manual_review");
  const creditPurchasesRequestEpoch = useRef(0);
  const creditPurchaseDetailRequestEpoch = useRef(0);
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

  const setSelectedCreditPurchase = useCallback(async (purchase: AdminCreditPurchaseSummary | null) => {
    const requestEpoch = ++creditPurchaseDetailRequestEpoch.current;
    if (purchase === null) {
      setSelectedCreditPurchaseDetail(null);
      return;
    }
    setBusy(true);
    try {
      const detail = await getAdminCreditPurchaseDetail(request, purchase.id);
      if (requestEpoch !== creditPurchaseDetailRequestEpoch.current) {
        return;
      }
      setSelectedCreditPurchaseDetail(detail);
      setView("credit-detail");
      setNotice("Detalle de compra cargado.");
    } catch (error) {
      if (requestEpoch === creditPurchaseDetailRequestEpoch.current) {
        setNotice(error instanceof Error ? error.message : "No se pudo cargar el detalle de la compra.");
      }
    } finally {
      if (requestEpoch === creditPurchaseDetailRequestEpoch.current) {
        setBusy(false);
      }
    }
  }, [request, setBusy, setNotice, setView]);

  const reviewCreditPurchase = useCallback((action: "approve" | "reject") => {
    if (!selectedCreditPurchase || !adminMutable) {
      setNotice("Accion no permitida para este rol.");
      return;
    }
    const onchain = selectedCreditPurchase.purchase.payment_method === "base_usdc_onchain";
    const title = action === "approve" ? "Aprobar pago manual" : onchain ? "Rechazar compra on-chain" : "Rechazar pago manual";
    queueCriticalAction(title, "Backend valida estado, motivo e idempotencia.", async () => {
      const data = await reviewAdminCreditPurchase(
        request,
        selectedCreditPurchase.purchase.id,
        action,
        reason,
        idempotencyKey(`credit_${action}`)
      );
      setSelectedCreditPurchaseDetail(data);
      setCreditPurchases((current) => {
        if (!purchaseMatchesStatusFilter(data.purchase.status, creditPurchasesQueryRef.current)) {
          return current.filter((item) => item.id !== data.purchase.id);
        }
        return current.map((item) => (
          item.id === data.purchase.id
            ? {
                ...item,
                status: data.purchase.status,
                verification_status: data.onchain_evidence?.verification_status ?? item.verification_status,
                updated_at: data.purchase.updated_at
              }
            : item
        ));
      });
      setReason("");
      setNotice(action === "approve" ? "Pago aprobado y acreditado por backend." : "Pago rechazado sin acreditar.");
    });
  }, [adminMutable, queueCriticalAction, reason, request, selectedCreditPurchase, setNotice, setReason]);

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
