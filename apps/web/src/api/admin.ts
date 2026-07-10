import type { AuthenticatedRequest } from "./client";

function listParams(limit = 20, key?: string, value?: string) {
  const params = new URLSearchParams({ limit: String(limit) });
  if (key && value) {
    params.set(key, value);
  }
  return params.toString();
}

export function getAdminDashboard<T>(request: AuthenticatedRequest) {
  return request<T>("/api/v1/admin/dashboard");
}

export function getAdminMetrics<T>(request: AuthenticatedRequest) {
  return request<T>("/api/v1/admin/metrics");
}

export function listAdminBusinesses<T>(request: AuthenticatedRequest, status?: string) {
  return request<T>(`/api/v1/admin/businesses?${listParams(20, "verification_status", status)}`);
}

export function listPendingAdminBusinesses<T>(request: AuthenticatedRequest) {
  return request<T>("/api/v1/admin/businesses/pending?limit=20");
}

export function getAdminBusiness<T>(request: AuthenticatedRequest, businessId: string) {
  return request<T>(`/api/v1/admin/businesses/${businessId}`);
}

export function reviewAdminBusiness<T>(request: AuthenticatedRequest, businessId: string, action: "approve" | "reject", reason: string, idempotencyKey: string) {
  return request<T>(`/api/v1/admin/businesses/${businessId}/${action}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Idempotency-Key": idempotencyKey
    },
    body: JSON.stringify({ reason })
  });
}

export function getAdminBusinessDocumentViewUrl<T>(request: AuthenticatedRequest, businessId: string, fileId: string, reason: string) {
  return request<T>(`/api/v1/admin/businesses/${businessId}/verification-documents/${fileId}/view-url`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ reason })
  });
}

export function listAdminOrders<T>(request: AuthenticatedRequest, status?: string) {
  return request<T>(`/api/v1/admin/orders?${listParams(20, "status", status)}`);
}

export function getAdminOrder<T>(request: AuthenticatedRequest, orderId: string) {
  return request<T>(`/api/v1/admin/orders/${orderId}`);
}

export function listAdminDisputes<T>(request: AuthenticatedRequest, status?: string) {
  return request<T>(`/api/v1/admin/disputes?${listParams(20, "status", status)}`);
}

export function getAdminDispute<T>(request: AuthenticatedRequest, disputeId: string) {
  return request<T>(`/api/v1/admin/disputes/${disputeId}`);
}

export function resolveAdminDispute<T>(request: AuthenticatedRequest, disputeId: string, resolutionType: string, reason: string, idempotencyKey: string) {
  return request<T>(`/api/v1/admin/disputes/${disputeId}/resolve`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Idempotency-Key": idempotencyKey
    },
    body: JSON.stringify({ resolution_type: resolutionType, reason })
  });
}

export function listAdminAuditLogs<T>(request: AuthenticatedRequest, eventType?: string) {
  return request<T>(`/api/v1/admin/audit-logs?${listParams(20, "event_type", eventType)}`);
}

export function listAdminCreditPurchases<T>(request: AuthenticatedRequest, status?: string) {
  return request<T>(`/api/v1/admin/credit-purchases?${listParams(20, "status", status)}`);
}

export function reviewAdminCreditPurchase<T>(request: AuthenticatedRequest, purchaseId: string, action: "approve" | "reject", reason: string, idempotencyKey: string) {
  return request<T>(`/api/v1/admin/credit-purchases/${purchaseId}/${action}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Idempotency-Key": idempotencyKey
    },
    body: JSON.stringify({ reason })
  });
}

export function submitAdminCreditAdjustment<T>(
  request: AuthenticatedRequest,
  payload: { business_id: string; amount: number; direction: "add" | "remove"; reason: string },
  idempotencyKey: string
) {
  return request<T>("/api/v1/admin/credits/adjust", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Idempotency-Key": idempotencyKey
    },
    body: JSON.stringify(payload)
  });
}

export function listAdminJobRuns<T>(request: AuthenticatedRequest) {
  return request<T>("/api/v1/admin/jobs/runs?limit=20");
}

export function listAdminBusinessIntakes<T>(request: AuthenticatedRequest, status?: string) {
  return request<T>(`/api/v1/admin/business-intake?${listParams(20, "status", status)}`);
}

export function getAdminBusinessIntake<T>(request: AuthenticatedRequest, intakeId: string) {
  return request<T>(`/api/v1/admin/business-intake/${intakeId}`);
}

export function deleteAdminBusinessIntake<T>(request: AuthenticatedRequest, intakeId: string, reason: string, idempotencyKey: string) {
  return request<T>(`/api/v1/admin/business-intake/${intakeId}/delete`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Idempotency-Key": idempotencyKey
    },
    body: JSON.stringify({ reason })
  });
}

export function acceptAdminBusinessIntake<T>(
  request: AuthenticatedRequest,
  intakeId: string,
  payload: { reason: string; create_business: boolean; public_business_name: string },
  idempotencyKey: string
) {
  return request<T>(`/api/v1/admin/business-intake/${intakeId}/accept`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Idempotency-Key": idempotencyKey
    },
    body: JSON.stringify(payload)
  });
}

export function dryRunExpireAndEscalateOrders<T>(request: AuthenticatedRequest, idempotencyKey: string) {
  return request<T>("/api/v1/admin/jobs/expire-and-escalate-orders/dry-run", {
    method: "POST",
    headers: { "Idempotency-Key": idempotencyKey }
  });
}
