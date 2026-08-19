import { useCallback, useRef, useState } from "react";
import { listAdminAuditLogs } from "../../api/admin";
import type { AuthenticatedRequest } from "../../api/client";
import type { AdminAuditLog } from "../../types/admin";
import { appendUniqueById } from "../pagination";

type AuditLogsView = "audit-logs";

export function useAdminAuditLogsModel({
  request,
  setBusy,
  setNotice,
  setView
}: {
  request: AuthenticatedRequest;
  setBusy: (busy: boolean) => void;
  setNotice: (notice: string) => void;
  setView: (view: AuditLogsView) => void;
}) {
  const [auditLogs, setAuditLogs] = useState<AdminAuditLog[]>([]);
  const [auditLogsNextCursor, setAuditLogsNextCursor] = useState<string | null>(null);
  const [auditLogsLoadingMore, setAuditLogsLoadingMore] = useState(false);
  const [auditFilter, setAuditFilter] = useState("");
  const auditLogsRequestEpoch = useRef(0);
  const auditLogsQueryRef = useRef("");

  const loadAuditLogs = useCallback(async () => {
    const requestEpoch = ++auditLogsRequestEpoch.current;
    setAuditLogsLoadingMore(false);
    setBusy(true);
    try {
      const data = await listAdminAuditLogs(request, auditFilter);
      if (requestEpoch !== auditLogsRequestEpoch.current) {
        return;
      }
      setAuditLogs(data.items);
      setAuditLogsNextCursor(data.next_cursor);
      auditLogsQueryRef.current = auditFilter;
      setView("audit-logs");
      setNotice(data.items.length ? "Audit logs cargados con masking." : "No hay audit logs para ese filtro.");
    } catch (error) {
      if (requestEpoch === auditLogsRequestEpoch.current) {
        setAuditLogs([]);
        setAuditLogsNextCursor(null);
        setNotice(error instanceof Error ? error.message : "No se pudo cargar audit logs.");
      }
    } finally {
      if (requestEpoch === auditLogsRequestEpoch.current) {
        setBusy(false);
      }
    }
  }, [auditFilter, request, setBusy, setNotice, setView]);

  const loadMoreAuditLogs = useCallback(async () => {
    const cursor = auditLogsNextCursor;
    if (!cursor || auditLogsLoadingMore) {
      return;
    }
    const requestEpoch = ++auditLogsRequestEpoch.current;
    const requestedFilter = auditLogsQueryRef.current;
    setAuditLogsLoadingMore(true);
    try {
      const data = await listAdminAuditLogs(request, requestedFilter, cursor);
      if (requestEpoch !== auditLogsRequestEpoch.current) {
        return;
      }
      setAuditLogs((current) => appendUniqueById(current, data.items));
      setAuditLogsNextCursor(data.next_cursor);
    } catch (error) {
      if (requestEpoch === auditLogsRequestEpoch.current) {
        setNotice(error instanceof Error ? error.message : "No se pudieron cargar mas audit logs.");
      }
    } finally {
      if (requestEpoch === auditLogsRequestEpoch.current) {
        setAuditLogsLoadingMore(false);
      }
    }
  }, [auditLogsLoadingMore, auditLogsNextCursor, request, setNotice]);

  return {
    auditLogs,
    auditLogsLoadingMore,
    auditLogsNextCursor,
    auditFilter,
    loadAuditLogs,
    loadMoreAuditLogs,
    setAuditFilter
  };
}
