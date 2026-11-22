# TenderPulse — Adversarial Security & Threat Model Review

## Executive Summary

TenderPulse is designed as a mission-critical public procurement and reverse-auction RFP clearinghouse operating on GenLayer Studionet. This document details the adversarial review conducted across 7 distinct attack surfaces, detailing attack vectors, impact, and formal protocol mitigations enforced in `contracts/tender_pulse.py`.

---

## Threat Matrix

| Threat ID | Threat Vector | Vulnerability Classification | Mitigation & Invariant |
| :--- | :--- | :--- | :--- |
| **TM-01** | Off-Topic Authoritative Domain Exploit | Sybil / Semantic Bypass | Dual-predicate evaluation (`provenance_valid` AND `supports_rfp_criteria`). Off-topic documents score 0 bps and are marked `NON_COMPLIANT_DISQUALIFIED`. |
| **TM-02** | Evidence Unavailability / 404 / Truncated Payload | Denial of Service / Liveness Attack | Fail-closed policy: fetches failing or returning `< 32` chars yield `BAND_FAIL_CLOSED`, blocking tender settlement without slashing. |
| **TM-03** | Cross-Domain Asset Leakage (`TPT` vs `Native GEN`) | Fund Drainage / Value Extraction | Domain A (`TPT` balances & custody vault) and Domain B (`Native GEN` custody) are strictly segregated. 0 wei cross-domain interaction. |
| **TM-04** | Stranded Native Residue Exploitation | Asset Trapping | Strict conservation invariant: `native_custody_balance == active_bid_bonds + active_challenge_bonds + total_refundable_balances`. 0 wei stranded. |
| **TM-05** | Payable Underpayment / Overpayment Griefing | Trapped Native Funds | Non-trapping soft-fail: rejected calls credit 100% of sent value to `refundable_balances[sender]` with non-reverting diagnostic record. |
| **TM-06** | EOA Payout Delivery Failure (Reentrancy / Gas OOG) | Loss of Funds / State Desync | Payouts execute via `@gl.evm.contract_interface` `IEoaRecipient`. If delivery raises, `refundable_balances[sender]` is restored intact. |
| **TM-07** | Frivolous Bid Challenge Griefing | Malicious Delay | Challenger must stake `required_challenge_bond_gen`. If the challenge fails, 100% of the challenge bond is forfeited to the vendor. |

---

## Detailed Vulnerability Analyses

### 1. Off-Topic Authoritative Domain Exploit (Rule 4, 6)
- **Vector**: An attacker quotes a rock-bottom price (e.g. 1 TPT) and submits a URL from an authoritative domain (e.g. `w3.org`, `ietf.org`, or `github.com`) pointing to an unrelated document (e.g. HTTP specification or sourdough recipe) to fool naive domain-matching or LLMs into awarding the procurement contract.
- **Protocol Defense**: TenderPulse never uses domain whitelisting as proof of compliance. In `_run_rfp_compliance_audit_nondet`, the LLM prompt evaluates:
  1. `provenance_valid: bool` — authentic technical source.
  2. `supports_rfp_criteria: bool` — technical document satisfies the specific RFP requirements.
  If `supports_rfp_criteria` is false, `quantized_compliance_bps` is forced to `0`, `award_band` is set to `NON_COMPLIANT_DISQUALIFIED`, and the bid is ineligible for award.

### 2. Evidence Unavailability & Fail-Closed Guard (Rule 9)
- **Vector**: A malicious buyer or competing vendor attempts to trigger false slashing or premature tender closure by targeting unavailable or intermittently failing URLs.
- **Protocol Defense**: Any HTTP status $\ge 400$, network timeout, connection abort, or content with substantive character length $< 32$ immediately triggers `source_fetch_ok = False` and `award_band = "EVIDENCE_UNAVAILABLE_FAIL_CLOSED"`. Crucially, Rule 5 zero-slash guarantees that unavailable evidence does NOT slash vendor bid bonds, while `finalize_tender_award` refuses to settle tenders whose winning candidate is in `FAIL_CLOSED` status.

### 3. Non-Trapping Soft-Fail & EOA Delivery Preservation (Rule 2, 8)
- **Vector**: If payable entrypoints revert on invalid parameters or underpayment, callers lose gas or cross-contract callers encounter unexpected execution reverts. If contract-to-EOA transfers revert, state could become permanently locked.
- **Protocol Defense**:
  - All payable functions (`submit_vendor_bid_payable`, `challenge_vendor_bid_payable`, `top_up_procurement_escrow_payable`) never revert on business rule rejections; they immediately credit `gl.message.value` to `refundable_balances[sender]` and record `last_payable_rejection[sender]`.
  - When claiming refunds, `claim_refundable_balance` calls `IEoaRecipient.emit_transfer(value=amount)`. If an exception is encountered, `refundable_balances[sender]` is immediately restored, allowing subsequent retry without capital destruction.
