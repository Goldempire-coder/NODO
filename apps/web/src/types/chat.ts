export type ChatAttachment = {
  id: string;
  file_asset_id: string;
  file_type: string;
  mime_type: string;
  size_bytes: number;
  created_at: string;
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
};
