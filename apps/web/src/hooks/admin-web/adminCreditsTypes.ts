export type CreditsView = "credit-purchases" | "credit-detail" | "credit-adjustments";

export type ListResponse<T> = {
  items: T[];
  next_cursor: string | null;
  disclaimer?: string;
};

export type QueueCriticalAction = (title: string, detail: string, run: () => Promise<void>) => void;
