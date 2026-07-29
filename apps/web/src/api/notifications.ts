import type { AuthenticatedRequest } from "./client";
import type { SurfaceAttentionAcknowledgeRequest, SurfaceAttentionSummary } from "../types/notifications";

export function getSurfaceAttentionSummary(request: AuthenticatedRequest) {
  return request<SurfaceAttentionSummary>("/api/v1/notifications/attention-summary", {
    cache: "no-store"
  });
}

export function acknowledgeSurfaceAttention(
  request: AuthenticatedRequest,
  payload: SurfaceAttentionAcknowledgeRequest
) {
  return request<{ acknowledged: boolean }>("/api/v1/notifications/attention/acknowledge", {
    method: "POST",
    cache: "no-store",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
}
