import { useCallback, useState } from "react";
import type { AuthenticatedRequest } from "../../api/client";
import { getBusinessOrder, listBusinessOrders, mutateBusinessOrder as mutateBusinessOrderRequest } from "../../api/businessOrders";
import type { BusinessMiniAppView } from "../../constants/businessViews";
import type { BusinessOrderDetail, BusinessOrderSummary } from "../../types/orders";
import { idempotencyKey } from "./helpers";

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

  const loadBusinessOrders = useCallback(async (status?: string) => {
    setBusy(true);
    try {
      const data = await listBusinessOrders<{ items: BusinessOrderSummary[] }>(request, status);
      setBusinessOrders(data.items);
      setBusinessOrderDetail(null);
      setView("business-orders");
      setNotice(data.items.length ? "Ordenes del negocio cargadas." : "No hay ordenes entrantes por ahora.");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "No logramos cargar las ordenes del negocio.");
    } finally {
      setBusy(false);
    }
  }, [request, setBusy, setNotice, setView]);

  const openBusinessOrder = useCallback(async (orderId: string) => {
    setBusy(true);
    try {
      const data = await getBusinessOrder<BusinessOrderDetail>(request, orderId);
      setBusinessOrderDetail(data);
      setBusinessOrderReason("");
      setView("business-order-detail");
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
    setBusy(true);
    try {
      await mutateBusinessOrderRequest(request, businessOrderDetail.order.id, action, businessOrderReason || undefined, idempotencyKey(`business_order_${action}_${businessOrderDetail.order.id}`));
      setNotice(action === "confirm-payment" ? "Pago confirmado. Se consumieron los creditos del anuncio." : action === "mark-delivered" ? "Pago movil marcado como enviado." : "Reporte rechazado y enviado a revision.");
      await openBusinessOrder(businessOrderDetail.order.id);
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "No pudimos operar la orden.");
    } finally {
      setBusy(false);
    }
  }, [businessOrderDetail, businessOrderReason, openBusinessOrder, request, setBusy, setNotice]);

  return {
    businessOrderDetail,
    businessOrderReason,
    businessOrders,
    loadBusinessOrders,
    mutateBusinessOrder,
    openBusinessOrder,
    setBusinessOrderReason
  };
}
