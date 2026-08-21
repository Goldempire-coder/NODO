import type { BusinessOperationalCapacity, BusinessSummary } from "./business";
import type { AdminCreditPurchaseDetail, AdminCreditPurchaseSummary } from "./credits";
import type { SupportTicket } from "./support";

export type AdminBusinessPublicationHold = {
  id: string;
  business_id: string;
  order_id: string;
  support_ticket_id: string;
  status: "active" | "released";
  reason_type: "structured_operation_report";
  created_at: string;
  released_at: string | null;
  released_by: string | null;
  release_reason: string | null;
};

export type AdminSupportTicket = SupportTicket & {
  publication_hold?: AdminBusinessPublicationHold | null;
};

export type AdminSupportTicketListResponse = {
  items: AdminSupportTicket[];
  next_cursor: string | null;
};

export type AdminTelegramAlertLinkCodeResponse = {
  code: string;
  expires_at: string;
  instructions: string;
};

export type AdminPublicationHoldReleaseResponse = {
  hold: AdminBusinessPublicationHold;
};

export type DocumentFile = {
  id: string;
  file_type: string;
  mime_type: string;
  size_bytes: number;
  created_at: string;
};

export type AdminBusinessAccessDiagnostic = {
  business_status: string;
  business_risk_level: string;
  business_can_access_surface: boolean;
  owner_user_id: string;
  owner_user_status: string;
  owner_role_valid: boolean;
  owner_link_id: string | null;
  owner_link_status: string;
  owner_link_role: string | null;
  owner_link_conflict: boolean;
  telegram_matches: boolean | null;
  blocking_reason: string | null;
  recommended_admin_action:
    | "none"
    | "unblock_business"
    | "reactivate_business"
    | "review_business_approval"
    | "unblock_owner_user"
    | "reactivate_owner_user"
    | "reactivate_owner_link"
    | "create_owner_link"
    | "regenerate_owner_link"
    | "review_owner_binding";
};

export type AdminBusinessDetail = {
  business: BusinessSummary & {
    address?: string | null;
    owner_user_id?: string | null;
    trust_level?: string;
    risk_level?: string;
    min_order_amount_usd?: string;
    max_order_amount_usd?: string;
    daily_limit_usd?: string;
    active_order_limit?: number;
    created_at?: string;
    updated_at?: string;
  };
  access_diagnostic: AdminBusinessAccessDiagnostic;
  latest_submission: {
    id: string;
    status: string;
    submitted_data: Record<string, unknown>;
    submitted_at: string;
    reviewed_at: string | null;
  } | null;
  documents: DocumentFile[];
  referrals: {
    referred_by: {
      business_id: string;
      business_name: string;
    } | null;
    code_used: string | null;
    earned_credits: number;
    remaining_bonus_credits: number;
    cap: number;
    referred_businesses_truncated: boolean;
    referred_businesses: Array<{
      business_id: string;
      business_name: string | null;
      status: string;
      credits_awarded: number;
      created_at: string;
      rewarded_at: string | null;
    }>;
  };
};

export type AdminBusinessSummary = {
  id: string;
  business_name?: string;
  display_name?: string;
  verification_status?: string;
  risk_level?: string;
  trust_level?: string;
  created_at?: string;
  submitted_at?: string | null;
};

export type AdminBusinessListResponse = {
  items: AdminBusinessSummary[];
  next_cursor: string | null;
  disclaimer?: string;
};

export type AdminBusinessOperationalCapacity = BusinessOperationalCapacity & {
  updated_by_user_id?: string | null;
  active_reservations: Array<{
    order_id: string;
    amount_usd: string;
    status: "reserved";
    created_at: string;
  }>;
  daily_orders: Array<{
    order_id: string;
    amount_usd: string;
    capacity_status: "reserved" | "consumed";
    created_at: string;
    consumed_at: string | null;
  }>;
  daily_orders_truncated: boolean;
};

