export type AdminWebView =
  | "dashboard"
  | "businesses"
  | "business-detail"
  | "users"
  | "user-detail"
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
  | "support"
  | "staff"
  | "staff-detail"
  | "staff-invite";

export type RequestFn = <T = unknown>(path: string, options?: RequestInit) => Promise<T>;

export type ConfirmAction = {
  title: string;
  detail: string;
  run: () => Promise<void>;
};
