import type { AuthenticatedRequest } from "./client";
import type { SurfaceAttentionSummary } from "../types/notifications";

export function getSurfaceAttentionSummary(request: AuthenticatedRequest) {
  return request<SurfaceAttentionSummary>("/api/v1/notifications/attention-summary", {
    cache: "no-store"
  });
}
