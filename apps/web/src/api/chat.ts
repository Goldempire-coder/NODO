import type { AuthenticatedRequest } from "./client";

export function listOrderMessages<T>(
  request: AuthenticatedRequest,
  orderId: string,
  limit = 25,
  cursor?: string
) {
  const query = new URLSearchParams({ limit: String(limit) });
  if (cursor) {
    query.set("cursor", cursor);
  }
  return request<T>(`/api/v1/orders/${orderId}/messages?${query.toString()}`);
}

export function uploadOrderMessageAttachment<T>(request: AuthenticatedRequest, orderId: string, file: File, idempotencyKey: string) {
  const body = new FormData();
  body.append("file", file);
  return request<T>(`/api/v1/orders/${orderId}/message-attachments`, {
    method: "POST",
    headers: {
      "Idempotency-Key": idempotencyKey
    },
    body
  });
}

export function openOrderMessageAttachment<T>(
  request: AuthenticatedRequest,
  orderId: string,
  attachmentId: string
) {
  return request<T>(`/api/v1/orders/${orderId}/message-attachments/${attachmentId}/view-url`, {
    method: "POST"
  });
}

export function sendOrderMessage<T>(request: AuthenticatedRequest, orderId: string, payload: { body: string; attachment_ids: string[] }, idempotencyKey: string) {
  return request<T>(`/api/v1/orders/${orderId}/messages`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Idempotency-Key": idempotencyKey
    },
    body: JSON.stringify(payload)
  });
}

export function shareConfiguredZelle<T>(
  request: AuthenticatedRequest,
  orderId: string,
  idempotencyKey: string
) {
  return request<T>(`/api/v1/orders/${orderId}/share-zelle`, {
    method: "POST",
    headers: {
      "Idempotency-Key": idempotencyKey
    }
  });
}

export function openOrderDispute<T>(
  request: AuthenticatedRequest,
  orderId: string,
  payload: { reason: string; description?: string; evidence_file_ids: string[] },
  idempotencyKey: string
) {
  return request<T>(`/api/v1/orders/${orderId}/disputes`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Idempotency-Key": idempotencyKey
    },
    body: JSON.stringify(payload)
  });
}
