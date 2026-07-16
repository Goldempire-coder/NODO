"use client";

import { useCallback, useState } from "react";
import {
  createAdminStaffInvite,
  getAdminStaff,
  listAdminStaff,
  listAdminStaffActivity,
  updateAdminStaffPermissions,
  updateAdminStaffStatus
} from "../../api/admin";
import type { RequestFn } from "./adminWebTypes";
import { idempotencyKey } from "./helpers";

export type StaffPermissionInput = { permission: string; scope: string; scope_value?: string | null };
export type StaffSummary = {
  id: string;
  user_id: string;
  display_name?: string | null;
  username?: string | null;
  staff_role: string;
  status: string;
  permission_count: number;
  last_activity_at?: string | null;
  created_at?: string | null;
};
export type StaffDetail = StaffSummary & {
  user_status?: string | null;
  base_role?: string | null;
  permissions: Array<StaffPermissionInput & { id?: string; status: string }>;
  reason?: string | null;
};
export type StaffActivityItem = {
  event_type: string;
  actor_role?: string | null;
  resource_type?: string | null;
  resource_id?: string | null;
  created_at?: string | null;
};

export function useAdminStaffModel({
  request,
  setBusy,
  setNotice,
  setView,
  queueCriticalAction,
  reason,
  setReason
}: {
  request: RequestFn;
  setBusy: (value: boolean) => void;
  setNotice: (value: string) => void;
  setView: (view: "staff" | "staff-detail" | "staff-invite") => void;
  queueCriticalAction: (title: string, detail: string, run: () => Promise<void>) => void;
  reason: string;
  setReason: (value: string) => void;
}) {
  const [staff, setStaff] = useState<StaffSummary[]>([]);
  const [selectedStaff, setSelectedStaff] = useState<StaffDetail | null>(null);
  const [staffActivity, setStaffActivity] = useState<StaffActivityItem[]>([]);
  const [staffFilters, setStaffFilters] = useState({ status: "", staff_role: "", q: "" });
  const [staffInvite, setStaffInvite] = useState({
    target_user_id: "",
    target_telegram_id: "",
    target_username: "",
    staff_role: "support_agent",
    expires_at: "",
    permission: "view_assigned_support_tickets",
    scope: "assigned_only",
    scope_value: ""
  });

  const loadStaff = useCallback(
    async (status = staffFilters.status) => {
      setBusy(true);
      try {
        const response = await listAdminStaff<{ data: { items: StaffSummary[] } }>(request, { ...staffFilters, status });
        setStaff(response.data.items);
        setView("staff");
        setNotice("Staff interno cargado. Mutaciones siguen limitadas a super_admin.");
      } finally {
        setBusy(false);
      }
    },
    [request, setBusy, setNotice, setView, staffFilters]
  );

  const openStaff = useCallback(
    async (staffId: string) => {
      setBusy(true);
      try {
        const response = await getAdminStaff<{ data: { staff: StaffDetail } }>(request, staffId);
        setSelectedStaff(response.data.staff);
        const activity = await listAdminStaffActivity<{ data: { items: StaffActivityItem[] } }>(request, staffId);
        setStaffActivity(activity.data.items);
        setView("staff-detail");
        setNotice("Detalle staff con permisos y actividad limitada.");
      } finally {
        setBusy(false);
      }
    },
    [request, setBusy, setNotice, setView]
  );

  const submitStaffInvite = useCallback(async () => {
    setBusy(true);
    try {
      const expiresAt = staffInvite.expires_at || new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString();
      await createAdminStaffInvite(
        request,
        {
          target_user_id: staffInvite.target_user_id || undefined,
          target_telegram_id: staffInvite.target_telegram_id || undefined,
          target_username: staffInvite.target_username || undefined,
          staff_role: staffInvite.staff_role,
          permissions: [
            {
              permission: staffInvite.permission,
              scope: staffInvite.scope,
              scope_value: staffInvite.scope_value || null
            }
          ],
          expires_at: expiresAt,
          reason
        },
        idempotencyKey("staff-invite")
      );
      setNotice("Invitacion staff creada sin exponer secretos. Backend valido permisos.");
      setReason("");
      await loadStaff();
    } finally {
      setBusy(false);
    }
  }, [loadStaff, reason, request, setBusy, setNotice, setReason, staffInvite]);

  const changeStaffStatus = useCallback(
    (staffId: string, action: "activate" | "suspend" | "revoke") => {
      queueCriticalAction(
        `${action} staff`,
        "Esta mutacion requiere reason, idempotencia, RBAC backend y audit.",
        async () => {
          await updateAdminStaffStatus(request, staffId, action, reason, idempotencyKey(`staff-${action}`));
          setReason("");
          await openStaff(staffId);
        }
      );
    },
    [openStaff, queueCriticalAction, reason, request, setReason]
  );

  const replaceStaffPermissions = useCallback(
    (staffId: string, permissions: StaffPermissionInput[]) => {
      queueCriticalAction(
        "Actualizar permisos staff",
        "Reemplaza permisos activos por una matriz granular. No concede acciones criticas prohibidas.",
        async () => {
          await updateAdminStaffPermissions(request, staffId, permissions, reason, idempotencyKey("staff-permissions"));
          setReason("");
          await openStaff(staffId);
        }
      );
    },
    [openStaff, queueCriticalAction, reason, request, setReason]
  );

  return {
    staff,
    selectedStaff,
    staffActivity,
    staffFilters,
    setStaffFilters,
    staffInvite,
    setStaffInvite,
    loadStaff,
    openStaff,
    submitStaffInvite,
    changeStaffStatus,
    replaceStaffPermissions
  };
}
