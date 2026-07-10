import type { AuthenticatedRequest } from "../../api/client";
import { useAdminBusinessesModel } from "./useAdminBusinessesModel";
import { useAdminBusinessIntakesModel } from "./useAdminBusinessIntakesModel";
import type { BusinessIntakeView, QueueCriticalAction } from "./adminBusinessIntakeTypes";

export function useAdminBusinessIntakeModel({
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
  setView: (view: BusinessIntakeView) => void;
}) {
  const businessAdmin = useAdminBusinessesModel({
    adminMutable,
    queueCriticalAction,
    reason,
    request,
    setBusy,
    setNotice,
    setReason,
    setView
  });
  const intakeAdmin = useAdminBusinessIntakesModel({
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
    ...businessAdmin,
    ...intakeAdmin
  };
}

export type {
  AdminBusinessIntakeDetail,
  AdminBusinessIntakeSummary,
  BusinessSummaryForAdmin
} from "./adminBusinessIntakeTypes";
