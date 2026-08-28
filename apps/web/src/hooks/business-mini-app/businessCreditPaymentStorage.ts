import type { CreditPurchase } from "../../types/credits";
import { isRememberableBaseUsdcPurchase } from "./businessCreditPaymentRules";

const BASE_USDC_PENDING_PURCHASE_LEGACY_KEY = "nodo_base_usdc_pending_purchase_id";
const BASE_USDC_PENDING_PURCHASE_KEY_PREFIX = "nodo_base_usdc_pending_purchase_id";
const BASE_USDC_HANDOFF_KEY_PREFIX = "nodo_base_usdc_handoff_id";

export function pendingBaseUsdcPurchaseStorageKey(businessId: string | null | undefined) {
  return businessId ? `${BASE_USDC_PENDING_PURCHASE_KEY_PREFIX}:${businessId}` : null;
}

export function creditHandoffStorageKey(businessId: string | null | undefined) {
  return businessId ? `${BASE_USDC_HANDOFF_KEY_PREFIX}:${businessId}` : null;
}

export function rememberCreditHandoffId(storageKey: string | null, handoffId: string) {
  if (typeof window !== "undefined" && storageKey) {
    window.localStorage.setItem(storageKey, handoffId);
  }
}

export function readRememberedCreditHandoffId(storageKey: string | null) {
  return typeof window !== "undefined" && storageKey
    ? window.localStorage.getItem(storageKey)
    : null;
}

export function clearRememberedCreditHandoffId(storageKey: string | null) {
  if (typeof window !== "undefined" && storageKey) {
    window.localStorage.removeItem(storageKey);
  }
}

export function rememberPendingBaseUsdcPurchase(purchase: CreditPurchase, storageKey: string | null) {
  if (typeof window === "undefined") {
    return;
  }
  const legacyPurchaseId = window.localStorage.getItem(BASE_USDC_PENDING_PURCHASE_LEGACY_KEY);
  if (legacyPurchaseId === purchase.id) {
    window.localStorage.removeItem(BASE_USDC_PENDING_PURCHASE_LEGACY_KEY);
  }
  if (!storageKey) {
    return;
  }
  if (isRememberableBaseUsdcPurchase(purchase)) {
    window.localStorage.setItem(storageKey, purchase.id);
    return;
  }
  const rememberedPurchaseId = window.localStorage.getItem(storageKey);
  if (rememberedPurchaseId === purchase.id) {
    window.localStorage.removeItem(storageKey);
  }
}

export function readRememberedBaseUsdcPurchaseId(storageKey: string | null) {
  if (typeof window === "undefined") {
    return null;
  }
  return (storageKey ? window.localStorage.getItem(storageKey) : null) || window.localStorage.getItem(BASE_USDC_PENDING_PURCHASE_LEGACY_KEY);
}

export function clearRememberedBaseUsdcPurchase(storageKey: string | null, purchaseId?: string | null) {
  if (typeof window === "undefined") {
    return;
  }
  const legacyPurchaseId = window.localStorage.getItem(BASE_USDC_PENDING_PURCHASE_LEGACY_KEY);
  if (!purchaseId || legacyPurchaseId === purchaseId) {
    window.localStorage.removeItem(BASE_USDC_PENDING_PURCHASE_LEGACY_KEY);
  }
  if (storageKey) {
    const rememberedPurchaseId = window.localStorage.getItem(storageKey);
    if (!purchaseId || rememberedPurchaseId === purchaseId) {
      window.localStorage.removeItem(storageKey);
    }
  }
}
