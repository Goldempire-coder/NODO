import { useCallback, useRef, useState } from "react";
import {
  createAdminBusinessAccessLink,
  getAdminBusiness,
  getAdminBusinessOperationalCapacity,
  getAdminBusinessDocumentViewUrl,
  listAdminBusinessAccessLinks,
  listAdminBusinesses,
  updateAdminBusinessCapacity,
  updateAdminBusinessOperationalCapacity,
  updateAdminBusinessAccessLink,
  updateAdminBusinessStatus
} from "../../api/admin";
import type { AuthenticatedRequest } from "../../api/client";
import type {
  AdminBusinessAccessLink,
  AdminBusinessDetail,
  AdminBusinessOperationalCapacity
} from "../../types/admin";
import { idempotencyKey } from "./helpers";
import { appendUniqueById } from "../pagination";
import type { BusinessIntakeView, BusinessSummaryForAdmin, QueueCriticalAction } from "./adminBusinessIntakeTypes";

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
  const [businessesNextCursor, setBusinessesNextCursor] = useState<string | null>(null);
  const [businessesLoadingMore, setBusinessesLoadingMore] = useState(false);
  const [selectedBusiness, setSelectedBusiness] = useState<AdminBusinessDetail | null>(null);
  const [businessAccessLinks, setBusinessAccessLinks] = useState<AdminBusinessAccessLink[]>([]);
  const [businessOperationalCapacity, setBusinessOperationalCapacity] =
    useState<AdminBusinessOperationalCapacity | null>(null);
  const [businessOperationalCapacityDraft, setBusinessOperationalCapacityDraft] = useState("0.00");
  const [businessFilter, setBusinessFilter] = useState("");
  const [businessSearchFilter, setBusinessSearchFilter] = useState("");
  const businessesRequestEpoch = useRef(0);
  const businessesQueryRef = useRef({ status: "", search: "" });
  const [businessCapacityDraft, setBusinessCapacityDraft] = useState({
    trust_level: "new",
    min_order_amount_usd: "20.00",
    max_order_amount_usd: "100.00",
    daily_limit_usd: "1000.00",
    active_order_limit: 1
  });

  const loadBusinesses = useCallback(async (status = businessFilter, search = businessSearchFilter) => {
    const requestEpoch = ++businessesRequestEpoch.current;
    setBusinessesLoadingMore(false);
    setBusy(true);
    const normalizedSearch = search.trim();
    const isBusinessId = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(normalizedSearch);
    try {
      const data = await listAdminBusinesses(request, {
        verification_status: status,
        business_id: isBusinessId ? normalizedSearch : undefined,
        business_name: normalizedSearch && !isBusinessId ? normalizedSearch : undefined
      });
      if (requestEpoch !== businessesRequestEpoch.current) {
        return;
      }
      setBusinesses(data.items);
      setBusinessesNextCursor(data.next_cursor);
      setView("businesses");
      setBusinessFilter(status);
      setBusinessSearchFilter(normalizedSearch);
      businessesQueryRef.current = { status, search: normalizedSearch };
      setNotice(data.items.length ? "Negocios cargados." : "No hay negocios para ese filtro.");
    } catch (error) {
      if (requestEpoch === businessesRequestEpoch.current) {
        setBusinesses([]);
        setBusinessesNextCursor(null);
        setNotice(error instanceof Error ? error.message : "No se pudo cargar negocios.");
      }
    } finally {
      if (requestEpoch === businessesRequestEpoch.current) {
        setBusy(false);
      }
    }
  }, [businessFilter, businessSearchFilter, request, setBusy, setNotice, setView]);

  const loadMoreBusinesses = useCallback(async () => {
    const cursor = businessesNextCursor;
    if (!cursor || businessesLoadingMore) {
      return;
    }
    const requestEpoch = ++businessesRequestEpoch.current;
    const { status: requestedStatus, search: requestedSearch } = businessesQueryRef.current;
    const isBusinessId = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(requestedSearch);
    setBusinessesLoadingMore(true);
    try {
      const data = await listAdminBusinesses(
        request,
        {
          verification_status: requestedStatus,
          business_id: isBusinessId ? requestedSearch : undefined,
          business_name: requestedSearch && !isBusinessId ? requestedSearch : undefined
        },
        cursor
      );
      if (requestEpoch !== businessesRequestEpoch.current) {
        return;
      }
      setBusinesses((current) => appendUniqueById(current, data.items));
      setBusinessesNextCursor(data.next_cursor);
    } catch (error) {
      if (requestEpoch === businessesRequestEpoch.current) {
        setNotice(error instanceof Error ? error.message : "No se pudieron cargar mas negocios.");
      }
    } finally {
      if (requestEpoch === businessesRequestEpoch.current) {
        setBusinessesLoadingMore(false);
      }
    }
  }, [businessesLoadingMore, businessesNextCursor, request, setNotice]);

  const loadPendingBusinesses = useCallback(async () => {
    await loadBusinesses("pending", "");
  }, [loadBusinesses]);

  const openBusiness = useCallback(async (businessId: string) => {
    setBusy(true);
    try {
      const [data, links, operationalCapacity] = await Promise.all([
        getAdminBusiness<AdminBusinessDetail>(request, businessId),
        listAdminBusinessAccessLinks<{ items: AdminBusinessAccessLink[] }>(request, businessId),
        getAdminBusinessOperationalCapacity<AdminBusinessOperationalCapacity>(request, businessId)
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
      setBusinessOperationalCapacity(operationalCapacity);
      setBusinessOperationalCapacityDraft(operationalCapacity.declared_available_capacity_usd);
      setView("business-detail");
      setNotice("Detalle de negocio cargado.");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "No se pudo cargar detalle de negocio.");
    } finally {
      setBusy(false);
    }
  }, [request, setBusy, setNotice, setView]);

  const submitBusinessCapacity = useCallback(() => {
    if (!selectedBusiness || !adminMutable) {
      setNotice("Accion no permitida para este rol.");
      return;
    }
    queueCriticalAction(
      "Actualizar capacidad",
      "Ajusta minimo, maximo, limite diario y ordenes activas. Backend valida rango, permisos, idempotencia y audit log.",
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
      },
      { requiresReason: false }
    );
  }, [adminMutable, businessCapacityDraft, openBusiness, queueCriticalAction, reason, request, selectedBusiness, setNotice, setReason]);

  const submitBusinessOperationalCapacity = useCallback(() => {
    if (!selectedBusiness || !adminMutable) {
      setNotice("Accion no permitida para este rol.");
      return;
    }
    queueCriticalAction(
      "Actualizar disponible ahora",
      "Ajusta la capacidad operativa declarada. No modifica creditos ni pagos.",
      async () => {
        await updateAdminBusinessOperationalCapacity(
          request,
          selectedBusiness.business.id,
          {
            declared_available_capacity_usd: businessOperationalCapacityDraft,
            reason
          },
          idempotencyKey("business_operational_capacity")
        );
        setReason("");
        setNotice("Disponible operativo actualizado.");
        await openBusiness(selectedBusiness.business.id);
      },
      { requiresReason: false }
    );
  }, [
    adminMutable,
    businessOperationalCapacityDraft,
    openBusiness,
    queueCriticalAction,
    reason,
    request,
    selectedBusiness,
    setNotice,
    setReason
  ]);

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
    }, { requiresReason: false });
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
    queueCriticalAction("Crear acceso negocio", "Vincula el owner del negocio a la Mini App Negocio. Backend valida permisos e idempotencia.", async () => {
      await createAdminBusinessAccessLink(
        request,
        selectedBusiness.business.id,
        { user_id: ownerUserId, role_in_business: "owner", reason },
        idempotencyKey("business_access_link_create")
      );
      setReason("");
      setNotice("Acceso de negocio creado.");
      await openBusiness(selectedBusiness.business.id);
    }, { requiresReason: false });
  }, [adminMutable, openBusiness, queueCriticalAction, reason, request, selectedBusiness, setNotice, setReason]);

  const changeBusinessStatus = useCallback((action: "suspend" | "reactivate" | "block") => {
    if (!selectedBusiness || !adminMutable) {
      setNotice("Accion no permitida para este rol.");
      return;
    }
    const currentStatus = selectedBusiness.business.verification_status;
    const title =
      action === "reactivate"
        ? currentStatus === "blocked" ? "Desbloquear negocio" : "Reactivar negocio"
        : action === "suspend" ? "Suspender negocio" : "Bloquear negocio";
    const successMessage =
      action === "reactivate"
        ? currentStatus === "blocked" ? "Negocio desbloqueado." : "Negocio reactivado."
        : action === "suspend" ? "Negocio suspendido." : "Negocio bloqueado.";
    queueCriticalAction(
      title,
      "Cambia el estado operativo del negocio. El acceso del dueno se gestiona por separado.",
      async () => {
        const data = await updateAdminBusinessStatus<{ business: { id: string; verification_status: string } }>(
          request,
          selectedBusiness.business.id,
          action,
          reason,
          idempotencyKey(`business_status_${action}`)
        );
        setBusinesses((current) => current.map((item) => (
          item.id === data.business.id ? { ...item, verification_status: data.business.verification_status } : item
        )));
        setReason("");
        await openBusiness(selectedBusiness.business.id);
        setNotice(successMessage);
      }
    );
  }, [adminMutable, openBusiness, queueCriticalAction, reason, request, selectedBusiness, setNotice, setReason]);

  const changeBusinessAccessLink = useCallback((linkId: string, action: "suspend" | "reactivate" | "revoke" | "block") => {
    if (!selectedBusiness || !adminMutable) {
      setNotice("Accion no permitida para este rol.");
      return;
    }
    queueCriticalAction(
      `${action} acceso negocio`,
      "Cambia el acceso del negocio sin borrar historial. Backend valida estado, permisos, idempotencia y audit.",
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
      },
      { requiresReason: false }
    );
  }, [adminMutable, openBusiness, queueCriticalAction, reason, request, selectedBusiness, setNotice, setReason]);

  return {
    businessAccessLinks,
    businessCapacityDraft,
    businessOperationalCapacity,
    businessOperationalCapacityDraft,
    businesses,
    businessFilter,
    businessesLoadingMore,
    businessesNextCursor,
    businessSearchFilter,
    changeBusinessAccessLink,
    changeBusinessStatus,
    createBusinessOwnerAccessLink,
    loadBusinesses,
    loadMoreBusinesses,
    loadPendingBusinesses,
    openBusiness,
    openDocument,
    selectedBusiness,
    setBusinessCapacityDraft,
    setBusinessSearchFilter,
    setBusinessOperationalCapacityDraft,
    setBusinessFilter,
    submitBusinessCapacity,
    submitBusinessOperationalCapacity
  };
}
