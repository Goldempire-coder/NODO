export type AdminWebView =
  | "dashboard"
  | "businesses"
  | "business-detail"
  | "orders"
  | "order-detail"
  | "disputes"
  | "dispute-detail"
  | "audit-logs"
  | "metrics"
  | "credit-purchases"
  | "credit-detail"
  | "credit-adjustments"
  | "jobs"
  | "intake"
  | "intake-detail"
  | "support-placeholder";

export type RequestFn = <T = unknown>(path: string, options?: RequestInit) => Promise<T>;

export type ConfirmAction = {
  title: string;
  detail: string;
  run: () => Promise<void>;
};
