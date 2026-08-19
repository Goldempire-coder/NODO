import type {
  AdminBusinessDetail,
  AdminBusinessIntakeSummary as AdminBusinessIntakeSummaryDto,
  AdminBusinessSummary
} from "../../types/admin";

export type BusinessIntakeView = "businesses" | "business-detail" | "intake" | "intake-detail" | "users" | "user-detail";

export type ListResponse<T> = {
  items: T[];
  next_cursor: string | null;
  disclaimer?: string;
};

export type QueueCriticalAction = (title: string, detail: string, run: () => Promise<void>, options?: { requiresReason?: boolean }) => void;

export type AdminBusinessIntakeSummary = AdminBusinessIntakeSummaryDto;

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

export type BusinessSummaryForAdmin = AdminBusinessSummary;

export type AdminBusinessState = {
  businesses: BusinessSummaryForAdmin[];
  businessFilter: string;
  selectedBusiness: AdminBusinessDetail | null;
};
