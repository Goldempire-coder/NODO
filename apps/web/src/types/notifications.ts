export type AttentionKind = "order" | "support";

export type SurfaceAttentionItem = {
  kind: AttentionKind;
  resource_id: string;
  signature: string;
  message: string;
  occurred_at: string;
};

export type SurfaceAttentionCounts = {
  orders: number;
  support: number;
  total: number;
};

export type SurfaceAttentionTruncated = {
  orders: boolean;
  support: boolean;
};

export type SurfaceAttentionSummary = {
  counts: SurfaceAttentionCounts;
  items: SurfaceAttentionItem[];
  truncated: SurfaceAttentionTruncated;
};

export type SurfaceAttentionAcknowledgeRequest = {
  kind: AttentionKind;
  resource_id: string;
  signature: string;
};
