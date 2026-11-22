export interface Tender {
  tender_id: number;
  title: string;
  rfp_spec: string;
  buyer: string;
  max_budget_tpt: number;
  min_qualification_bps: number;
  required_bid_bond_gen: number;
  required_challenge_bond_gen: number;
  bid_deadline: number;
  challenge_deadline: number;
  created_at: number;
  status: string;
  winning_bid_id: number;
  winning_vendor: string;
  winning_bid_amount_tpt: number;
  buyer_refund_tpt: number;
  bid_count: number;
  settled_at: number;
  award_band: string;
  buyer_approved: boolean;
  vendor_approved: boolean;
  buyer_bps: number;
  vendor_bps: number;
}

export interface Bid {
  bid_id: number;
  tender_id: number;
  vendor: string;
  bid_amount_tpt: number;
  proposal_spec_url: string;
  bid_bond_gen: number;
  created_at: number;
  evaluated: boolean;
  source_fetch_ok: boolean;
  provenance_valid: boolean;
  supports_rfp_criteria: boolean;
  quantized_compliance_bps: number;
  award_band: string;
  slash_amount: number;
  status: string;
  summary: string;
  challenger: string;
  challenge_bond_gen: number;
  challenge_reason: string;
  counter_evidence_url: string;
  challenged_at: number;
  adjudicated: boolean;
}

export interface TokenMetadata {
  name: string;
  symbol: string;
  decimals: number;
  total_supply: number;
  vault_custody_balance: number;
  sum_token_balances: number;
}

export interface NativeCustodySummary {
  native_custody_balance: number;
  active_bid_bonds: number;
  active_challenge_bonds: number;
  total_refundable_balances: number;
  conservation_ok: boolean;
}
