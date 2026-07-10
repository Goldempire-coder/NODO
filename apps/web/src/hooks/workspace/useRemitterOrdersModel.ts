"use client";

import { useRef } from "react";
import type { AuthenticatedRequest } from "../../api/client";
import { cancelRemitterOrder, createRemitterOrder, extendPaymentDeadline, getOrder, listMyOrders } from "../../api/orders";
import type { OrderSummary } from "../../types/orders";
import type { ClientWorkspaceState } from "./useClientWorkspaceState";

type RemitterOrdersState = Pick<
  ClientWorkspaceState,
  | "selectedAd"
  | "orderForm"
  | "setSelectedOrder"
  | "setMyOrders"
  | "setNotice"
  | "setBusy"
  | "setView"
>;

export function useRemitterOrdersModel(state: RemitterOrdersState & { request: AuthenticatedRequest }) {
  const { request, selectedAd, orderForm, setSelectedOrder, setMyOrders, setNotice, setBusy, setView } = state;
  const ordersCacheRef = useRef<{ items: OrderSummary[]; loadedAt: number } | null>(null);

  async function createOrder() {
    if (!selectedAd) {
      setNotice("Selecciona un anuncio activo.");
      return;
    }
    setBusy(true);
    setNotice("Preparando tu orden");
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
        `order_create_${selectedAd.id}_${Date.now()}`
      );
      setSelectedOrder(data.order);
      setView("order-summary");
      setNotice("");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "No logramos crear la orden. Revisa los datos e intenta de nuevo.");
    } finally {
      setBusy(false);
    }
  }

  async function loadMyOrders(targetView: "my-orders" | "messages" = "my-orders") {
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
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "No logramos cargar tus ordenes.");
    }
  }

  async function openOrderDetail(orderId: string) {
    const optimisticOrder = ordersCacheRef.current?.items.find((order) => order.id === orderId);
    if (optimisticOrder) {
      setSelectedOrder(optimisticOrder);
      setView("order-summary");
      setNotice("");
    } else {
      setBusy(true);
    }
    try {
      const data = await getOrder<{ order: OrderSummary }>(request, orderId);
      setSelectedOrder(data.order);
      setView("order-summary");
      setNotice("");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "No logramos abrir la orden.");
    } finally {
      if (!optimisticOrder) {
        setBusy(false);
      }
    }
  }

  async function extendOrder(orderId: string) {
    setBusy(true);
    try {
      const data = await extendPaymentDeadline<{ order: OrderSummary }>(request, orderId, "Necesito unos minutos mas", `order_extend_${orderId}_${Date.now()}`);
      setSelectedOrder(data.order);
      setNotice("Tiempo extendido una vez.");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "No logramos extender el tiempo.");
    } finally {
      setBusy(false);
    }
  }

  async function cancelOrder(orderId: string) {
    setBusy(true);
    try {
      const data = await cancelRemitterOrder<{ order: OrderSummary }>(request, orderId, "No pude realizar el pago", `order_cancel_${orderId}_${Date.now()}`);
      setSelectedOrder(data.order);
      setNotice("Orden cancelada.");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "No logramos cancelar la orden.");
    } finally {
      setBusy(false);
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
