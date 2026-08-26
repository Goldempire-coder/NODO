export type CreditWallet = {
  business_id: string;
  available_credits: number;
  blocked_credits: number;
  consumed_credits: number;
  lifetime_purchased_credits: number;
  lifetime_bonus_credits: number;
  lifetime_adjusted_credits: number;
  founder_status: string | null;
  founder_expires_at: string | null;
  referral_credits_earned: number;
};

export type CreditPurchase = {
  id: string;
  business_id: string;
  package_code: string;
  credits_amount: number;
  price_usd: string;
  payment_method: string;
  status: string;
  proof_file_id: string | null;
  manual_payment_reference_masked?: string | null;
  manual_tx_hash_masked?: string | null;
  manual_network?: string | null;
  chain_id?: number | null;
  network?: string | null;
  token_symbol?: string | null;
  token_contract_address?: string | null;
  token_decimals?: number | null;
  expected_amount_units?: string | null;
  destination_wallet_address?: string | null;
  tx_hash_masked?: string | null;
  tx_amount_units?: string | null;
  tx_from_address_masked?: string | null;
  tx_to_address?: string | null;
  tx_block_number?: number | null;
  tx_log_index?: number | null;
  confirmations?: number | null;
  verification_status?: string | null;
  detected_at?: string | null;
  verified_at?: string | null;
  credited_at?: string | null;
  expires_at?: string | null;
  admin_note?: string | null;
  created_at: string;
  approved_at: string | null;
  rejected_at: string | null;
};

export type ContractCreditAuthorizationStatus = "valid" | "expired" | "reissue_required";

export type CreditPaymentNetwork = "base_sepolia" | "base_mainnet";

export type ContractCreditPayment = {
  network: CreditPaymentNetwork | null;
  chain_id: number | null;
  network_display_name?: string | null;
  is_testnet?: boolean | null;
  token_symbol: string | null;
  token_contract_address: string | null;
  token_decimals: number | null;
  expected_amount_units: string | null;
  expected_amount_display: string;
  contract_address: string | null;
  contract_version: number | null;
  purchase_ref: string | null;
  payer_wallet_address: string | null;
  authorization_valid_until: number | null;
  authorization_typed_data?: Record<string, unknown>;
  authorization_signature?: string;
  authorization_status: ContractCreditAuthorizationStatus;
  capabilities: {
    can_pay: boolean;
  };
  min_confirmations?: number;
};

export type BusinessCreditPurchaseDetail = {
  purchase: CreditPurchase;
  payment?: ContractCreditPayment;
  disclaimer?: string;
};

export type CreditHandoff = {
  id: string;
  status: "active" | "claiming" | "prepared" | "expired";
  expires_at: string;
  wallet_address_masked?: string | null;
  network: CreditPaymentNetwork;
  chain_id: number;
  network_display_name: string;
  is_testnet: boolean;
};

export type CreditHandoffCreated = {
  handoff: CreditHandoff & {
    token: string;
  };
};

export type CreditHandoffChallenge = {
  challenge: string;
  chain_id: number;
  network: CreditPaymentNetwork;
  network_display_name: string;
  is_testnet: boolean;
  expires_at: string;
};

export type CreditHandoffStatus = BusinessCreditPurchaseDetail & {
  handoff: CreditHandoff;
};

export type AdminCreditPurchaseSummary = {
  id: string;
  business_id: string;
  package_code: string;
  credits_amount: number;
  price_usd: string;
  payment_method: string;
  status: string;
  verification_status: string | null;
  has_reported_tx: boolean;
  created_at: string;
  updated_at: string;
};

export type AdminCreditPurchaseRecord = {
  id: string;
  business_id: string;
  package_code: string;
  credits_amount: number;
  price_usd: string;
  payment_method: string;
  status: string;
  proof_file_id: string | null;
  manual_payment_reference_masked: string | null;
  manual_tx_hash_masked: string | null;
  manual_network: string | null;
  admin_note: string | null;
  created_at: string;
  updated_at: string;
  paid_at: string | null;
  approved_at: string | null;
  rejected_at: string | null;
  failed_at: string | null;
  expired_at: string | null;
};

export type AdminCreditOnchainEvidence = {
  chain_id: number | null;
  network: string | null;
  token_symbol: string | null;
  token_contract_address_masked: string | null;
  token_decimals: number | null;
  expected_amount_units: string | null;
  destination_wallet_masked: string | null;
  tx_hash_masked: string | null;
  tx_amount_units: string | null;
  tx_from_address_masked: string | null;
  tx_to_address_masked: string | null;
  tx_block_number: number | null;
  tx_log_index: number | null;
  confirmations: number | null;
  verification_source: string | null;
  verification_status: string | null;
  destination_matches: boolean | null;
  amount_matches: boolean | null;
  detected_at: string | null;
  verified_at: string | null;
  credited_at: string | null;
  expires_at: string | null;
};

export type AdminCreditLedgerEntry = {
  id: string;
  business_id: string;
  type: string;
  amount: number;
  balance_available_before: number;
  balance_available_after: number;
  balance_blocked_before: number;
  balance_blocked_after: number;
  balance_consumed_before: number;
  balance_consumed_after: number;
  reason: string;
  source: string;
  reference_type: string;
  reference_id: string;
  related_credit_purchase_id: string | null;
  created_at: string;
};

export type AdminCreditPurchaseDetail = {
  purchase: AdminCreditPurchaseRecord;
  onchain_evidence: AdminCreditOnchainEvidence | null;
  ledger: AdminCreditLedgerEntry | null;
  reconciliation: {
    state: "matched" | "pending" | "warning" | "failed";
    warning_codes: string[];
  };
};

export type ReferralEvent = {
  id: string;
  direction: "earned" | "used";
  status: string;
  credits_awarded: number;
  created_at: string;
  rewarded_at: string | null;
};

export type ReferralData = {
  referral_code: string;
  status: string;
  cap: number;
  earned_credits: number;
  remaining_bonus_credits: number;
  events: ReferralEvent[];
  disclaimer: string;
};
