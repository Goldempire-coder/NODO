import { useCallback, useState } from "react";
import { ApiClientError, type AuthenticatedRequest } from "../../api/client";
import { declineBusinessOrder, getBusinessOrder, listBusinessOrders, mutateBusinessOrder as mutateBusinessOrderRequest } from "../../api/businessOrders";
import type { BusinessMiniAppView } from "../../constants/businessViews";
import type { BusinessOrderDetail, BusinessOrderSummary } from "../../types/orders";
import { actionStartedAt, recordBusinessActionCompleted, recordBusinessActionFailed, recordBusinessActionStarted } from "../actionTelemetry";
import { useStableIdempotencyKeys } from "../useStableIdempotencyKeys";

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
  const [businessOrderAction, setBusinessOrderAction] = useState<"confirm-payment" | "reject-payment-report" | "mark-delivered" | "cannot-attend" | null>(null);
  const { clearIdempotencyKey, getIdempotencyKey } = useStableIdempotencyKeys();

  const loadBusinessOrders = useCallback(async (status?: string) => {
    const requestedStatus = status || "open";
    setView("business-orders");
    setBusy(true);
    try {
      const data = await listBusinessOrders<{ items: BusinessOrderSummary[] }>(request, requestedStatus);
      setBusinessOrders(data.items);
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
      return true;
    } catch {
      setBusinessOrders([]);
      return false;
    }
  }, [request]);

  const syncBusinessOrderFromChat = useCallback((order: BusinessOrderSummary) => {
    setBusinessOrders((current) => current.map((item) => (item.id === order.id ? order : item)));
    setBusinessOrderDetail((current) => {
      if (!current || current.order.id !== order.id) {
        return current;
      }
      return { ...current, order };
    });
  }, []);

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
      return true;
    } catch (error) {
      setBusinessOrderDetail(null);
      setNotice(error instanceof Error ? error.message : "No logramos abrir la orden del negocio.");
      return false;
    } finally {
      setBusy(false);
    }
  }, [request, setBusy, setNotice, setView]);

  const mutateBusinessOrder = useCallback(async (action: "confirm-payment" | "reject-payment-report" | "mark-delivered" | "cannot-attend") => {
    if (!businessOrderDetail) {
      return;
    }
    if (action === "reject-payment-report" && !businessOrderReason.trim()) {
      setNotice("Para rechazar un reporte, escribe el motivo. Los creditos quedan bloqueados mientras se revisa.");
      return;
    }
    setBusinessOrderAction(action);
    const telemetryAction = action === "confirm-payment"
      ? "business_order_confirm_payment"
      : action === "mark-delivered"
        ? "business_order_mark_delivered"
        : action === "cannot-attend"
          ? "business_order_cannot_attend"
          : "business_order_reject_payment_report";
    const startedAt = actionStartedAt();
    recordBusinessActionStarted(telemetryAction, "business-order-detail");
    const idempotencyScope = `business_order_${action}_${businessOrderDetail.order.id}`;
    try {
      const idempotencyKey = getIdempotencyKey(
        idempotencyScope,
        {
          orderId: businessOrderDetail.order.id,
          action,
          reason: action === "cannot-attend" ? undefined : businessOrderReason || undefined
        }
      );
      if (action === "cannot-attend") {
        await declineBusinessOrder(
          request,
          businessOrderDetail.order.id,
          idempotencyKey
        );
      } else {
        await mutateBusinessOrderRequest(
          request,
          businessOrderDetail.order.id,
          action,
          businessOrderReason || undefined,
          idempotencyKey
        );
      }
      clearIdempotencyKey(idempotencyScope);
      const data = await getBusinessOrder<BusinessOrderDetail>(request, businessOrderDetail.order.id);
      setBusinessOrderDetail(data);
      setBusinessOrderReason("");
      setNotice(
        action === "confirm-payment"
          ? "Pago confirmado. Se consumieron los creditos del anuncio."
          : action === "mark-delivered"
            ? "Pago movil marcado como enviado."
            : action === "cannot-attend"
              ? "Orden cancelada antes de reportar pago. El cliente fue avisado."
              : "Reporte rechazado y enviado a revision."
      );
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
    refreshBusinessOrders,
    syncBusinessOrderFromChat,
    setBusinessOrderReason
  };
}
