import { useCallback, useEffect, useRef, useState } from "react";
import { openOrderDispute } from "../../api/chat";
import { ApiClientError, type AuthenticatedRequest } from "../../api/client";
import { declineBusinessOrder, getBusinessOrder, listBusinessOrders, mutateBusinessOrder as mutateBusinessOrderRequest } from "../../api/businessOrders";
import type { BusinessMiniAppView } from "../../constants/businessViews";
import type { BusinessSummary } from "../../types/business";
import type { BusinessOrderDetail, BusinessOrderSummary } from "../../types/orders";
import { actionStartedAt, recordBusinessActionCompleted, recordBusinessActionFailed, recordBusinessActionStarted } from "../actionTelemetry";
import { useStableIdempotencyKeys } from "../useStableIdempotencyKeys";
import { handleBusinessPinError as routeBusinessPinError, isBusinessPinError, requireUnlockedBusinessPin } from "./businessPinGuards";

type BusinessOrderAction = "confirm-payment" | "report-payment-problem" | "mark-delivered" | "cannot-attend";
type PendingBusinessOrderPinAction = {
  orderId: string;
  action: "confirm-payment" | "cannot-attend";
};
type BusinessOrdersPage = {
  items: BusinessOrderSummary[];
  next_cursor?: string | null;
  disclaimer?: string;
};

const BUSINESS_ORDER_PAGE_SIZE = 20;

function businessOrderPinActionLabel(action: PendingBusinessOrderPinAction["action"]) {
  return action === "confirm-payment"
    ? "confirmar pago recibido"
    : "cancelar esta orden antes del pago";
}

function businessOrderActionSuccessMessage(action: BusinessOrderAction) {
  if (action === "confirm-payment") {
    return "Pago confirmado. Se consumieron los creditos del anuncio.";
  }
  if (action === "mark-delivered") {
    return "Pago movil marcado como enviado.";
  }
  if (action === "cannot-attend") {
    return "Orden cancelada antes de reportar pago. El cliente fue avisado.";
  }
  return "Problema reportado. NODO revisará la operación.";
}