export type AdminBusinessAccessLink = {
  id: string;
  business_id: string;
  user_id: string;
  telegram_id?: number | null;
  telegram_id_masked?: string | null;
  role_in_business: string;
  status: string;
  reason?: string | null;
  linked_by_admin_id?: string | null;
  linked_at?: string | null;
  suspended_at?: string | null;
  blocked_at?: string | null;
  revoked_at?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
  user?: {
    id: string;
    username?: string | null;
    first_name?: string | null;
    last_name?: string | null;
    phone_masked?: string | null;
    telegram_id_masked?: string | null;
    role?: string | null;
    status?: string | null;
  } | null;
  business?: {
    id: string;
    business_name?: string | null;
    display_name?: string | null;
    verification_status?: string | null;
  } | null;
};

export type AdminUserSummary = {
  id: string;
  telegram_id?: number | null;
  telegram_id_masked?: string | null;
  username?: string | null;
  first_name?: string | null;
  last_name?: string | null;
  phone?: string | null;
  phone_masked?: string | null;
  role: string;
  status: string;
  trust_level?: string | null;
  terms_version?: string | null;
  terms_accepted_at?: string | null;
  last_seen_at?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
};

export type AdminUserListResponse = {
  items: AdminUserSummary[];
  next_cursor: string | null;
  disclaimer?: string;
};

export type AdminUserDetail = {
  user: AdminUserSummary & {
    order_counts?: Record<string, number>;
    businesses?: {
      id: string;
      business_name?: string | null;
      display_name?: string | null;
      verification_status?: string | null;
      risk_level?: string | null;
    }[];
  };
  access_links: AdminBusinessAccessLink[];
  capabilities: {
    can_mutate_status: boolean;
    can_view_sensitive: boolean;
  };
  disclaimer: string;
};

export type AdminInvestigationResultType = "user" | "business" | "business_intake" | "order" | "support_ticket";

export type AdminInvestigationSearchItem = {
  type: AdminInvestigationResultType;
  id: string;
  title: string;
  subtitle: string;
  matched_on: string[];
  action_route: string;
  status?: string | null;
  reference?: string | null;
  created_at?: string | null;
  context: Record<string, string | number | boolean | null | undefined>;
};

export type AdminInvestigationSearchResponse = {
  groups: {
    users: AdminInvestigationSearchItem[];
    businesses: AdminInvestigationSearchItem[];
    business_intakes: AdminInvestigationSearchItem[];
    orders: AdminInvestigationSearchItem[];
    support_tickets: AdminInvestigationSearchItem[];
  };
  result_counts: Record<string, number>;
  disclaimer: string;
};

export type AdminInvestigationCandidateFilters = {
  client_hint: string;
  business_hint: string;
  amount_min_usd: string;
  amount_max_usd: string;
  created_from: string;
  created_to: string;
  order_status: string;
  support_status_group: "all" | "active" | "archived";
};

export type AdminInvestigationCandidate = {
  type: "order_candidate";
  order_id: string;
  public_order_code: string;
  status: string;
  amount_usd: string;
  created_at: string;
  updated_at: string;
  business: {
    business_id: string;
    name: string;
    status: string;
    action_route: string;
  };
  client: {
    user_id: string;
    display_name: string;
    telegram_hint?: string | null;
    action_route: string;
  };
  signals: string[];
  payment_report_present: boolean;
  support_ticket_count: number;
  case_file_route: string;
  order_route: string;
};

export type AdminInvestigationCandidatesResponse = {
  items: AdminInvestigationCandidate[];
  next_cursor?: string | null;
  truncated: boolean;
  disclaimer: string;
};

export type AdminInvestigationCaseFileSectionName =
  | "orders"
  | "support_tickets"
  | "business_intakes"
  | "evidence"
  | "timeline";

export type AdminInvestigationCaseFilePage<T> = {
  status: "ok" | "not_requested" | "partial_error" | "error";
  items: T[];
  truncated: boolean;
  next_cursor?: string | null;
  total_count?: number | null;
  error?: { code: string; message: string } | null;
};

