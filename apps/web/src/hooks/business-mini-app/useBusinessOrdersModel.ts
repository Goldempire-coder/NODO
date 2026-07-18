import { useCallback, useRef, useState } from "react";
import { ApiClientError, type AuthenticatedRequest } from "../../api/client";
import { getBusinessOrder, listBusinessOrders, mutateBusinessOrder as mutateBusinessOrderRequest } from "../../api/businessOrders";
import type { BusinessMiniAppView } from "../../constants/businessViews";
import { notifyTelegram } from "../../theme/telegramTheme";
import type { BusinessOrderDetail, BusinessOrderSummary } from "../../types/orders";
import { actionStartedAt, recordBusinessActionCompleted, recordBusinessActionFailed, recordBusinessActionStarted } from "../actionTelemetry";
import { useStableIdempotencyKeys } from "../useStableIdempotencyKeys";

type OrderSnapshot = Map<string, string>;

function snapshotOrder(order: BusinessOrderSummary) {
  return [
    order.status,
    order.paid_reported_at || "",
    order.payment_confirmed_at || "",
    order.delivered_at || "",
    order.business_response_deadline_at || "",
    order.delivery_deadline_at || ""
  ].join("|");
}

function buildOrderSnapshot(items: BusinessOrderSummary[]): OrderSnapshot {
  return new Map(items.map((item) => [item.id, snapshotOrder(item)]));
}

function orderUpdateNotice(previous: OrderSnapshot, items: BusinessOrderSummary[]) {
  const newOrder = items.find((item) => !previous.has(item.id));
  if (newOrder) {
    return `Nueva orden ${newOrder.public_order_code}. Revisala para atender al cliente.`;
  }
  const updatedOrder = items.find((item) => previous.get(item.id) !== snapshotOrder(item));
  if (!updatedOrder) {
    return "";
  }
  if (updatedOrder.status === "payment_reported") {
    return `Pago reportado en ${updatedOrder.public_order_code}. Revisa la orden.`;
  }
  return `Orden ${updatedOrder.public_order_code} actualizada.`;
}

