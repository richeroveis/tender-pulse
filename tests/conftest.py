"""Shared fixtures and helpers for TenderPulse direct mode tests."""

from __future__ import annotations

import json
import os
import sys
from types import SimpleNamespace
import pytest
import eth_utils

if sys.platform == "win32":
    _real_unlink = os.unlink
    _real_remove = os.remove

    def _force_unlink(path, *args, **kwargs):
        import stat
        try:
            _real_unlink(path, *args, **kwargs)
        except PermissionError:
            os.chmod(path, stat.S_IWRITE)
            _real_unlink(path, *args, **kwargs)

    os.unlink = _force_unlink
    os.remove = _force_unlink

TPT = 10**6
SDK_VERSION = os.environ.get("GENLAYER_DIRECT_SDK_VERSION", "v0.2.16")
BASE_ISO = "2030-01-01T00:00:00Z"
BASE_TS = 1893456000

DEFAULT_TITLE = "Decentralized High-Speed RPC Node Cluster Procurement"
DEFAULT_RFP_SPEC = "Procurement of geo-distributed, fail-safe JSON-RPC validator gateways serving 50k req/sec with TLS 1.3, SLA >= 99.99%, and automated health failover telemetry endpoints."
DEFAULT_MAX_BUDGET = 100_000 * TPT
DEFAULT_MIN_QUAL_BPS = 8000
DEFAULT_BID_BOND_GEN = 500_000_000_000_000_000  # 0.5 GEN in wei
DEFAULT_CHALLENGE_BOND_GEN = 250_000_000_000_000_000  # 0.25 GEN in wei
DEFAULT_BID_WINDOW = 3600
DEFAULT_CHALLENGE_WINDOW = 3600

DEFAULT_SPEC_URL = "https://raw.githubusercontent.com/richeroveis/tender-pulse/main/evidence/proposals/bid_proposal_alpha.md"
DEFAULT_PROPOSAL_BODY = """# TenderPulse Technical Proposal: High-Speed RPC Node Cluster
Architecture: Multi-region geo-replicated gateway cluster with TLS 1.3 termination, raft health telemetry, and 50k rps sustained capacity.
Conforms strictly to RFC 8446 and procurement RFP specifications.
Automated failover SLA: 99.995%.
"""

def set_chain_time(direct_vm, iso_timestamp: str) -> None:
    direct_vm.warp(iso_timestamp)
    import genlayer.gl as gl_module
    gl_module.message_raw["datetime"] = iso_timestamp

def addr_hex(account) -> str:
    if isinstance(account, str):
        return eth_utils.to_checksum_address(account)
    return eth_utils.to_checksum_address("0x" + bytes(account).hex())

def clear_mocks(direct_vm) -> None:
    direct_vm._web_mocks.clear()
    direct_vm._llm_mocks.clear()

def mint(direct_vm, contract, account, amount: int = 5_000_000 * TPT) -> None:
    direct_vm.sender = account
    contract.faucet_or_deposit(amount)

def create_tender(
    direct_vm,
    contract,
    buyer,
    title: str = DEFAULT_TITLE,
    rfp_spec: str = DEFAULT_RFP_SPEC,
    max_budget: int = DEFAULT_MAX_BUDGET,
    min_qual_bps: int = DEFAULT_MIN_QUAL_BPS,
    bid_bond: int = DEFAULT_BID_BOND_GEN,
    challenge_bond: int = DEFAULT_CHALLENGE_BOND_GEN,
    bid_win: int = DEFAULT_BID_WINDOW,
    challenge_win: int = DEFAULT_CHALLENGE_WINDOW,
) -> dict:
    direct_vm.sender = buyer
    return contract.create_tender(
        title,
        rfp_spec,
        max_budget,
        min_qual_bps,
        bid_bond,
        challenge_bond,
        bid_win,
        challenge_win,
    )

def submit_bid(
    direct_vm,
    contract,
    vendor,
    tender_id: int,
    bid_amount_tpt: int = 80_000 * TPT,
    spec_url: str = DEFAULT_SPEC_URL,
    value: int | None = None,
) -> dict:
    direct_vm.sender = vendor
    t = contract.get_tender(tender_id)
    req = int(t.get("required_bid_bond_gen", 0))
    direct_vm.value = req if value is None else value
    try:
        return contract.submit_vendor_bid_payable(tender_id, bid_amount_tpt, spec_url)
    finally:
        direct_vm.value = 0

def challenge_bid(
    direct_vm,
    contract,
    challenger,
    tender_id: int,
    bid_id: int,
    reason: str = "Technical proposal URL is off-topic RFC document",
    counter_url: str = "https://w3.org/standards/counter_evidence.html",
    value: int | None = None,
) -> dict:
    direct_vm.sender = challenger
    t = contract.get_tender(tender_id)
    req = int(t.get("required_challenge_bond_gen", 0))
    direct_vm.value = req if value is None else value
    try:
        return contract.challenge_vendor_bid_payable(tender_id, bid_id, reason, counter_url)
    finally:
        direct_vm.value = 0

def mock_audit(
    direct_vm,
    provenance_valid: bool = True,
    supports_rfp: bool = True,
    compliance_bps: int = 9250,
    summary: str = "Fully qualified compliant technical proposal.",
    body: str | None = None,
    url_pattern: str = r"https://.*",
    clear_existing: bool = True,
) -> None:
    if clear_existing:
        clear_mocks(direct_vm)
    direct_vm.mock_web(url_pattern, {"status": 200, "body": body or DEFAULT_PROPOSAL_BODY})
    payload = f"{'true' if provenance_valid else 'false'}|{'true' if supports_rfp else 'false'}|{compliance_bps}|{summary}"
    direct_vm.mock_llm(r"(?s).*AI Public Procurement Auditor.*", payload)

@pytest.fixture
def world(direct_vm, direct_deploy, direct_alice, direct_bob, direct_charlie):
    contract = direct_deploy("contracts/tender_pulse.py", sdk_version=SDK_VERSION)
    set_chain_time(direct_vm, BASE_ISO)
    clear_mocks(direct_vm)
    for account in (direct_alice, direct_bob, direct_charlie):
        mint(direct_vm, contract, account)
    return SimpleNamespace(
        contract=contract,
        vm=direct_vm,
        alice=direct_alice,
        bob=direct_bob,
        charlie=direct_charlie,
    )

@pytest.fixture
def tender(world):
    res = create_tender(world.vm, world.contract, world.alice)
    return SimpleNamespace(
        id=int(res["tender_id"]),
        buyer=world.alice,
        vendor=world.bob,
        challenger=world.charlie,
        contract=world.contract,
        vm=world.vm,
    )
