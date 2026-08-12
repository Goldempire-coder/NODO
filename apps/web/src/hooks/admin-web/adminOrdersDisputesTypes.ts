export type OrdersDisputesView = "orders" | "order-detail" | "disputes" | "dispute-detail";

export type QueueCriticalAction = (
  title: string,
  detail: string,
  run: () => Promise<void>,
  options?: { requiresReason?: boolean }
) => void;
