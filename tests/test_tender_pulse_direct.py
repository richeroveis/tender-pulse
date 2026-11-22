"""Comprehensive direct mode test suite for TenderPulse (60+ tests).

Tests verify:
- Off-topic authoritative-domain rejection in BOTH evaluation and challenge flows.
- Diverse valid authoritative specifications accepted and lowest-cost reverse-auction winner awarded.
- Rule 5 zero-slash invariant for compliant vendors.
- Fail-closed on unavailable or <32 substantive char fetches.
- Strict Domain A (TPT) vs Domain B (Native GEN) separation.
- IEoaRecipient native EOA payouts and balance preservation on delivery failure.
- Zero-winner & expiry refunds.
- 0-wei residue conservation across all terminal exits.
"""

import pytest
from conftest import (
    BASE_ISO,
    BASE_TS,
    DEFAULT_BID_BOND_GEN,
    DEFAULT_BID_WINDOW,
    DEFAULT_CHALLENGE_BOND_GEN,
    DEFAULT_CHALLENGE_WINDOW,
    DEFAULT_MAX_BUDGET,
    DEFAULT_MIN_QUAL_BPS,
    DEFAULT_RFP_SPEC,
    DEFAULT_SPEC_URL,
    DEFAULT_TITLE,
    TPT,
    addr_hex,
    challenge_bid,
    clear_mocks,
    create_tender,
    mint,
    mock_audit,
    set_chain_time,
    submit_bid,
)

# ---------------------------------------------------------------------------
# 1. Token, Metadata, Governance, & Domain A Ledger
# ---------------------------------------------------------------------------

def test_01_token_metadata(world):
    meta = world.contract.get_token_metadata()
    assert meta["name"] == "TenderPulse Token"
    assert meta["symbol"] == "TPT"
    assert meta["decimals"] == 6
    assert meta["vault_custody_balance"] == 0
    assert meta["total_supply"] > 0
    assert meta["sum_token_balances"] == meta["total_supply"]

def test_02_governance_boundary_has_no_owner_or_admin(world):
    gov = world.contract.get_governance_boundary()
    assert gov["has_owner"] is False
    assert gov["has_admin"] is False
    assert gov["protocol"] == "TenderPulse"

def test_03_faucet_minting_and_allowance_cap(world):
    world.vm.sender = world.alice
    res = world.contract.faucet_or_deposit(500_000 * TPT)
    assert res["amount_tpt"] == 500_000 * TPT
    bal = world.contract.get_token_balance(addr_hex(world.alice))
    assert bal >= 5_500_000 * TPT

def test_04_faucet_rejects_negative_or_zero(world):
    world.vm.sender = world.alice
    with pytest.raises(Exception, match=r"\[EXPECTED\] amount must be positive"):
        world.contract.faucet_or_deposit(0)

def test_05_faucet_exceeding_allowance_fails(world):
    world.vm.sender = world.alice
    with pytest.raises(Exception, match=r"\[EXPECTED\] exceeds faucet allowance"):
        world.contract.faucet_or_deposit(20_000_000 * TPT)

def test_06_chain_clock_matches_iso_time(world):
    set_chain_time(world.vm, "2030-06-15T12:00:00Z")
    clock = world.contract.get_chain_clock()
    assert clock == 1907755200
    set_chain_time(world.vm, BASE_ISO)

# ---------------------------------------------------------------------------
# 2. RFP Tender Creation & Domain A Escrow Locking
# ---------------------------------------------------------------------------

def test_07_create_tender_locks_budget_in_vault(world):
    before_bal = world.contract.get_token_balance(addr_hex(world.alice))
    before_vault = world.contract.get_token_metadata()["vault_custody_balance"]
    res = create_tender(world.vm, world.contract, world.alice, max_budget=50_000 * TPT)
    after_bal = world.contract.get_token_balance(addr_hex(world.alice))
    after_vault = world.contract.get_token_metadata()["vault_custody_balance"]

    assert res["tender_id"] >= 1
    assert res["status"] == "OPEN"
    assert res["max_budget_tpt"] == 50_000 * TPT
    assert before_bal - after_bal == 50_000 * TPT
    assert after_vault - before_vault == 50_000 * TPT

def test_08_create_tender_enforces_250_bps_grid(world):
    with pytest.raises(Exception, match=r"\[EXPECTED\] min qualification score must be on 250-bps grid"):
        create_tender(world.vm, world.contract, world.alice, min_qual_bps=7800)

def test_09_create_tender_accepts_valid_250_bps_multiples(world):
    for valid_bps in [250, 7500, 8000, 9750, 10000]:
        t = create_tender(world.vm, world.contract, world.alice, min_qual_bps=valid_bps)
        assert t["min_qualification_bps"] == valid_bps

def test_10_create_tender_rejects_insufficient_buyer_tpt(world):
    world.vm.sender = world.bob
    huge_budget = 100_000_000 * TPT
    with pytest.raises(Exception, match=r"\[EXPECTED\] insufficient TPT balance"):
        world.contract.create_tender(
            DEFAULT_TITLE, DEFAULT_RFP_SPEC, huge_budget, 8000, 100, 100, 3600, 3600
        )

