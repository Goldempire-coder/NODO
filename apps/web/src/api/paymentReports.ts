import type { AuthenticatedRequest } from "./client";

export function getPaymentInstructions<T>(request: AuthenticatedRequest, orderId: string) {
  return request<T>(`/api/v1/orders/${orderId}/payment-instructions`);
}

export function uploadPaymentEvidence<T>(
  request: AuthenticatedRequest,
  orderId: string,
  file: File,
  pendingPaymentReportId: string | null,
  idempotencyKey: string
) {
  const body = new FormData();
  body.append("file", file);
  body.append("file_type", "payment_evidence");
  if (pendingPaymentReportId) {
    body.append("pending_payment_report_id", pendingPaymentReportId);
  }
  return request<T>(`/api/v1/orders/${orderId}/payment-evidence`, {
    method: "POST",
    headers: {
      "Idempotency-Key": idempotencyKey
    },
    body
  });
}

export function submitOrderPaymentReport<T>(request: AuthenticatedRequest, orderId: string, payload: Record<string, unknown>, idempotencyKey: string) {
  return request<T>(`/api/v1/orders/${orderId}/payment-report`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Idempotency-Key": idempotencyKey
    },
    body: JSON.stringify(payload)
  });
}
