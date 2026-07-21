export type AdSummary = {
  id: string;
  business_id: string;
  payment_method_id: string;
  payment_method: string;
  delivery_method: string;
  rate_bs_per_usd: string;
  amount_min_usd: string;
  amount_max_usd: string;
  required_credits: number;
  status: string;
  effective_status: string;
  created_at?: string;
  updated_at?: string;
  activated_at?: string | null;
  expires_at: string | null;
  business?: {
    id: string;
    business_name: string;
    verification_status: string;
    rating_avg?: string | null;
    completed_orders_count?: number;
    reputation?: {
      tier: "new" | "active" | "reliable" | "elite";
      label: "Nuevo" | "Activo" | "Confiable" | "Elite";
      rating_avg: string | null;
      ratings_count: number;
      completed_orders_count: number;
      success_rate: string | null;
      average_delivery_seconds: number | null;
    };
  };
  payment_method_details?: {
    id?: string;
    method_type: string;
    network: string | null;
    account_masked: string;
    holder_name: string;
    verified_status?: string;
    active?: boolean;
  };
};

export type AdFormState = {
  payment_method_id: string;
  payment_method: "zelle" | "usdt_trc20";
  delivery_method: "pago_movil_ve";
  rate_bs_per_usd: string;
  amount_min_usd: string;
  amount_max_usd: string;
};

export type AdUpdatePayload = {
  payment_method_id: string;
  rate_bs_per_usd: string;
  amount_min_usd: string;
  amount_max_usd: string;
};