def test_11_create_tender_validates_title_length(world):
    with pytest.raises(Exception, match=r"\[EXPECTED\] invalid tender title length"):
        create_tender(world.vm, world.contract, world.alice, title="AB")
    with pytest.raises(Exception, match=r"\[EXPECTED\] invalid tender title length"):
        create_tender(world.vm, world.contract, world.alice, title="X" * 125)

def test_12_create_tender_validates_rfp_spec_length(world):
    with pytest.raises(Exception, match=r"\[EXPECTED\] invalid rfp specification length"):
        create_tender(world.vm, world.contract, world.alice, rfp_spec="short")

def test_13_create_tender_validates_window_minimums(world):
    with pytest.raises(Exception, match=r"\[EXPECTED\] window seconds must be at least 60"):
        create_tender(world.vm, world.contract, world.alice, bid_win=30)
    with pytest.raises(Exception, match=r"\[EXPECTED\] window seconds must be at least 60"):
        create_tender(world.vm, world.contract, world.alice, challenge_win=45)

def test_14_list_tenders_and_count(world, tender):
    count = world.contract.get_tender_count()
    assert count >= 1
    t_list = world.contract.list_tenders()
    assert len(t_list) == count
    assert t_list[-1]["tender_id"] == tender.id

# ---------------------------------------------------------------------------
# 3. Reverse-Auction Vendor Bidding & Domain B Soft-Fail Handling
# ---------------------------------------------------------------------------

def test_15_submit_bid_payable_with_exact_bond(world, tender):
    res = submit_bid(world.vm, world.contract, world.bob, tender.id, bid_amount_tpt=75_000 * TPT)
    assert res["ok"] is True
    assert res["bid_id"] == 1
    assert res["surplus_credited_wei"] == 0

    bid = world.contract.get_bid(tender.id, 1)
    assert bid["bid_amount_tpt"] == 75_000 * TPT
    assert bid["vendor"] == addr_hex(world.bob)
    assert bid["evaluated"] is False

def test_16_submit_bid_payable_overpayment_surplus_credited(world, tender):
    req_bond = DEFAULT_BID_BOND_GEN
    extra = 150_000_000_000_000_000
    res = submit_bid(world.vm, world.contract, world.bob, tender.id, value=req_bond + extra)
    assert res["ok"] is True
    assert res["surplus_credited_wei"] == extra

    ref_bal = world.contract.get_refundable_balance(addr_hex(world.bob))
    assert ref_bal == extra

def test_17_submit_bid_soft_fail_insufficient_bond_no_revert(world, tender):
    insufficient_val = DEFAULT_BID_BOND_GEN - 1000
    res = submit_bid(world.vm, world.contract, world.bob, tender.id, value=insufficient_val)
    assert res["ok"] is False
    assert res["soft_fail"] is True
    assert "insufficient native bid bond value" in res["reason"]
    assert res["refunded_wei"] == insufficient_val

    ref_bal = world.contract.get_refundable_balance(addr_hex(world.bob))
    assert ref_bal >= insufficient_val
    assert "insufficient native bid bond" in world.contract.get_last_payable_rejection(addr_hex(world.bob))

def test_18_submit_bid_soft_fail_exceeds_max_budget(world, tender):
    over_budget = DEFAULT_MAX_BUDGET + 10_000 * TPT
    res = submit_bid(world.vm, world.contract, world.bob, tender.id, bid_amount_tpt=over_budget)
    assert res["ok"] is False
    assert res["soft_fail"] is True
    assert "within budget" in res["reason"]

def test_19_submit_bid_soft_fail_zero_or_negative_amount(world, tender):
    res = submit_bid(world.vm, world.contract, world.bob, tender.id, bid_amount_tpt=0)
    assert res["ok"] is False
    assert res["soft_fail"] is True
    assert "positive and within budget" in res["reason"]

def test_20_submit_bid_soft_fail_non_https_url(world, tender):
    res = submit_bid(world.vm, world.contract, world.bob, tender.id, spec_url="http://insecure.example.com/spec.md")
    assert res["ok"] is False
    assert res["soft_fail"] is True
    assert "must use https" in res["reason"]

def test_21_submit_bid_soft_fail_private_ip_host(world, tender):
    for private_url in [
        "https://127.0.0.1/spec.md",
        "https://localhost/spec.md",
        "https://192.168.1.1/spec.md",
        "https://10.0.0.1/spec.md",
    ]:
        res = submit_bid(world.vm, world.contract, world.bob, tender.id, spec_url=private_url)
        assert res["ok"] is False
        assert res["soft_fail"] is True
        assert "private host not allowed" in res["reason"]

def test_22_submit_bid_soft_fail_after_deadline(world, tender):
    set_chain_time(world.vm, "2030-01-01T02:00:00Z")  # 2 hours later, window was 1 hour
    res = submit_bid(world.vm, world.contract, world.bob, tender.id)
    assert res["ok"] is False
    assert res["soft_fail"] is True
    assert "bidding window has expired" in res["reason"]
    set_chain_time(world.vm, BASE_ISO)

