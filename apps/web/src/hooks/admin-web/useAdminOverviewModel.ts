import type { AuthenticatedRequest } from "../../api/client";
import { useAdminDashboardMetricsModel } from "./useAdminDashboardMetricsModel";
import { useAdminEmergencyModeModel } from "./useAdminEmergencyModeModel";
import { useAdminIncidentModel } from "./useAdminIncidentModel";
import { useAdminJobsModel } from "./useAdminJobsModel";
import { useAdminUXFrictionModel } from "./useAdminUXFrictionModel";
import type { AdminOverviewView, QueueCriticalAction } from "./adminOverviewTypes";

export function useAdminOverviewModel({
  adminMutable,
  adminReadable,
  queueCriticalAction,
  reason,
  request,
  setBusy,
  setNotice,
  setReason,
  setView
}: {
  adminMutable: boolean;
  adminReadable: boolean;
  queueCriticalAction: QueueCriticalAction;
  reason: string;
  request: AuthenticatedRequest;
  setBusy: (busy: boolean) => void;
  setNotice: (notice: string) => void;
  setReason: (reason: string) => void;
  setView: (view: AdminOverviewView) => void;
}) {
  const dashboardMetrics = useAdminDashboardMetricsModel({
    adminReadable,
    request,
    setBusy,
    setNotice,
    setView
  });
  const emergencyMode = useAdminEmergencyModeModel({
    adminMutable,
    loadDashboard: dashboardMetrics.loadDashboard,
    queueCriticalAction,
    reason,
    request,
    setEmergencyMode: dashboardMetrics.setEmergencyMode,
    setNotice,
    setReason
  });
  const incidents = useAdminIncidentModel({
    adminReadable,
    request,
    setBusy,
    setNotice,
    setView
  });
  const uxFriction = useAdminUXFrictionModel({
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
    ...emergencyMode,
    ...incidents,
    ...uxFriction,
    ...jobs
  };
}

export type { AdminWebJobRun } from "./adminOverviewTypes";
