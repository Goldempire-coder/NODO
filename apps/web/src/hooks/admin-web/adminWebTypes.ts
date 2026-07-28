export type AdminWebView =
  | "dashboard"
  | "incidents"
  | "ux-friction"
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
  | "investigation"
  | "investigation-candidates"
  | "case-file"
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
