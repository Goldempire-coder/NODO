"use client";

import { useRef } from "react";
import { ApiClientError, type AuthenticatedRequest } from "../../api/client";
import { cancelRemitterOrder, createRemitterOrder, extendPaymentDeadline, getOrder, listMyOrders, submitOrderRating } from "../../api/orders";
import type {
  OrderCancelReason,
  OrderRatingResult,
  OrderSummary
} from "../../types/orders";
import { actionStartedAt, recordActionCompleted, recordActionFailed, recordActionStarted } from "../actionTelemetry";
import { useStableIdempotencyKeys } from "../useStableIdempotencyKeys";
import type { ClientWorkspaceState } from "./useClientWorkspaceState";

const CLIENT_ORDERS_CACHE_TTL_MS = 15_000;

type RemitterOrdersState = Pick<
  ClientWorkspaceState,
  | "selectedAd"
  | "setSelectedAd"
  | "orderForm"
  | "setSelectedOrder"
  | "setMyOrders"
  | "setNotice"
  | "setCreatingOrder"
  | "setLoadingOrders"
  | "setOpeningOrderId"
  | "setExtendingOrderId"
  | "setCancellingOrderId"
  | "selectedRatingStars"
  | "setSelectedRatingStars"
  | "setSubmittingRatingOrderId"
  | "setView"
>;

