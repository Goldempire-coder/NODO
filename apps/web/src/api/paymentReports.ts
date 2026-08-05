import type { AuthenticatedRequest } from "./client";
import type {
  PaymentEvidenceUploadResult,
  PaymentInstructions,
  PaymentReportPayload,
  PaymentReportResult
} from "../types/payments";

export function getPaymentInstructions(request: AuthenticatedRequest, orderId: string) {
  return request<PaymentInstructions>(`/api/v1/orders/${orderId}/payment-instructions`);
}

export function uploadPaymentEvidence(
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
  return request<PaymentEvidenceUploadResult>(`/api/v1/orders/${orderId}/payment-evidence`, {
    method: "POST",
    headers: {
      "Idempotency-Key": idempotencyKey
    },
    body
  });
}

export function submitOrderPaymentReport(
  request: AuthenticatedRequest,
  orderId: string,
  payload: PaymentReportPayload,
  idempotencyKey: string
) {
  return request<PaymentReportResult>(`/api/v1/orders/${orderId}/payment-report`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Idempotency-Key": idempotencyKey
    },
    body: JSON.stringify(payload)
  });
}
