import type { AuthenticatedRequest } from "../../api/client";
import { useAdminDashboardMetricsModel } from "./useAdminDashboardMetricsModel";
import { useAdminJobsModel } from "./useAdminJobsModel";
import type { AdminOverviewView, QueueCriticalAction } from "./adminOverviewTypes";

export function useAdminOverviewModel({
  adminMutable,
  adminReadable,
  queueCriticalAction,
  request,
  setBusy,
  setNotice,
  setView
}: {
  adminMutable: boolean;
  adminReadable: boolean;
  queueCriticalAction: QueueCriticalAction;
  request: AuthenticatedRequest;
  setBusy: (busy: boolean) => void;
  setNotice: (notice: string) => void;
  setView: (view: AdminOverviewView) => void;
}) {
  const dashboardMetrics = useAdminDashboardMetricsModel({
    adminReadable,
    request,
    setBusy,
    setNotice,
    setView
  });
  const jobs = useAdminJobsModel({
    adminMutable,
    queueCriticalAction,
    request,
    setBusy,
    setNotice,
    setView
  });

  return {
    ...dashboardMetrics,
    ...jobs
  };
}

export type { AdminWebJobRun } from "./adminOverviewTypes";