def test_23_submit_bid_soft_fail_non_existent_tender(world):
    world.vm.sender = world.bob
    world.vm.value = DEFAULT_BID_BOND_GEN
    res = world.contract.submit_vendor_bid_payable(999, 50_000 * TPT, DEFAULT_SPEC_URL)
    world.vm.value = 0
    assert res["ok"] is False
    assert res["soft_fail"] is True
    assert "tender does not exist" in res["reason"]

def test_24_multiple_competing_bids_recorded(world, tender):
    submit_bid(world.vm, world.contract, world.bob, tender.id, bid_amount_tpt=90_000 * TPT)
    submit_bid(world.vm, world.contract, world.charlie, tender.id, bid_amount_tpt=80_000 * TPT)
    bids = world.contract.list_bids_for_tender(tender.id)
    assert len(bids) == 2
    assert bids[0]["bid_amount_tpt"] == 90_000 * TPT
    assert bids[1]["bid_amount_tpt"] == 80_000 * TPT

# ---------------------------------------------------------------------------
# 4. AI Consensus Bid Evaluation & Off-Topic Authoritative Reject
# ---------------------------------------------------------------------------

def test_25_evaluate_bid_off_topic_authoritative_rejected(world, tender):
    """Off-topic document from authoritative host (e.g. w3.org) MUST be rejected with NON_COMPLIANT_DISQUALIFIED and score 0."""
    submit_bid(world.vm, world.contract, world.bob, tender.id, bid_amount_tpt=70_000 * TPT)
    off_topic_rfc_body = "RFC 793: TRANSMISSION CONTROL PROTOCOL SPECIFICATION. Abstract: The Transmission Control Protocol (TCP) is intended for use as a highly reliable host-to-host protocol..."
    mock_audit(
        world.vm,
        provenance_valid=True,
        supports_rfp=False,  # Off-topic!
        compliance_bps=0,
        summary="Off-topic TCP RFC document; does not address RFP RPC Node Cluster criteria.",
        body=off_topic_rfc_body,
    )
    world.vm.sender = world.alice
    res = world.contract.evaluate_vendor_bid(tender.id, 1)

    assert res["provenance_valid"] is True
    assert res["supports_rfp_criteria"] is False
    assert res["quantized_compliance_bps"] == 0
    assert res["award_band"] == "NON_COMPLIANT_DISQUALIFIED"
    assert res["status"] == "DISQUALIFIED"

    t = world.contract.get_tender(tender.id)
    assert t["winning_bid_id"] == 0

def test_26_evaluate_bid_diverse_valid_authoritative_sources_accepted(world, tender):
    """Legitimate authoritative docs matching RFP criteria are QUALIFIED_AWARD_ELIGIBLE."""
    submit_bid(world.vm, world.contract, world.bob, tender.id, bid_amount_tpt=72_000 * TPT)
    mock_audit(
        world.vm,
        provenance_valid=True,
        supports_rfp=True,
        compliance_bps=9500,
        summary="High-speed geo-distributed RPC gateway specification fully satisfies criteria.",
    )
    world.vm.sender = world.alice
    res = world.contract.evaluate_vendor_bid(tender.id, 1)

    assert res["provenance_valid"] is True
    assert res["supports_rfp_criteria"] is True
    assert res["quantized_compliance_bps"] == 9500
    assert res["award_band"] == "QUALIFIED_AWARD_ELIGIBLE"
    assert res["status"] == "EVALUATED"

    t = world.contract.get_tender(tender.id)
    assert t["winning_bid_id"] == 1
    assert t["winning_vendor"] == addr_hex(world.bob)

def test_27_discrete_250_bps_quantization_in_evaluation(world, tender):
    submit_bid(world.vm, world.contract, world.bob, tender.id, bid_amount_tpt=70_000 * TPT)
    mock_audit(world.vm, provenance_valid=True, supports_rfp=True, compliance_bps=8875)
    world.vm.sender = world.alice
    res = world.contract.evaluate_vendor_bid(tender.id, 1)
    # 8875 // 250 * 250 = 8750
    assert res["quantized_compliance_bps"] == 8750

def test_28_score_below_qualification_threshold_is_remediation_hold(world, tender):
    submit_bid(world.vm, world.contract, world.bob, tender.id, bid_amount_tpt=70_000 * TPT)
    mock_audit(world.vm, provenance_valid=True, supports_rfp=True, compliance_bps=6500)
    world.vm.sender = world.alice
    res = world.contract.evaluate_vendor_bid(tender.id, 1)
    # Min qualification is 8000; 6500 < 8000 -> PARTIAL_REMEDIATION_HOLD
    assert res["award_band"] == "PARTIAL_REMEDIATION_HOLD"
    t = world.contract.get_tender(tender.id)
    assert t["winning_bid_id"] == 0

def test_29_fail_closed_on_unavailable_fetch(world, tender):
    submit_bid(world.vm, world.contract, world.bob, tender.id)
    clear_mocks(world.vm)
    world.vm.mock_web(r"https://.*", {"status": 404, "body": "404 Not Found"})
    world.vm.sender = world.alice
    res = world.contract.evaluate_vendor_bid(tender.id, 1)

    assert res["source_fetch_ok"] is False
    assert res["award_band"] == "EVIDENCE_UNAVAILABLE_FAIL_CLOSED"
    assert res["status"] == "EVIDENCE_UNAVAILABLE"