export type AdminInvestigationCaseFile = {
  anchor: {
    type: AdminInvestigationResultType;
    id: string;
    title: string;
    status?: string | null;
    action_route: string;
  };
  summary: {
    case_title: string;
    anchor_reason: string;
    last_activity_at?: string | null;
    counts: {
      orders: number;
      support_tickets: number;
      business_intakes: number;
      timeline_events?: number | null;
    };
  };
  participants: {
    client?: {
      user_id: string;
      display_name: string;
      telegram_hint?: string | null;
      action_route: string;
    } | null;
    business?: {
      business_id: string;
      name: string;
      status: string;
      action_route: string;
    } | null;
    business_owner?: {
      user_id: string;
      telegram_hint?: string | null;
      action_route: string;
    } | null;
  };
  orders: AdminInvestigationCaseFilePage<{
    id: string;
    public_order_code: string;
    status: string;
    business_id: string;
    remitter_user_id: string;
    amount_usd: string;
    created_at: string;
    updated_at: string;
    action_route: string;
  }>;
  support_tickets: AdminInvestigationCaseFilePage<{
    id: string;
    status: string;
    scope: string;
    category: string;
    priority: string;
    requester_user_id: string;
    business_id?: string | null;
    order_id?: string | null;
    created_at: string;
    updated_at: string;
    action_route: string;
  }>;
  business_intakes: AdminInvestigationCaseFilePage<{
    id: string;
    status: string;
    referral_code?: string | null;
    business_name?: string | null;
    city?: string | null;
    created_business_id?: string | null;
    created_at: string;
    submitted_at?: string | null;
    reviewed_at?: string | null;
    action_route: string;
  }>;
  evidence: {
    status: "ok" | "not_requested" | "partial_error" | "error";
    payment_report_present: boolean;
    chat_evidence_available: boolean;
    chat_action_routes: string[];
    documents: Array<{
      document_type: string;
      mime_type: string;
      size_bytes: number;
      created_at: string;
      download_available: boolean;
      action_route: string;
    }>;
    attachments: Array<{
      attachment_type: string;
      mime_type: string;
      size_bytes: number;
      created_at: string;
      download_available: boolean;
      action_route: string;
    }>;
    truncated: boolean;
    next_cursor?: string | null;
    total_count?: number | null;
    error?: { code: string; message: string } | null;
  };
  timeline: AdminInvestigationCaseFilePage<{
    id: string;
    event_type: string;
    label: string;
    entity_type: string;
    entity_id: string;
    from_status?: string | null;
    to_status?: string | null;
    created_at: string;
    action_route: string;
  }>;
  review_checklist: Array<{
    code: string;
    label: string;
    status: "present" | "missing" | "not_checked" | "not_authorized";
    action_route?: string | null;
  }>;
  warnings: Array<{ code: string; section?: string; message: string }>;
  disclaimer: string;
};

export type AdminDashboard = {
  emergency_mode?: AdminEmergencyMode;
  queues: {
    pending_businesses: number;
    pending_business_intakes?: number;
    pending_credit_purchases: number;
    open_disputes: number;
  };
  orders: {
    active_count: number;
    disputed_count: number;
    delivered_waiting_close_count: number;
  };
  credits: {
    manual_review_count: number;
  };
  risk: {
    businesses_under_review: number;
  };
  disclaimer: string;
};

export type AdminStaffPermissionInput = {
  permission: string;
  scope: string;
  scope_value?: string | null;
};

export type AdminStaffSummary = {
  id: string;
  user_id: string;
  display_name?: string | null;
  username?: string | null;
  staff_role: string;
  status: string;
  permission_count: number;
  last_activity_at?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
};

export type AdminStaffDetail = AdminStaffSummary & {
  user_status?: string | null;
  base_role?: string | null;
  permissions: Array<AdminStaffPermissionInput & { id?: string; status: string }>;
  reason?: string | null;
};

export type AdminStaffActivityItem = {
  event_type: string;
  actor_role?: string | null;
  resource_type?: string | null;
  resource_id?: string | null;
  created_at?: string | null;
};

export type AdminStaffListResponse = {
  items: AdminStaffSummary[];
  next_cursor?: string | null;
  disclaimer: string;
};

export type AdminStaffDetailResponse = {
  staff: AdminStaffDetail;
  disclaimer: string;
};

export type AdminStaffActivityResponse = {
  items: AdminStaffActivityItem[];
  next_cursor?: string | null;
  disclaimer: string;
};

export type AdminEmergencyMode = {
  enabled: boolean;
  reason?: string | null;
  message?: string | null;
  activated_by_user_id?: string | null;
  activated_at?: string | null;
  deactivated_by_user_id?: string | null;
  deactivated_at?: string | null;
  updated_at?: string | null;
};