export function useBusinessOrdersModel({
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
  const [businessOrders, setBusinessOrders] = useState<BusinessOrderSummary[]>([]);
  const [businessOrderDetail, setBusinessOrderDetail] = useState<BusinessOrderDetail | null>(null);
  const [businessOrderReason, setBusinessOrderReason] = useState("");
  const [businessOrderFilter, setBusinessOrderFilter] = useState<string>("open");
  const [businessOrderAction, setBusinessOrderAction] = useState<"confirm-payment" | "reject-payment-report" | "mark-delivered" | null>(null);
  const businessOrdersSnapshotRef = useRef<OrderSnapshot>(new Map());
  const businessOrdersWatchReadyRef = useRef(false);
  const { clearIdempotencyKey, getIdempotencyKey } = useStableIdempotencyKeys();

  const loadBusinessOrders = useCallback(async (status?: string) => {
    const requestedStatus = status || "open";
    setView("business-orders");
    setBusy(true);
    try {
      const data = await listBusinessOrders<{ items: BusinessOrderSummary[] }>(request, requestedStatus);
      setBusinessOrders(data.items);
      if (requestedStatus === "open") {
        businessOrdersSnapshotRef.current = buildOrderSnapshot(data.items);
        businessOrdersWatchReadyRef.current = true;
      }
      setBusinessOrderDetail(null);
      setBusinessOrderFilter(requestedStatus);
      setNotice(data.items.length ? "Ordenes del negocio cargadas." : requestedStatus === "history" ? "No hay ordenes completadas todavia." : "No hay ordenes abiertas por ahora.");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "No logramos cargar las ordenes del negocio.");
    } finally {
      setBusy(false);
    }
  }, [request, setBusy, setNotice, setView]);

  const refreshBusinessOrders = useCallback(async () => {
    try {
      const data = await listBusinessOrders<{ items: BusinessOrderSummary[] }>(request, "open");
      setBusinessOrders(data.items);
      businessOrdersSnapshotRef.current = buildOrderSnapshot(data.items);
      businessOrdersWatchReadyRef.current = true;
      return true;
    } catch {
      setBusinessOrders([]);
      return false;
    }
  }, [request]);

  const pollBusinessOrderUpdates = useCallback(async () => {
    try {
      const data = await listBusinessOrders<{ items: BusinessOrderSummary[] }>(request, "open");
      const nextSnapshot = buildOrderSnapshot(data.items);
      if (businessOrdersWatchReadyRef.current) {
        const notice = orderUpdateNotice(businessOrdersSnapshotRef.current, data.items);
        if (notice) {
          setNotice(notice);
          notifyTelegram("success");
        }
      }
      businessOrdersSnapshotRef.current = nextSnapshot;
      businessOrdersWatchReadyRef.current = true;
      if (businessOrderFilter === "open") {
        setBusinessOrders(data.items);
      }
      return true;
    } catch {
      return false;
    }
  }, [businessOrderFilter, request, setNotice]);

  const openBusinessOrder = useCallback(async (orderId: string) => {
    setBusinessOrderDetail(null);
    setBusinessOrderReason("");
    setView("business-order-detail");
    setBusy(true);
    try {
      const data = await getBusinessOrder<BusinessOrderDetail>(request, orderId);
      setBusinessOrderDetail(data);
      setBusinessOrderReason("");
      setNotice(data.disclaimer || "Orden lista para operar desde el negocio.");
    } catch (error) {
      setBusinessOrderDetail(null);
      setNotice(error instanceof Error ? error.message : "No logramos abrir la orden del negocio.");
    } finally {
      setBusy(false);
    }
  }, [request, setBusy, setNotice, setView]);

  const mutateBusinessOrder = useCallback(async (action: "confirm-payment" | "reject-payment-report" | "mark-delivered") => {
    if (!businessOrderDetail) {
      return;
    }
    if (action === "reject-payment-report" && !businessOrderReason.trim()) {
      setNotice("Para rechazar un reporte, escribe el motivo. Los creditos quedan bloqueados mientras se revisa.");
      return;
    }
    setBusinessOrderAction(action);
    const telemetryAction = action === "confirm-payment" ? "business_order_confirm_payment" : action === "mark-delivered" ? "business_order_mark_delivered" : "business_order_reject_payment_report";
    const startedAt = actionStartedAt();
    recordBusinessActionStarted(telemetryAction, "business-order-detail");
    const idempotencyScope = `business_order_${action}_${businessOrderDetail.order.id}`;
    try {
      await mutateBusinessOrderRequest(
        request,
        businessOrderDetail.order.id,
        action,
        businessOrderReason || undefined,
        getIdempotencyKey(idempotencyScope, { orderId: businessOrderDetail.order.id, action, reason: businessOrderReason || undefined })
      );
      clearIdempotencyKey(idempotencyScope);
      const data = await getBusinessOrder<BusinessOrderDetail>(request, businessOrderDetail.order.id);
      setBusinessOrderDetail(data);
      setBusinessOrderReason("");
      setNotice(action === "confirm-payment" ? "Pago confirmado. Se consumieron los creditos del anuncio." : action === "mark-delivered" ? "Pago movil marcado como enviado." : "Reporte rechazado y enviado a revision.");
      recordBusinessActionCompleted(telemetryAction, "business-order-detail", startedAt);
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "No pudimos operar la orden.");
      recordBusinessActionFailed(telemetryAction, "business-order-detail", startedAt, error instanceof ApiClientError ? error.code : undefined);
    } finally {
      setBusinessOrderAction(null);
    }
  }, [businessOrderDetail, businessOrderReason, clearIdempotencyKey, getIdempotencyKey, request, setNotice]);

  return {
    businessOrderAction,
    businessOrderDetail,
    businessOrderFilter,
    businessOrderReason,
    businessOrders,
    loadBusinessOrders,
    mutateBusinessOrder,
    openBusinessOrder,
    pollBusinessOrderUpdates,
    refreshBusinessOrders,
    setBusinessOrderReason
  };
}
