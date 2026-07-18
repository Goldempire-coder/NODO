import { useCallback, useState } from "react";
import { getAdminIncidentConsole } from "../../api/admin";
import type { AuthenticatedRequest } from "../../api/client";
import type { AdminIncidentConsole } from "../../types/admin";
import type { AdminOverviewView } from "./adminOverviewTypes";

export function useAdminIncidentModel({
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
  const [incidentConsole, setIncidentConsole] = useState<AdminIncidentConsole | null>(null);

  const loadIncidentConsole = useCallback(async () => {
    if (!adminReadable) {
      setView("incidents");
      setNotice("Acceso admin denegado por superficie.");
      return;
    }
    setBusy(true);
    try {
      const data = await getAdminIncidentConsole<AdminIncidentConsole>(request);
      setIncidentConsole(data);
      setView("incidents");
      setNotice(data.status === "healthy" ? "NODO sin incidentes visibles." : "Centro de incidentes cargado.");
    } catch (error) {
      setIncidentConsole(null);
      setNotice(error instanceof Error ? error.message : "No se pudo cargar el centro de incidentes.");
    } finally {
      setBusy(false);
    }
  }, [adminReadable, request, setBusy, setNotice, setView]);

  return {
    incidentConsole,
    loadIncidentConsole
  };
}
