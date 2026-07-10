import { useCallback, useState } from "react";
import {
  getAdminBusiness,
  getAdminBusinessDocumentViewUrl,
  listAdminBusinesses,
  listPendingAdminBusinesses,
  reviewAdminBusiness
} from "../../api/admin";
import type { AuthenticatedRequest } from "../../api/client";
import type { AdminBusinessDetail } from "../../types/admin";
import { idempotencyKey } from "./helpers";
import type { BusinessIntakeView, BusinessSummaryForAdmin, ListResponse, QueueCriticalAction } from "./adminBusinessIntakeTypes";

export function useAdminBusinessesModel({
  adminMutable,
  queueCriticalAction,
  reason,
  request,
  setBusy,
  setNotice,
  setReason,
  setView
}: {
  adminMutable: boolean;
  queueCriticalAction: QueueCriticalAction;
  reason: string;
  request: AuthenticatedRequest;
  setBusy: (busy: boolean) => void;
  setNotice: (notice: string) => void;
  setReason: (reason: string) => void;
  setView: (view: BusinessIntakeView) => void;
}) {
  const [businesses, setBusinesses] = useState<BusinessSummaryForAdmin[]>([]);
  const [selectedBusiness, setSelectedBusiness] = useState<AdminBusinessDetail | null>(null);
  const [businessFilter, setBusinessFilter] = useState("pending");

  const loadBusinesses = useCallback(async (status = businessFilter) => {
    setBusy(true);
    try {
      const data = await listAdminBusinesses<ListResponse<BusinessSummaryForAdmin>>(request, status);
      setBusinesses(data.items);
      setView("businesses");
      setBusinessFilter(status);
      setNotice(data.items.length ? "Negocios cargados." : "No hay negocios para ese filtro.");
    } catch (error) {
      setBusinesses([]);
      setNotice(error instanceof Error ? error.message : "No se pudo cargar negocios.");
    } finally {
      setBusy(false);
    }
  }, [businessFilter, request, setBusy, setNotice, setView]);

  const loadPendingBusinesses = useCallback(async () => {
    setBusy(true);
    try {
      const data = await listPendingAdminBusinesses<ListResponse<BusinessSummaryForAdmin>>(request);
      setBusinesses(data.items);
      setView("businesses");
      setBusinessFilter("pending");
      setNotice(data.items.length ? "Negocios pendientes cargados." : "No hay negocios pendientes.");
    } catch (error) {
      setBusinesses([]);
      setNotice(error instanceof Error ? error.message : "No se pudo cargar negocios pendientes.");
    } finally {
      setBusy(false);
    }
  }, [request, setBusy, setNotice, setView]);

  const openBusiness = useCallback(async (businessId: string) => {
    setBusy(true);
    try {
      const data = await getAdminBusiness<AdminBusinessDetail>(request, businessId);
      setSelectedBusiness(data);
      setView("business-detail");
      setNotice("Detalle de negocio cargado.");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "No se pudo cargar detalle de negocio.");
    } finally {
      setBusy(false);
    }
  }, [request, setBusy, setNotice, setView]);

  const reviewBusiness = useCallback((action: "approve" | "reject") => {
    if (!selectedBusiness || !adminMutable) {
      setNotice("Accion no permitida para este rol.");
      return;
    }
    queueCriticalAction(
      action === "approve" ? "Aprobar negocio" : "Rechazar negocio",
      "Esta accion requiere reason, idempotencia, backend RBAC y audit log.",
      async () => {
        await reviewAdminBusiness(request, selectedBusiness.business.id, action, reason, idempotencyKey(`business_${action}`));
        setReason("");
        setNotice(action === "approve" ? "Negocio aprobado." : "Negocio rechazado.");
        await loadPendingBusinesses();
      }
    );
  }, [adminMutable, loadPendingBusinesses, queueCriticalAction, reason, request, selectedBusiness, setNotice, setReason]);

  const openDocument = useCallback((fileId: string) => {
    if (!selectedBusiness || !adminMutable) {
      setNotice("Solo admin/super_admin puede solicitar URL privada.");
      return;
    }
    queueCriticalAction("Abrir documento privado", "La URL corta no se persiste y la apertura queda auditada.", async () => {
      const data = await getAdminBusinessDocumentViewUrl<{ url: string; expires_in: number }>(request, selectedBusiness.business.id, fileId, reason);
      window.open(data.url, "_blank", "noopener,noreferrer");
      setReason("");
      setNotice(`URL privada generada por ${data.expires_in}s.`);
    });
  }, [adminMutable, queueCriticalAction, reason, request, selectedBusiness, setNotice, setReason]);

  return {
    businesses,
    businessFilter,
    loadBusinesses,
    loadPendingBusinesses,
    openBusiness,
    openDocument,
    reviewBusiness,
    selectedBusiness,
    setBusinessFilter
  };
}
