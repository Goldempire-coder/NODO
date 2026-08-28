import type { CreditPurchase } from "../../types/credits";

export const DEFAULT_CREDIT_PACKAGE = "starter";
export const BASE_USDC_PENDING_STATUSES = new Set([
  "pending_payment",
  "pending_onchain_confirmation",
  "detected",
  "under_review",
]);
export const BASE_USDC_PAYABLE_PENDING_STATUS = "pending_payment";

export function isRememberableBaseUsdcPurchase(purchase: CreditPurchase) {
  return (
    purchase.payment_method === "base_usdc_contract" &&
    BASE_USDC_PENDING_STATUSES.has(purchase.status) &&
    !(purchase.status === BASE_USDC_PAYABLE_PENDING_STATUS && purchase.owner_dismissed)
  );
}

export function isPendingBaseUsdcPurchaseForBusiness(
  purchase: CreditPurchase,
  businessId: string | null | undefined,
) {
  return Boolean(
    businessId &&
    purchase.business_id === businessId &&
    isRememberableBaseUsdcPurchase(purchase),
  );
}

export function isDismissableBaseUsdcPurchase(
  purchase: CreditPurchase | null,
  businessId: string | null | undefined,
) {
  return Boolean(
    purchase &&
    businessId &&
    purchase.business_id === businessId &&
    purchase.payment_method === "base_usdc_contract" &&
    purchase.status === BASE_USDC_PAYABLE_PENDING_STATUS &&
    !purchase.owner_dismissed,
  );
}
