"use client";

import type { PublicUser } from "../../types/auth";
import { useClientWorkspaceModel } from "../../hooks/useClientWorkspaceModel";
import { ClientWorkspaceShell } from "./ClientWorkspaceShell";

export function ClientWorkspace(props: { user: PublicUser; token: string }) {
  const model = useClientWorkspaceModel(props);
  return <ClientWorkspaceShell model={model} />;
}
