import type { AuthenticatedRequest } from "./client";

export function getBusinessSurfaceSession<T>(request: AuthenticatedRequest) {
  return request<T>("/api/v1/surface/session", {
    headers: { "X-NODO-Surface": "business_mini_app" }
  });
}