export type AdminMetrics = {
  source: string;
  table_created: boolean;
  businesses: Record<string, number>;
  orders: Record<string, number>;
  disputes: Record<string, number>;
  credits: Record<string, number>;
  disclaimer: string;
};

export type AdminIncidentStatus = "healthy" | "attention" | "degraded" | "critical";

export type AdminIncidentConsole = {
  status: AdminIncidentStatus;
  generated_at?: string | null;
  environment: string;
  version: string;
  build_id: string;
  emergency_mode: AdminEmergencyMode;
  dependencies: {
    ok: boolean;
    status: string;
    checks: Record<string, { ok?: boolean; code?: string | null; message?: string | null }>;
  };
  queues: Record<string, number>;
  orders: Record<string, number>;
  jobs: {
    status_counts: Record<string, number>;
    recent_runs: AdminWebJobRun[];
    recent_failed: AdminWebJobRun[];
  };
  notifications: {
    status_counts: Record<string, number>;
    pending_due: number;
    recent_problems: Array<{
      id: string;
      notification_type: string;
      status: string;
      recipient_role?: string | null;
      recipient_user_id?: string | null;
      order_id?: string | null;
      business_id?: string | null;
      attempts: number;
      last_error_code?: string | null;
      created_at: string;
      updated_at: string;
    }>;
  };
  recent_audit: AdminAuditLog[];
  recommended_actions: string[];
  disclaimer: string;
};

export type AdminUXFriction = {
  ingest_enabled: boolean;
  window_hours: number;
  total_events: number;
  unique_sessions: number;
  friction_events: number;
  surfaces: Array<{
    surface: string;
    event_count: number;
    friction_count: number;
    screen_views: number;
    api_failures: number;
    slow_events: number;
  }>;
  top_screens: Array<{
    surface: string;
    screen: string;
    views: number;
    friction_count: number;
    slow_count: number;
    failure_count: number;
    p95_duration_ms?: number | null;
  }>;
  top_actions: Array<{
    surface: string;
    action: string;
    started: number;
    completed: number;
    failed: number;
    slow_count: number;
    friction_count: number;
    p95_duration_ms?: number | null;
  }>;
  api_failures: Array<{
    surface: string;
    route_template: string;
    count: number;
    friction_count: number;
    status_counts: Record<string, number>;
    error_codes: Record<string, number>;
  }>;
  recent_friction: Array<{
    event_type: string;
    surface: string;
    screen?: string | null;
    action?: string | null;
    route_template?: string | null;
    status_code?: number | null;
    error_code?: string | null;
    duration_ms?: number | null;
    occurred_at?: string | null;
  }>;
  recommended_actions: string[];
  disclaimer: string;
};

export type AdminOrderSummary = {
  id: string;
  public_order_code: string;
  status: string;
  business_id: string;
  remitter_user_id: string;
  amount_usd: string;
  amount_bs_calculated: string;
  payment_method_snapshot: string;
  delivery_method_snapshot: string;
  created_at: string;
};

export type AdminOrderListResponse = {
  items: AdminOrderSummary[];
  next_cursor: string | null;
  disclaimer?: string;
};

export type AdminOrderDetailResponse = {
  order: AdminOrderSummary;
  payment_report?: Record<string, unknown> | null;
  timeline?: Record<string, unknown>[];
  disclaimer?: string;
};

export type AdminOrderChatEvidenceAttachment = {
  attachment_id: string;
  mime_type: string;
  size_bytes: number;
  download_available: boolean;
};

export type AdminOrderChatEvidenceMessage = {
  message_id: string;
  sender_role: string;
  sender_label: string;
  body?: string | null;
  status: string;
  created_at: string;
  highlighted: boolean;
  attachments: AdminOrderChatEvidenceAttachment[];
};

export type AdminOrderChatEvidence = {
  order_id: string;
  items: AdminOrderChatEvidenceMessage[];
  older_cursor?: string | null;
  newer_cursor?: string | null;
  highlight_message_id?: string | null;
  highlight_found: boolean;
};

export type AdminDisputeSummary = {
  id: string;
  order_id: string;
  status: string;
  reason: string;
  description?: string | null;
  previous_order_status: string;
  resolution_type?: string | null;
  created_at: string;
  resolved_at?: string | null;
};

