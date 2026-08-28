import type { AuthenticatedRequest } from "./client";
import { resolveApiUrl } from "../lib/env";
import type {
  BusinessCreditPurchaseDetail,
  BusinessPendingCreditPurchaseDetail,
  CreditHandoffChallenge,
  CreditHandoffCreated,
  CreditHandoffStatus,
} from "../types/credits";

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

export function getBusinessPendingContractCreditPurchase(request: AuthenticatedRequest) {
  return request<BusinessPendingCreditPurchaseDetail>("/api/v1/business/credits/purchases/pending-contract", {
    cache: "no-store",
  });
}

export function dismissBusinessContractCreditPurchase(
  request: AuthenticatedRequest,
  purchaseId: string,
) {
  return request<BusinessCreditPurchaseDetail>(`/api/v1/business/credits/purchases/${purchaseId}/dismiss`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ confirmation: "NO_PAYMENT_SENT" }),
  });
}

export function createBusinessCreditHandoff(
  request: AuthenticatedRequest,
  packageCode: string,
) {
  return request<CreditHandoffCreated>("/api/v1/business/credits/handoffs", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ package_code: packageCode }),
  });
}

export function getBusinessCreditHandoff(
  request: AuthenticatedRequest,
  handoffId: string,
) {
  return request<CreditHandoffStatus>(`/api/v1/business/credits/handoffs/${handoffId}`, {
    cache: "no-store",
  });
}

async function publicCreditHandoffRequest<T>(path: string, body: object): Promise<T> {
  const response = await fetch(resolveApiUrl(path), {
    method: "POST",
    cache: "no-store",
    credentials: "omit",
    referrerPolicy: "no-referrer",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(payload.error?.message || "No pudimos completar la preparacion de wallet.");
  }
  return payload.data as T;
}

export function getCreditHandoffChallenge(handoffToken: string) {
  return publicCreditHandoffRequest<CreditHandoffChallenge>(
    "/api/v1/business/credits/handoffs/challenge",
    { handoff_token: handoffToken },
  );
}

export function claimCreditHandoff(payload: {
  handoffToken: string;
  walletAddress: string;
  chainId: number;
  signature: string;
}) {
  return publicCreditHandoffRequest<CreditHandoffStatus>(
    "/api/v1/business/credits/handoffs/claim",
    {
      handoff_token: payload.handoffToken,
      wallet_address: payload.walletAddress,
      chain_id: payload.chainId,
      signature: payload.signature,
    },
  );
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