export function useBusinessOrdersModel({
  business,
  request,
  setBusy,
  setNotice,
  setView
}: {
  business: BusinessSummary | null;
  request: AuthenticatedRequest;
  setBusy: (busy: boolean) => void;
  setNotice: (notice: string) => void;
  setView: (view: BusinessMiniAppView) => void;
}) {
  const [businessOrders, setBusinessOrders] = useState<BusinessOrderSummary[]>([]);
  const [businessOrderNextCursor, setBusinessOrderNextCursor] = useState<string | null>(null);
  const [businessOrderLoadingMore, setBusinessOrderLoadingMore] = useState(false);
  const [businessOrderDetail, setBusinessOrderDetail] = useState<BusinessOrderDetail | null>(null);
  const [businessOrderReason, setBusinessOrderReason] = useState("");
  const [businessOrderFilter, setBusinessOrderFilter] = useState<string>("open");
  const [loadedBusinessOrderFilters, setLoadedBusinessOrderFilters] = useState<Set<string>>(new Set());
  const [businessOrderFilterCounts, setBusinessOrderFilterCounts] = useState<Record<string, number>>({});
  const [businessOrderAction, setBusinessOrderAction] = useState<BusinessOrderAction | null>(null);
  const [businessOrderInlineNotice, setBusinessOrderInlineNotice] = useState("");
  const [pendingBusinessOrderPinAction, setPendingBusinessOrderPinAction] = useState<PendingBusinessOrderPinAction | null>(null);
  const businessOrderListRequestIdRef = useRef(0);
  const businessOrderFilterRef = useRef("open");
  const businessOrderRefreshInFlightRef = useRef(false);
  const businessOrderDetailEpochRef = useRef(0);
  const businessOrderDetailIdRef = useRef<string | null>(null);
  const businessOrderActionsRef = useRef(new Map<string, BusinessOrderAction>());
  const pendingBusinessOrderPinActionRef = useRef<PendingBusinessOrderPinAction | null>(null);
  const { clearIdempotencyKey, getIdempotencyKey } = useStableIdempotencyKeys();

  useEffect(() => {
    businessOrderFilterRef.current = businessOrderFilter;
  }, [businessOrderFilter]);

  const isCurrentBusinessOrderDetail = useCallback((orderId: string, requestEpoch: number) => (
    businessOrderDetailIdRef.current === orderId
    && businessOrderDetailEpochRef.current === requestEpoch
  ), []);

  const queuePendingBusinessOrderPinAction = useCallback((pending: PendingBusinessOrderPinAction | null) => {
    pendingBusinessOrderPinActionRef.current = pending;
    setPendingBusinessOrderPinAction(pending);
  }, []);

  const markBusinessOrderFilterLoaded = useCallback((filter: string, count: number) => {
    setLoadedBusinessOrderFilters((current) => {
      if (current.has(filter)) {
        return current;
      }
      const next = new Set(current);
      next.add(filter);
      return next;
    });
    setBusinessOrderFilterCounts((current) => (
      current[filter] === count ? current : { ...current, [filter]: count }
    ));
  }, []);

  const applyBusinessOrdersPage = useCallback((page: BusinessOrdersPage, options: { append?: boolean } = {}) => {
    setBusinessOrders((current) => {
      if (!options.append) {
        return page.items;
      }
      const knownIds = new Set(current.map((item) => item.id));
      return [
        ...current,
        ...page.items.filter((item) => !knownIds.has(item.id))
      ];
    });
    setBusinessOrderNextCursor(page.next_cursor ?? null);
  }, []);

  const reconcileBusinessOrder = useCallback((order: BusinessOrderSummary) => {
    setBusinessOrders((current) => {
      if (businessOrderFilterRef.current === "open" && order.status === "cancelled") {
        return current.filter((item) => item.id !== order.id);
      }
      return current.map((item) => (item.id === order.id ? order : item));
    });
    setBusinessOrderDetail((current) => {
      if (!current || current.order.id !== order.id) {
        return current;
      }
      return { ...current, order };
    });
  }, []);

  useEffect(() => {
    if (!loadedBusinessOrderFilters.has(businessOrderFilter)) {
      return;
    }
    setBusinessOrderFilterCounts((current) => (
      current[businessOrderFilter] === businessOrders.length
        ? current
        : { ...current, [businessOrderFilter]: businessOrders.length }
    ));
  }, [businessOrderFilter, businessOrders.length, loadedBusinessOrderFilters]);

  const loadBusinessOrders = useCallback(async (status?: string) => {
    const requestedStatus = status || "open";
    const targetListRequestId = businessOrderListRequestIdRef.current + 1;
    const previousFilter = businessOrderFilterRef.current;
    businessOrderListRequestIdRef.current = targetListRequestId;
    businessOrderFilterRef.current = requestedStatus;
    businessOrderDetailEpochRef.current += 1;
    businessOrderDetailIdRef.current = null;
    setView("business-orders");
    setBusy(true);
    try {
      const data = await listBusinessOrders<BusinessOrdersPage>(request, requestedStatus, null, BUSINESS_ORDER_PAGE_SIZE);
      if (businessOrderListRequestIdRef.current !== targetListRequestId) {
        return;
      }
      applyBusinessOrdersPage(data);
      markBusinessOrderFilterLoaded(requestedStatus, data.items.length);
      setBusinessOrderDetail(null);
      setBusinessOrderFilter(requestedStatus);
      setNotice(data.items.length ? "Ordenes del negocio cargadas." : requestedStatus === "history" ? "No hay operaciones cerradas todavia." : "No hay ordenes abiertas por ahora.");
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
  }, [applyBusinessOrdersPage, markBusinessOrderFilterLoaded, request, setBusy, setNotice, setView]);

  const openBusinessOrdersLanding = useCallback(async () => {
    return loadBusinessOrders("open");
  }, [loadBusinessOrders]);

  const refreshBusinessOrderList = useCallback(async (status: string) => {
    if (businessOrderRefreshInFlightRef.current) {
      return false;
    }
    businessOrderRefreshInFlightRef.current = true;
    try {
      const data = await listBusinessOrders<BusinessOrdersPage>(request, status, null, BUSINESS_ORDER_PAGE_SIZE);
      if (businessOrderFilterRef.current !== status) {
        return false;
      }
      applyBusinessOrdersPage(data);
      markBusinessOrderFilterLoaded(status, data.items.length);
      return true;
    } catch {
      return false;
    } finally {
      businessOrderRefreshInFlightRef.current = false;
    }
  }, [applyBusinessOrdersPage, markBusinessOrderFilterLoaded, request]);

  const loadMoreBusinessOrders = useCallback(async () => {
    const cursor = businessOrderNextCursor;
    const status = businessOrderFilterRef.current;
    const targetListRequestId = businessOrderListRequestIdRef.current;
    if (!cursor || businessOrderLoadingMore) {
      return false;
    }
    setBusinessOrderLoadingMore(true);
    try {
      const data = await listBusinessOrders<BusinessOrdersPage>(request, status, cursor, BUSINESS_ORDER_PAGE_SIZE);
      if (
        businessOrderListRequestIdRef.current !== targetListRequestId
        || businessOrderFilterRef.current !== status
      ) {
        return false;
      }
      applyBusinessOrdersPage(data, { append: true });
      return true;
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "No logramos cargar mas ordenes.");
      return false;
    } finally {
      setBusinessOrderLoadingMore(false);
    }
  }, [applyBusinessOrdersPage, businessOrderLoadingMore, businessOrderNextCursor, request, setNotice]);

  const refreshBusinessOrders = useCallback(async () => {
    if (businessOrderFilterRef.current !== "open" || businessOrderRefreshInFlightRef.current) {
      return false;
    }
    return refreshBusinessOrderList("open");
  }, [refreshBusinessOrderList]);

  const syncBusinessOrderFromChat = reconcileBusinessOrder;

  const openBusinessOrder = useCallback(async (orderId: string) => {
    const targetRequestEpoch = businessOrderDetailEpochRef.current + 1;
    businessOrderDetailEpochRef.current = targetRequestEpoch;
    businessOrderDetailIdRef.current = orderId;
    setBusinessOrderDetail(null);
    setBusinessOrderReason("");
    setBusinessOrderInlineNotice("");
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

  const refreshBusinessOrderFromAttention = useCallback(async (orderId: string) => {
    if (businessOrderDetailIdRef.current !== orderId) {
      return refreshBusinessOrderList(businessOrderFilterRef.current);
    }
    const targetRequestEpoch = businessOrderDetailEpochRef.current;
    try {
      const data = await getBusinessOrder<BusinessOrderDetail>(request, orderId);
      if (!isCurrentBusinessOrderDetail(orderId, targetRequestEpoch)) {
        return false;
      }
      setBusinessOrderDetail(data);
      reconcileBusinessOrder(data.order);
      setBusinessOrderInlineNotice(
        data.order.status === "cancelled"
          ? "El cliente cancelo la negociacion. La orden quedo cerrada."
          : ""
      );
      return true;
    } catch {
      return false;
    }
  }, [isCurrentBusinessOrderDetail, reconcileBusinessOrder, refreshBusinessOrderList, request]);

  const executeBusinessOrderAction = useCallback(async ({
    action,
    targetOrderId,
    targetOrder,
    targetRequestEpoch,
    targetReason
  }: {
    action: BusinessOrderAction;
    targetOrderId: string;
    targetOrder: BusinessOrderSummary;
    targetRequestEpoch: number | null;
    targetReason: string;
  }) => {
    if (businessOrderActionsRef.current.has(targetOrderId)) {
      return false;
    }
    const isCurrentTarget = targetRequestEpoch !== null
      && isCurrentBusinessOrderDetail(targetOrderId, targetRequestEpoch);
    businessOrderActionsRef.current.set(targetOrderId, action);
    if (isCurrentTarget) {
      setBusinessOrderAction(action);
      setBusinessOrderInlineNotice("");
    }
    const telemetryAction = action === "confirm-payment"
      ? "business_order_confirm_payment"
      : action === "mark-delivered"
        ? "business_order_mark_delivered"
        : action === "cannot-attend"
          ? "business_order_cannot_attend"
          : "business_order_report_payment_problem";
    const startedAt = actionStartedAt();
    recordBusinessActionStarted(telemetryAction, "business-order-detail");
    const idempotencyScope = `business_order_${action}_${targetOrderId}`;
    try {
      const disputePayload = {
        reason: "payment_not_received_or_incomplete",
        description: targetReason,
        evidence_file_ids: []
      };
      const idempotencyKey = getIdempotencyKey(idempotencyScope, {
        orderId: targetOrderId,
        action,
        payload: action === "report-payment-problem"
          ? disputePayload
          : { reason: action === "cannot-attend" ? undefined : targetReason || undefined }
      });
      let reconciledOrder: BusinessOrderSummary;
      if (action === "report-payment-problem") {
        await openOrderDispute(
          request,
          targetOrderId,
          disputePayload,
          idempotencyKey
        );
        reconciledOrder = {
          ...targetOrder,
          status: "disputed",
          capabilities: {
            ...targetOrder.capabilities,
            can_confirm_payment: false,
            can_reject_payment_report: false,
            can_open_dispute: false
          }
        };
      } else {
        const mutation = action === "cannot-attend"
          ? await declineBusinessOrder<{ order: BusinessOrderSummary }>(
            request,
            targetOrderId,
            idempotencyKey
          )
          : await mutateBusinessOrderRequest<{ order: BusinessOrderSummary }>(
            request,
            targetOrderId,
            action,
            targetReason || undefined,
            idempotencyKey
          );
        reconciledOrder = mutation.order;
      }
      clearIdempotencyKey(idempotencyScope);
      queuePendingBusinessOrderPinAction(null);
      recordBusinessActionCompleted(telemetryAction, "business-order-detail", startedAt);
      reconcileBusinessOrder(reconciledOrder);
      if (targetRequestEpoch === null || !isCurrentBusinessOrderDetail(targetOrderId, targetRequestEpoch)) {
        return true;
      }
      try {
        const data = await getBusinessOrder<BusinessOrderDetail>(request, targetOrderId);
        if (!isCurrentBusinessOrderDetail(targetOrderId, targetRequestEpoch)) {
          return;
        }
        setBusinessOrderDetail(data);
        setBusinessOrderReason("");
        const successMessage = businessOrderActionSuccessMessage(action);
        setBusinessOrderInlineNotice(successMessage);
        setNotice(successMessage);
      } catch {
        if (isCurrentBusinessOrderDetail(targetOrderId, targetRequestEpoch)) {
          const refreshMessage = action === "report-payment-problem"
            ? "Problema reportado. NODO revisará la operación. No pudimos actualizar el detalle; toca Actualizar."
            : "La accion fue aplicada, pero no pudimos actualizar el detalle. Toca Actualizar.";
          setBusinessOrderInlineNotice(refreshMessage);
          setNotice(refreshMessage);
        }
      }
      return true;
    } catch (error) {
      if ((action === "confirm-payment" || action === "cannot-attend") && isBusinessPinError(error)) {
        const isStillCurrentTarget = isCurrentTarget
          && isCurrentBusinessOrderDetail(targetOrderId, targetRequestEpoch);
        if (isStillCurrentTarget) {
          routeBusinessPinError({
            action: businessOrderPinActionLabel(action),
            error,
            setNotice,
            setView
          });
          queuePendingBusinessOrderPinAction({ orderId: targetOrderId, action });
          setBusinessOrderInlineNotice("Desbloquea tu PIN para completar esta accion.");
        }
        recordBusinessActionFailed(telemetryAction, "business-order-detail", startedAt, error instanceof ApiClientError ? error.code : undefined);
        return false;
      }
      if (isCurrentTarget && isCurrentBusinessOrderDetail(targetOrderId, targetRequestEpoch)) {
        const errorMessage = error instanceof Error ? error.message : "No pudimos operar la orden.";
        setBusinessOrderInlineNotice(errorMessage);
        setNotice(errorMessage);
      }
      recordBusinessActionFailed(telemetryAction, "business-order-detail", startedAt, error instanceof ApiClientError ? error.code : undefined);
      return false;
    } finally {
      businessOrderActionsRef.current.delete(targetOrderId);
      if (businessOrderDetailIdRef.current === targetOrderId) {
        setBusinessOrderAction(null);
      }
    }
  }, [
    clearIdempotencyKey,
    getIdempotencyKey,
    isCurrentBusinessOrderDetail,
    queuePendingBusinessOrderPinAction,
    reconcileBusinessOrder,
    request,
    setNotice,
    setView
  ]);

  const mutateBusinessOrder = useCallback(async (action: BusinessOrderAction) => {
    if (!businessOrderDetail) {
      return;
    }
    const targetOrderId = businessOrderDetail.order.id;
    const targetOrder = businessOrderDetail.order;
    const targetRequestEpoch = businessOrderDetailEpochRef.current;
    const targetReason = businessOrderReason.trim();
    if (
      !isCurrentBusinessOrderDetail(targetOrderId, targetRequestEpoch)
      || businessOrderActionsRef.current.has(targetOrderId)
    ) {
      return;
    }
    if (
      action === "report-payment-problem"
      && (targetOrder.status !== "payment_reported" || !targetOrder.capabilities.can_open_dispute)
    ) {
      return;
    }
    if (action === "report-payment-problem" && !targetReason) {
      setNotice("Describe brevemente el problema con el pago antes de reportarlo.");
      setBusinessOrderInlineNotice("Describe brevemente el problema con el pago antes de reportarlo.");
      return;
    }
    if ((action === "confirm-payment" || action === "cannot-attend") && !requireUnlockedBusinessPin({
      action: businessOrderPinActionLabel(action),
      business,
      setNotice,
      setView
    })) {
      queuePendingBusinessOrderPinAction({ orderId: targetOrderId, action });
      setBusinessOrderInlineNotice("Desbloquea tu PIN para completar esta accion.");
      return;
    }
    queuePendingBusinessOrderPinAction(null);
    await executeBusinessOrderAction({ action, targetOrderId, targetOrder, targetRequestEpoch, targetReason });
  }, [
    business,
    businessOrderDetail,
    businessOrderReason,
    executeBusinessOrderAction,
    isCurrentBusinessOrderDetail,
    queuePendingBusinessOrderPinAction,
    setNotice,
    setView
  ]);

  const resumePendingBusinessOrderPinAction = useCallback(async () => {
    const pending = pendingBusinessOrderPinActionRef.current;
    if (!pending) {
      return false;
    }
    // Clear before awaiting so repeated PIN callbacks cannot replay the same action twice.
    queuePendingBusinessOrderPinAction(null);
    const targetRequestEpoch = businessOrderDetailIdRef.current === pending.orderId
      ? businessOrderDetailEpochRef.current
      : null;
    try {
      const data = await getBusinessOrder<BusinessOrderDetail>(request, pending.orderId);
      reconcileBusinessOrder(data.order);
      if (targetRequestEpoch !== null && isCurrentBusinessOrderDetail(pending.orderId, targetRequestEpoch)) {
        setBusinessOrderDetail(data);
      }
      const canResume = pending.action === "confirm-payment"
        ? data.order.capabilities.can_confirm_payment
        : data.order.capabilities.can_decline_before_payment;
      // Capabilities are UX guidance only; the backend still owns the conditional transition.
      if (!canResume) {
        const stateMessage = pending.action === "confirm-payment"
          ? "La orden cambio y ya no se puede confirmar este pago."
          : "La orden cambio y ya no se puede cancelar antes del pago.";
        if (targetRequestEpoch !== null && isCurrentBusinessOrderDetail(pending.orderId, targetRequestEpoch)) {
          setBusinessOrderInlineNotice(stateMessage);
          setView("business-order-detail");
        } else {
          setNotice(stateMessage);
        }
        return true;
      }
      const completed = await executeBusinessOrderAction({
        action: pending.action,
        targetOrderId: pending.orderId,
        targetOrder: data.order,
        targetRequestEpoch,
        targetReason: ""
      });
      if (targetRequestEpoch !== null && businessOrderDetailIdRef.current === pending.orderId) {
        setView("business-order-detail");
      } else if (completed) {
        setNotice("La orden pendiente fue cancelada antes de reportar pago.");
      }
      return true;
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : "No pudimos reanudar la accion pendiente.";
      if (targetRequestEpoch !== null && isCurrentBusinessOrderDetail(pending.orderId, targetRequestEpoch)) {
        setBusinessOrderInlineNotice(errorMessage);
        setView("business-order-detail");
      } else {
        setNotice(errorMessage);
      }
      return true;
    }
  }, [
    executeBusinessOrderAction,
    isCurrentBusinessOrderDetail,
    queuePendingBusinessOrderPinAction,
    reconcileBusinessOrder,
    request,
    setNotice,
    setView
  ]);

  return {
    businessOrderAction,
    businessOrderDetail,
    businessOrderFilter,
    businessOrderFilterCounts,
    businessOrderInlineNotice,
    businessOrderLoadingMore,
    businessOrderNextCursor,
    businessOrderReason,
    businessOrders,
    loadedBusinessOrderFilters,
    loadBusinessOrders,
    loadMoreBusinessOrders,
    openBusinessOrdersLanding,
    mutateBusinessOrder,
    openBusinessOrder,
    pendingBusinessOrderPinAction,
    refreshBusinessOrderFromAttention,
    refreshBusinessOrders,
    resumePendingBusinessOrderPinAction,
    syncBusinessOrderFromChat,
    setBusinessOrderReason
  };
}
