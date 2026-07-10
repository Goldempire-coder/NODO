export type ClientProfileFormState = {
  first_name: string;
  phone: string;
};

export type SearchFormState = {
  amount_usd: string;
  payment_method: "zelle" | "usdt_trc20";
  delivery_method: "pago_movil_ve";
  sort: "trust" | "rate" | "speed";
};
