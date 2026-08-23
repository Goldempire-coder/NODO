import type { AuthenticatedRequest } from "./client";
import type { BusinessCreditPurchaseDetail } from "../types/credits";

export function getBusinessCreditWallet<T>(request: AuthenticatedRequest) {
  return request<T>(`/api/v1/business/credits/wallet?_=${Date.now()}`, { cache: "no-store" });
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

export function startBusinessBaseUsdcPayment(
  request: AuthenticatedRequest,
  packageCode: string,
  payerWalletAddress: string,
  idempotencyKey: string
) {
  return request<BusinessCreditPurchaseDetail>("/api/v1/business/credits/base-payment", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Idempotency-Key": idempotencyKey
    },
    body: JSON.stringify({ package_code: packageCode, payer_wallet_address: payerWalletAddress })
  });
}

export function getBusinessCreditPurchase(request: AuthenticatedRequest, purchaseId: string) {
  return request<BusinessCreditPurchaseDetail>(`/api/v1/business/credits/purchases/${purchaseId}`);
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