def test_30_fail_closed_on_substantive_body_under_32_chars(world, tender):
    submit_bid(world.vm, world.contract, world.bob, tender.id)
    clear_mocks(world.vm)
    world.vm.mock_web(r"https://.*", {"status": 200, "body": "short text"})
    world.vm.sender = world.alice
    res = world.contract.evaluate_vendor_bid(tender.id, 1)

    assert res["source_fetch_ok"] is False
    assert res["award_band"] == "EVIDENCE_UNAVAILABLE_FAIL_CLOSED"

def test_31_retry_evaluation_allowed_after_fail_closed(world, tender):
    submit_bid(world.vm, world.contract, world.bob, tender.id)
    clear_mocks(world.vm)
    world.vm.mock_web(r"https://.*", {"status": 500, "body": "Server error"})
    world.contract.evaluate_vendor_bid(tender.id, 1)
    b = world.contract.get_bid(tender.id, 1)
    assert b["award_band"] == "EVIDENCE_UNAVAILABLE_FAIL_CLOSED"

    # Now live service recovers:
    mock_audit(world.vm, provenance_valid=True, supports_rfp=True, compliance_bps=9000, clear_existing=True)
    res = world.contract.evaluate_vendor_bid(tender.id, 1)
    assert res["award_band"] == "QUALIFIED_AWARD_ELIGIBLE"
    assert res["quantized_compliance_bps"] == 9000

def test_32_evaluate_bid_rejects_duplicate_once_qualified(world, tender):
    submit_bid(world.vm, world.contract, world.bob, tender.id)
    mock_audit(world.vm, provenance_valid=True, supports_rfp=True, compliance_bps=9000)
    world.contract.evaluate_vendor_bid(tender.id, 1)
    with pytest.raises(Exception, match=r"\[EXPECTED\] bid is already evaluated"):
        world.contract.evaluate_vendor_bid(tender.id, 1)

# ---------------------------------------------------------------------------
# 5. Reverse-Auction Winning Bid Invariant & Tie-Breaking
# ---------------------------------------------------------------------------

def test_33_reverse_auction_lowest_cost_vendor_wins(world, tender):
    submit_bid(world.vm, world.contract, world.bob, tender.id, bid_amount_tpt=85_000 * TPT)
    submit_bid(world.vm, world.contract, world.charlie, tender.id, bid_amount_tpt=70_000 * TPT)

    mock_audit(world.vm, compliance_bps=9000)
    world.contract.evaluate_vendor_bid(tender.id, 1)
    t1 = world.contract.get_tender(tender.id)
    assert t1["winning_bid_id"] == 1

    mock_audit(world.vm, compliance_bps=9000)
    world.contract.evaluate_vendor_bid(tender.id, 2)
    t2 = world.contract.get_tender(tender.id)
    # Bid 2 was lower (70k < 85k), so bid 2 takes the lead!
    assert t2["winning_bid_id"] == 2
    assert t2["winning_vendor"] == addr_hex(world.charlie)
    assert t2["winning_bid_amount_tpt"] == 70_000 * TPT

def test_34_reverse_auction_higher_cost_does_not_override_winner(world, tender):
    submit_bid(world.vm, world.contract, world.bob, tender.id, bid_amount_tpt=65_000 * TPT)
    submit_bid(world.vm, world.contract, world.charlie, tender.id, bid_amount_tpt=85_000 * TPT)

    mock_audit(world.vm, compliance_bps=9000)
    world.contract.evaluate_vendor_bid(tender.id, 1)
    mock_audit(world.vm, compliance_bps=9500)
    world.contract.evaluate_vendor_bid(tender.id, 2)

    t = world.contract.get_tender(tender.id)
    assert t["winning_bid_id"] == 1
    assert t["winning_vendor"] == addr_hex(world.bob)

def test_35_reverse_auction_tie_break_by_higher_compliance_score(world, tender):
    submit_bid(world.vm, world.contract, world.bob, tender.id, bid_amount_tpt=70_000 * TPT)
    submit_bid(world.vm, world.contract, world.charlie, tender.id, bid_amount_tpt=70_000 * TPT)

    mock_audit(world.vm, compliance_bps=8500)
    world.contract.evaluate_vendor_bid(tender.id, 1)
    mock_audit(world.vm, compliance_bps=9250)
    world.contract.evaluate_vendor_bid(tender.id, 2)

    t = world.contract.get_tender(tender.id)
    # Same price (70k), but bid 2 has 9250 > 8500!
    assert t["winning_bid_id"] == 2
    assert t["winning_vendor"] == addr_hex(world.charlie)

