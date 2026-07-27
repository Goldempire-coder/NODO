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

export function listAdminOrders<T>(request: AuthenticatedRequest, status?: string) {
  return request<T>(`/api/v1/admin/orders?${listParams(20, "status", status)}`);
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

export function getAdminOrder<T>(request: AuthenticatedRequest, orderId: string) {
  return request<T>(`/api/v1/admin/orders/${orderId}`);
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

export function listAdminStaff<T>(request: AuthenticatedRequest, filters: { status?: string; staff_role?: string; q?: string }) {
  const params = new URLSearchParams({ limit: "20" });
  Object.entries(filters).forEach(([key, value]) => {
    if (value) {
      params.set(key, value);
    }
  });
  return request<T>(`/api/v1/admin/staff?${params.toString()}`);
}

export function getAdminStaff<T>(request: AuthenticatedRequest, staffId: string) {
  return request<T>(`/api/v1/admin/staff/${staffId}`);
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

export function listAdminStaffActivity<T>(request: AuthenticatedRequest, staffId: string) {
  return request<T>(`/api/v1/admin/staff/${staffId}/activity?limit=20`);
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
