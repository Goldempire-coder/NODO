import type { AdminDisputeSummary, AdminOrderSummary } from "../../types/admin";

export type OrdersDisputesView = "orders" | "order-detail" | "disputes" | "dispute-detail";

export type ListResponse<T> = {
  items: T[];
  next_cursor: string | null;
  disclaimer?: string;
};

export type QueueCriticalAction = (
  title: string,
  detail: string,
  run: () => Promise<void>,
  options?: { requiresReason?: boolean }
) => void;

export type AdminWebOrderDetail = Record<string, unknown> & {
  order?: AdminOrderSummary;
  dispute?: AdminDisputeSummary;
  disclaimer?: string;
};

export type AdminWebDisputeDetail = {
  dispute: AdminDisputeSummary;
  order_summary?: Record<string, unknown>;
  events?: Record<string, unknown>[];
  disclaimer?: string;
};