def test_36_preview_tender_award_shows_projected_savings(world, tender):
    submit_bid(world.vm, world.contract, world.bob, tender.id, bid_amount_tpt=75_000 * TPT)
    mock_audit(world.vm, compliance_bps=9000)
    world.contract.evaluate_vendor_bid(tender.id, 1)

    prev = world.contract.preview_tender_award(tender.id)
    assert prev["vendor_payout_tpt"] == 75_000 * TPT
    assert prev["buyer_savings_tpt"] == 25_000 * TPT

# ---------------------------------------------------------------------------
# 6. Bid-Integrity Challenges & Adjudication
# ---------------------------------------------------------------------------

def test_37_challenge_vendor_bid_payable_with_exact_bond(world, tender):
    submit_bid(world.vm, world.contract, world.bob, tender.id)
    res = challenge_bid(world.vm, world.contract, world.charlie, tender.id, 1)
    assert res["ok"] is True
    assert res["tender_id"] == tender.id
    assert res["bid_id"] == 1
    assert res["surplus_credited_wei"] == 0

    bid = world.contract.get_bid(tender.id, 1)
    assert bid["challenger"] == addr_hex(world.charlie)
    assert bid["status"] == "CHALLENGED"

def test_38_challenge_vendor_bid_surplus_credited(world, tender):
    submit_bid(world.vm, world.contract, world.bob, tender.id)
    extra = 50_000_000_000_000_000
    res = challenge_bid(world.vm, world.contract, world.charlie, tender.id, 1, value=DEFAULT_CHALLENGE_BOND_GEN + extra)
    assert res["ok"] is True
    assert res["surplus_credited_wei"] == extra

def test_39_challenge_soft_fail_insufficient_bond(world, tender):
    submit_bid(world.vm, world.contract, world.bob, tender.id)
    val = DEFAULT_CHALLENGE_BOND_GEN - 100
    res = challenge_bid(world.vm, world.contract, world.charlie, tender.id, 1, value=val)
    assert res["ok"] is False
    assert res["soft_fail"] is True
    assert "insufficient native challenge bond value" in res["reason"]

def test_40_challenge_soft_fail_after_challenge_deadline(world, tender):
    submit_bid(world.vm, world.contract, world.bob, tender.id)
    # Move time beyond bid_window (3600) + challenge_window (3600)
    set_chain_time(world.vm, "2030-01-01T03:00:00Z")
    res = challenge_bid(world.vm, world.contract, world.charlie, tender.id, 1)
    assert res["ok"] is False
    assert res["soft_fail"] is True
    assert "challenge window has closed" in res["reason"]
    set_chain_time(world.vm, BASE_ISO)

def test_41_adjudicate_challenge_upheld_slashes_vendor_rewards_challenger(world, tender):
    """Off-topic document challenged: challenge is UPHELD! Vendor bond slashed; challenger gets both bonds."""
    submit_bid(world.vm, world.contract, world.bob, tender.id, bid_amount_tpt=60_000 * TPT)
    challenge_bid(world.vm, world.contract, world.charlie, tender.id, 1)

    # Mock audit finds document off-topic:
    mock_audit(world.vm, provenance_valid=True, supports_rfp=False, compliance_bps=0)
    world.vm.sender = world.alice
    res = world.contract.adjudicate_bid_challenge(tender.id, 1)

    assert res["award_band"] == "NON_COMPLIANT_DISQUALIFIED"
    assert res["status"] == "DISQUALIFIED"
    assert res["slash_amount"] == DEFAULT_BID_BOND_GEN

    # Challenger receives their challenge bond + vendor's bid bond!
    c_ref = world.contract.get_refundable_balance(addr_hex(world.charlie))
    assert c_ref == DEFAULT_CHALLENGE_BOND_GEN + DEFAULT_BID_BOND_GEN

    t = world.contract.get_tender(tender.id)
    assert t["winning_bid_id"] == 0

def test_42_adjudicate_challenge_dismissed_enforces_rule5_zero_slash(world, tender):
    """Compliant vendor challenged: challenge DISMISSED! Vendor bond has zero slash; challenger bond awarded to vendor."""
    submit_bid(world.vm, world.contract, world.bob, tender.id, bid_amount_tpt=65_000 * TPT)
    challenge_bid(world.vm, world.contract, world.charlie, tender.id, 1)

    mock_audit(world.vm, provenance_valid=True, supports_rfp=True, compliance_bps=9500)
    world.vm.sender = world.alice
    res = world.contract.adjudicate_bid_challenge(tender.id, 1)

    assert res["award_band"] == "QUALIFIED_AWARD_ELIGIBLE"
    assert res["slash_amount"] == 0  # RULE 5 ZERO-SLASH INVARIANT!
    assert res["status"] == "EVALUATED"

    # Frivolous challenger's bond awarded to honest vendor!
    v_ref = world.contract.get_refundable_balance(addr_hex(world.bob))
    assert v_ref == DEFAULT_CHALLENGE_BOND_GEN

    t = world.contract.get_tender(tender.id)
    assert t["winning_bid_id"] == 1

