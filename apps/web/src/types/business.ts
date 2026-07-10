export type BusinessSummary = {
  id: string;
  business_name: string;
  rif?: string | null;
  phone?: string | null;
  country?: string | null;
  verification_status: string;
  risk_level: string;
};

export type BusinessFormState = {
  business_name: string;
  rif: string;
  address: string;
  phone: string;
  country: string;
};

export type BusinessPaymentMethod = {
  id: string;
  label: string;
  receive_method: "zelle" | "usdt_trc20";
  delivery_method: "pago_movil_ve";
  receive_display: string;
  delivery_display: string;
  delivery_currency: string;
  status: "approved";
  is_available: boolean;
  limits: {
    min_amount_usd: string;
    max_amount_usd: string;
  };
  masked_account: string | null;
};
