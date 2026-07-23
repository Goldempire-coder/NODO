import { useCallback, useState } from "react";
import { getAdminOrder, listAdminOrders } from "../../api/admin";
import type { AuthenticatedRequest } from "../../api/client";
import type { AdminOrderSummary } from "../../types/admin";
import type { AdminWebOrderDetail, ListResponse, OrdersDisputesView } from "./adminOrdersDisputesTypes";
import { useAdminOrderChatEvidenceModel } from "./useAdminOrderChatEvidenceModel";

export function useAdminOrdersModel({
  request,
  setBusy,
  setNotice,
  setView
}: {
  request: AuthenticatedRequest;
  setBusy: (busy: boolean) => void;
  setNotice: (notice: string) => void;
  setView: (view: OrdersDisputesView) => void;
}) {
  const [orders, setOrders] = useState<AdminOrderSummary[]>([]);
  const [selectedOrder, setSelectedOrder] = useState<AdminWebOrderDetail | null>(null);
  const [orderFilter, setOrderFilter] = useState("");
  const chatEvidence = useAdminOrderChatEvidenceModel({ request });

  const loadOrders = useCallback(async (status = orderFilter) => {
    setBusy(true);
    try {
      const data = await listAdminOrders<ListResponse<AdminOrderSummary>>(request, status);
      setOrders(data.items);
      setOrderFilter(status);
      setView("orders");
      setNotice(data.items.length ? "Ordenes admin cargadas." : "No hay ordenes para ese filtro.");
    } catch (error) {
      setOrders([]);
      setNotice(error instanceof Error ? error.message : "No se pudo cargar ordenes.");
    } finally {
      setBusy(false);
    }
  }, [orderFilter, request, setBusy, setNotice, setView]);

  const openOrder = useCallback(async (orderId: string, highlightMessageId?: string) => {
    setBusy(true);
    try {
      const data = await getAdminOrder<AdminWebOrderDetail>(request, orderId);
      setSelectedOrder(data);
      setView("order-detail");
      setNotice("Detalle de orden cargado con masking.");
      void chatEvidence.loadOrderChatEvidence(orderId, highlightMessageId);
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "No se pudo cargar orden.");
    } finally {
      setBusy(false);
    }
  }, [chatEvidence.loadOrderChatEvidence, request, setBusy, setNotice, setView]);

  return {
    ...chatEvidence,
    loadOrders,
    openOrder,
    orderFilter,
    orders,
    selectedOrder,
    setOrderFilter
  };
}
