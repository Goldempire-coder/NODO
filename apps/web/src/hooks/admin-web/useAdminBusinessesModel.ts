import { useCallback, useState } from "react";
import {
  createAdminBusinessAccessLink,
  getAdminBusiness,
  getAdminBusinessDocumentViewUrl,
  listAdminBusinessAccessLinks,
  listAdminBusinesses,
  listPendingAdminBusinesses,
  reviewAdminBusiness,
  updateAdminBusinessCapacity,
  updateAdminBusinessAccessLink
} from "../../api/admin";
import type { AuthenticatedRequest } from "../../api/client";
import type { AdminBusinessAccessLink, AdminBusinessDetail } from "../../types/admin";
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
  const [businessAccessLinks, setBusinessAccessLinks] = useState<AdminBusinessAccessLink[]>([]);
  const [businessFilter, setBusinessFilter] = useState("pending");
  const [businessCapacityDraft, setBusinessCapacityDraft] = useState({
    trust_level: "new",
    min_order_amount_usd: "20.00",
    max_order_amount_usd: "100.00",
    daily_limit_usd: "1000.00",
    active_order_limit: 1
  });

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
      const [data, links] = await Promise.all([
        getAdminBusiness<AdminBusinessDetail>(request, businessId),
        listAdminBusinessAccessLinks<{ items: AdminBusinessAccessLink[] }>(request, businessId)
      ]);
      setSelectedBusiness(data);
      setBusinessCapacityDraft({
        trust_level: data.business.trust_level || "new",
        min_order_amount_usd: data.business.min_order_amount_usd || "20.00",
        max_order_amount_usd: data.business.max_order_amount_usd || "100.00",
        daily_limit_usd: data.business.daily_limit_usd || "1000.00",
        active_order_limit: data.business.active_order_limit || 1
      });
      setBusinessAccessLinks(links.items);
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

  const changeBusinessStatus = useCallback((action: "suspend" | "reactivate" | "block") => {
    if (!selectedBusiness || !adminMutable) {
      setNotice("Accion no permitida para este rol.");
      return;
    }
    const labels = {
      suspend: "Suspender negocio",
      reactivate: "Reactivar negocio",
      block: "Bloquear negocio"
    };
    queueCriticalAction(
      labels[action],
      "Cambia el estado del negocio completo. Backend valida estado, reason, idempotencia, audit y acceso a Mini App Negocio.",
      async () => {
        await reviewAdminBusiness(request, selectedBusiness.business.id, action, reason, idempotencyKey(`business_status_${action}`));
        setReason("");
        setNotice("Estado del negocio actualizado.");
        await openBusiness(selectedBusiness.business.id);
      }
    );
  }, [adminMutable, openBusiness, queueCriticalAction, reason, request, selectedBusiness, setNotice, setReason]);

  const submitBusinessCapacity = useCallback(() => {
    if (!selectedBusiness || !adminMutable) {
      setNotice("Accion no permitida para este rol.");
      return;
    }
    queueCriticalAction(
      "Actualizar capacidad",
      "Ajusta minimo, maximo, limite diario y ordenes activas. Backend valida rango, reason, idempotencia y audit log.",
      async () => {
        await updateAdminBusinessCapacity(
          request,
          selectedBusiness.business.id,
          { ...businessCapacityDraft, reason },
          idempotencyKey("business_capacity")
        );
        setReason("");
        setNotice("Capacidad del negocio actualizada.");
        await openBusiness(selectedBusiness.business.id);
      }
    );
  }, [adminMutable, businessCapacityDraft, openBusiness, queueCriticalAction, reason, request, selectedBusiness, setNotice, setReason]);

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

  const createBusinessOwnerAccessLink = useCallback(() => {
    if (!selectedBusiness || !adminMutable) {
      setNotice("Accion no permitida para este rol.");
      return;
    }
    const ownerUserId = selectedBusiness.business.owner_user_id;
    if (!ownerUserId) {
      setNotice("Este negocio no tiene owner_user_id para crear link.");
      return;
    }
    queueCriticalAction("Crear acceso negocio", "Vincula el owner del negocio a la Mini App Negocio. Backend valida RBAC, reason e idempotencia.", async () => {
      await createAdminBusinessAccessLink(
        request,
        selectedBusiness.business.id,
        { user_id: ownerUserId, role_in_business: "owner", reason },
        idempotencyKey("business_access_link_create")
      );
      setReason("");
      setNotice("Acceso de negocio creado.");
      await openBusiness(selectedBusiness.business.id);
    });
  }, [adminMutable, openBusiness, queueCriticalAction, reason, request, selectedBusiness, setNotice, setReason]);

  const changeBusinessAccessLink = useCallback((linkId: string, action: "suspend" | "reactivate" | "revoke" | "block") => {
    if (!selectedBusiness || !adminMutable) {
      setNotice("Accion no permitida para este rol.");
      return;
    }
    queueCriticalAction(
      `${action} acceso negocio`,
      "Cambia el acceso del negocio sin borrar historial. Backend valida estado, reason, idempotencia y audit.",
      async () => {
        await updateAdminBusinessAccessLink(
          request,
          selectedBusiness.business.id,
          linkId,
          action,
          reason,
          idempotencyKey(`business_access_link_${action}`)
        );
        setReason("");
        setNotice("Acceso de negocio actualizado.");
        await openBusiness(selectedBusiness.business.id);
      }
    );
  }, [adminMutable, openBusiness, queueCriticalAction, reason, request, selectedBusiness, setNotice, setReason]);

  return {
    businessAccessLinks,
    businessCapacityDraft,
    businesses,
    businessFilter,
    changeBusinessAccessLink,
    changeBusinessStatus,
    createBusinessOwnerAccessLink,
    loadBusinesses,
    loadPendingBusinesses,
    openBusiness,
    openDocument,
    reviewBusiness,
    selectedBusiness,
    setBusinessCapacityDraft,
    setBusinessFilter,
    submitBusinessCapacity
  };
}
