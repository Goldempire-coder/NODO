import type { AuthenticatedRequest } from "./client";
import type { AdFormState, AdUpdatePayload } from "../types/ads";

export function listBusinessAds<T>(request: AuthenticatedRequest, limit = 20) {
  return request<T>(`/api/v1/business/ads?limit=${limit}`);
}

export function listArchivedBusinessAds<T>(request: AuthenticatedRequest, limit = 20) {
  return request<T>(`/api/v1/business/ads/archived?limit=${limit}`);
}

export function createBusinessAd<T>(request: AuthenticatedRequest, payload: AdFormState & { business_id: string }, idempotencyKey: string) {
  return request<T>("/api/v1/business/ads", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Idempotency-Key": idempotencyKey
    },
    body: JSON.stringify(payload)
  });
}

export function mutateBusinessAd<T>(request: AuthenticatedRequest, adId: string, action: "pause" | "archive" | "reactivate" | "republish", idempotencyKey: string) {
  return request<T>(`/api/v1/business/ads/${adId}/${action}`, {
    method: "POST",
    headers: { "Idempotency-Key": idempotencyKey }
  });
}

export function updateBusinessAd<T>(request: AuthenticatedRequest, adId: string, payload: AdUpdatePayload, idempotencyKey: string) {
  return request<T>(`/api/v1/business/ads/${adId}`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
      "Idempotency-Key": idempotencyKey
    },
    body: JSON.stringify(payload)
  });
}
