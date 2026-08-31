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
  const [orderCodeFilter, setOrderCodeFilter] = useState("");
  const ordersRequestEpoch = useRef(0);
  const chatEvidence = useAdminOrderChatEvidenceModel({ request });

  const loadOrders = useCallback(async (status = orderFilter, publicOrderCode = orderCodeFilter) => {
    const requestEpoch = ++ordersRequestEpoch.current;
    const normalizedCode = publicOrderCode.trim();
    setOrdersLoadingMore(false);
    setBusy(true);
    try {
      const data = await listAdminOrders(request, status, null, normalizedCode);
      if (requestEpoch !== ordersRequestEpoch.current) {
        return;
      }
      setOrders(data.items);
      setOrdersNextCursor(data.next_cursor);
      setOrderFilter(status);
      setOrderCodeFilter(normalizedCode);
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
  }, [orderCodeFilter, orderFilter, request, setBusy, setNotice, setView]);

  const loadMoreOrders = useCallback(async () => {
    const cursor = ordersNextCursor;
    if (!cursor || ordersLoadingMore) {
      return;
    }
    const requestEpoch = ++ordersRequestEpoch.current;
    const requestedFilter = orderFilter;
    const requestedCode = orderCodeFilter;
    setOrdersLoadingMore(true);
    try {
      const data = await listAdminOrders(request, requestedFilter, cursor, requestedCode);
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
  }, [orderCodeFilter, orderFilter, ordersLoadingMore, ordersNextCursor, request, setNotice]);

  const openOrder = useCallback(async (orderId: string, highlightMessageId?: string) => {
    setBusy(true);
    try {
      const data = await getAdminOrder(request, orderId);
      setSelectedOrder(data);
      chatEvidence.prepareOrderChatEvidence(orderId, highlightMessageId);
      setView("order-detail");
      setNotice("Detalle de orden cargado con masking.");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "No se pudo cargar orden.");
    } finally {
      setBusy(false);
    }
  }, [chatEvidence.prepareOrderChatEvidence, request, setBusy, setNotice, setView]);

  return {
    ...chatEvidence,
    loadMoreOrders,
    loadOrders,
    openOrder,
    orderCodeFilter,
    orderFilter,
    orders,
    ordersLoadingMore,
    ordersNextCursor,
    selectedOrder,
    setOrderCodeFilter,
    setOrderFilter
  };
}
