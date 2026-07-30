import type { AuthenticatedRequest } from "./client";

export function listBusinessOrders<T>(request: AuthenticatedRequest, status?: string, limit = 20) {
  const params = new URLSearchParams({ limit: String(limit) });
  if (status) {
    params.set("status", status);
  }
  return request<T>(`/api/v1/business/orders?${params.toString()}`);
}

export function getBusinessOrder<T>(request: AuthenticatedRequest, orderId: string) {
  return request<T>(`/api/v1/business/orders/${orderId}`);
}

export function mutateBusinessOrder<T>(
  request: AuthenticatedRequest,
  orderId: string,
  action: "confirm-payment" | "reject-payment-report" | "mark-delivered" | "cannot-attend",
  reason: string | undefined,
  idempotencyKey: string
) {
  return request<T>(`/api/v1/business/orders/${orderId}/${action}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Idempotency-Key": idempotencyKey
    },
    body: JSON.stringify({ reason })
  });
}

export function declineBusinessOrder<T>(
  request: AuthenticatedRequest,
  orderId: string,
  idempotencyKey: string
) {
  return request<T>(`/api/v1/business/orders/${orderId}/cannot-attend`, {
    method: "POST",
    headers: {
      "Idempotency-Key": idempotencyKey
    }
  });
}
