export const BUSINESS_MINI_APP_VIEWS = [
  "business-dashboard",
  "credits-dashboard",
  "buy-credits",
  "credit-payment-pending",
  "create-ad",
  "my-ads",
  "archived-ads",
  "business-orders",
  "business-order-detail",
  "business-chat",
  "referrals",
  "payment-methods",
  "business-settings",
  "business-pin",
  "business-rules",
  "business-support"
] as const;

export type BusinessMiniAppView = (typeof BUSINESS_MINI_APP_VIEWS)[number];

export function isBusinessMiniAppView(view: string): view is BusinessMiniAppView {
  return (BUSINESS_MINI_APP_VIEWS as readonly string[]).includes(view);
}
