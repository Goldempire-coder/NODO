"use client";

import { useRef } from "react";
import type { AuthenticatedRequest } from "../../api/client";
import { cancelRemitterOrder, createRemitterOrder, extendPaymentDeadline, getOrder, listMyOrders } from "../../api/orders";
import type { OrderSummary } from "../../types/orders";
import { actionStartedAt, recordActionCompleted, recordActionFailed, recordActionStarted } from "../actionTelemetry";
import { useStableIdempotencyKeys } from "../useStableIdempotencyKeys";
import type { ClientWorkspaceState } from "./useClientWorkspaceState";

type RemitterOrdersState = Pick<
  ClientWorkspaceState,
  | "selectedAd"
  | "orderForm"
  | "setSelectedOrder"
  | "setMyOrders"
  | "setNotice"
  | "setCreatingOrder"
  | "setLoadingOrders"
  | "setOpeningOrderId"
  | "setExtendingOrderId"
  | "setCancellingOrderId"
  | "setView"
>;

export function useRemitterOrdersModel(state: RemitterOrdersState & { request: AuthenticatedRequest }) {
  const {
    request,
    selectedAd,
    orderForm,
    setCancellingOrderId,
    setCreatingOrder,
    setExtendingOrderId,
    setLoadingOrders,
    setMyOrders,
    setNotice,
    setOpeningOrderId,
    setSelectedOrder,
    setView
  } = state;
  const ordersCacheRef = useRef<{ items: OrderSummary[]; loadedAt: number } | null>(null);
  const { clearIdempotencyKey, getIdempotencyKey } = useStableIdempotencyKeys();

  function rememberOrder(order: OrderSummary) {
    ordersCacheRef.current = {
      items: [order, ...(ordersCacheRef.current?.items || []).filter((item) => item.id !== order.id)],
      loadedAt: Date.now()
    };
    setMyOrders(ordersCacheRef.current.items);
  }

  async function createOrder() {
    if (!selectedAd) {
      setNotice("Selecciona un anuncio activo.");
      return;
    }
    const startedAt = actionStartedAt();
    recordActionStarted("client_order_create", "create-order");
    setCreatingOrder(true);
    setNotice("Preparando tu orden");
    const idempotencyScope = `order_create_${selectedAd.id}`;
    try {
      const data = await createRemitterOrder<{ order: OrderSummary }>(
        request,
        {
          ad_id: selectedAd.id,
          amount_usd: orderForm.amount_usd,
          receiver_data: {
            bank: orderForm.bank,
            phone: orderForm.phone,
            document: orderForm.document,
            holder: orderForm.holder
          }
        },
        getIdempotencyKey(idempotencyScope, { ad_id: selectedAd.id, ...orderForm })
      );
      clearIdempotencyKey(idempotencyScope);
      setSelectedOrder(data.order);
      rememberOrder(data.order);
      setView("order-summary");
      setNotice("");
      recordActionCompleted("client_order_create", "create-order", startedAt);
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "No logramos crear la orden. Revisa los datos e intenta de nuevo.");
      recordActionFailed("client_order_create", "create-order", startedAt, error instanceof Error ? error.name : undefined);
    } finally {
      setCreatingOrder(false);
    }
  }

  async function loadMyOrders(targetView: "my-orders" | "messages" = "my-orders") {
    const screen = targetView === "messages" ? "messages" : "my-orders";
    const startedAt = actionStartedAt();
    recordActionStarted("client_orders_load", screen);
    setLoadingOrders(true);
    setView(targetView);
    const cached = ordersCacheRef.current;
    if (cached && Date.now() - cached.loadedAt < 30_000) {
      setMyOrders(cached.items);
      setNotice(cached.items.length ? "" : targetView === "messages" ? "Todavia no tienes conversaciones." : "Todavia no tienes ordenes.");
    }
    try {
      const data = await listMyOrders<{ items: OrderSummary[] }>(request);
      ordersCacheRef.current = { items: data.items, loadedAt: Date.now() };
      setMyOrders(data.items);
      setNotice(data.items.length ? "" : targetView === "messages" ? "Todavia no tienes conversaciones." : "Todavia no tienes ordenes.");
      recordActionCompleted("client_orders_load", screen, startedAt);
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "No logramos cargar tus ordenes.");
      recordActionFailed("client_orders_load", screen, startedAt, error instanceof Error ? error.name : undefined);
    } finally {
      setLoadingOrders(false);
    }
  }

  async function openOrderDetail(orderId: string) {
    const startedAt = actionStartedAt();
    recordActionStarted("client_order_detail_open", "order-summary");
    const optimisticOrder = ordersCacheRef.current?.items.find((order) => order.id === orderId);
    if (optimisticOrder) {
      setSelectedOrder(optimisticOrder);
      setView("order-summary");
      setNotice("");
    } else {
      setOpeningOrderId(orderId);
    }
    try {
      const data = await getOrder<{ order: OrderSummary }>(request, orderId);
      setSelectedOrder(data.order);
      rememberOrder(data.order);
      setView("order-summary");
      setNotice("");
      recordActionCompleted("client_order_detail_open", "order-summary", startedAt);
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "No logramos abrir la orden.");
      recordActionFailed("client_order_detail_open", "order-summary", startedAt, error instanceof Error ? error.name : undefined);
    } finally {
      if (!optimisticOrder) {
        setOpeningOrderId(null);
      }
    }
  }

  async function extendOrder(orderId: string) {
    const startedAt = actionStartedAt();
    recordActionStarted("client_order_extend", "order-summary");
    setExtendingOrderId(orderId);
    const idempotencyScope = `order_extend_${orderId}`;
    try {
      const data = await extendPaymentDeadline<{ order: OrderSummary }>(request, orderId, "Necesito unos minutos mas", getIdempotencyKey(idempotencyScope, { orderId, reason: "Necesito unos minutos mas" }));
      clearIdempotencyKey(idempotencyScope);
      setSelectedOrder(data.order);
      rememberOrder(data.order);
      setNotice("Tiempo extendido una vez.");
      recordActionCompleted("client_order_extend", "order-summary", startedAt);
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "No logramos extender el tiempo.");
      recordActionFailed("client_order_extend", "order-summary", startedAt, error instanceof Error ? error.name : undefined);
    } finally {
      setExtendingOrderId(null);
    }
  }

  async function cancelOrder(orderId: string) {
    const startedAt = actionStartedAt();
    recordActionStarted("client_order_cancel", "order-summary");
    setCancellingOrderId(orderId);
    const idempotencyScope = `order_cancel_${orderId}`;
    try {
      const data = await cancelRemitterOrder<{ order: OrderSummary }>(request, orderId, "No pude realizar el pago", getIdempotencyKey(idempotencyScope, { orderId, reason: "No pude realizar el pago" }));
      clearIdempotencyKey(idempotencyScope);
      setSelectedOrder(data.order);
      rememberOrder(data.order);
      setNotice("Orden cancelada.");
      recordActionCompleted("client_order_cancel", "order-summary", startedAt);
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "No logramos cancelar la orden.");
      recordActionFailed("client_order_cancel", "order-summary", startedAt, error instanceof Error ? error.name : undefined);
    } finally {
      setCancellingOrderId(null);
    }
  }

  async function prefetchMyOrders() {
    const cached = ordersCacheRef.current;
    if (cached && Date.now() - cached.loadedAt < 30_000) {
      return;
    }
    try {
      const data = await listMyOrders<{ items: OrderSummary[] }>(request);
      ordersCacheRef.current = { items: data.items, loadedAt: Date.now() };
      setMyOrders(data.items);
    } catch {
      // Background warmup should never interrupt the active screen.
    }
  }

  return { createOrder, loadMyOrders, openOrderDetail, extendOrder, cancelOrder, prefetchMyOrders };
}
