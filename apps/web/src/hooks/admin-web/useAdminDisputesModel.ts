import { useCallback, useState } from "react";
import { getAdminDispute, listAdminDisputes, resolveAdminDispute } from "../../api/admin";
import type { AuthenticatedRequest } from "../../api/client";
import type { AdminDisputeSummary } from "../../types/admin";
import { idempotencyKey } from "./helpers";
import type { AdminWebDisputeDetail, ListResponse, OrdersDisputesView, QueueCriticalAction } from "./adminOrdersDisputesTypes";

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
  const [selectedDispute, setSelectedDispute] = useState<AdminWebDisputeDetail | null>(null);
  const [disputeFilter, setDisputeFilter] = useState("open");
  const [resolutionType, setResolutionType] = useState("keep_under_review");

  const loadDisputes = useCallback(async (status = disputeFilter) => {
    setBusy(true);
    try {
      const data = await listAdminDisputes<ListResponse<AdminDisputeSummary>>(request, status);
      setDisputes(data.items);
      setDisputeFilter(status);
      setView("disputes");
      setNotice(data.items.length ? "Disputas cargadas." : "No hay disputas para ese filtro.");
    } catch (error) {
      setDisputes([]);
      setNotice(error instanceof Error ? error.message : "No se pudo cargar disputas.");
    } finally {
      setBusy(false);
    }
  }, [disputeFilter, request, setBusy, setNotice, setView]);

  const openDispute = useCallback(async (disputeId: string) => {
    setBusy(true);
    try {
      const data = await getAdminDispute<AdminWebDisputeDetail>(request, disputeId);
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
      const data = await resolveAdminDispute<AdminWebDisputeDetail>(request, selectedDispute.dispute.id, resolutionType, reason, idempotencyKey("resolve_dispute"));
      setSelectedDispute(data);
      setReason("");
      setNotice("Disputa actualizada con audit log.");
    });
  }, [adminMutable, queueCriticalAction, reason, request, resolutionType, selectedDispute, setNotice, setReason]);

  return {
    disputeFilter,
    disputes,
    loadDisputes,
    openDispute,
    resolutionType,
    resolveDispute,
    selectedDispute,
    setDisputeFilter,
    setResolutionType
  };
}
