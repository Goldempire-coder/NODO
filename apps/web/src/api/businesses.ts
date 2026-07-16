import type { AuthenticatedRequest } from "./client";

export function listBusinessPaymentMethods<T>(request: AuthenticatedRequest) {
  return request<T>(`/api/v1/business/payment-methods?_=${Date.now()}`, {
    cache: "no-store"
  });
}

export function createBusinessPaymentMethod<T>(
  request: AuthenticatedRequest,
  payload: { method_type: "zelle" | "usdt_trc20"; account_value: string; holder_name: string },
  idempotencyKey: string
) {
  return request<T>("/api/v1/business/payment-methods", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Idempotency-Key": idempotencyKey
    },
    body: JSON.stringify(payload)
  });
}

export function updateBusinessPaymentMethod<T>(
  request: AuthenticatedRequest,
  paymentMethodId: string,
  payload: { account_value?: string; holder_name: string },
  idempotencyKey: string
) {
  return request<T>(`/api/v1/business/payment-methods/${paymentMethodId}`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
      "Idempotency-Key": idempotencyKey
    },
    body: JSON.stringify(payload)
  });
}

export function deleteBusinessPaymentMethod<T>(
  request: AuthenticatedRequest,
  paymentMethodId: string,
  idempotencyKey: string
) {
  return request<T>(`/api/v1/business/payment-methods/${paymentMethodId}`, {
    method: "DELETE",
    headers: { "Idempotency-Key": idempotencyKey }
  });
}

export function updateBusinessAvailability<T>(request: AuthenticatedRequest, acceptingOrders: boolean, idempotencyKey: string) {
  return request<T>("/api/v1/business/availability", {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
      "Idempotency-Key": idempotencyKey
    },
    body: JSON.stringify({ accepting_orders: acceptingOrders })
  });
}

export function setupBusinessPin<T>(request: AuthenticatedRequest, payload: { pin: string; current_pin?: string }) {
  return request<T>("/api/v1/business/security/pin/setup", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
}

export function verifyBusinessPin<T>(request: AuthenticatedRequest, pin: string) {
  return request<T>("/api/v1/business/security/pin/verify", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ pin })
  });
}

export function lockBusinessPin<T>(request: AuthenticatedRequest) {
  return request<T>("/api/v1/business/security/pin/lock", {
    method: "POST"
  });
}
