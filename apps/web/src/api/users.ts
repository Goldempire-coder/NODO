import type { AuthenticatedRequest } from "./client";
import type { ClientProfileFormState } from "../types/client";

export function acceptTerms<T>(request: AuthenticatedRequest, termsVersion: string) {
  return request<T>("/api/v1/users/me/terms-acceptance", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({ terms_version: termsVersion })
  });
}

export function saveClientProfile<T>(request: AuthenticatedRequest, profile: ClientProfileFormState) {
  return request<T>("/api/v1/users/me/profile", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(profile)
  });
}
