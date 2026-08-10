import type { PaymentEvidence } from "./payments";

export type OrderCancelReason =
  | "business_not_responding"
  | "business_unavailable"
  | "customer_mistake"
  | "choose_another_business";

export type OrderSummary = {
  id: string;
  public_order_code: string;
  status: string;
  amount_usd: string;
  rate_snapshot: string;
  amount_bs_calculated: string;
  business_name: string;
  payment_method_snapshot: string;
  delivery_method_snapshot: string;
  payment_instructions_masked: {
    method_type?: string | null;
    network?: string | null;
    account_masked?: string | null;
  };
  receiver_data_masked: {
    bank?: string | null;
    phone?: string | null;
    document?: string | null;
    holder?: string | null;
  };
  payment_report_deadline_at: string;
  extension_used: boolean;
  expires_at: string;
  cancel_reason?: string | null;
  terminal_display_status?: "payment_rejected_admin_review" | null;
  can_view_payment_instructions: boolean;
  rating?: {
    can_rate: boolean;
    already_rated: boolean;
    stars: number | null;
  };
};

export type OrderRatingResult = {
  rating: {
    id: string;
    order_id: string;
    business_id: string;
    stars: number;
    created_at: string;
  };
  business_reputation: {
    publication_status: "withheld_pending_snapshot";
    label: string;
  };
};

export type OrderFormState = {
  amount_usd: string;
};

export type ReceiverDetailsInput = {
  bank: string;
  phone: string;
  document: string;
  holder: string;
};

export type ReceiverDetailsMasked = {
  bank: string;
  phone: string;
  document: string;
  holder: string;
};

export type ReceiverDetails = ReceiverDetailsInput & {
  order_id: string;
  shared_at: string;
};

export type BusinessOrderSummary = {
  id: string;
  public_order_code: string;
  status: string;
  cancel_reason?: string | null;
  amount_usd: string;
  amount_bs_calculated: string;
  payment_method_snapshot: string;
  delivery_method_snapshot: string;
  paid_reported_at: string | null;
  payment_confirmed_at: string | null;
  delivered_at: string | null;
  business_response_deadline_at: string | null;
  delivery_deadline_at: string | null;
  auto_complete_at: string | null;
  receiver_data_masked?: {
    bank?: string | null;
    phone?: string | null;
    document?: string | null;
    holder?: string | null;
  };
  receiver_data?: {
    bank?: string | null;
    phone?: string | null;
    document?: string | null;
    holder?: string | null;
  };
  capabilities: {
    can_confirm_payment: boolean;
    can_reject_payment_report: boolean;
    can_open_dispute: boolean;
    can_mark_delivered: boolean;
    can_decline_before_payment: boolean;
    receiver_details_shared: boolean;
  };
};

export type BusinessOrderDetail = {
  order: BusinessOrderSummary;
  receiver_data: {
    bank?: string | null;
    phone_masked?: string | null;
    document_masked?: string | null;
    holder?: string | null;
  };
  payment_report: {
    id: string;
    status: string;
    payment_type: string;
    payment_reference_masked: string | null;
    tx_hash_masked: string | null;
    payment_amount: string;
    proof_file_id: string | null;
    created_at: string;
  } | null;
  evidence: PaymentEvidence[];
  timeline: {
    event_type: string;
    from_status: string | null;
    to_status: string;
    created_at: string;
    reason: string | null;
  }[];
  disclaimer: string;
};
