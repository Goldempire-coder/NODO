export const CLIENT_VIEWS = [
  "welcome",
  "terms",
  "client-profile-setup",
  "profile",
  "marketplace-search",
  "marketplace-list",
  "marketplace-detail",
  "create-order",
  "order-summary",
  "payment-instructions",
  "report-payment",
  "my-orders",
  "messages",
  "order-chat",
  "support"
] as const;

export type ClientView = (typeof CLIENT_VIEWS)[number];

export const CLIENT_VIEW_SET = new Set<string>(CLIENT_VIEWS);

export function isClientView(view: string): view is ClientView {
  return CLIENT_VIEW_SET.has(view);
}

export function coerceClientView(view: string): ClientView {
  return isClientView(view) ? view : "marketplace-search";
}
