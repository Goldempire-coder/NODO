import { useCallback, useRef, useState } from "react";
import { getAdminOrder, listAdminOrders } from "../../api/admin";
import type { AuthenticatedRequest } from "../../api/client";
import type { AdminOrderDetailResponse, AdminOrderSummary } from "../../types/admin";
import type { OrdersDisputesView } from "./adminOrdersDisputesTypes";
import { appendUniqueById } from "../pagination";
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
  const [ordersNextCursor, setOrdersNextCursor] = useState<string | null>(null);
  const [ordersLoadingMore, setOrdersLoadingMore] = useState(false);
  const [selectedOrder, setSelectedOrder] = useState<AdminOrderDetailResponse | null>(null);
  const [orderFilter, setOrderFilter] = useState("");
  const ordersRequestEpoch = useRef(0);
  const chatEvidence = useAdminOrderChatEvidenceModel({ request });

  const loadOrders = useCallback(async (status = orderFilter) => {
    const requestEpoch = ++ordersRequestEpoch.current;
    setOrdersLoadingMore(false);
    setBusy(true);
    try {
      const data = await listAdminOrders(request, status);
      if (requestEpoch !== ordersRequestEpoch.current) {
        return;
      }
      setOrders(data.items);
      setOrdersNextCursor(data.next_cursor);
      setOrderFilter(status);
      setView("orders");
      setNotice(data.items.length ? "Ordenes admin cargadas." : "No hay ordenes para ese filtro.");
    } catch (error) {
      if (requestEpoch === ordersRequestEpoch.current) {
        setOrders([]);
        setOrdersNextCursor(null);
        setNotice(error instanceof Error ? error.message : "No se pudo cargar ordenes.");
      }
    } finally {
      if (requestEpoch === ordersRequestEpoch.current) {
        setBusy(false);
      }
    }
  }, [orderFilter, request, setBusy, setNotice, setView]);

  const loadMoreOrders = useCallback(async () => {
    const cursor = ordersNextCursor;
    if (!cursor || ordersLoadingMore) {
      return;
    }
    const requestEpoch = ++ordersRequestEpoch.current;
    const requestedFilter = orderFilter;
    setOrdersLoadingMore(true);
    try {
      const data = await listAdminOrders(request, requestedFilter, cursor);
      if (requestEpoch !== ordersRequestEpoch.current) {
        return;
      }
      setOrders((current) => appendUniqueById(current, data.items));
      setOrdersNextCursor(data.next_cursor);
    } catch (error) {
      if (requestEpoch === ordersRequestEpoch.current) {
        setNotice(error instanceof Error ? error.message : "No se pudieron cargar mas ordenes.");
      }
    } finally {
      if (requestEpoch === ordersRequestEpoch.current) {
        setOrdersLoadingMore(false);
      }
    }
  }, [orderFilter, ordersLoadingMore, ordersNextCursor, request, setNotice]);

  const openOrder = useCallback(async (orderId: string, highlightMessageId?: string) => {
    setBusy(true);
    try {
      const data = await getAdminOrder(request, orderId);
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
    loadMoreOrders,
    loadOrders,
    openOrder,
    orderFilter,
    orders,
    ordersLoadingMore,
    ordersNextCursor,
    selectedOrder,
    setOrderFilter
  };
}