export type AdminDisputeOrderSummary = {
  id: string;
  public_order_code?: string | null;
  status?: string | null;
  amount_usd?: string | null;
  business_id?: string | null;
  created_at?: string | null;
};

export type AdminDisputeListResponse = {
  items: AdminDisputeSummary[];
  next_cursor: string | null;
  disclaimer?: string;
};

export type AdminDisputeDetailResponse = {
  dispute: AdminDisputeSummary;
  order_summary?: AdminDisputeOrderSummary;
  events?: Record<string, unknown>[];
  messages?: Record<string, unknown>[];
  disclaimer?: string;
};

export type AdminDisputeResolveResponse = {
  dispute: AdminDisputeSummary;
  order: AdminDisputeOrderSummary;
  credit_effect?: Record<string, unknown> | null;
  ad?: Record<string, unknown> | null;
  disclaimer?: string;
};

export type AdminOrderDisputeOpenResponse = {
  order: AdminOrderSummary;
  dispute: AdminDisputeSummary;
  disclaimer?: string;
};

export type AdminAuditLog = {
  id: string;
  event_type: string;
  actor_role: string | null;
  resource_type: string;
  resource_id: string | null;
  created_at: string;
};

export type AdminAuditLogListResponse = {
  items: AdminAuditLog[];
  next_cursor: string | null;
  disclaimer?: string;
};

export type AdminCreditPurchaseListResponse = {
  items: AdminCreditPurchaseSummary[];
  next_cursor: string | null;
  disclaimer?: string;
};

export type AdminCreditPurchaseDetailResponse = AdminCreditPurchaseDetail;

export type AdminCreditPurchaseMutationResponse = AdminCreditPurchaseDetail;

export type AdminWebJobRun = {
  id: string;
  job_type: string;
  status: string;
  started_at?: string | null;
  finished_at?: string | null;
  created_at?: string | null;
  duration_ms?: number | null;
  processed_count?: number;
  changed_count?: number;
  skipped_count?: number;
  failed_count?: number;
  error_code?: string | null;
  error_message_safe?: string | null;
};

export type AdminJobRunListResponse = {
  items: AdminWebJobRun[];
  next_cursor: string | null;
  disclaimer?: string;
};

export type AdminBusinessIntakeSummary = {
  id: string;
  status: string;
  last_step: string;
  referral_code?: string | null;
  business_name?: string | null;
  business_tax_id?: string | null;
  responsible_name?: string | null;
  responsible_id_number?: string | null;
  city?: string | null;
  operation?: string | null;
  contact_phone?: string | null;
  contact_phone_masked?: string | null;
  business_phone?: string | null;
  business_phone_masked?: string | null;
  submitted_at?: string | null;
  created_at: string;
  updated_at: string;
  banks?: string[];
  methods?: string[];
  min_amount_usd?: string | null;
  max_amount_usd?: string | null;
  daily_limit_usd?: string | null;
  schedule?: string | null;
  references?: string[];
  reviewed_at?: string | null;
  admin_reason?: string | null;
  created_business_id?: string | null;
  linked_telegram_user_id?: number | null;
  ready_for_review?: boolean;
  review_missing_count?: number;
};

export type AdminBusinessIntakeListResponse = {
  items: AdminBusinessIntakeSummary[];
  next_cursor: string | null;
};

export type AdminNotificationPriority = "info" | "attention" | "high" | "critical";
export type AdminNotificationStatus = "unread" | "read" | "dismissed" | "resolved";

export type AdminNotification = {
  id: string;
  notification_type: string;
  priority: AdminNotificationPriority;
  status: AdminNotificationStatus;
  source_surface?: string | null;
  resource_type: string;
  resource_id?: string | null;
  business_id?: string | null;
  actor_user_id?: string | null;
  title: string;
  summary: string;
  action_route?: string | null;
  metadata: Record<string, string | number | boolean | null>;
  first_seen_at: string;
  last_seen_at: string;
  read_at?: string | null;
  dismissed_at?: string | null;
  resolved_at?: string | null;
  created_at: string;
  updated_at: string;
};

export type AdminNotificationsList = {
  items: AdminNotification[];
  next_cursor?: string | null;
};
