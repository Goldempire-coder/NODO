import { useCallback, useState } from "react";
import { getAdminUXFriction } from "../../api/admin";
import type { AdminUXFriction } from "../../types/admin";
import type { AdminOverviewView } from "./adminOverviewTypes";

export function useAdminUXFrictionModel({
  adminReadable,
  request,
  setBusy,
  setNotice,
  setView
}: {
  adminReadable: boolean;
  request: <T = unknown>(path: string, options?: RequestInit) => Promise<T>;
  setBusy: (busy: boolean) => void;
  setNotice: (notice: string) => void;
  setView: (view: AdminOverviewView) => void;
}) {
  const [uxFriction, setUXFriction] = useState<AdminUXFriction | null>(null);

  const loadUXFriction = useCallback(async () => {
    if (!adminReadable) {
      setView("ux-friction");
      setNotice("Acceso admin denegado por superficie.");
      return;
    }
    setBusy(true);
    try {
      const data = await getAdminUXFriction<AdminUXFriction>(request);
      setUXFriction(data);
      setView("ux-friction");
      setNotice(data.total_events ? "Friccion UX cargada." : "No hay eventos UX para el periodo.");
    } catch (error) {
      setUXFriction(null);
      setNotice(error instanceof Error ? error.message : "No se pudo cargar friccion UX.");
    } finally {
      setBusy(false);
    }
  }, [adminReadable, request, setBusy, setNotice, setView]);

  return {
    uxFriction,
    loadUXFriction
  };
}
