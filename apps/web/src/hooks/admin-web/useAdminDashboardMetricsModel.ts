import { useCallback, useState } from "react";
import { getAdminDashboard, getAdminMetrics } from "../../api/admin";
import type { AuthenticatedRequest } from "../../api/client";
import type { AdminDashboard, AdminMetrics } from "../../types/admin";
import type { AdminOverviewView } from "./adminOverviewTypes";

export function useAdminDashboardMetricsModel({
  adminReadable,
  request,
  setBusy,
  setNotice,
  setView
}: {
  adminReadable: boolean;
  request: AuthenticatedRequest;
  setBusy: (busy: boolean) => void;
  setNotice: (notice: string) => void;
  setView: (view: AdminOverviewView) => void;
}) {
  const [dashboard, setDashboard] = useState<AdminDashboard | null>(null);
  const [metrics, setMetrics] = useState<AdminMetrics | null>(null);

  const setEmergencyMode = useCallback((emergencyMode: AdminDashboard["emergency_mode"]) => {
    setDashboard((current) => current ? { ...current, emergency_mode: emergencyMode } : current);
  }, []);

  const loadDashboard = useCallback(async () => {
    if (!adminReadable) {
      setView("dashboard");
      setNotice("Acceso admin denegado por superficie.");
      return;
    }
    setBusy(true);
    try {
      const data = await getAdminDashboard<AdminDashboard>(request);
      setDashboard(data);
      setView("dashboard");
      setNotice(data.disclaimer || "Dashboard admin cargado.");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "No se pudo cargar dashboard admin.");
    } finally {
      setBusy(false);
    }
  }, [adminReadable, request, setBusy, setNotice, setView]);

  const refreshDashboardSnapshot = useCallback(async () => {
    if (!adminReadable) {
      return;
    }
    try {
      const data = await getAdminDashboard<AdminDashboard>(request);
      setDashboard(data);
    } catch {
      // Keep the last good snapshot; foreground actions still surface errors.
    }
  }, [adminReadable, request]);

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
