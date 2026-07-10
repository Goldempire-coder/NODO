import { useCallback, useState } from "react";
import { dryRunExpireAndEscalateOrders, listAdminJobRuns } from "../../api/admin";
import type { AuthenticatedRequest } from "../../api/client";
import { idempotencyKey } from "./helpers";
import type { AdminOverviewView, AdminWebJobRun, ListResponse, QueueCriticalAction } from "./adminOverviewTypes";

export function useAdminJobsModel({
  adminMutable,
  queueCriticalAction,
  request,
  setBusy,
  setNotice,
  setView
}: {
  adminMutable: boolean;
  queueCriticalAction: QueueCriticalAction;
  request: AuthenticatedRequest;
  setBusy: (busy: boolean) => void;
  setNotice: (notice: string) => void;
  setView: (view: AdminOverviewView) => void;
}) {
  const [jobRuns, setJobRuns] = useState<AdminWebJobRun[]>([]);

  const loadJobs = useCallback(async () => {
    setBusy(true);
    try {
      const data = await listAdminJobRuns<ListResponse<AdminWebJobRun>>(request);
      setJobRuns(data.items);
      setView("jobs");
      setNotice(data.items.length ? "Job runs cargados." : "No hay job runs.");
    } catch (error) {
      setJobRuns([]);
      setNotice(error instanceof Error ? error.message : "No se pudo cargar jobs.");
    } finally {
      setBusy(false);
    }
  }, [request, setBusy, setNotice, setView]);

  const dryRunJobs = useCallback(() => {
    if (!adminMutable) {
      setNotice("Support no puede ejecutar dry-run.");
      return;
    }
    queueCriticalAction("Dry-run expire/escalate", "Dry-run no muta ordenes, anuncios, creditos, disputas ni notificaciones.", async () => {
      await dryRunExpireAndEscalateOrders(request, idempotencyKey("jobs_dry_run"));
      setNotice("Dry-run solicitado.");
      await loadJobs();
    });
  }, [adminMutable, loadJobs, queueCriticalAction, request, setNotice]);

  return {
    dryRunJobs,
    jobRuns,
    loadJobs
  };
}
