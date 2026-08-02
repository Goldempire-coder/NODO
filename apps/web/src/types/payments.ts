export type PaymentInstructions = {
  order: {
    id: string;
    public_order_code: string;
    status: string;
    amount_usd: string;
    amount_bs_calculated: string;
    rate_snapshot: string;
    payment_report_deadline_at: string;
  };
  payment_instructions: {
    method_type: "zelle" | "usdt_trc20";
    network: string | null;
    account_value: string;
    account_masked: string;
    holder_name: string;
  } & Record<string, string | null>;
  disclaimer: string;
};

export type PaymentEvidence = {
  id: string;
  file_type: string;
  mime_type: string;
  size_bytes: number;
  created_at: string;
};

export type PaymentReportFormState = {
  payment_reference: string;
  payment_sender_name: string;
  payment_sender_account_masked: string;
  payment_amount: string;
  tx_hash: string;
};
