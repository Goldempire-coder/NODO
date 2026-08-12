import type {
  AdminDisputeDetailResponse,
  AdminDisputeListResponse,
  AdminDisputeResolveResponse,
  AdminOrderDetailResponse,
  AdminOrderDisputeOpenResponse,
  AdminOrderListResponse,
  AdminStaffActivityResponse,
  AdminStaffDetailResponse,
  AdminStaffListResponse
} from "../types/admin";
import type { AuthenticatedRequest } from "./client";

function listParams(limit = 20, key?: string, value?: string, cursor?: string | null) {
  const params = new URLSearchParams({ limit: String(limit) });
  if (key && value) {
    params.set(key, value);
  }
  if (cursor) {
    params.set("cursor", cursor);
  }
  return params.toString();
}

export function getAdminDashboard<T>(request: AuthenticatedRequest) {
  return request<T>("/api/v1/admin/dashboard");
}

export function getAdminEmergencyMode<T>(request: AuthenticatedRequest) {
  return request<T>("/api/v1/admin/emergency-mode");
}

export function activateAdminEmergencyMode<T>(request: AuthenticatedRequest, payload: { reason: string; message?: string }, idempotencyKey: string) {
  return request<T>("/api/v1/admin/emergency-mode/activate", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Idempotency-Key": idempotencyKey
    },
    body: JSON.stringify(payload)
  });
}

export function deactivateAdminEmergencyMode<T>(request: AuthenticatedRequest, reason: string, idempotencyKey: string) {
  return request<T>("/api/v1/admin/emergency-mode/deactivate", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Idempotency-Key": idempotencyKey
    },
    body: JSON.stringify({ reason })
  });
}

export function getAdminMetrics<T>(request: AuthenticatedRequest) {
  return request<T>("/api/v1/admin/metrics");
}

export function getAdminIncidentConsole<T>(request: AuthenticatedRequest) {
  return request<T>("/api/v1/admin/incident-console");
}

export function getAdminUXFriction<T>(request: AuthenticatedRequest) {
  return request<T>("/api/v1/admin/ux-friction");
}

export function searchAdminInvestigation<T>(request: AuthenticatedRequest, query: string, limit = 20) {
  const params = new URLSearchParams({ q: query, limit: String(limit) });
  return request<T>(`/api/v1/admin/investigation/search?${params.toString()}`, { cache: "no-store" });
}

export function searchAdminInvestigationCandidates<T>(
  request: AuthenticatedRequest,
  filters: {
    client_hint?: string;
    business_hint?: string;
    amount_min_usd?: string;
    amount_max_usd?: string;
    created_from?: string;
    created_to?: string;
    order_status?: string;
    support_status_group: "all" | "active" | "archived";
  },
  cursor?: string,
  limit = 10
) {
  const params = new URLSearchParams({
    support_status_group: filters.support_status_group,
    limit: String(limit)
  });
  for (const [key, value] of Object.entries(filters)) {
    if (key !== "support_status_group" && value?.trim()) {
      params.set(key, value.trim());
    }
  }
  if (cursor) {
    params.set("cursor", cursor);
  }
  return request<T>(`/api/v1/admin/investigation/order-candidates?${params.toString()}`, { cache: "no-store" });
}

export function getAdminInvestigationCaseFile<T>(
  request: AuthenticatedRequest,
  options: {
    anchorType: string;
    anchorId: string;
    section?: string;
    cursor?: string;
    limit?: number;
    includeArchived?: boolean;
  }
) {
  const params = new URLSearchParams({
    anchor_type: options.anchorType,
    anchor_id: options.anchorId,
    section: options.section ?? "all",
    limit: String(options.limit ?? 25),
    include_archived: String(options.includeArchived ?? true)
  });
  if (options.cursor) {
    params.set("cursor", options.cursor);
  }
  return request<T>(`/api/v1/admin/investigation/case-file?${params.toString()}`, { cache: "no-store" });
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

export function listAdminBusinessAccessLinks<T>(request: AuthenticatedRequest, businessId: string) {
  return request<T>(`/api/v1/admin/businesses/${businessId}/access-links`);
}

export function createAdminBusinessAccessLink<T>(request: AuthenticatedRequest, businessId: string, payload: { user_id: string; role_in_business: string; reason: string }, idempotencyKey: string) {
  return request<T>(`/api/v1/admin/businesses/${businessId}/access-links`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Idempotency-Key": idempotencyKey
    },
    body: JSON.stringify(payload)
  });
}

