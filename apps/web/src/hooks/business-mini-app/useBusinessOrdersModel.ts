import { useCallback, useEffect, useRef, useState } from "react";
import { ApiClientError, type AuthenticatedRequest } from "../../api/client";
import { declineBusinessOrder, getBusinessOrder, listBusinessOrders, mutateBusinessOrder as mutateBusinessOrderRequest } from "../../api/businessOrders";
import type { BusinessMiniAppView } from "../../constants/businessViews";
import type { BusinessOrderDetail, BusinessOrderSummary } from "../../types/orders";
import { actionStartedAt, recordBusinessActionCompleted, recordBusinessActionFailed, recordBusinessActionStarted } from "../actionTelemetry";
import { useStableIdempotencyKeys } from "../useStableIdempotencyKeys";

type BusinessOrderAction = "confirm-payment" | "reject-payment-report" | "mark-delivered" | "cannot-attend";

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
  const [businessOrderAction, setBusinessOrderAction] = useState<BusinessOrderAction | null>(null);
  const businessOrderListRequestIdRef = useRef(0);
  const businessOrderFilterRef = useRef("open");
  const businessOrderRefreshInFlightRef = useRef(false);
  const businessOrderDetailEpochRef = useRef(0);
  const businessOrderDetailIdRef = useRef<string | null>(null);
  const businessOrderActionsRef = useRef(new Map<string, BusinessOrderAction>());
  const { clearIdempotencyKey, getIdempotencyKey } = useStableIdempotencyKeys();

  useEffect(() => {
    businessOrderFilterRef.current = businessOrderFilter;
  }, [businessOrderFilter]);

  const isCurrentBusinessOrderDetail = useCallback((orderId: string, requestEpoch: number) => (
    businessOrderDetailIdRef.current === orderId
    && businessOrderDetailEpochRef.current === requestEpoch
  ), []);

  const loadBusinessOrders = useCallback(async (status?: string) => {
    const requestedStatus = status || "open";
    const targetListRequestId = businessOrderListRequestIdRef.current + 1;
    const previousFilter = businessOrderFilterRef.current;
    businessOrderListRequestIdRef.current = targetListRequestId;
    businessOrderFilterRef.current = requestedStatus;
    setView("business-orders");
    setBusy(true);
    try {
      const data = await listBusinessOrders<{ items: BusinessOrderSummary[] }>(request, requestedStatus);
      if (businessOrderListRequestIdRef.current !== targetListRequestId) {
        return;
      }
      setBusinessOrders(data.items);
      setBusinessOrderDetail(null);
      setBusinessOrderFilter(requestedStatus);
      setNotice(data.items.length ? "Ordenes del negocio cargadas." : requestedStatus === "history" ? "No hay ordenes completadas todavia." : "No hay ordenes abiertas por ahora.");
    } catch (error) {
      if (businessOrderListRequestIdRef.current !== targetListRequestId) {
        return;
      }
      businessOrderFilterRef.current = previousFilter;
      setNotice(error instanceof Error ? error.message : "No logramos cargar las ordenes del negocio.");
    } finally {
      if (businessOrderListRequestIdRef.current === targetListRequestId) {
        setBusy(false);
      }
    }
  }, [request, setBusy, setNotice, setView]);

  const refreshBusinessOrders = useCallback(async () => {
    if (businessOrderFilterRef.current !== "open" || businessOrderRefreshInFlightRef.current) {
      return false;
    }
    businessOrderRefreshInFlightRef.current = true;
    try {
      const data = await listBusinessOrders<{ items: BusinessOrderSummary[] }>(request, "open");
      if (businessOrderFilterRef.current !== "open") {
        return false;
      }
      setBusinessOrders(data.items);
      return true;
    } catch {
      return false;
    } finally {
      businessOrderRefreshInFlightRef.current = false;
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
    const targetRequestEpoch = businessOrderDetailEpochRef.current + 1;
    businessOrderDetailEpochRef.current = targetRequestEpoch;
    businessOrderDetailIdRef.current = orderId;
    setBusinessOrderDetail(null);
    setBusinessOrderReason("");
    setBusinessOrderAction(businessOrderActionsRef.current.get(orderId) ?? null);
    setView("business-order-detail");
    setBusy(true);
    try {
      const data = await getBusinessOrder<BusinessOrderDetail>(request, orderId);
      if (!isCurrentBusinessOrderDetail(orderId, targetRequestEpoch)) {
        return false;
      }
      setBusinessOrderDetail(data);
      setBusinessOrderReason("");
      setNotice(data.disclaimer || "Orden lista para operar desde el negocio.");
      return true;
    } catch (error) {
      if (!isCurrentBusinessOrderDetail(orderId, targetRequestEpoch)) {
        return false;
      }
      setBusinessOrderDetail(null);
      setNotice(error instanceof Error ? error.message : "No logramos abrir la orden del negocio.");
      return false;
    } finally {
      if (isCurrentBusinessOrderDetail(orderId, targetRequestEpoch)) {
        setBusy(false);
      }
    }
  }, [isCurrentBusinessOrderDetail, request, setBusy, setNotice, setView]);

  const mutateBusinessOrder = useCallback(async (action: BusinessOrderAction) => {
    if (!businessOrderDetail) {
      return;
    }
    const targetOrderId = businessOrderDetail.order.id;
    const targetRequestEpoch = businessOrderDetailEpochRef.current;
    const targetReason = businessOrderReason.trim();
    if (
      !isCurrentBusinessOrderDetail(targetOrderId, targetRequestEpoch)
      || businessOrderActionsRef.current.has(targetOrderId)
    ) {
      return;
    }
    if (action === "reject-payment-report" && !targetReason) {
      setNotice("Para rechazar un reporte, escribe el motivo. Los creditos quedan bloqueados mientras se revisa.");
      return;
    }
    businessOrderActionsRef.current.set(targetOrderId, action);
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
    const idempotencyScope = `business_order_${action}_${targetOrderId}`;
    try {
      const idempotencyKey = getIdempotencyKey(
        idempotencyScope,
        {
          orderId: targetOrderId,
          action,
          reason: action === "cannot-attend" ? undefined : targetReason || undefined
        }
      );
      if (action === "cannot-attend") {
        await declineBusinessOrder(
          request,
          targetOrderId,
          idempotencyKey
        );
      } else {
        await mutateBusinessOrderRequest(
          request,
          targetOrderId,
          action,
          targetReason || undefined,
          idempotencyKey
        );
      }
      clearIdempotencyKey(idempotencyScope);
      recordBusinessActionCompleted(telemetryAction, "business-order-detail", startedAt);
      if (!isCurrentBusinessOrderDetail(targetOrderId, targetRequestEpoch)) {
        return;
      }
      try {
        const data = await getBusinessOrder<BusinessOrderDetail>(request, targetOrderId);
        if (!isCurrentBusinessOrderDetail(targetOrderId, targetRequestEpoch)) {
          return;
        }
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
      } catch {
        if (isCurrentBusinessOrderDetail(targetOrderId, targetRequestEpoch)) {
          setNotice("La accion fue aplicada, pero no pudimos actualizar el detalle. Toca Actualizar.");
        }
      }
    } catch (error) {
      if (isCurrentBusinessOrderDetail(targetOrderId, targetRequestEpoch)) {
        setNotice(error instanceof Error ? error.message : "No pudimos operar la orden.");
      }
      recordBusinessActionFailed(telemetryAction, "business-order-detail", startedAt, error instanceof ApiClientError ? error.code : undefined);
    } finally {
      businessOrderActionsRef.current.delete(targetOrderId);
      if (businessOrderDetailIdRef.current === targetOrderId) {
        setBusinessOrderAction(null);
      }
    }
  }, [
    businessOrderDetail,
    businessOrderReason,
    clearIdempotencyKey,
    getIdempotencyKey,
    isCurrentBusinessOrderDetail,
    request,
    setNotice
  ]);

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
