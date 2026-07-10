import type { AuthenticatedRequest } from "./client";

export function getBusinessCreditWallet<T>(request: AuthenticatedRequest) {
  return request<T>("/api/v1/business/credits/wallet");
}

export function listBusinessCreditLedger<T>(request: AuthenticatedRequest, limit = 20) {
  return request<T>(`/api/v1/business/credits/ledger?limit=${limit}`);
}

export function startBusinessStripeCheckout<T>(request: AuthenticatedRequest, packageCode: string, idempotencyKey: string) {
  return request<T>("/api/v1/business/credits/stripe-checkout", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Idempotency-Key": idempotencyKey
    },
    body: JSON.stringify({ package_code: packageCode })
  });
}

export function submitBusinessManualCreditPayment<T>(
  request: AuthenticatedRequest,
  payload: {
    packageCode: string;
    paymentMethod: "zelle_manual_admin_approved" | "usdt_manual_admin_approved";
    manualPaymentReference: string;
    manualTxHash: string;
    file: File;
  },
  idempotencyKey: string
) {
  const body = new FormData();
  body.append("package_code", payload.packageCode);
  body.append("payment_method", payload.paymentMethod);
  if (payload.paymentMethod === "zelle_manual_admin_approved") {
    body.append("manual_payment_reference", payload.manualPaymentReference);
  } else {
    body.append("manual_tx_hash", payload.manualTxHash);
    body.append("manual_network", "TRC20");
  }
  body.append("file", payload.file);
  return request<T>("/api/v1/business/credits/manual-payment", {
    method: "POST",
    headers: { "Idempotency-Key": idempotencyKey },
    body
  });
}

export function getBusinessReferrals<T>(request: AuthenticatedRequest) {
  return request<T>("/api/v1/business/referrals");
}

export function applyBusinessReferral<T>(request: AuthenticatedRequest, referralCode: string, idempotencyKey: string) {
  return request<T>("/api/v1/business/referrals/apply", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Idempotency-Key": idempotencyKey
    },
    body: JSON.stringify({ referral_code: referralCode })
  });
}
