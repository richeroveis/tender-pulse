# TenderPulse — Deployment & Multi-Signer Lifecycle Specification

## Network & RPC Infrastructure

- **Target Network**: GenLayer Studionet
- **Chain ID**: `61999`
- **JSON-RPC Endpoint**: `https://studio.genlayer.com/api`
- **Block Explorer**: `https://explorer-studio.genlayer.com`
- **Contract Language**: GenLayer Python VM (Classic SDK, `from genlayer import *`)
- **Execution Dependency**: `# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }`

---

## Multi-Signer Role Topology

| Role Name | Protocol Function | Asset Domain Interaction |
| :--- | :--- | :--- |
| **Procurement Buyer** | Publishes RFP tenders, funds award escrow, finalizes lowest-cost winner | Locks Domain A (`TPT`), receives surplus savings refund upon award |
| **Vendor Alpha** | Submits conforming proposal at 95,000 TPT with Native GEN bid bond | Stakes Domain B (`GEN`), claims 100% bond refund as evaluated runner-up |
| **Vendor Beta** | Submits conforming proposal at 78,000 TPT with Native GEN bid bond | Stakes Domain B (`GEN`), wins award, receives 78,000 TPT + 100% bond refund |
| **Challenger Charlie** | Files bid-integrity challenges or probes payable soft-fail bounds | Stakes Domain B (`GEN`), claims non-trapping refunds via `IEoaRecipient` |
| **Observer Dave** | Read-only validator observer, audits on-chain state and custody | Read-only inspection of discrete 250-bps scores and custody balance invariants |

---

## End-to-End Lifecycle Sequence

```mermaid
sequenceDiagram
    autonumber
    actor Buyer as Procurement Buyer
    actor Alpha as Vendor Alpha
    actor Beta as Vendor Beta
    participant Contract as TenderPulse Ledger
    participant Consensus as GenLayer AI Validators
    actor Recipient as EOA Wallets

    Buyer->>Contract: create_tender(budget=120k TPT, min_qual=8000 bps)
    Note over Contract: Domain A Escrow Locked (120,000 TPT)

    Alpha->>Contract: submit_vendor_bid_payable(quote=95k TPT, url_alpha) + 0.00002 GEN
    Note over Contract: Domain B Active Bid Bond +0.00002 GEN

    Beta->>Contract: submit_vendor_bid_payable(quote=78k TPT, url_beta) + 0.00002 GEN
    Note over Contract: Domain B Active Bid Bond +0.00002 GEN

    Buyer->>Contract: evaluate_vendor_bid(tender_id=1, bid_id=1)
    Contract->>Consensus: gl.eq_principle.prompt_comparative(fetch_and_audit)
    Consensus-->>Contract: MAJORITY_AGREE (10,000 bps, QUALIFIED)

    Buyer->>Contract: evaluate_vendor_bid(tender_id=1, bid_id=2)
    Contract->>Consensus: gl.eq_principle.prompt_comparative(fetch_and_audit)
    Consensus-->>Contract: MAJORITY_AGREE (10,000 bps, QUALIFIED)
    Note over Contract: Beta synced as lowest qualified bidder (78k < 95k)

    Buyer->>Contract: finalize_tender_award(tender_id=1)
    Note over Contract: Beta awarded 78,000 TPT; Buyer refunded 42,000 TPT savings; Beta bond unlocked

    Alpha->>Contract: refund_runner_up_bid_bond(tender_id=1, bid_id=1)
    Note over Contract: Alpha bond routed 100% to refundable_balances

    Alpha->>Contract: claim_refundable_balance()
    Contract->>Recipient: IEoaRecipient.emit_transfer(value=amount)
    Note over Recipient: Native GEN delivered with 0 stranded residue
```

---

## 4-Way LF SHA-256 Identity Invariant

Every deployment artifact maintains cryptographic equivalence across all storage tiers:
1. `local_file_lf_sha256`: SHA-256 of `contracts/tender_pulse.py` normalized to Unix LF line endings.
2. `git_blob_sha256`: `git show HEAD:contracts/tender_pulse.py | sha256sum`.
3. `on_chain_code_sha256`: Code retrieved via `gen_getContractCode(contract_address)` base64/hex decoded.
4. `deployment_payload_sha256`: Exact source code string deployed in the deployment transaction.

All four values must match with 0 byte deviation.
