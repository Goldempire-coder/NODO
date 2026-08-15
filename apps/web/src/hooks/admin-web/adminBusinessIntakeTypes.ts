import type { AdminBusinessDetail } from "../../types/admin";

export type BusinessIntakeView = "businesses" | "business-detail" | "intake" | "intake-detail" | "users" | "user-detail";

export type ListResponse<T> = {
  items: T[];
  next_cursor: string | null;
  disclaimer?: string;
};

export type QueueCriticalAction = (title: string, detail: string, run: () => Promise<void>, options?: { requiresReason?: boolean }) => void;

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

export type AdminBusinessIntakeEditDraft = {
  referral_code: string;
  contact_phone: string;
  business_name: string;
  business_tax_id: string;
  responsible_name: string;
  responsible_id_number: string;
  city: string;
  business_phone: string;
  operation: string;
  banks: string;
  methods: string;
  min_amount_usd: string;
  max_amount_usd: string;
  daily_limit_usd: string;
  schedule: string;
  references: string;
};

export type AdminBusinessIntakeDetail = {
  intake: AdminBusinessIntakeSummary;
  documents: {
    id: string;
    file_type: string;
    document_kind: string;
    mime_type: string;
    size_bytes: number;
    created_at: string;
  }[];
};

export type BusinessSummaryForAdmin = {
  id: string;
  business_name?: string;
  display_name?: string;
  verification_status?: string;
  risk_level?: string;
  trust_level?: string;
  created_at?: string;
  submitted_at?: string | null;
};

export type AdminBusinessState = {
  businesses: BusinessSummaryForAdmin[];
  businessFilter: string;
  selectedBusiness: AdminBusinessDetail | null;
};
