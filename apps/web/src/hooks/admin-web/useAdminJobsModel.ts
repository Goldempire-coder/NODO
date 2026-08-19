import { useCallback, useRef, useState } from "react";
import { dryRunExpireAndEscalateOrders, listAdminJobRuns } from "../../api/admin";
import type { AuthenticatedRequest } from "../../api/client";
import { appendUniqueById } from "../pagination";
import { idempotencyKey } from "./helpers";
import type { AdminOverviewView, AdminWebJobRun, QueueCriticalAction } from "./adminOverviewTypes";

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
  const [jobRunsNextCursor, setJobRunsNextCursor] = useState<string | null>(null);
  const [jobRunsLoadingMore, setJobRunsLoadingMore] = useState(false);
  const jobRunsRequestEpoch = useRef(0);

  const loadJobs = useCallback(async () => {
    const requestEpoch = ++jobRunsRequestEpoch.current;
    setJobRunsLoadingMore(false);
    setBusy(true);
    try {
      const data = await listAdminJobRuns(request);
      if (requestEpoch !== jobRunsRequestEpoch.current) {
        return;
      }
      setJobRuns(data.items);
      setJobRunsNextCursor(data.next_cursor);
      setView("jobs");
      setNotice(data.items.length ? "Job runs cargados." : "No hay job runs.");
    } catch (error) {
      if (requestEpoch === jobRunsRequestEpoch.current) {
        setJobRuns([]);
        setJobRunsNextCursor(null);
        setNotice(error instanceof Error ? error.message : "No se pudo cargar jobs.");
      }
    } finally {
      if (requestEpoch === jobRunsRequestEpoch.current) {
        setBusy(false);
      }
    }
  }, [request, setBusy, setNotice, setView]);

  const loadMoreJobs = useCallback(async () => {
    const cursor = jobRunsNextCursor;
    if (!cursor || jobRunsLoadingMore) {
      return;
    }
    const requestEpoch = ++jobRunsRequestEpoch.current;
    setJobRunsLoadingMore(true);
    try {
      const data = await listAdminJobRuns(request, cursor);
      if (requestEpoch !== jobRunsRequestEpoch.current) {
        return;
      }
      setJobRuns((current) => appendUniqueById(current, data.items));
      setJobRunsNextCursor(data.next_cursor);
    } catch (error) {
      if (requestEpoch === jobRunsRequestEpoch.current) {
        setNotice(error instanceof Error ? error.message : "No se pudieron cargar mas jobs.");
      }
    } finally {
      if (requestEpoch === jobRunsRequestEpoch.current) {
        setJobRunsLoadingMore(false);
      }
    }
  }, [jobRunsLoadingMore, jobRunsNextCursor, request, setNotice]);

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
    jobRunsLoadingMore,
    jobRunsNextCursor,
    loadJobs,
    loadMoreJobs
  };
}
