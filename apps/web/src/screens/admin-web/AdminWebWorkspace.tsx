"use client";

import { useAdminWebModel } from "../../hooks/useAdminWebModel";
import type { PublicUser } from "../../types/auth";
import { AdminWebShell } from "./AdminWebShell";

export function AdminWebWorkspace(props: {
  user: PublicUser;
  token: string;
  loggingOut?: boolean;
  onLogout: () => Promise<void> | void;
}) {
  const model = useAdminWebModel(props);
  return <AdminWebShell model={model} />;
}
