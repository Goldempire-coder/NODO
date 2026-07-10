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
    trust_level?: string;
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

export type AdminDashboard = {
  queues: {
    pending_businesses: number;
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

export type AdminMetrics = {
  source: string;
  table_created: boolean;
  businesses: Record<string, number>;
  orders: Record<string, number>;
  disputes: Record<string, number>;
  credits: Record<string, number>;
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
