import type { AuthenticatedRequest } from "../../api/client";
import { useAdminCreditAdjustmentsModel } from "./useAdminCreditAdjustmentsModel";
import { useAdminCreditPurchasesModel } from "./useAdminCreditPurchasesModel";
import { useAdminCreditTransactionsModel } from "./useAdminCreditTransactionsModel";
import type { CreditsView, QueueCriticalAction } from "./adminCreditsTypes";

export function useAdminCreditsModel({
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
  setView: (view: CreditsView) => void;
}) {
  const purchases = useAdminCreditPurchasesModel({
    adminMutable,
    queueCriticalAction,
    reason,
    request,
    setBusy,
    setNotice,
    setReason,
    setView
  });
  const adjustments = useAdminCreditAdjustmentsModel({
    adminMutable,
    queueCriticalAction,
    reason,
    request,
    setNotice,
    setReason
  });
  const transactions = useAdminCreditTransactionsModel({
    request,
    setBusy,
    setNotice,
    setView
  });

  return {
    ...purchases,
    ...adjustments,
    ...transactions
  };
}