def test_43_adjudicate_challenge_fail_closed_returns_challenge_bond(world, tender):
    submit_bid(world.vm, world.contract, world.bob, tender.id)
    challenge_bid(world.vm, world.contract, world.charlie, tender.id, 1)

    clear_mocks(world.vm)
    world.vm.mock_web(r"https://.*", {"status": 500, "body": "Unavailable"})
    world.contract.adjudicate_bid_challenge(tender.id, 1)

    # Fail closed -> hold settlement, return challenge bond to challenger
    c_ref = world.contract.get_refundable_balance(addr_hex(world.charlie))
    assert c_ref == DEFAULT_CHALLENGE_BOND_GEN

def test_44_adjudicate_rejects_unchallenged_bid(world, tender):
    submit_bid(world.vm, world.contract, world.bob, tender.id)
    with pytest.raises(Exception, match=r"\[EXPECTED\] bid has not been challenged"):
        world.contract.adjudicate_bid_challenge(tender.id, 1)

def test_45_adjudicate_rejects_already_adjudicated_challenge(world, tender):
    submit_bid(world.vm, world.contract, world.bob, tender.id)
    challenge_bid(world.vm, world.contract, world.charlie, tender.id, 1)
    mock_audit(world.vm, compliance_bps=9000)
    world.contract.adjudicate_bid_challenge(tender.id, 1)
    with pytest.raises(Exception, match=r"\[EXPECTED\] challenge is already adjudicated"):
        world.contract.adjudicate_bid_challenge(tender.id, 1)

# ---------------------------------------------------------------------------
# 7. Final Award Settlement & Zero-Residue Invariants
# ---------------------------------------------------------------------------

def test_46_finalize_tender_award_settles_tpt_and_refunds_winner_bond(world, tender):
    submit_bid(world.vm, world.contract, world.bob, tender.id, bid_amount_tpt=70_000 * TPT)
    mock_audit(world.vm, compliance_bps=9250)
    world.contract.evaluate_vendor_bid(tender.id, 1)

    bob_tpt_before = world.contract.get_token_balance(addr_hex(world.bob))
    alice_tpt_before = world.contract.get_token_balance(addr_hex(world.alice))

    world.vm.sender = world.alice
    res = world.contract.finalize_tender_award(tender.id)

    assert res["status"] == "AWARDED"
    assert res["winning_bid_amount_tpt"] == 70_000 * TPT
    assert res["buyer_savings_tpt"] == 30_000 * TPT

    # Domain A TPT verification:
    bob_tpt_after = world.contract.get_token_balance(addr_hex(world.bob))
    alice_tpt_after = world.contract.get_token_balance(addr_hex(world.alice))
    assert bob_tpt_after - bob_tpt_before == 70_000 * TPT
    assert alice_tpt_after - alice_tpt_before == 30_000 * TPT

    # Domain B Native GEN verification: Winner bond returned to refundable_balances
    bob_gen_ref = world.contract.get_refundable_balance(addr_hex(world.bob))
    assert bob_gen_ref == DEFAULT_BID_BOND_GEN

def test_47_finalize_tender_award_fails_without_winner(world, tender):
    world.vm.sender = world.alice
    with pytest.raises(Exception, match=r"\[EXPECTED\] no qualified winning bid to award"):
        world.contract.finalize_tender_award(tender.id)

def test_48_finalize_tender_award_cannot_be_called_twice(world, tender):
    submit_bid(world.vm, world.contract, world.bob, tender.id, bid_amount_tpt=70_000 * TPT)
    mock_audit(world.vm, compliance_bps=9000)
    world.contract.evaluate_vendor_bid(tender.id, 1)
    world.contract.finalize_tender_award(tender.id)

    with pytest.raises(Exception, match=r"\[EXPECTED\] tender is already settled"):
        world.contract.finalize_tender_award(tender.id)

def test_49_refund_runner_up_bid_bond(world, tender):
    submit_bid(world.vm, world.contract, world.bob, tender.id, bid_amount_tpt=60_000 * TPT)
    submit_bid(world.vm, world.contract, world.charlie, tender.id, bid_amount_tpt=80_000 * TPT)

    mock_audit(world.vm, compliance_bps=9000)
    world.contract.evaluate_vendor_bid(tender.id, 1)
    mock_audit(world.vm, compliance_bps=9000)
    world.contract.evaluate_vendor_bid(tender.id, 2)
    world.contract.finalize_tender_award(tender.id)

    # Runner-up charlie claims their bid bond back:
    res = world.contract.refund_runner_up_bid_bond(tender.id, 2)
    assert res["refunded_wei"] == DEFAULT_BID_BOND_GEN
    charlie_ref = world.contract.get_refundable_balance(addr_hex(world.charlie))
    assert charlie_ref == DEFAULT_BID_BOND_GEN

def test_50_runner_up_refund_fails_for_winner(world, tender):
    submit_bid(world.vm, world.contract, world.bob, tender.id, bid_amount_tpt=60_000 * TPT)
    mock_audit(world.vm, compliance_bps=9000)
    world.contract.evaluate_vendor_bid(tender.id, 1)
    world.contract.finalize_tender_award(tender.id)

    with pytest.raises(Exception, match=r"\[EXPECTED\] winning bid bond is refunded via finalize_tender_award"):
        world.contract.refund_runner_up_bid_bond(tender.id, 1)

