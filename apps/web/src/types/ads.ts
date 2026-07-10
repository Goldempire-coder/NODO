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
  expires_at: string | null;
  business?: {
    business_name: string;
    verification_status: string;
    trust_level: string;
    risk_level: string;
    rating_avg: string | null;
    completed_orders_count: number;
  };
  payment_method_details?: {
    method_type: string;
    network: string | null;
    account_masked: string;
    holder_name: string;
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
