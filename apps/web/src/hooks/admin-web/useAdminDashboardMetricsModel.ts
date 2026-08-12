import { useCallback, useRef, useState } from "react";
import { getAdminDashboard, getAdminMetrics } from "../../api/admin";
import type { AuthenticatedRequest } from "../../api/client";
import type { AdminDashboard, AdminMetrics } from "../../types/admin";
import type { AdminOverviewView } from "./adminOverviewTypes";
import type { AdminPollingResultGuard } from "./useVisibleAdminPolling";

export function useAdminDashboardMetricsModel({
  adminReadable,
  clearNoticeIf,
  request,
  setBusy,
  setNotice,
  setView
}: {
  adminReadable: boolean;
  clearNoticeIf: (expected: string) => void;
  request: AuthenticatedRequest;
  setBusy: (busy: boolean) => void;
  setNotice: (notice: string) => void;
  setView: (view: AdminOverviewView) => void;
}) {
  const [dashboard, setDashboard] = useState<AdminDashboard | null>(null);
  const [metrics, setMetrics] = useState<AdminMetrics | null>(null);
  const refreshRequestEpoch = useRef(0);
  const foregroundDashboardRequests = useRef(0);
  const dashboardErrorRef = useRef("");

  const setEmergencyMode = useCallback((emergencyMode: AdminDashboard["emergency_mode"]) => {
    setDashboard((current) => current ? { ...current, emergency_mode: emergencyMode } : current);
  }, []);

  const loadDashboard = useCallback(async () => {
    if (!adminReadable) {
      setView("dashboard");
      setNotice("Acceso admin denegado por superficie.");
      return;
    }
    foregroundDashboardRequests.current += 1;
    const requestEpoch = ++refreshRequestEpoch.current;
    setBusy(true);
    try {
      const data = await getAdminDashboard<AdminDashboard>(request);
      const isLatest = requestEpoch === refreshRequestEpoch.current;
      if (!isLatest) {
        return;
      }
      if (dashboardErrorRef.current) {
        clearNoticeIf(dashboardErrorRef.current);
        dashboardErrorRef.current = "";
      }
      setDashboard(data);
      setView("dashboard");
      setNotice(data.disclaimer || "Dashboard admin cargado.");
    } catch (error) {
      if (requestEpoch !== refreshRequestEpoch.current) {
        return;
      }
      const message = error instanceof Error ? error.message : "No se pudo cargar dashboard admin.";
      dashboardErrorRef.current = message;
      setNotice(message);
    } finally {
      foregroundDashboardRequests.current = Math.max(0, foregroundDashboardRequests.current - 1);
      setBusy(false);
    }
  }, [adminReadable, clearNoticeIf, request, setBusy, setNotice, setView]);

  const refreshDashboardSnapshot = useCallback(async (shouldApply: AdminPollingResultGuard = () => true) => {
    if (!adminReadable || foregroundDashboardRequests.current > 0) {
      return;
    }
    const requestEpoch = ++refreshRequestEpoch.current;
    try {
      const data = await getAdminDashboard<AdminDashboard>(request);
      const isLatest = requestEpoch === refreshRequestEpoch.current;
      if (!isLatest || !shouldApply()) {
        return;
      }
      setDashboard(data);
      const staleError = dashboardErrorRef.current;
      if (staleError) {
        dashboardErrorRef.current = "";
        clearNoticeIf(staleError);
      }
    } catch {
      // Keep the last good snapshot; foreground actions still surface errors.
    }
  }, [adminReadable, clearNoticeIf, request]);

  const loadMetrics = useCallback(async () => {
    setBusy(true);
    try {
      const data = await getAdminMetrics<AdminMetrics>(request);
      setMetrics(data);
      setView("metrics");
      setNotice("Metricas calculadas desde tablas existentes.");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "No se pudo cargar metricas.");
    } finally {
      setBusy(false);
    }
  }, [request, setBusy, setNotice, setView]);

  return {
    dashboard,
    loadDashboard,
    loadMetrics,
    metrics,
    refreshDashboardSnapshot,
    setEmergencyMode
  };
}