def test_51_runner_up_refund_cannot_be_double_claimed(world, tender):
    submit_bid(world.vm, world.contract, world.bob, tender.id, bid_amount_tpt=60_000 * TPT)
    submit_bid(world.vm, world.contract, world.charlie, tender.id, bid_amount_tpt=80_000 * TPT)
    mock_audit(world.vm, compliance_bps=9000)
    world.contract.evaluate_vendor_bid(tender.id, 1)
    mock_audit(world.vm, compliance_bps=9000)
    world.contract.evaluate_vendor_bid(tender.id, 2)
    world.contract.finalize_tender_award(tender.id)

    world.contract.refund_runner_up_bid_bond(tender.id, 2)
    with pytest.raises(Exception, match=r"\[EXPECTED\] bid bond already refunded or slashed"):
        world.contract.refund_runner_up_bid_bond(tender.id, 2)

# ---------------------------------------------------------------------------
# 8. Zero-Winner & Expiry Refunds
# ---------------------------------------------------------------------------

def test_52_claim_zero_winner_tender_refund_after_deadline(world, tender):
    submit_bid(world.vm, world.contract, world.bob, tender.id)
    # Bid evaluated as disqualified:
    mock_audit(world.vm, supports_rfp=False, compliance_bps=0)
    world.contract.evaluate_vendor_bid(tender.id, 1)

    # Warp past challenge deadline:
    set_chain_time(world.vm, "2030-01-01T04:00:00Z")

    alice_tpt_before = world.contract.get_token_balance(addr_hex(world.alice))
    res = world.contract.claim_zero_winner_tender_refund(tender.id)
    assert res["status"] == "SETTLED_ZERO_WINNERS"
    assert res["refunded_budget_tpt"] == DEFAULT_MAX_BUDGET

    alice_tpt_after = world.contract.get_token_balance(addr_hex(world.alice))
    assert alice_tpt_after - alice_tpt_before == DEFAULT_MAX_BUDGET
    set_chain_time(world.vm, BASE_ISO)

def test_53_claim_zero_winner_fails_prematurely(world, tender):
    with pytest.raises(Exception, match=r"\[EXPECTED\] challenge deadline has not passed"):
        world.contract.claim_zero_winner_tender_refund(tender.id)

def test_54_claim_expired_tender_refund_with_zero_bids(world, tender):
    set_chain_time(world.vm, "2030-01-01T02:00:00Z")  # Past bid window
    alice_tpt_before = world.contract.get_token_balance(addr_hex(world.alice))
    world.vm.sender = world.alice
    res = world.contract.claim_expired_tender_refund(tender.id)
    assert res["status"] == "EXPIRED_REFUNDED"
    assert res["refunded_budget_tpt"] == DEFAULT_MAX_BUDGET

    alice_tpt_after = world.contract.get_token_balance(addr_hex(world.alice))
    assert alice_tpt_after - alice_tpt_before == DEFAULT_MAX_BUDGET
    set_chain_time(world.vm, BASE_ISO)

def test_55_claim_expired_tender_refund_fails_if_bids_exist(world, tender):
    submit_bid(world.vm, world.contract, world.bob, tender.id)
    set_chain_time(world.vm, "2030-01-01T02:00:00Z")
    world.vm.sender = world.alice
    with pytest.raises(Exception, match=r"\[EXPECTED\] tender received bids"):
        world.contract.claim_expired_tender_refund(tender.id)
    set_chain_time(world.vm, BASE_ISO)

# ---------------------------------------------------------------------------
# 9. Mutual Co-Sign Settlement Bay
# ---------------------------------------------------------------------------

def test_56_mutual_release_successful_co_signature(world, tender):
    submit_bid(world.vm, world.contract, world.bob, tender.id, bid_amount_tpt=70_000 * TPT)
    mock_audit(world.vm, compliance_bps=9000)
    world.contract.evaluate_vendor_bid(tender.id, 1)

    bob_tpt_before = world.contract.get_token_balance(addr_hex(world.bob))
    alice_tpt_before = world.contract.get_token_balance(addr_hex(world.alice))

    # Buyer approves 6000 bps (60% to vendor, 40% refund to buyer)
    world.vm.sender = world.alice
    r1 = world.contract.propose_mutual_release(tender.id, 6000)
    assert r1["settled"] is False
    assert r1["buyer_approved"] is True

    # Vendor approves matching 6000 bps
    world.vm.sender = world.bob
    r2 = world.contract.propose_mutual_release(tender.id, 6000)
    assert r2["settled"] is True
    assert r2["status"] == "MUTUAL_SETTLED"
    assert r2["vendor_payout_tpt"] == 60_000 * TPT
    assert r2["buyer_refund_tpt"] == 40_000 * TPT

    bob_tpt_after = world.contract.get_token_balance(addr_hex(world.bob))
    alice_tpt_after = world.contract.get_token_balance(addr_hex(world.alice))
    assert bob_tpt_after - bob_tpt_before == 60_000 * TPT
    assert alice_tpt_after - alice_tpt_before == 40_000 * TPT

