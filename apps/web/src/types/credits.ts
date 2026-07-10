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

export type CreditLedgerEntry = {
  id: string;
  type: string;
  amount: number;
  balance_available_before: number;
  balance_available_after: number;
  reason: string;
  source: string;
  reference_type: string;
  reference_id: string;
  created_at: string;
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
  admin_note?: string | null;
  created_at: string;
  approved_at: string | null;
  rejected_at: string | null;
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