export function updateAdminBusinessAccessLink<T>(request: AuthenticatedRequest, businessId: string, linkId: string, action: "suspend" | "reactivate" | "revoke" | "block", reason: string, idempotencyKey: string) {
  return request<T>(`/api/v1/admin/businesses/${businessId}/access-links/${linkId}/${action}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Idempotency-Key": idempotencyKey
    },
    body: JSON.stringify({ reason })
  });
}

export function updateAdminBusinessCapacity<T>(
  request: AuthenticatedRequest,
  businessId: string,
  payload: {
    trust_level: string;
    min_order_amount_usd: string;
    max_order_amount_usd: string;
    daily_limit_usd: string;
    active_order_limit: number;
    reason: string;
  },
  idempotencyKey: string
) {
  return request<T>(`/api/v1/admin/businesses/${businessId}/capacity`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Idempotency-Key": idempotencyKey
    },
    body: JSON.stringify(payload)
  });
}

export function getAdminBusinessOperationalCapacity<T>(
  request: AuthenticatedRequest,
  businessId: string
) {
  return request<T>(`/api/v1/admin/businesses/${businessId}/capacity`, {
    cache: "no-store"
  });
}

export function updateAdminBusinessOperationalCapacity<T>(
  request: AuthenticatedRequest,
  businessId: string,
  payload: { declared_available_capacity_usd: string; reason?: string },
  idempotencyKey: string
) {
  return request<T>(`/api/v1/admin/businesses/${businessId}/capacity`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
      "Idempotency-Key": idempotencyKey
    },
    body: JSON.stringify(payload)
  });
}

export function getAdminBusinessDocumentViewUrl<T>(request: AuthenticatedRequest, businessId: string, fileId: string, reason: string) {
  return request<T>(`/api/v1/admin/businesses/${businessId}/verification-documents/${fileId}/view-url`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ reason })
  });
}

export function listAdminOrders(request: AuthenticatedRequest, status?: string, cursor?: string | null) {
  return request<AdminOrderListResponse>(`/api/v1/admin/orders?${listParams(20, "status", status, cursor)}`);
}

export function listAdminUsers<T>(request: AuthenticatedRequest, filters: { phone?: string; telegram_id?: string; username?: string; role?: string; status?: string }) {
  const params = new URLSearchParams({ limit: "20" });
  Object.entries(filters).forEach(([key, value]) => {
    if (value) {
      params.set(key, value);
    }
  });
  return request<T>(`/api/v1/admin/users?${params.toString()}`);
}

export function getAdminUser<T>(request: AuthenticatedRequest, userId: string) {
  return request<T>(`/api/v1/admin/users/${userId}`);
}

export function listAdminUserAccessLinks<T>(request: AuthenticatedRequest, userId: string) {
  return request<T>(`/api/v1/admin/users/${userId}/access-links`);
}

export function updateAdminUserStatus<T>(request: AuthenticatedRequest, userId: string, action: "suspend" | "reactivate" | "block", reason: string, idempotencyKey: string) {
  return request<T>(`/api/v1/admin/users/${userId}/${action}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Idempotency-Key": idempotencyKey
    },
    body: JSON.stringify({ reason })
  });
}

export function getAdminOrder(request: AuthenticatedRequest, orderId: string) {
  return request<AdminOrderDetailResponse>(`/api/v1/admin/orders/${orderId}`);
}

export function getAdminOrderChatEvidence<T>(
  request: AuthenticatedRequest,
  orderId: string,
  options: { cursor?: string; direction?: "older" | "newer"; highlightMessageId?: string; limit?: number } = {}
) {
  const params = new URLSearchParams({ limit: String(options.limit ?? 50) });
  if (options.cursor) {
    params.set("cursor", options.cursor);
  }
  if (options.direction) {
    params.set("direction", options.direction);
  }
  if (options.highlightMessageId) {
    params.set("highlight_message_id", options.highlightMessageId);
  }
  return request<T>(`/api/v1/admin/orders/${orderId}/chat-evidence?${params.toString()}`, { cache: "no-store" });
}

export function listAdminDisputes(request: AuthenticatedRequest, status?: string, cursor?: string | null) {
  return request<AdminDisputeListResponse>(`/api/v1/admin/disputes?${listParams(20, "status", status, cursor)}`);
}

export function getAdminDispute(request: AuthenticatedRequest, disputeId: string) {
  return request<AdminDisputeDetailResponse>(`/api/v1/admin/disputes/${disputeId}`);
}

export function openAdminOrderDispute(
  request: AuthenticatedRequest,
  orderId: string,
  reason: string,
  idempotencyKey: string
) {
  return request<AdminOrderDisputeOpenResponse>(`/api/v1/admin/orders/${orderId}/open-dispute`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Idempotency-Key": idempotencyKey
    },
    body: JSON.stringify({ reason })
  });
}

