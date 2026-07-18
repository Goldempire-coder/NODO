import { useCallback, useState } from "react";
import {
  acceptAdminBusinessIntake,
  deleteAdminBusinessIntake,
  getAdminBusinessIntake,
  listAdminBusinessIntakes
} from "../../api/admin";
import type { AuthenticatedRequest } from "../../api/client";
import { idempotencyKey } from "./helpers";
import type {
  AdminBusinessIntakeDetail,
  AdminBusinessIntakeSummary,
  BusinessIntakeView,
  ListResponse,
  QueueCriticalAction
} from "./adminBusinessIntakeTypes";

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
      setView("intake-detail");
      setNotice("Detalle de solicitud cargado.");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "No se pudo cargar solicitud.");
    } finally {
      setBusy(false);
    }
  }, [request, setBusy, setNotice, setView]);

  const deleteBusinessIntake = useCallback(() => {
    if (!selectedBusinessIntake || !adminMutable) {
      setNotice("Accion no permitida para este rol.");
      return;
    }
    queueCriticalAction("Borrar solicitud de negocio", "El registro se elimina del panel; audit logs quedan intactos.", async () => {
      await deleteAdminBusinessIntake(request, selectedBusinessIntake.intake.id, reason, idempotencyKey("business_intake_delete"));
      setSelectedBusinessIntake(null);
      setReason("");
      setNotice("Solicitud borrada del panel. Audit log preservado.");
      await loadBusinessIntakes(intakeFilter);
    });
  }, [adminMutable, intakeFilter, loadBusinessIntakes, queueCriticalAction, reason, request, selectedBusinessIntake, setNotice, setReason]);

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
    intakePublicBusinessName,
    loadBusinessIntakes,
    openBusinessIntake,
    selectedBusinessIntake,
    setIntakeFilter,
    setIntakePublicBusinessName
  };
}
