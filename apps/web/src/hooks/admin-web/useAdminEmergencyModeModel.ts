import { useCallback, useState } from "react";
import { activateAdminEmergencyMode, deactivateAdminEmergencyMode, getAdminEmergencyMode } from "../../api/admin";
import type { AuthenticatedRequest } from "../../api/client";
import type { AdminEmergencyMode } from "../../types/admin";
import { idempotencyKey } from "./helpers";
import type { QueueCriticalAction } from "./adminOverviewTypes";

export function useAdminEmergencyModeModel({
  adminMutable,
  loadDashboard,
  queueCriticalAction,
  reason,
  request,
  setEmergencyMode,
  setNotice,
  setReason
}: {
  adminMutable: boolean;
  loadDashboard: () => Promise<void>;
  queueCriticalAction: QueueCriticalAction;
  reason: string;
  request: AuthenticatedRequest;
  setEmergencyMode: (emergencyMode: AdminEmergencyMode) => void;
  setNotice: (notice: string) => void;
  setReason: (reason: string) => void;
}) {
  const [emergencyMessage, setEmergencyMessage] = useState("Estamos revisando NODO. Intenta nuevamente en unos minutos.");

  const loadEmergencyMode = useCallback(async () => {
    try {
      const data = await getAdminEmergencyMode<{ emergency_mode: AdminEmergencyMode }>(request);
      setEmergencyMode(data.emergency_mode);
      setNotice(data.emergency_mode.enabled ? "Modo emergencia activo." : "Modo emergencia desactivado.");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "No se pudo cargar modo emergencia.");
    }
  }, [request, setEmergencyMode, setNotice]);

  const activateEmergencyMode = useCallback(() => {
    if (!adminMutable) {
      setNotice("Accion no permitida para este rol.");
      return;
    }
    queueCriticalAction(
      "Activar modo emergencia",
      "Bloquea nuevas ordenes, nuevos anuncios/reactivaciones y nuevas compras de creditos. No bloquea soporte ni cierre de ordenes existentes.",
      async () => {
        const cleanReason = reason.trim();
        const cleanMessage = emergencyMessage.trim();
        if (!cleanReason) {
          setNotice("Escribe una razon antes de activar emergencia.");
          return;
        }
        const data = await activateAdminEmergencyMode<{ emergency_mode: AdminEmergencyMode }>(
          request,
          { reason: cleanReason, message: cleanMessage || undefined },
          idempotencyKey("platform_emergency_activate")
        );
        setEmergencyMode(data.emergency_mode);
        setReason("");
        setNotice("Modo emergencia activado.");
        await loadDashboard();
      }
    );
  }, [adminMutable, emergencyMessage, loadDashboard, queueCriticalAction, reason, request, setEmergencyMode, setNotice, setReason]);

  const deactivateEmergencyMode = useCallback(() => {
    if (!adminMutable) {
      setNotice("Accion no permitida para este rol.");
      return;
    }
    queueCriticalAction(
      "Desactivar modo emergencia",
      "Restaura nuevas ordenes, anuncios y compras de creditos. Backend mantiene audit log de la decision.",
      async () => {
        const cleanReason = reason.trim();
        if (!cleanReason) {
          setNotice("Escribe una razon antes de desactivar emergencia.");
          return;
        }
        const data = await deactivateAdminEmergencyMode<{ emergency_mode: AdminEmergencyMode }>(
          request,
          cleanReason,
          idempotencyKey("platform_emergency_deactivate")
        );
        setEmergencyMode(data.emergency_mode);
        setReason("");
        setNotice("Modo emergencia desactivado.");
        await loadDashboard();
      }
    );
  }, [adminMutable, loadDashboard, queueCriticalAction, reason, request, setEmergencyMode, setNotice, setReason]);

  return {
    activateEmergencyMode,
    deactivateEmergencyMode,
    emergencyMessage,
    loadEmergencyMode,
    setEmergencyMessage
  };
}
