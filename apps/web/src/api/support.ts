import type { AuthenticatedRequest } from "./client";
import type { SupportMessage, SupportTicket, SupportTicketCreateInput } from "../types/support";

export type SupportListResponse = {
  items: SupportTicket[];
  next_cursor: string | null;
};

export type SupportMessageResponse = {
  message: SupportMessage;
  ticket: SupportTicket;
  disclaimer?: string;
};

export type AdminSupportAttachmentViewUrlResponse = {
  url: string;
  expires_in_seconds: number;
  download_filename: string;
};

export async function createSupportTicket(request: AuthenticatedRequest, input: SupportTicketCreateInput, idempotencyKey: string): Promise<SupportTicket> {
  return request<SupportTicket>("/api/v1/support/tickets", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Idempotency-Key": idempotencyKey
    },
    body: JSON.stringify(input)
  });
}

export async function listSupportTickets(request: AuthenticatedRequest, query = ""): Promise<SupportListResponse> {
  return request<SupportListResponse>(`/api/v1/support/tickets${query}`);
}

export async function getSupportTicket(request: AuthenticatedRequest, ticketId: string): Promise<SupportTicket> {
  return request<SupportTicket>(`/api/v1/support/tickets/${ticketId}`);
}

export async function sendSupportMessage(request: AuthenticatedRequest, ticketId: string, body: string, idempotencyKey: string): Promise<SupportMessageResponse> {
  return request<SupportMessageResponse>(`/api/v1/support/tickets/${ticketId}/messages`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Idempotency-Key": idempotencyKey
    },
    body: JSON.stringify({ body })
  });
}

export async function uploadSupportAttachment(request: AuthenticatedRequest, ticketId: string, file: File, idempotencyKey: string): Promise<SupportMessageResponse> {
  const data = new FormData();
  data.append("file", file);
  return request<SupportMessageResponse>(`/api/v1/support/tickets/${ticketId}/attachments`, {
    method: "POST",
    headers: {
      "Idempotency-Key": idempotencyKey
    },
    body: data
  });
}

export async function closeSupportTicket(request: AuthenticatedRequest, ticketId: string, idempotencyKey: string): Promise<SupportTicket> {
  return request<SupportTicket>(`/api/v1/support/tickets/${ticketId}/close`, {
    method: "POST",
    headers: {
      "Idempotency-Key": idempotencyKey
    }
  });
}

export async function adminListSupportTickets(request: AuthenticatedRequest, query = ""): Promise<SupportListResponse> {
  return request<SupportListResponse>(`/api/v1/admin/support/tickets${query}`);
}

export async function adminGetSupportTicket(request: AuthenticatedRequest, ticketId: string): Promise<SupportTicket> {
  return request<SupportTicket>(`/api/v1/admin/support/tickets/${ticketId}`);
}

export async function adminSendSupportMessage(request: AuthenticatedRequest, ticketId: string, body: string, idempotencyKey: string): Promise<SupportMessageResponse> {
  return request<SupportMessageResponse>(`/api/v1/admin/support/tickets/${ticketId}/messages`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Idempotency-Key": idempotencyKey
    },
    body: JSON.stringify({ body, visibility: "participants" })
  });
}

export async function adminAssignSupportTicket(request: AuthenticatedRequest, ticketId: string, assignedSupportUserId: string, reason: string, idempotencyKey: string): Promise<SupportTicket> {
  return request<SupportTicket>(`/api/v1/admin/support/tickets/${ticketId}/assign`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Idempotency-Key": idempotencyKey
    },
    body: JSON.stringify({ assigned_support_user_id: assignedSupportUserId, reason })
  });
}

export async function adminEscalateSupportTicket(request: AuthenticatedRequest, ticketId: string, reason: string, idempotencyKey: string): Promise<SupportTicket> {
  return request<SupportTicket>(`/api/v1/admin/support/tickets/${ticketId}/escalate`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Idempotency-Key": idempotencyKey
    },
    body: JSON.stringify({ reason })
  });
}

export async function adminResolveSupportTicket(request: AuthenticatedRequest, ticketId: string, reason: string, idempotencyKey: string): Promise<SupportTicket> {
  return request<SupportTicket>(`/api/v1/admin/support/tickets/${ticketId}/resolve`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Idempotency-Key": idempotencyKey
    },
    body: JSON.stringify({ reason })
  });
}

export async function adminCloseSupportTicket(request: AuthenticatedRequest, ticketId: string, reason: string, idempotencyKey: string): Promise<SupportTicket> {
  return request<SupportTicket>(`/api/v1/admin/support/tickets/${ticketId}/close`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Idempotency-Key": idempotencyKey
    },
    body: JSON.stringify({ reason })
  });
}

export async function adminSupportAttachmentViewUrl(request: AuthenticatedRequest, ticketId: string, fileId: string, reason: string): Promise<AdminSupportAttachmentViewUrlResponse> {
  return request(`/api/v1/admin/support/tickets/${ticketId}/attachments/${fileId}/view-url`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ reason })
  });
}
