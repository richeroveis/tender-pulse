# TenderPulse 🏛️⚡

> **AI-Audited Public Procurement & Reverse-Auction RFP Award Hub on GenLayer Studionet**  
> *Chain ID: 61999* | *Contract:* [`0xc48cbf6D7D4B3ddFFe496f8046D37c9C64717acF`](https://explorer-studio.genlayer.com/address/0xc48cbf6D7D4B3ddFFe496f8046D37c9C64717acF) | *Live App:* [https://richeroveis.github.io/tender-pulse/](https://richeroveis.github.io/tender-pulse/)

[![Lint](https://img.shields.io/badge/genvm--lint-passed%20(3%20checks)-success)](file:///home/hoveiser/Project/TenderPulse/contracts/tender_pulse.py)
[![Tests](https://img.shields.io/badge/pytest-63%2F63%20passed%20(100%25)-brightgreen)](file:///home/hoveiser/Project/TenderPulse/tests/test_tender_pulse_direct.py)
[![Studionet](https://img.shields.io/badge/GenLayer%20Studionet-Chain%2061999-teal)](https://explorer-studio.genlayer.com/address/0xc48cbf6D7D4B3ddFFe496f8046D37c9C64717acF)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](file:///home/hoveiser/Project/TenderPulse/LICENSE)

---

## Overview

**TenderPulse** brings trustless accountability to municipal, DAO, and enterprise public procurement. It replaces opaque evaluation committees with decentralized **GenLayer AI validator consensus** paired with a competitive **reverse-auction bid room**.

### The Problem It Solves
Traditional public tenders suffer from procurement bias, collusion, opaque qualification scoring, and slow vendor disputes. Existing Web3 escrow platforms only lock tokens deterministically, lacking the semantic intelligence to evaluate whether a vendor's submitted technical proposal satisfies an RFP's engineering specification.

### The TenderPulse Solution
1. **Domain A (`TPT` Procurement Award Escrow)**: Buyers lock procurement budget tokens in custody when publishing an RFP.
2. **Domain B (`Native GEN` Vendor Bid & Challenge Bonds)**: Competing vendors submit descending price quotes staked with native GEN bid bonds to prevent spam and Sybil proposals.
3. **Dual-Predicate AI Compliance Consensus**: GenLayer validators execute non-deterministic audits (`gl.nondet.web.render` + `gl.eq_principle.prompt_comparative`), evaluating both **provenance authenticity** and **RFP criteria relevance** on a discrete **250-bps grid**.
4. **Automated Lowest-Cost Award Settlement**: The lowest-priced qualified bidder receives the contract award; unspent budget is refunded to the buyer, and runner-up vendor bonds are returned in full.

---

## 12 Hard Steward Invariants

| Invariant | Description | Enforced Implementation |
| :--- | :--- | :--- |
| **Rule 1: Classic SDK & No Admin Bypass** | Uses classic `from genlayer import *`. Zero deterministic bypasses, zero mock clock advances. | `contracts/tender_pulse.py:1` |
| **Rule 2: Asset Domain Separation** | Domain A (`TPT` token) and Domain B (`Native GEN` bonds) are 100% segregated. | `contracts/tender_pulse.py:90-130` |
| **Rule 3: Discrete 250-bps Grid** | Compliance scores quantize to multiples of 250 bps. | `contracts/tender_pulse.py:250` |
| **Rule 4: Dual-Predicate Audit** | Evaluates `provenance_valid` and `supports_rfp_criteria` independently. Off-topic yields 0 bps. | `contracts/tender_pulse.py:245` |
| **Rule 5: Zero-Slash Conforming Invariant** | Slashing is strictly 0 whenever score $\ge$ threshold and criteria are met. | `contracts/tender_pulse.py:133-145` |
| **Rule 6: Single Unified Audit Consensus** | Shared internal helper `_run_rfp_compliance_audit_nondet` across evaluations and challenges. | `contracts/tender_pulse.py:230-265` |
| **Rule 7: Single Winner Sync Invariant** | Shared `_sync_winning_bid_if_evaluated` updates winning bidder across all paths. | `contracts/tender_pulse.py:147-158` |
| **Rule 8: Non-Trapping Soft-Fail Payables** | Payable functions credit 100% value to `refundable_balances` on business rejection. | `contracts/tender_pulse.py:160-175` |
| **Rule 9: Fail-Closed Unavailable Fetches** | HTTP $\ge 400$ or $<32$ substantive chars triggers `FAIL_CLOSED`, blocking settlement. | `contracts/tender_pulse.py:238-242` |
| **Rule 10: Supported EOA Payouts** | Native GEN dispatched via `IEoaRecipient`, preserving balances on delivery failure. | `contracts/tender_pulse.py:177-195` |
| **Rule 11: Zero-Residue Conservation** | `native_custody == bid_bonds + challenge_bonds + refundable_balances` (0 wei stranded). | `contracts/tender_pulse.py:122-128` |
| **Rule 12: Mutual Co-Sign Settlement** | 2-party cooperative settlement path with matching buyer and vendor payout percentages. | `contracts/tender_pulse.py:400-435` |

---

## Architecture Diagram

```
                 +---------------------------------------------------------+
                 |            GenLayer Studionet (Chain 61999)             |
                 +---------------------------------------------------------+
                                              |
                +-----------------------------+-----------------------------+
                |                                                           |
  [Domain A: TPT Escrow]                                      [Domain B: Native GEN Bonds]
  - Buyer budget locked in custody                            - Vendor bid bonds staked
  - Surplus savings refunded upon award                       - Challenge bonds staked
  - Lowest qualified quote distributed                        - 0 wei stranded residue
                |                                                           |
                +-----------------------------+-----------------------------+
                                              |
                     +------------------------------------------------+
                     |        AI Validator Consensus (nondet)         |
                     | - gl.nondet.web.render (fail-closed < 32 char) |
                     | - gl.eq_principle.prompt_comparative           |
                     | - Provenance Valid & Supports Criteria         |
                     | - Discrete 250-bps Compliance Grid             |
                     +------------------------------------------------+
```

---

## Live Studionet Deployment

- **Contract Address**: `0xc48cbf6D7D4B3ddFFe496f8046D37c9C64717acF`
- **Explorer**: [https://explorer-studio.genlayer.com/address/0xc48cbf6D7D4B3ddFFe496f8046D37c9C64717acF](https://explorer-studio.genlayer.com/address/0xc48cbf6D7D4B3ddFFe496f8046D37c9C64717acF)
- **Frontend App**: [https://richeroveis.github.io/tender-pulse/](https://richeroveis.github.io/tender-pulse/)
- **Demo Video**: [`docs/demo-video-subtitled.mp4`](file:///home/hoveiser/Project/TenderPulse/docs/demo-video-subtitled.mp4)
- **Protocol Logo**: [`docs/logo.png`](file:///home/hoveiser/Project/TenderPulse/docs/logo.png)

---

## Quick Start & Verification

### 1. Verify Contract Syntax & Linting
```bash
genvm-lint check contracts/tender_pulse.py
```

### 2. Run Direct Test Suite (63 Tests, 100% Pass)
```bash
python3 -m pytest tests/ -q
```

### 3. Build Bespoke Frontend
```bash
cd frontend
npm run build
```

---

## Multi-Signer Lifecycle Testing

The protocol lifecycle is orchestrated via `scripts/deploy_studionet.py`, verifying:
1. **Contract Deployment**: Published with classic SDK dependencies.
2. **Soft-Fail Demonstration**: Underpaid bid credited to `refundable_balances` and claimed to EOA wallet with balance verification.
3. **Primary Tender Creation**: Buyer locks 120,000 TPT budget.
4. **Competing Bids**: Vendor Alpha quotes 95,000 TPT; Vendor Beta quotes 78,000 TPT.
5. **AI Validator Consensus**: Validators reach `MAJORITY_AGREE` on technical compliance.
6. **Award Settlement**: Vendor Beta wins at 78,000 TPT; buyer is refunded 42,000 TPT in savings.
7. **Bond Refunds**: Vendor Beta and Vendor Alpha reclaim 100% of their Native GEN bonds.

---

## License

MIT License. Designed and maintained by `richeroveis <oveis.richer@gmail.com>`.
