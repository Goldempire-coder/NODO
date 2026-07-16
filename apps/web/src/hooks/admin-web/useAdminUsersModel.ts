import { useCallback, useState } from "react";
import { getAdminUser, listAdminUsers, updateAdminUserStatus } from "../../api/admin";
import type { AuthenticatedRequest } from "../../api/client";
import type { AdminUserDetail, AdminUserSummary } from "../../types/admin";
import { idempotencyKey } from "./helpers";
import type { ListResponse, QueueCriticalAction } from "./adminBusinessIntakeTypes";
import type { AdminWebView } from "./adminWebTypes";

export type AdminUserFilters = {
  phone: string;
  telegram_id: string;
  username: string;
  role: string;
  status: string;
};

const EMPTY_FILTERS: AdminUserFilters = {
  phone: "",
  telegram_id: "",
  username: "",
  role: "",
  status: ""
};

export function useAdminUsersModel({
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
  setView: (view: AdminWebView) => void;
}) {
  const [users, setUsers] = useState<AdminUserSummary[]>([]);
  const [selectedUser, setSelectedUser] = useState<AdminUserDetail | null>(null);
  const [userFilters, setUserFilters] = useState<AdminUserFilters>(EMPTY_FILTERS);

  const loadUsers = useCallback(async (filters = userFilters) => {
    setBusy(true);
    try {
      const data = await listAdminUsers<ListResponse<AdminUserSummary>>(request, filters);
      setUsers(data.items);
      setUserFilters(filters);
      setView("users");
      setNotice(data.items.length ? "Usuarios cargados." : "No hay usuarios para ese filtro.");
    } catch (error) {
      setUsers([]);
      setNotice(error instanceof Error ? error.message : "No se pudo cargar usuarios.");
    } finally {
      setBusy(false);
    }
  }, [request, setBusy, setNotice, setView, userFilters]);

  const openUser = useCallback(async (userId: string) => {
    setBusy(true);
    try {
      const data = await getAdminUser<AdminUserDetail>(request, userId);
      setSelectedUser(data);
      setView("user-detail");
      setNotice("Detalle de usuario cargado.");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "No se pudo cargar usuario.");
    } finally {
      setBusy(false);
    }
  }, [request, setBusy, setNotice, setView]);

  const changeUserStatus = useCallback((userId: string, action: "suspend" | "reactivate" | "block") => {
    if (!adminMutable) {
      setNotice("Accion no permitida para este rol.");
      return;
    }
    queueCriticalAction(
      `${action} usuario`,
      "Cambia el estado del usuario sin borrar historial. Backend valida transicion, reason, idempotencia y audit.",
      async () => {
        await updateAdminUserStatus(request, userId, action, reason, idempotencyKey(`admin_user_${action}`));
        setReason("");
        setNotice("Estado de usuario actualizado.");
        await openUser(userId);
      }
    );
  }, [adminMutable, openUser, queueCriticalAction, reason, request, setNotice, setReason]);

  return {
    changeUserStatus,
    loadUsers,
    openUser,
    selectedUser,
    setUserFilters,
    userFilters,
    users
  };
}
