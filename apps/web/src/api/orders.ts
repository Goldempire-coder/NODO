import type { AuthenticatedRequest } from "./client";

export type CreateOrderPayload = {
  ad_id: string;
  amount_usd: string;
  receiver_data: {
    bank: string;
    phone: string;
    document: string;
    holder: string;
  };
};

export function createRemitterOrder<T>(request: AuthenticatedRequest, payload: CreateOrderPayload, idempotencyKey: string) {
  return request<T>("/api/v1/orders", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Idempotency-Key": idempotencyKey
    },
    body: JSON.stringify(payload)
  });
}

export function listMyOrders<T>(request: AuthenticatedRequest, limit = 20) {
  return request<T>(`/api/v1/orders/mine?limit=${limit}`);
}

export function getOrder<T>(request: AuthenticatedRequest, orderId: string) {
  return request<T>(`/api/v1/orders/${orderId}`);
}

export function extendPaymentDeadline<T>(request: AuthenticatedRequest, orderId: string, reason: string, idempotencyKey: string) {
  return request<T>(`/api/v1/orders/${orderId}/extend-payment-deadline`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Idempotency-Key": idempotencyKey
    },
    body: JSON.stringify({ reason })
  });
}

export function cancelRemitterOrder<T>(request: AuthenticatedRequest, orderId: string, reason: string, idempotencyKey: string) {
  return request<T>(`/api/v1/orders/${orderId}/cancel`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Idempotency-Key": idempotencyKey
    },
    body: JSON.stringify({ reason })
  });
}

export function submitOrderRating<T>(request: AuthenticatedRequest, orderId: string, stars: number, idempotencyKey: string) {
  return request<T>(`/api/v1/orders/${orderId}/rating`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Idempotency-Key": idempotencyKey
    },
    body: JSON.stringify({ stars })
  });
}
