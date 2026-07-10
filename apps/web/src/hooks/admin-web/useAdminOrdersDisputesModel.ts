import type { AuthenticatedRequest } from "../../api/client";
import { useAdminDisputesModel } from "./useAdminDisputesModel";
import { useAdminOrdersModel } from "./useAdminOrdersModel";
import type { OrdersDisputesView, QueueCriticalAction } from "./adminOrdersDisputesTypes";

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

  return {
    ...orders,
    ...disputes
  };
}

export type { AdminWebDisputeDetail, AdminWebOrderDetail } from "./adminOrdersDisputesTypes";
