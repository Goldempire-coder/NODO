import type { AdminWebJobRun } from "../../types/admin";

export type AdminOverviewView = "dashboard" | "incidents" | "ux-friction" | "metrics" | "jobs";

export type ListResponse<T> = {
  items: T[];
  next_cursor: string | null;
  disclaimer?: string;
};

export type { AdminWebJobRun };

export type QueueCriticalAction = (title: string, detail: string, run: () => Promise<void>) => void;
