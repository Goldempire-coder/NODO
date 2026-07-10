"use client";

import type { PublicUser } from "../../types/auth";
import { useBusinessMiniAppModel } from "../../hooks/useBusinessMiniAppModel";
import { BusinessMiniAppShell } from "./BusinessMiniAppShell";

export function BusinessMiniAppWorkspace(props: { user: PublicUser; token: string }) {
  const model = useBusinessMiniAppModel(props);
  return <BusinessMiniAppShell model={model} />;
}
