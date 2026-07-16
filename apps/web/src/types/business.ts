export type BusinessSummary = {
  id: string;
  business_name: string;
  rif?: string | null;
  phone?: string | null;
  country?: string | null;
  verification_status: string;
  trust_level?: string;
  risk_level: string;
  min_order_amount_usd?: string;
  max_order_amount_usd?: string;
  daily_limit_usd?: string;
  active_order_limit?: number;
  is_accepting_orders?: boolean;
  access_link?: {
    id: string;
    status: string;
    role_in_business: string;
    linked_at: string;
    pin_required?: boolean;
    pin_configured?: boolean;
    pin_unlocked?: boolean;
    pin_locked_until?: string | null;
    pin_unlocked_until?: string | null;
  };
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
  network?: string | null;
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
  holder_name?: string | null;
};

export type BusinessPaymentMethodFormState = {
  method_type: "zelle" | "usdt_trc20";
  account_value: string;
  holder_name: string;
};
