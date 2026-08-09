export type SupportTicketStatus = "open" | "waiting_support" | "waiting_user" | "escalated" | "resolved" | "closed";

export type SupportTicketScope =
  | "client_general"
  | "client_order"
  | "business_general"
  | "business_order"
  | "business_ad"
  | "business_credit"
  | "admin_internal";

export type SupportTicketCategory =
  | "technical_issue"
  | "account_access"
  | "order_help"
  | "payment_report_help"
  | "business_access"
  | "credits_help"
  | "suspicious_activity"
  | "other";

export type OperationReportCategory =
  | "order_help"
  | "payment_report_help"
  | "suspicious_activity"
  | "other";

export type SupportAttachment = {
  id: string;
  resource_type: string;
  resource_id: string;
  file_type: "support_attachment";
  mime_type: string;
  size_bytes: number;
  created_at: string;
};

export type SupportMessage = {
  id: string;
  ticket_id: string;
  sender_role: string;
  body: string;
  visibility: string;
  attachments: SupportAttachment[];
  created_at: string;
};

export type SupportEvent = {
  id: string;
  ticket_id: string;
  actor_role: string;
  event_type: string;
  from_status: SupportTicketStatus | null;
  to_status: SupportTicketStatus | null;
  reason: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
};

export type SupportTicket = {
  id: string;
  requester_role: string;
  requester_surface: string;
  business_id: string | null;
  business_name?: string | null;
  order_id: string | null;
  ad_id: string | null;
  credit_purchase_id: string | null;
  dispute_id: string | null;
  assigned_support_user_id: string | null;
  scope: SupportTicketScope;
  category: SupportTicketCategory;
  status: SupportTicketStatus;
  priority: "low" | "normal" | "high" | "urgent";
  subject: string;
  last_message_at: string | null;
  created_at: string;
  updated_at: string;
  attachments?: SupportAttachment[];
  messages?: SupportMessage[];
  events?: SupportEvent[];
  disclaimer?: string;
};

export type SupportTicketCreateInput = {
  scope: SupportTicketScope;
  category: SupportTicketCategory;
  subject: string;
  message: string;
  order_id?: string | null;
  ad_id?: string | null;
  credit_purchase_id?: string | null;
};

export type OperationReportCreateInput = {
  category: OperationReportCategory;
  message: string;
};

export type OperationReportCreateResult = {
  ticket: SupportTicket;
};
