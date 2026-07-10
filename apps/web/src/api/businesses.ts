import type { AuthenticatedRequest } from "./client";

export function listBusinessPaymentMethods<T>(request: AuthenticatedRequest) {
  return request<T>("/api/v1/business/payment-methods");
}
