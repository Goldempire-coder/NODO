import type { BusinessSummary } from "./business";

export type DocumentFile = {
  id: string;
  file_type: string;
  mime_type: string;
  size_bytes: number;
  created_at: string;
};

export type AdminBusinessDetail = {
  business: BusinessSummary & {
    address?: string | null;
    owner_user_id?: string | null;
    trust_level?: string;
    min_order_amount_usd?: string;
    max_order_amount_usd?: string;
    daily_limit_usd?: string;
    active_order_limit?: number;
    created_at?: string;
    updated_at?: string;
  };
  latest_submission: {
    id: string;
    status: string;
    submitted_data: Record<string, unknown>;
    submitted_at: string;
    reviewed_at: string | null;
  } | null;
  documents: DocumentFile[];
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
  users?: {
    clients_total: number;
    client_profiles_with_phone: number;
    recent_client_contacts: {
      id: string;
      first_name: string | null;
      username: string | null;
      phone: string | null;
      updated_at: string;
    }[];
  };
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

export type AdminAuditLog = {
  event_type: string;
  actor_role: string | null;
  resource_type: string;
  resource_id: string | null;
  created_at: string;
};

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
