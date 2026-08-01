export type ChatAttachment = {
  id: string;
  file_asset_id: string;
  file_type: string;
  mime_type: string;
  size_bytes: number;
  created_at: string;
};

export type ChatAttachmentViewUrl = {
  url: string;
  expires_in_seconds: number;
  download_filename: string;
};

export type ChatMessage = {
  id: string;
  order_id: string;
  sender_role: string;
  body: string | null;
  visibility: string;
  status: string;
  attachments: ChatAttachment[];
  created_at: string;
};

export type ChatCapabilities = {
  can_send_message: boolean;
  can_open_dispute: boolean;
  can_share_zelle: boolean;
  payment_details_shared: boolean;
  can_report_payment: boolean;
  receiver_details_shared: boolean;
  can_share_receiver_details: boolean;
  can_reveal_receiver_details: boolean;
  receiver_details_required: boolean;
  can_confirm_received: boolean;
  can_confirm_payment: boolean;
  can_mark_delivered: boolean;
};

export type ChatThread = {
  items: ChatMessage[];
  system_messages: ChatMessage[];
  capabilities: ChatCapabilities;
  disclaimer?: string;
  next_cursor?: string | null;
};