export function useRemitterOrdersModel(
  state: RemitterOrdersState & {
    request: AuthenticatedRequest;
    openOrderChat: (orderId: string) => Promise<void>;
    searchFreshForAmount: (amountUsd: string) => Promise<void>;
  }
) {
  const {
    request,
    openOrderChat,
    searchFreshForAmount,
    selectedAd,
    setSelectedAd,
    orderForm,
    setCancellingOrderId,
    setCreatingOrder,
    setExtendingOrderId,
    setLoadingOrders,
    setMyOrders,
    setNotice,
    setOpeningOrderId,
    selectedRatingStars,
    setSelectedRatingStars,
    setSelectedOrder,
    setSubmittingRatingOrderId,
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
          expected_rate_bs_per_usd: selectedAd.rate_bs_per_usd
        },
        getIdempotencyKey(idempotencyScope, {
          ad_id: selectedAd.id,
          amount_usd: orderForm.amount_usd,
          expected_rate_bs_per_usd: selectedAd.rate_bs_per_usd
        })
      );
      clearIdempotencyKey(idempotencyScope);
      setSelectedOrder(data.order);
      rememberOrder(data.order);
      await openOrderChat(data.order.id);
      recordActionCompleted("client_order_create", "create-order", startedAt);
    } catch (error) {
      if (
        error instanceof ApiClientError
        && ["BUSINESS_CAPACITY_INSUFFICIENT", "BUSINESS_DAILY_LIMIT_EXCEEDED"].includes(error.code)
      ) {
        setSelectedAd(null);
        setView("marketplace-search");
        setNotice("Ese negocio ya no puede cubrir este monto. Elige otro negocio.");
        recordActionFailed("client_order_create", "create-order", startedAt, error.code);
        return;
      }
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
    setView(targetView);
    const cached = ordersCacheRef.current;
    if (cached && Date.now() - cached.loadedAt < CLIENT_ORDERS_CACHE_TTL_MS) {
      setMyOrders(cached.items);
      setNotice(cached.items.length ? "" : targetView === "messages" ? "Todavia no tienes conversaciones." : "Todavia no tienes ordenes.");
      recordActionCompleted("client_orders_load", screen, startedAt);
      setLoadingOrders(false);
      return;
    }
    if (cached) {
      setMyOrders(cached.items);
      setNotice(cached.items.length ? "" : targetView === "messages" ? "Todavia no tienes conversaciones." : "Todavia no tienes ordenes.");
      setLoadingOrders(false);
    } else {
      setLoadingOrders(true);
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

  async function refreshMyOrdersSilently() {
    try {
      const data = await listMyOrders<{ items: OrderSummary[] }>(request);
      ordersCacheRef.current = { items: data.items, loadedAt: Date.now() };
      setMyOrders(data.items);
    } catch {
      // The active chat remains authoritative; a background list refresh must not navigate or interrupt it.
    }
  }

  async function openOrderDetail(orderId: string) {
    const startedAt = actionStartedAt();
    recordActionStarted("client_order_detail_open", "order-summary");
    const optimisticOrder = ordersCacheRef.current?.items.find((order) => order.id === orderId);
    if (optimisticOrder) {
      setSelectedOrder(optimisticOrder);
      setSelectedRatingStars(optimisticOrder.rating?.stars || 0);
      setView("order-summary");
      setNotice("");
    } else {
      setOpeningOrderId(orderId);
    }
    try {
      const data = await getOrder<{ order: OrderSummary }>(request, orderId);
      setSelectedOrder(data.order);
      setSelectedRatingStars(data.order.rating?.stars || 0);
      rememberOrder(data.order);
      setView("order-summary");
      setNotice("");
      recordActionCompleted("client_order_detail_open", "order-summary", startedAt);
      return true;
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "No logramos abrir la orden.");
      recordActionFailed("client_order_detail_open", "order-summary", startedAt, error instanceof Error ? error.name : undefined);
      return false;
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

  async function cancelOrder(
    orderId: string,
    reason: OrderCancelReason,
    paymentNotSentConfirmed: boolean
  ): Promise<boolean> {
    const startedAt = actionStartedAt();
    recordActionStarted("client_order_cancel", "order-summary");
    setCancellingOrderId(orderId);
    const idempotencyScope = `order_cancel_${orderId}`;
    try {
      const data = await cancelRemitterOrder<{ order: OrderSummary }>(
        request,
        orderId,
        reason,
        paymentNotSentConfirmed,
        getIdempotencyKey(idempotencyScope, {
          orderId,
          reason,
          payment_not_sent_confirmed: paymentNotSentConfirmed
        })
      );
      clearIdempotencyKey(idempotencyScope);
      setSelectedOrder(data.order);
      rememberOrder(data.order);
      await searchFreshForAmount(data.order.amount_usd);
      recordActionCompleted("client_order_cancel", "order-summary", startedAt);
      return true;
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "No logramos cancelar la orden.");
      recordActionFailed("client_order_cancel", "order-summary", startedAt, error instanceof Error ? error.name : undefined);
      return false;
    } finally {
      setCancellingOrderId(null);
    }
  }

  async function submitRating(orderId: string, surface: "order-summary" | "order-chat" = "order-summary") {
    if (selectedRatingStars < 1 || selectedRatingStars > 5) {
      setNotice("Selecciona de 1 a 5 estrellas.");
      return;
    }
    const startedAt = actionStartedAt();
    recordActionStarted("client_order_rating_submit", surface);
    setSubmittingRatingOrderId(orderId);
    const idempotencyScope = `order_rating_${orderId}`;
    try {
      const data = await submitOrderRating<OrderRatingResult>(
        request,
        orderId,
        selectedRatingStars,
        getIdempotencyKey(idempotencyScope, { orderId, stars: selectedRatingStars })
      );
      clearIdempotencyKey(idempotencyScope);
      const updatedRating = { can_rate: false, already_rated: true, stars: data.rating.stars };
      setSelectedOrder((current) => {
        if (!current || current.id !== orderId) {
          return current;
        }
        return { ...current, rating: updatedRating };
      });
      setSelectedRatingStars(data.rating.stars);
      setNotice("Calificacion enviada.");
      recordActionCompleted("client_order_rating_submit", surface, startedAt);
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "No logramos enviar la calificacion.");
      recordActionFailed("client_order_rating_submit", surface, startedAt, error instanceof Error ? error.name : undefined);
    } finally {
      setSubmittingRatingOrderId(null);
    }
  }

  async function prefetchMyOrders() {
    const cached = ordersCacheRef.current;
    if (cached && Date.now() - cached.loadedAt < CLIENT_ORDERS_CACHE_TTL_MS) {
      return;
    }
    try {
      const data = await listMyOrders<{ items: OrderSummary[] }>(request);
      ordersCacheRef.current = { items: data.items, loadedAt: Date.now() };
    } catch {
      // Background warmup should never interrupt the active screen.
    }
  }

  return {
    cancelOrder,
    createOrder,
    extendOrder,
    loadMyOrders,
    openOrderDetail,
    prefetchMyOrders,
    refreshMyOrdersSilently,
    submitRating
  };
}
