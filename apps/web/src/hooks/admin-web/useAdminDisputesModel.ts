import { useCallback, useRef, useState } from "react";
import { getAdminDispute, listAdminDisputes, resolveAdminDispute } from "../../api/admin";
import type { AuthenticatedRequest } from "../../api/client";
import type { AdminDisputeDetailResponse, AdminDisputeSummary } from "../../types/admin";
import { appendUniqueById } from "../pagination";
import { idempotencyKey } from "./helpers";
import type { OrdersDisputesView, QueueCriticalAction } from "./adminOrdersDisputesTypes";

export function useAdminDisputesModel({
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
  setView: (view: OrdersDisputesView) => void;
}) {
  const [disputes, setDisputes] = useState<AdminDisputeSummary[]>([]);
  const [disputesNextCursor, setDisputesNextCursor] = useState<string | null>(null);
  const [disputesLoadingMore, setDisputesLoadingMore] = useState(false);
  const [selectedDispute, setSelectedDispute] = useState<AdminDisputeDetailResponse | null>(null);
  const [disputeFilter, setDisputeFilter] = useState("open");
  const [resolutionType, setResolutionType] = useState("keep_under_review");
  const disputesRequestEpoch = useRef(0);

  const loadDisputes = useCallback(async (status = disputeFilter) => {
    const requestEpoch = ++disputesRequestEpoch.current;
    setDisputesLoadingMore(false);
    setBusy(true);
    try {
      const data = await listAdminDisputes(request, status);
      if (requestEpoch !== disputesRequestEpoch.current) {
        return;
      }
      setDisputes(data.items);
      setDisputesNextCursor(data.next_cursor);
      setDisputeFilter(status);
      setView("disputes");
      setNotice(data.items.length ? "Disputas cargadas." : "No hay disputas para ese filtro.");
    } catch (error) {
      if (requestEpoch === disputesRequestEpoch.current) {
        setDisputes([]);
        setDisputesNextCursor(null);
        setNotice(error instanceof Error ? error.message : "No se pudo cargar disputas.");
      }
    } finally {
      if (requestEpoch === disputesRequestEpoch.current) {
        setBusy(false);
      }
    }
  }, [disputeFilter, request, setBusy, setNotice, setView]);

  const loadMoreDisputes = useCallback(async () => {
    const cursor = disputesNextCursor;
    if (!cursor || disputesLoadingMore) {
      return;
    }
    const requestEpoch = ++disputesRequestEpoch.current;
    const requestedFilter = disputeFilter;
    setDisputesLoadingMore(true);
    try {
      const data = await listAdminDisputes(request, requestedFilter, cursor);
      if (requestEpoch !== disputesRequestEpoch.current) {
        return;
      }
      setDisputes((current) => appendUniqueById(current, data.items));
      setDisputesNextCursor(data.next_cursor);
    } catch (error) {
      if (requestEpoch === disputesRequestEpoch.current) {
        setNotice(error instanceof Error ? error.message : "No se pudieron cargar mas disputas.");
      }
    } finally {
      if (requestEpoch === disputesRequestEpoch.current) {
        setDisputesLoadingMore(false);
      }
    }
  }, [disputeFilter, disputesLoadingMore, disputesNextCursor, request, setNotice]);

  const openDispute = useCallback(async (disputeId: string) => {
    setBusy(true);
    try {
      const data = await getAdminDispute(request, disputeId);
      setSelectedDispute(data);
      setView("dispute-detail");
      setNotice("Detalle de disputa cargado.");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "No se pudo cargar disputa.");
    } finally {
      setBusy(false);
    }
  }, [request, setBusy, setNotice, setView]);

  const resolveDispute = useCallback(() => {
    if (!selectedDispute || !adminMutable) {
      setNotice("Support es read-only y no puede resolver disputas.");
      return;
    }
    queueCriticalAction("Resolver disputa", "Resolver registra decision operativa; NODO no mueve dinero real.", async () => {
      const data = await resolveAdminDispute(request, selectedDispute.dispute.id, resolutionType, reason, idempotencyKey("resolve_dispute"));
      setSelectedDispute((current) => current ? {
        ...current,
        dispute: data.dispute,
        order_summary: data.order,
        disclaimer: data.disclaimer
      } : null);
      setReason("");
      setNotice("Disputa actualizada con audit log.");
    });
  }, [adminMutable, queueCriticalAction, reason, request, resolutionType, selectedDispute, setNotice, setReason]);

  return {
    disputeFilter,
    disputes,
    disputesLoadingMore,
    disputesNextCursor,
    loadDisputes,
    loadMoreDisputes,
    openDispute,
    resolutionType,
    resolveDispute,
    selectedDispute,
    setDisputeFilter,
    setResolutionType
  };
}