def test_57_mutual_release_bps_mismatch_blocks_settlement(world, tender):
    submit_bid(world.vm, world.contract, world.bob, tender.id)
    mock_audit(world.vm, compliance_bps=9000)
    world.contract.evaluate_vendor_bid(tender.id, 1)

    world.vm.sender = world.alice
    world.contract.propose_mutual_release(tender.id, 5000)
    world.vm.sender = world.bob
    r2 = world.contract.propose_mutual_release(tender.id, 7000)
    assert r2["settled"] is False
    assert "mismatch" in r2.get("reason", "")

def test_58_mutual_release_unauthorized_party_rejected(world, tender):
    submit_bid(world.vm, world.contract, world.bob, tender.id)
    mock_audit(world.vm, compliance_bps=9000)
    world.contract.evaluate_vendor_bid(tender.id, 1)
    world.vm.sender = world.charlie
    with pytest.raises(Exception, match=r"\[EXPECTED\] only the buyer or nominated vendor"):
        world.contract.propose_mutual_release(tender.id, 5000)

# ---------------------------------------------------------------------------
# 10. Native GEN Refund Withdrawals & Zero-Residue Conservation
# ---------------------------------------------------------------------------

def test_59_native_custody_conservation_invariant_throughout_lifecycle(world, tender):
    summary0 = world.contract.get_native_custody_summary()
    assert summary0["conservation_ok"] is True
    assert summary0["native_custody_balance"] == 0

    # Bid with surplus:
    submit_bid(world.vm, world.contract, world.bob, tender.id, value=DEFAULT_BID_BOND_GEN + 100_000)
    summary1 = world.contract.get_native_custody_summary()
    assert summary1["conservation_ok"] is True
    assert summary1["active_bid_bonds"] == DEFAULT_BID_BOND_GEN
    assert summary1["total_refundable_balances"] == 100_000
    assert summary1["native_custody_balance"] == DEFAULT_BID_BOND_GEN + 100_000

    # Challenge with surplus:
    challenge_bid(world.vm, world.contract, world.charlie, tender.id, 1, value=DEFAULT_CHALLENGE_BOND_GEN + 50_000)
    summary2 = world.contract.get_native_custody_summary()
    assert summary2["conservation_ok"] is True
    assert summary2["active_challenge_bonds"] == DEFAULT_CHALLENGE_BOND_GEN

    # Settle challenge:
    mock_audit(world.vm, compliance_bps=9500)
    world.contract.adjudicate_bid_challenge(tender.id, 1)
    summary3 = world.contract.get_native_custody_summary()
    assert summary3["conservation_ok"] is True
    assert summary3["active_challenge_bonds"] == 0

    # Finalize award:
    world.contract.finalize_tender_award(tender.id)
    summary4 = world.contract.get_native_custody_summary()
    assert summary4["conservation_ok"] is True
    assert summary4["active_bid_bonds"] == 0
    # Everything is in refundable balances, 0 wei lost!
    assert summary4["native_custody_balance"] == summary4["total_refundable_balances"]

def test_60_withdraw_refundable_native_full(world, tender):
    # Give bob some refundable balance via surplus
    submit_bid(world.vm, world.contract, world.bob, tender.id, value=DEFAULT_BID_BOND_GEN + 250_000)
    bob_ref = world.contract.get_refundable_balance(addr_hex(world.bob))
    assert bob_ref == 250_000

    world.vm.sender = world.bob
    res = world.contract.claim_refundable_balance()
    assert res["amount_wei"] == 250_000
    assert res["remaining_refundable_wei"] == 0

    assert world.contract.get_refundable_balance(addr_hex(world.bob)) == 0

def test_61_withdraw_refundable_native_partial(world, tender):
    submit_bid(world.vm, world.contract, world.bob, tender.id, value=DEFAULT_BID_BOND_GEN + 300_000)
    world.vm.sender = world.bob
    res = world.contract.withdraw_refundable_native(100_000)
    assert res["amount_wei"] == 100_000
    assert res["remaining_refundable_wei"] == 200_000
    assert world.contract.get_refundable_balance(addr_hex(world.bob)) == 200_000

def test_62_withdraw_refundable_fails_if_zero_or_exceeding(world):
    world.vm.sender = world.bob
    with pytest.raises(Exception, match=r"\[EXPECTED\] no refundable balance available"):
        world.contract.withdraw_refundable_native(1000)

def test_63_strict_asset_domain_separation_zero_cross_domain_leakage(world, tender):
    """TPT vault movements never alter native custody; Native bond movements never alter TPT vault."""
    meta_before = world.contract.get_token_metadata()
    native_before = world.contract.get_native_custody_summary()

    # Domain B activity:
    submit_bid(world.vm, world.contract, world.bob, tender.id)
    meta_after_bid = world.contract.get_token_metadata()
    native_after_bid = world.contract.get_native_custody_summary()

    # TPT vault completely unaffected by native bond!
    assert meta_after_bid["vault_custody_balance"] == meta_before["vault_custody_balance"]
    assert meta_after_bid["total_supply"] == meta_before["total_supply"]
    assert native_after_bid["native_custody_balance"] == native_before["native_custody_balance"] + DEFAULT_BID_BOND_GEN
