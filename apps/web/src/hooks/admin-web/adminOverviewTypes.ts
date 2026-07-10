export type AdminOverviewView = "dashboard" | "metrics" | "jobs";

export type ListResponse<T> = {
  items: T[];
  next_cursor: string | null;
  disclaimer?: string;
};

export type AdminWebJobRun = {
  id: string;
  job_type: string;
  status: string;
  started_at?: string | null;
  finished_at?: string | null;
  created_at?: string | null;
  error_message_safe?: string | null;
};

export type QueueCriticalAction = (title: string, detail: string, run: () => Promise<void>) => void;
