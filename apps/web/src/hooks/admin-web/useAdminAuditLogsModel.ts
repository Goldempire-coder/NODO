import { useCallback, useState } from "react";
import { listAdminAuditLogs } from "../../api/admin";
import type { AuthenticatedRequest } from "../../api/client";
import type { AdminAuditLog } from "../../types/admin";

type AuditLogsView = "audit-logs";

type ListResponse<T> = {
  items: T[];
  next_cursor: string | null;
  disclaimer?: string;
};

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
  const [auditFilter, setAuditFilter] = useState("");

  const loadAuditLogs = useCallback(async () => {
    setBusy(true);
    try {
      const data = await listAdminAuditLogs<ListResponse<AdminAuditLog>>(request, auditFilter);
      setAuditLogs(data.items);
      setView("audit-logs");
      setNotice(data.items.length ? "Audit logs cargados con masking." : "No hay audit logs para ese filtro.");
    } catch (error) {
      setAuditLogs([]);
      setNotice(error instanceof Error ? error.message : "No se pudo cargar audit logs.");
    } finally {
      setBusy(false);
    }
  }, [auditFilter, request, setBusy, setNotice, setView]);

  return {
    auditLogs,
    auditFilter,
    setAuditFilter,
    loadAuditLogs
  };
}
