import { useCallback, useEffect, useRef, useState } from "react";
import { getAdminUser, listAdminUsers, revealAdminUserPhone, updateAdminUserStatus } from "../../api/admin";
import type { AuthenticatedRequest } from "../../api/client";
import type { AdminUserDetail, AdminUserSummary } from "../../types/admin";
import { appendUniqueById } from "../pagination";
import { idempotencyKey } from "./helpers";
import type { QueueCriticalAction } from "./adminBusinessIntakeTypes";
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
  role: "remitter",
  status: ""
};

type RevealedUserPhone = {
  user_id: string;
  phone: string | null;
  phone_masked?: string | null;
};

type AdminUserStatusMutationResponse = {
  user: AdminUserSummary;
  disclaimer?: string;
};

export function useAdminUsersModel({
  adminMutable,
  queueCriticalAction,
  reason,
  request,
  setBusy,
  setNotice,
  setReason,
  setView,
  view
}: {
  adminMutable: boolean;
  queueCriticalAction: QueueCriticalAction;
  reason: string;
  request: AuthenticatedRequest;
  setBusy: (busy: boolean) => void;
  setNotice: (notice: string) => void;
  setReason: (reason: string) => void;
  setView: (view: AdminWebView) => void;
  view: AdminWebView;
}) {
  const [users, setUsers] = useState<AdminUserSummary[]>([]);
  const [usersNextCursor, setUsersNextCursor] = useState<string | null>(null);
  const [usersLoadingMore, setUsersLoadingMore] = useState(false);
  const [selectedUser, setSelectedUser] = useState<AdminUserDetail | null>(null);
  const [revealedUserPhone, setRevealedUserPhone] = useState<RevealedUserPhone | null>(null);
  const [userFilters, setUserFilters] = useState<AdminUserFilters>(EMPTY_FILTERS);
  const activeUserDetailRef = useRef<string | null>(null);
  const usersRequestEpoch = useRef(0);
  const usersQueryRef = useRef<AdminUserFilters>(EMPTY_FILTERS);

  useEffect(() => {
    if (view !== "user-detail") {
      activeUserDetailRef.current = null;
      setRevealedUserPhone(null);
    }
  }, [view]);

  const loadUsers = useCallback(async (filters = userFilters) => {
    const requestEpoch = ++usersRequestEpoch.current;
    activeUserDetailRef.current = null;
    setRevealedUserPhone(null);
    setUsersLoadingMore(false);
    setBusy(true);
    try {
      const data = await listAdminUsers(request, filters);
      if (requestEpoch !== usersRequestEpoch.current) {
        return;
      }
      setUsers(data.items);
      setUsersNextCursor(data.next_cursor);
      setUserFilters(filters);
      usersQueryRef.current = { ...filters };
      setView("users");
      setNotice(data.items.length ? "Usuarios cargados." : "No hay usuarios para ese filtro.");
    } catch (error) {
      if (requestEpoch === usersRequestEpoch.current) {
        setUsers([]);
        setUsersNextCursor(null);
        setNotice(error instanceof Error ? error.message : "No se pudo cargar usuarios.");
      }
    } finally {
      if (requestEpoch === usersRequestEpoch.current) {
        setBusy(false);
      }
    }
  }, [request, setBusy, setNotice, setView, userFilters]);

  const loadMoreUsers = useCallback(async () => {
    const cursor = usersNextCursor;
    if (!cursor || usersLoadingMore) {
      return;
    }
    const requestEpoch = ++usersRequestEpoch.current;
    const requestedFilters = usersQueryRef.current;
    setUsersLoadingMore(true);
    try {
      const data = await listAdminUsers(request, requestedFilters, cursor);
      if (requestEpoch !== usersRequestEpoch.current) {
        return;
      }
      setUsers((current) => appendUniqueById(current, data.items));
      setUsersNextCursor(data.next_cursor);
    } catch (error) {
      if (requestEpoch === usersRequestEpoch.current) {
        setNotice(error instanceof Error ? error.message : "No se pudieron cargar mas usuarios.");
      }
    } finally {
      if (requestEpoch === usersRequestEpoch.current) {
        setUsersLoadingMore(false);
      }
    }
  }, [request, setNotice, usersLoadingMore, usersNextCursor]);

  const openUser = useCallback(async (userId: string) => {
    activeUserDetailRef.current = null;
    setRevealedUserPhone(null);
    setBusy(true);
    try {
      const data = await getAdminUser<AdminUserDetail>(request, userId);
      activeUserDetailRef.current = userId;
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
    const currentStatus = selectedUser?.user.id === userId
      ? selectedUser.user.status
      : users.find((candidate) => candidate.id === userId)?.status;
    const title = action === "reactivate" && currentStatus === "blocked"
      ? "Desbloquear cliente"
      : `${action} usuario`;
    const successMessage = action === "reactivate" && currentStatus === "blocked"
      ? "Cliente desbloqueado."
      : "Estado de usuario actualizado.";
    queueCriticalAction(
      title,
      "Cambia el estado del usuario sin borrar historial. Backend valida transicion, reason, idempotencia y audit.",
      async () => {
        const data = await updateAdminUserStatus<AdminUserStatusMutationResponse>(
          request,
          userId,
          action,
          reason,
          idempotencyKey(`admin_user_${action}`)
        );
        setUsers((current) => current.map((candidate) => (
          candidate.id === data.user.id
            ? { ...candidate, status: data.user.status, updated_at: data.user.updated_at }
            : candidate
        )));
        setSelectedUser((current) => current?.user.id === data.user.id
          ? {
              ...current,
              user: { ...current.user, status: data.user.status, updated_at: data.user.updated_at }
            }
          : current);
        setReason("");
        setNotice(successMessage);
      },
      { requiresReason: true }
    );
  }, [adminMutable, queueCriticalAction, reason, request, selectedUser, setNotice, setReason, users]);

  const revealUserPhone = useCallback((userId: string) => {
    if (!adminMutable) {
      setNotice("Accion no permitida para este rol.");
      return;
    }
    queueCriticalAction(
      "Revelar telefono",
      "Muestra el telefono completo mientras mantengas abierto este detalle. Backend exige razon y audita la lectura.",
      async () => {
        const data = await revealAdminUserPhone<RevealedUserPhone>(request, userId, reason);
        if (activeUserDetailRef.current !== userId) {
          return;
        }
        setRevealedUserPhone(data);
        setReason("");
        setNotice(data.phone ? "Telefono revelado con auditoria." : "Este cliente no tiene telefono registrado.");
      },
      { requiresReason: true }
    );
  }, [adminMutable, queueCriticalAction, reason, request, setNotice, setReason]);

  return {
    changeUserStatus,
    loadMoreUsers,
    loadUsers,
    openUser,
    revealedUserPhone,
    revealUserPhone,
    selectedUser,
    setUserFilters,
    userFilters,
    users,
    usersLoadingMore,
    usersNextCursor
  };
}
