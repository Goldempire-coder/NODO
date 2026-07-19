import { useCallback, useState } from "react";
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
  ListResponse,
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
    responsible_name: intake.responsible_name || "",
    city: intake.city || "",
    business_phone: intake.business_phone || "",
    operation: intake.operation || "",
    banks: listToInput(intake.banks),
    methods: listToInput(intake.methods),
    min_amount_usd: intake.min_amount_usd || "",
    max_amount_usd: intake.max_amount_usd || "",
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
  assignIfFilled(payload, "responsible_name", draft.responsible_name);
  assignIfFilled(payload, "city", draft.city);
  assignIfFilled(payload, "business_phone", draft.business_phone);
  assignIfFilled(payload, "operation", draft.operation);
  assignIfFilled(payload, "min_amount_usd", draft.min_amount_usd);
  assignIfFilled(payload, "max_amount_usd", draft.max_amount_usd);
  assignIfFilled(payload, "schedule", draft.schedule);
  assignListIfFilled(payload, "banks", draft.banks);
  assignListIfFilled(payload, "methods", draft.methods);
  assignListIfFilled(payload, "references", draft.references);
  return payload;
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
  const [selectedBusinessIntake, setSelectedBusinessIntake] = useState<AdminBusinessIntakeDetail | null>(null);
  const [intakeFilter, setIntakeFilter] = useState("all");
  const [intakePublicBusinessName, setIntakePublicBusinessName] = useState("");
  const [intakeEditDraft, setIntakeEditDraft] = useState<AdminBusinessIntakeEditDraft>(() => editDraftFromIntake({ id: "", status: "", last_step: "", created_at: "", updated_at: "" }));

  const loadBusinessIntakes = useCallback(async (status = intakeFilter) => {
    const normalizedStatus = status.trim().toLowerCase() || "all";
    setBusy(true);
    try {
      const data = await listAdminBusinessIntakes<ListResponse<AdminBusinessIntakeSummary>>(request, normalizedStatus);
      setBusinessIntakes(data.items);
      setIntakeFilter(normalizedStatus);
      setView("intake");
      setNotice(data.items.length ? "Solicitudes de negocio cargadas." : "No hay solicitudes para ese filtro.");
    } catch (error) {
      setBusinessIntakes([]);
      setNotice(error instanceof Error ? error.message : "No se pudo cargar solicitudes de negocio.");
    } finally {
      setBusy(false);
    }
  }, [intakeFilter, request, setBusy, setNotice, setView]);

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

  const openBusinessIntakeDocument = useCallback((fileId: string) => {
    if (!selectedBusinessIntake || !adminMutable) {
      setNotice("Solo admin/super_admin puede solicitar URL privada.");
      return;
    }
    queueCriticalAction("Ver documento de solicitud", "La URL temporal no se guarda y la apertura queda auditada.", async () => {
      const data = await getAdminBusinessIntakeDocumentViewUrl<{ url: string; expires_in: number }>(
        request,
        selectedBusinessIntake.intake.id,
        fileId,
        reason
      );
      window.open(data.url, "_blank", "noopener,noreferrer");
      setNotice(`Documento disponible por ${data.expires_in}s.`);
    }, { requiresReason: false });
  }, [adminMutable, queueCriticalAction, reason, request, selectedBusinessIntake, setNotice]);

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
      await deleteAdminBusinessIntake(request, selectedBusinessIntake.intake.id, idempotencyKey("business_intake_delete"));
      setSelectedBusinessIntake(null);
      setNotice("Solicitud borrada del panel. Audit log preservado.");
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
            reason,
            create_business: true,
            public_business_name: publicName
          },
          idempotencyKey("business_intake_create_business")
        );
        setSelectedBusinessIntake({ ...selectedBusinessIntake, intake: data.intake });
        setReason("");
        setNotice(data.business ? `Negocio creado: ${data.business.business_name}. Queda pendiente de aprobacion/acceso.` : "Solicitud aceptada.");
        await loadBusinessIntakes(intakeFilter);
      }
    );
  }, [adminMutable, intakeFilter, intakePublicBusinessName, loadBusinessIntakes, queueCriticalAction, reason, request, selectedBusinessIntake, setNotice, setReason]);

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
            reason,
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
        await loadBusinessIntakes(intakeFilter);
      }
    );
  }, [adminMutable, intakeFilter, intakePublicBusinessName, loadBusinessIntakes, queueCriticalAction, reason, request, selectedBusinessIntake, setNotice, setReason]);

  return {
    approveBusinessFromIntake,
    businessIntakes,
    createBusinessFromIntake,
    deleteBusinessIntake,
    intakeFilter,
    intakeEditDraft,
    intakePublicBusinessName,
    loadBusinessIntakes,
    openBusinessIntake,
    openBusinessIntakeDocument,
    saveBusinessIntakeManual,
    selectedBusinessIntake,
    setIntakeEditDraft,
    setIntakeFilter,
    setIntakePublicBusinessName
  };
}