export function resolveAdminDispute(request: AuthenticatedRequest, disputeId: string, resolutionType: string, reason: string, idempotencyKey: string) {
  return request<AdminDisputeResolveResponse>(`/api/v1/admin/disputes/${disputeId}/resolve`, {
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
  const normalizedStatus = status?.trim().toLowerCase();
  const filter = normalizedStatus && normalizedStatus !== "all" ? normalizedStatus : undefined;
  return request<T>(`/api/v1/admin/business-intake?${listParams(20, "status", filter)}`);
}

export function getAdminBusinessIntake<T>(request: AuthenticatedRequest, intakeId: string) {
  return request<T>(`/api/v1/admin/business-intake/${intakeId}`);
}

export function getAdminBusinessIntakeDocumentViewUrl<T>(request: AuthenticatedRequest, intakeId: string, fileId: string, reason: string) {
  return request<T>(`/api/v1/admin/business-intake/${intakeId}/documents/${fileId}/view-url`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(reason.trim() ? { reason } : {})
  });
}

export function updateAdminBusinessIntake<T>(
  request: AuthenticatedRequest,
  intakeId: string,
  payload: Record<string, unknown>
) {
  return request<T>(`/api/v1/admin/business-intake/${intakeId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
}

export function deleteAdminBusinessIntake<T>(request: AuthenticatedRequest, intakeId: string, idempotencyKey: string, reason?: string) {
  return request<T>(`/api/v1/admin/business-intake/${intakeId}/delete`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Idempotency-Key": idempotencyKey
    },
    body: JSON.stringify(reason?.trim() ? { reason } : {})
  });
}

export function acceptAdminBusinessIntake<T>(
  request: AuthenticatedRequest,
  intakeId: string,
  payload: { reason?: string; create_business: boolean; public_business_name?: string; approve_business?: boolean },
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

export function listAdminStaff(request: AuthenticatedRequest, filters: { status?: string; staff_role?: string; q?: string; cursor?: string; limit?: number }) {
  const { limit = 20, ...query } = filters;
  const params = new URLSearchParams({ limit: String(limit) });
  Object.entries(query).forEach(([key, value]) => {
    if (value) {
      params.set(key, value);
    }
  });
  return request<AdminStaffListResponse>(`/api/v1/admin/staff?${params.toString()}`);
}

export function getAdminStaff(request: AuthenticatedRequest, staffId: string) {
  return request<AdminStaffDetailResponse>(`/api/v1/admin/staff/${staffId}`);
}

export function createAdminStaffInvite<T>(
  request: AuthenticatedRequest,
  payload: {
    target_user_id?: string;
    target_telegram_id?: string;
    target_username?: string;
    staff_role: string;
    permissions: Array<{ permission: string; scope: string; scope_value?: string | null }>;
    expires_at: string;
    reason: string;
  },
  idempotencyKey: string
) {
  return request<T>("/api/v1/admin/staff/invites", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Idempotency-Key": idempotencyKey
    },
    body: JSON.stringify(payload)
  });
}

export function updateAdminStaffStatus<T>(request: AuthenticatedRequest, staffId: string, action: "activate" | "suspend" | "revoke", reason: string, idempotencyKey: string) {
  return request<T>(`/api/v1/admin/staff/${staffId}/${action}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Idempotency-Key": idempotencyKey
    },
    body: JSON.stringify({ reason })
  });
}

export function updateAdminStaffPermissions<T>(
  request: AuthenticatedRequest,
  staffId: string,
  permissions: Array<{ permission: string; scope: string; scope_value?: string | null }>,
  reason: string,
  idempotencyKey: string
) {
  return request<T>(`/api/v1/admin/staff/${staffId}/permissions`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Idempotency-Key": idempotencyKey
    },
    body: JSON.stringify({ permissions, reason })
  });
}

export function listAdminStaffActivity(request: AuthenticatedRequest, staffId: string) {
  return request<AdminStaffActivityResponse>(`/api/v1/admin/staff/${staffId}/activity?limit=20`);
}

export function listAdminNotifications<T>(request: AuthenticatedRequest, status = "unread") {
  const params = new URLSearchParams({ limit: "20" });
  if (status) {
    params.set("status", status);
  }
  return request<T>(`/api/v1/admin/notifications?${params.toString()}`);
}

export function getAdminNotificationsUnreadCount<T>(request: AuthenticatedRequest) {
  return request<T>("/api/v1/admin/notifications/unread-count");
}

export function markAdminNotificationRead<T>(request: AuthenticatedRequest, notificationId: string) {
  return request<T>(`/api/v1/admin/notifications/${notificationId}/read`, { method: "POST" });
}

export function dismissAdminNotification<T>(request: AuthenticatedRequest, notificationId: string) {
  return request<T>(`/api/v1/admin/notifications/${notificationId}/dismiss`, { method: "POST" });
}

export function resolveAdminNotification<T>(request: AuthenticatedRequest, notificationId: string) {
  return request<T>(`/api/v1/admin/notifications/${notificationId}/resolve`, { method: "POST" });
}
