import { useCallback } from "react";
import { openAdminOrderDispute, resolveAdminDispute } from "../../api/admin";
import type { AuthenticatedRequest } from "../../api/client";
import { useStableIdempotencyKeys } from "../useStableIdempotencyKeys";
import { useAdminDisputesModel } from "./useAdminDisputesModel";
import { useAdminOrdersModel } from "./useAdminOrdersModel";
import type { OrdersDisputesView, QueueCriticalAction } from "./adminOrdersDisputesTypes";

const STUCK_ORDER_RESOLUTION_PREVIEWS = {
  cancelled: {
    label: "Cancelar por pago no comprobado",
    effect: "Libera el credito publicitario bloqueado y la capacidad reservada. No consume credito."
  },
  keep_under_review: {
    label: "Mantener en investigacion",
    effect: "Mantiene la investigacion sin mover credito, capacidad ni anuncio."
  },
  remitter_favored: {
    label: "Resolver a favor del cliente",
    effect: "Cancela la orden y consume el credito publicitario segun el contrato vigente."
  },
  business_favored: {
    label: "Resolver a favor del negocio",
    effect: "Completa la orden y consume el credito publicitario segun el contrato vigente."
  }
} as const;

type StuckOrderResolutionType = keyof typeof STUCK_ORDER_RESOLUTION_PREVIEWS;

function isStuckOrderResolutionType(value: string): value is StuckOrderResolutionType {
  return value in STUCK_ORDER_RESOLUTION_PREVIEWS;
}

export function useAdminOrdersDisputesModel({
  adminMutable,
  queueCriticalAction,
  reason,
  request,
  setBusy,
  setNotice,
  setReason,
  setView
}: {
  adminMutable: boolean;
  queueCriticalAction: QueueCriticalAction;
  reason: string;
  request: AuthenticatedRequest;
  setBusy: (busy: boolean) => void;
  setNotice: (notice: string) => void;
  setReason: (reason: string) => void;
  setView: (view: OrdersDisputesView) => void;
}) {
  const orders = useAdminOrdersModel({
    request,
    setBusy,
    setNotice,
    setView
  });
  const disputes = useAdminDisputesModel({
    adminMutable,
    queueCriticalAction,
    reason,
    request,
    setBusy,
    setNotice,
    setReason,
    setView
  });
  const { clearIdempotencyKey, getIdempotencyKey } = useStableIdempotencyKeys();

  const resolveAdminStuckOrder = useCallback(() => {
    const order = orders.selectedOrder?.order;
    if (!order || order.status !== "payment_rejected") {
      setNotice("La orden ya no esta disponible para esta resolucion.");
      return;
    }
    if (!adminMutable) {
      setNotice("Support es read-only y no puede resolver ordenes.");
      return;
    }
    if (!isStuckOrderResolutionType(disputes.resolutionType)) {
      setNotice("Selecciona una resolucion permitida para la orden.");
      return;
    }

    const resolutionType = disputes.resolutionType;
    const resolutionPresentation = STUCK_ORDER_RESOLUTION_PREVIEWS[resolutionType];
    const normalizedReason = reason.trim();
    const openScope = `admin_stuck_order_open:${order.id}`;
    const resolveScope = `admin_stuck_order_resolve:${order.id}:${resolutionType}`;
    const openKey = getIdempotencyKey(openScope, { reason: normalizedReason });
    const resolveKey = getIdempotencyKey(resolveScope, { reason: normalizedReason, resolutionType });

    queueCriticalAction(
      "Resolver orden",
      `Orden ${order.public_order_code}. Resultado: ${resolutionPresentation.label}. Efecto esperado: ${resolutionPresentation.effect}`,
      async () => {
        const opened = await openAdminOrderDispute(request, order.id, normalizedReason, openKey);
        try {
          await resolveAdminDispute(
            request,
            opened.dispute.id,
            resolutionType,
            normalizedReason,
            resolveKey
          );
        } catch (error) {
          // Opening is already durable. Move the operator to the existing dispute
          // surface so a failed second step never looks like an untouched order.
          await disputes.openDispute(opened.dispute.id);
          setNotice(
            error instanceof Error
              ? `La investigacion se abrio, pero falta completar la resolucion: ${error.message}`
              : "La investigacion se abrio, pero falta completar la resolucion."
          );
          return;
        }
        clearIdempotencyKey(openScope);
        clearIdempotencyKey(resolveScope);
        setReason("");
        await orders.openOrder(order.id);
        setNotice("Orden resuelta y detalle actualizado.");
      },
      { requiresReason: true }
    );
  }, [
    adminMutable,
    clearIdempotencyKey,
    disputes,
    getIdempotencyKey,
    orders,
    queueCriticalAction,
    reason,
    request,
    setNotice,
    setReason
  ]);

  return {
    ...orders,
    ...disputes,
    resolveAdminStuckOrder,
    stuckOrderResolutionPreview: isStuckOrderResolutionType(disputes.resolutionType)
      ? `${STUCK_ORDER_RESOLUTION_PREVIEWS[disputes.resolutionType].label}. ${STUCK_ORDER_RESOLUTION_PREVIEWS[disputes.resolutionType].effect}`
      : ""
  };
}

export type {
  AdminDisputeDetailResponse as AdminWebDisputeDetail,
  AdminOrderDetailResponse as AdminWebOrderDetail
} from "../../types/admin";
