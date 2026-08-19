import { useCallback, useRef, useState } from "react";
import {
  acceptAdminBusinessIntake,
  deleteAdminBusinessIntake,
  getAdminBusinessIntake,
  getAdminBusinessIntakeDocumentViewUrl,
  listAdminBusinessIntakes,
  updateAdminBusinessIntake
} from "../../api/admin";
import type { AuthenticatedRequest } from "../../api/client";
import { idempotencyKey } from "./helpers";
import type {
  AdminBusinessIntakeDetail,
  AdminBusinessIntakeEditDraft,
  AdminBusinessIntakeSummary,
  BusinessIntakeView,
  QueueCriticalAction
} from "./adminBusinessIntakeTypes";

function listToInput(items?: string[] | null) {
  return items?.join(", ") || "";
}

function inputToList(value: string) {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function editDraftFromIntake(intake: AdminBusinessIntakeSummary): AdminBusinessIntakeEditDraft {
  return {
    referral_code: intake.referral_code || "",
    contact_phone: intake.contact_phone || "",
    business_name: intake.business_name || "",
    business_tax_id: intake.business_tax_id || "",
    responsible_name: intake.responsible_name || "",
    responsible_id_number: intake.responsible_id_number || "",
    city: intake.city || "",
    business_phone: intake.business_phone || "",
    operation: intake.operation || "",
    banks: listToInput(intake.banks),
    methods: listToInput(intake.methods),
    min_amount_usd: intake.min_amount_usd || "20.00",
    max_amount_usd: intake.max_amount_usd || "100.00",
    daily_limit_usd: intake.daily_limit_usd || "1000.00",
    schedule: intake.schedule || "",
    references: listToInput(intake.references)
  };
}

function assignIfFilled(payload: Record<string, unknown>, key: string, value: string) {
  const trimmed = value.trim();
  if (trimmed) {
    payload[key] = trimmed;
  }
}

function assignListIfFilled(payload: Record<string, unknown>, key: string, value: string) {
  const items = inputToList(value);
  if (items.length > 0) {
    payload[key] = items;
  }
}

function editPayload(draft: AdminBusinessIntakeEditDraft, submitForReview: boolean) {
  const payload: Record<string, unknown> = { submit_for_review: submitForReview };
  assignIfFilled(payload, "referral_code", draft.referral_code);
  assignIfFilled(payload, "contact_phone", draft.contact_phone);
  assignIfFilled(payload, "business_name", draft.business_name);
  assignIfFilled(payload, "business_tax_id", draft.business_tax_id);
  assignIfFilled(payload, "responsible_name", draft.responsible_name);
  assignIfFilled(payload, "responsible_id_number", draft.responsible_id_number);
  assignIfFilled(payload, "city", draft.city);
  assignIfFilled(payload, "business_phone", draft.business_phone);
  assignIfFilled(payload, "operation", draft.operation);
  assignIfFilled(payload, "min_amount_usd", draft.min_amount_usd);
  assignIfFilled(payload, "max_amount_usd", draft.max_amount_usd);
  assignIfFilled(payload, "daily_limit_usd", draft.daily_limit_usd);
  assignIfFilled(payload, "schedule", draft.schedule);
  assignListIfFilled(payload, "banks", draft.banks);
  assignListIfFilled(payload, "methods", draft.methods);
  assignListIfFilled(payload, "references", draft.references);
  return payload;
}

export type IntakeReadinessFilter = "all" | "ready" | "needs_info";

function mergeIntakes(current: AdminBusinessIntakeSummary[], incoming: AdminBusinessIntakeSummary[]) {
  const seen = new Set(current.map((item) => item.id));
  return [...current, ...incoming.filter((item) => !seen.has(item.id))];
}

export function useAdminBusinessIntakesModel({
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
  const [businessIntakes, setBusinessIntakes] = useState<AdminBusinessIntakeSummary[]>([]);
  const [businessIntakesNextCursor, setBusinessIntakesNextCursor] = useState<string | null>(null);
  const [businessIntakesLoadingMore, setBusinessIntakesLoadingMore] = useState(false);
  const [selectedBusinessIntake, setSelectedBusinessIntake] = useState<AdminBusinessIntakeDetail | null>(null);
  const [intakeFilter, setIntakeFilter] = useState("submitted");
  const [intakeReadinessFilter, setIntakeReadinessFilter] = useState<IntakeReadinessFilter>("all");
  const [intakePublicBusinessName, setIntakePublicBusinessName] = useState("");
  const [intakeEditDraft, setIntakeEditDraft] = useState<AdminBusinessIntakeEditDraft>(() => editDraftFromIntake({ id: "", status: "", last_step: "", created_at: "", updated_at: "" }));
  const businessIntakesRequestEpoch = useRef(0);
  const businessIntakesQueryRef = useRef<{ status: string; readiness: IntakeReadinessFilter }>({
    status: "submitted",
    readiness: "all"
  });

  const loadBusinessIntakes = useCallback(async (status = intakeFilter, readiness = intakeReadinessFilter) => {
    const requestEpoch = ++businessIntakesRequestEpoch.current;
    const normalizedStatus = status.trim().toLowerCase() || "submitted";
    const normalizedReadiness = readiness || "all";
    setBusinessIntakesLoadingMore(false);
    setBusy(true);
    try {
      const data = await listAdminBusinessIntakes(request, normalizedStatus, normalizedReadiness);
      if (requestEpoch !== businessIntakesRequestEpoch.current) {
        return;
      }
      setBusinessIntakes(data.items);
      setBusinessIntakesNextCursor(data.next_cursor);
      setIntakeFilter(normalizedStatus);
      setIntakeReadinessFilter(normalizedReadiness);
      businessIntakesQueryRef.current = { status: normalizedStatus, readiness: normalizedReadiness };
      setView("intake");
      setNotice(data.items.length ? "Solicitudes de negocio cargadas." : "No hay solicitudes para ese filtro.");
    } catch (error) {
      if (requestEpoch === businessIntakesRequestEpoch.current) {
        setBusinessIntakes([]);
        setBusinessIntakesNextCursor(null);
        setNotice(error instanceof Error ? error.message : "No se pudo cargar solicitudes de negocio.");
      }
    } finally {
      if (requestEpoch === businessIntakesRequestEpoch.current) {
        setBusy(false);
      }
    }
  }, [intakeFilter, intakeReadinessFilter, request, setBusy, setNotice, setView]);

  const loadMoreBusinessIntakes = useCallback(async () => {
    if (!businessIntakesNextCursor || businessIntakesLoadingMore) {
      return;
    }
    const requestEpoch = ++businessIntakesRequestEpoch.current;
    const cursor = businessIntakesNextCursor;
    const { status: requestedStatus, readiness: requestedReadiness } = businessIntakesQueryRef.current;
    setBusinessIntakesLoadingMore(true);
    try {
      const data = await listAdminBusinessIntakes(
        request,
        requestedStatus,
        requestedReadiness,
        cursor
      );
      if (requestEpoch !== businessIntakesRequestEpoch.current) {
        return;
      }
      setBusinessIntakes((current) => mergeIntakes(current, data.items));
      setBusinessIntakesNextCursor(data.next_cursor);
      setNotice(data.items.length ? "Mas solicitudes cargadas." : "No hay mas solicitudes para este filtro.");
    } catch (error) {
      if (requestEpoch === businessIntakesRequestEpoch.current) {
        setNotice(error instanceof Error ? error.message : "No se pudieron cargar mas solicitudes.");
      }
    } finally {
      if (requestEpoch === businessIntakesRequestEpoch.current) {
        setBusinessIntakesLoadingMore(false);
      }
    }
  }, [businessIntakesLoadingMore, businessIntakesNextCursor, request, setNotice]);

  const openBusinessIntake = useCallback(async (intakeId: string) => {
    setBusy(true);
    try {
      const data = await getAdminBusinessIntake<AdminBusinessIntakeDetail>(request, intakeId);
      setSelectedBusinessIntake(data);
      setIntakePublicBusinessName(data.intake.business_name || "");
      setIntakeEditDraft(editDraftFromIntake(data.intake));
      setView("intake-detail");
      setNotice("Detalle de solicitud cargado.");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "No se pudo cargar solicitud.");
    } finally {
      setBusy(false);
    }
  }, [request, setBusy, setNotice, setView]);

  const openBusinessIntakeDocument = useCallback(async (fileId: string, mode: "view" | "download" = "view") => {
    if (!selectedBusinessIntake || !adminMutable) {
      setNotice("Solo admin/super_admin puede solicitar URL privada.");
      return;
    }
    setBusy(true);
    try {
      const data = await getAdminBusinessIntakeDocumentViewUrl<{ url: string; expires_in: number; download_filename: string }>(
        request,
        selectedBusinessIntake.intake.id,
        fileId,
        reason
      );
      if (mode === "download") {
        const anchor = window.document.createElement("a");
        anchor.href = data.url;
        anchor.download = data.download_filename;
        anchor.target = "_blank";
        anchor.rel = "noopener noreferrer";
        anchor.click();
        setNotice(`Descarga solicitada: ${data.download_filename}.`);
        return;
      }
      window.open(data.url, "_blank", "noopener,noreferrer");
      setNotice(`Documento disponible por ${data.expires_in}s: ${data.download_filename}.`);
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "No se pudo abrir el documento.");
    } finally {
      setBusy(false);
    }
  }, [adminMutable, reason, request, selectedBusinessIntake, setBusy, setNotice]);

  const saveBusinessIntakeManual = useCallback((submitForReview = false) => {
    if (!selectedBusinessIntake || !adminMutable) {
      setNotice("Accion no permitida para este rol.");
      return;
    }
    const title = submitForReview ? "Guardar y poner en revision" : "Guardar ficha de negocio";
    const detail = submitForReview
      ? "Se guardaran los datos y la solicitud quedara lista para revision admin si cumple los requisitos."
      : "Se guardaran los datos confirmados por WhatsApp o revision manual.";
    queueCriticalAction(title, detail, async () => {
      const data = await updateAdminBusinessIntake<{ intake: AdminBusinessIntakeSummary }>(
        request,
        selectedBusinessIntake.intake.id,
        editPayload(intakeEditDraft, submitForReview)
      );
      const updatedDetail = { ...selectedBusinessIntake, intake: data.intake };
      setSelectedBusinessIntake(updatedDetail);
      setIntakePublicBusinessName(data.intake.business_name || "");
      setIntakeEditDraft(editDraftFromIntake(data.intake));
      setNotice(submitForReview ? "Ficha guardada y puesta en revision." : "Ficha guardada.");
    }, { requiresReason: false });
  }, [adminMutable, intakeEditDraft, queueCriticalAction, request, selectedBusinessIntake, setNotice]);

  const deleteBusinessIntake = useCallback(() => {
    if (!selectedBusinessIntake || !adminMutable) {
      setNotice("Accion no permitida para este rol.");
      return;
    }
    queueCriticalAction("Borrar solicitud de negocio", "El registro se elimina del panel; audit logs quedan intactos.", async () => {
      const data = await deleteAdminBusinessIntake<{ reset_notification_sent?: boolean }>(
        request,
        selectedBusinessIntake.intake.id,
        idempotencyKey("business_intake_delete")
      );
      setSelectedBusinessIntake(null);
      setNotice(
        data.reset_notification_sent
          ? "Solicitud borrada. El bot aviso al negocio que puede comenzar de nuevo."
          : "Solicitud borrada. No se pudo confirmar el aviso por Telegram; revisa audit logs."
      );
      await loadBusinessIntakes(intakeFilter);
    }, { requiresReason: false });
  }, [adminMutable, intakeFilter, loadBusinessIntakes, queueCriticalAction, request, selectedBusinessIntake, setNotice]);

  const createBusinessFromIntake = useCallback(() => {
    if (!selectedBusinessIntake || !adminMutable) {
      setNotice("Accion no permitida para este rol.");
      return;
    }
    const publicName = intakePublicBusinessName.trim();
    if (publicName.length < 2) {
      setNotice("Escribe el nombre publico del negocio como aparecera en la app.");
      return;
    }
    if (selectedBusinessIntake.intake.created_business_id) {
      setNotice("Esta solicitud ya tiene un negocio creado.");
      return;
    }
    queueCriticalAction(
      "Crear negocio desde solicitud",
      `Se creara un negocio pendiente llamado "${publicName}". No da acceso automatico a la Mini App Negocio.`,
      async () => {
        const data = await acceptAdminBusinessIntake<{
          intake: AdminBusinessIntakeSummary;
          created_business: boolean;
          business?: { id: string; business_name: string; verification_status: string } | null;
          access_link_created: boolean;
        }>(
          request,
          selectedBusinessIntake.intake.id,
          {
            ...(reason.trim() ? { reason } : {}),
            create_business: true,
            public_business_name: publicName
          },
          idempotencyKey("business_intake_create_business")
        );
        setSelectedBusinessIntake({ ...selectedBusinessIntake, intake: data.intake });
        setReason("");
        setNotice(data.business ? `Negocio creado: ${data.business.business_name}. Queda pendiente de aprobacion/acceso.` : "Solicitud aceptada.");
        await loadBusinessIntakes("submitted");
      },
      { requiresReason: false }
    );
  }, [adminMutable, intakePublicBusinessName, loadBusinessIntakes, queueCriticalAction, reason, request, selectedBusinessIntake, setNotice, setReason]);

  const approveBusinessFromIntake = useCallback(() => {
    if (!selectedBusinessIntake || !adminMutable) {
      setNotice("Accion no permitida para este rol.");
      return;
    }
    const publicName = intakePublicBusinessName.trim();
    const alreadyCreated = Boolean(selectedBusinessIntake.intake.created_business_id);
    if (!alreadyCreated && publicName.length < 2) {
      setNotice("Escribe el nombre publico del negocio como aparecera en la app.");
      return;
    }
    queueCriticalAction(
      "Crear y aprobar negocio",
      alreadyCreated
        ? "Se aprobara el negocio ya creado desde esta solicitud. El backend creara el acceso y el bot enviara el boton de NODO Negocio."
        : `Se creara y aprobara "${publicName}". El backend creara el acceso y el bot enviara el boton de NODO Negocio.`,
      async () => {
        const data = await acceptAdminBusinessIntake<{
          intake: AdminBusinessIntakeSummary;
          created_business: boolean;
          business?: { id: string; business_name: string; verification_status: string } | null;
          access_link_created: boolean;
          approval_notification_sent: boolean;
        }>(
          request,
          selectedBusinessIntake.intake.id,
          {
            ...(reason.trim() ? { reason } : {}),
            create_business: !alreadyCreated,
            approve_business: true,
            ...(alreadyCreated ? {} : { public_business_name: publicName })
          },
          idempotencyKey("business_intake_approve_business")
        );
        setSelectedBusinessIntake({ ...selectedBusinessIntake, intake: data.intake });
        setReason("");
        if (data.business && data.access_link_created && data.approval_notification_sent) {
          setNotice(`Negocio aprobado: ${data.business.business_name}. Boton enviado por Telegram.`);
        } else if (data.business && data.access_link_created) {
          setNotice(`Negocio aprobado: ${data.business.business_name}. Acceso activo; revisa notificacion Telegram.`);
        } else {
          setNotice(data.business ? `Negocio revisado: ${data.business.business_name}.` : "Solicitud aceptada.");
        }
        await loadBusinessIntakes("submitted");
      },
      { requiresReason: false }
    );
  }, [adminMutable, intakePublicBusinessName, loadBusinessIntakes, queueCriticalAction, reason, request, selectedBusinessIntake, setNotice, setReason]);

  return {
    approveBusinessFromIntake,
    businessIntakes,
    businessIntakesLoadingMore,
    businessIntakesNextCursor,
    createBusinessFromIntake,
    deleteBusinessIntake,
    intakeFilter,
    intakeReadinessFilter,
    intakeEditDraft,
    intakePublicBusinessName,
    loadBusinessIntakes,
    loadMoreBusinessIntakes,
    openBusinessIntake,
    openBusinessIntakeDocument,
    saveBusinessIntakeManual,
    selectedBusinessIntake,
    setIntakeEditDraft,
    setIntakeFilter,
    setIntakeReadinessFilter,
    setIntakePublicBusinessName
  };
}
