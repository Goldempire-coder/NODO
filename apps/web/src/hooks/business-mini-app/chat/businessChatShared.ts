import type { ChatCapabilities, ChatMessage } from "../../../types/chat";

export type ChatAttachmentLink = {
  url: string;
  downloadFilename: string;
  expiresInSeconds: number;
  mimeType: string;
};

export type BusinessChatAction = "confirm-payment" | "mark-delivered";

export type BusinessChatSessionScope = {
  chatOrderId: string | null;
  chatOrderIdRef: { current: string | null };
  chatSessionEpochRef: { current: number };
  chatCapabilitiesOrderIdRef: { current: string | null };
  isCurrentChatSession: (orderId: string, sessionEpoch: number) => boolean;
  refreshChatSession: (
    orderId: string,
    sessionEpoch: number,
    options?: { silent?: boolean }
  ) => Promise<boolean>;
};

export const EMPTY_CHAT_CAPABILITIES: ChatCapabilities = {
  can_send_message: false,
  can_open_dispute: false,
  can_share_zelle: false,
  can_share_payment_details: false,
  payment_details_shared: false,
  can_report_payment: false,
  receiver_details_shared: false,
  can_share_receiver_details: false,
  can_reveal_receiver_details: false,
  receiver_details_required: false,
  can_confirm_received: false,
  can_confirm_payment: false,
  can_mark_delivered: false
};

export function sortChatMessages(messages: ChatMessage[]) {
  return [...messages].sort((left, right) => {
    const timeDelta = new Date(left.created_at).getTime() - new Date(right.created_at).getTime();
    if (timeDelta !== 0) {
      return timeDelta;
    }
    return left.id.localeCompare(right.id);
  });
}

export function chatSessionKey(orderId: string, sessionEpoch: number) {
  return `${orderId}:${sessionEpoch}`;
}
