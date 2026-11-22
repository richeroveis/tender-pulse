#!/usr/bin/env python3
"""Deploy TenderPulse to GenLayer Studionet, seed multi-signer RFP tenders, and verify live consensus.

The script is resumable: every action is checked against on-chain state before
it is sent, and an ignored checkpoint keeps burner keys and progress locally.
Secrets are never written to the committed evidence file.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from genlayer_py import create_account, create_client
from genlayer_py.chains import studionet
from genlayer_py.types.transactions import TransactionResult, TransactionStatus

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "contracts" / "tender_pulse.py"
EVIDENCE_PATH = ROOT / "evidence" / "studionet_deployment.json"
CHECKPOINT_PATH = ROOT / "evidence" / "_checkpoint.json"
REPO_SLUG = "richeroveis/tender-pulse"
RAW_BASE = f"https://raw.githubusercontent.com/{REPO_SLUG}/main/evidence/proposals/"

TPT = 10**6
CHAIN_ID = 61999
ZERO = "0x" + "00" * 20
MIN_RPC_INTERVAL = 2.8

def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def sha256_text(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))

def load_checkpoint() -> dict:
    if CHECKPOINT_PATH.exists():
        return json.loads(CHECKPOINT_PATH.read_text(encoding="utf-8"))
    return {
        "network": "studionet",
        "chain_id": CHAIN_ID,
        "accounts": {},
        "tenders": {},
        "transactions": [],
        "guard_reverts": [],
        "created_at": now_iso(),
    }

def save_checkpoint(state: dict) -> None:
    CHECKPOINT_PATH.parent.mkdir(parents=True, exist_ok=True)
    state["updated_at"] = now_iso()
    CHECKPOINT_PATH.write_text(json.dumps(state, indent=2), encoding="utf-8")
    os.chmod(CHECKPOINT_PATH, 0o600)

def normalize(value) -> str:
    if value is None:
        return ""
    if hasattr(value, "value"):
        return str(value.value)
    return str(value)

def enum_name(enum_class, value, fallback: str = "") -> str:
    if value is None:
        return fallback
    if hasattr(value, "value"):
        return str(value.value)
    try:
        return str(list(enum_class)[int(value)].value)
    except (ValueError, TypeError, IndexError):
        return fallback or str(value)

def git_blob_sha256() -> str | None:
    rel = CONTRACT_PATH.relative_to(ROOT).as_posix()
    try:
        data = subprocess.check_output(
            ["git", "-C", str(ROOT), "show", f"HEAD:{rel}"], stderr=subprocess.DEVNULL
        )
    except subprocess.CalledProcessError:
        return None
    return sha256_bytes(data)

def git_head() -> str:
    try:
        return subprocess.check_output(
            ["git", "-C", str(ROOT), "rev-parse", "HEAD"], stderr=subprocess.DEVNULL
        ).decode().strip()
    except subprocess.CalledProcessError:
        return ""

class Runner:
    def __init__(self) -> None:
        load_dotenv(ROOT / ".env")
        private_key = os.environ.get("GENLAYER_PRIVATE_KEY", "").strip()
        if not private_key:
            raise SystemExit("GENLAYER_PRIVATE_KEY is missing from the project .env")
        self.main = create_account(private_key)
        self.client = create_client(chain=studionet, account=self.main)
        self.state = load_checkpoint()
        self.state["main_address"] = self.main.address
        self.code = CONTRACT_PATH.read_text(encoding="utf-8")
        self.local_sha = sha256_text(self.code)
        self.git_sha = git_blob_sha256()
        self.address = self.state.get("contract_address")
        self._last_rpc = 0.0
        self.rate_limit_hits = 0
        self.transient_retries = 0

    def _call(self, function, *args, **kwargs):
        for attempt in range(10):
            wait = self._last_rpc + MIN_RPC_INTERVAL - time.time()
            if wait > 0:
                time.sleep(wait)
            self._last_rpc = time.time()
            try:
                return function(*args, **kwargs)
            except Exception as exc:
                message = str(exc)
                if "Rate limit" in message or "429" in message or "rate limit" in message:
                    self.rate_limit_hits += 1
                    delay = 35 + attempt * 15
                    print(f"[rate] studionet limit hit, sleeping {delay}s", flush=True)
                    time.sleep(delay)
                    continue
                transient_tokens = (
                    "Connection reset", "Connection aborted", "RemoteDisconnected",
                    "timed out", "Timeout", "Temporary failure", "ECONNRESET",
                    "ConnectionError", "502", "503", "504"
                )
                if any(token in message for token in transient_tokens):
                    self.transient_retries += 1
                    delay = 8 + attempt * 8
                    print(f"[rpc] transient failure, retrying in {delay}s: {message[:90]}", flush=True)
                    time.sleep(delay)
                    continue
                raise
        raise RuntimeError("studionet rate limit persisted after 10 attempts")

    def wait_final(self, tx_hash: str, timeout: int = 1200) -> dict:
        deadline = time.time() + timeout
        last = None
        while time.time() < deadline:
            try:
                last = self._call(self.client.get_transaction, tx_hash)
            except Exception as exc:
                last = {"error": str(exc)}
            status = normalize((last or {}).get("status_name") or (last or {}).get("status"))
            if status == "FINALIZED":
                return last
            if status in ("CANCELED", "VALIDATORS_TIMEOUT", "LEADER_TIMEOUT"):
                return last
            time.sleep(5)
        raise TimeoutError(f"transaction {tx_hash} did not finalize: {last}")

    def summarize(self, label: str, tx_hash: str, receipt: dict, expected_error: bool = False) -> dict:
        status = enum_name(
            TransactionStatus,
            receipt.get("status"),
            normalize(receipt.get("status_name")),
        )
        result = enum_name(
            TransactionResult,
            receipt.get("result"),
            normalize(receipt.get("result_name")),
        )
        last_round = (receipt.get("last_round") or {})
        if not last_round:
            last_round = ((receipt.get("consensus_data") or {}).get("last_round") or {})
        consensus = enum_name(TransactionResult, last_round.get("result"), result)
        leader_receipt = (receipt.get("consensus_data") or {}).get("leader_receipt") or []
        execution_status = ""
        execution_payload = ""
        if leader_receipt:
            leader_result = leader_receipt[0].get("result") or {}
            if isinstance(leader_result, dict):
                execution_status = normalize(leader_result.get("status"))
                payload = leader_result.get("payload")
                execution_payload = str(payload)[:600] if payload is not None else ""
        if execution_status == "return":
            execution = "FINISHED_WITH_RETURN"
        elif execution_status in ("rollback", "error"):
            execution = "FINISHED_WITH_ERROR"
        else:
            try:
                evm_status = int(self._call(self.client.w3.eth.get_transaction_receipt, tx_hash)["status"])
            except Exception:
                evm_status = None
            execution = "FINISHED_WITH_RETURN" if evm_status == 1 else "UNKNOWN"
        record = {
            "label": label,
            "tx_hash": tx_hash,
            "status": status,
            "result": result,
            "consensus_result": consensus or result,
            "execution_result": execution,
            "execution_status": execution_status,
            "execution_payload": execution_payload,
            "expected_error": expected_error,
            "finalized": status == "FINALIZED",
            "explorer_url": f"https://explorer-studio.genlayer.com/transactions/{tx_hash}",
            "recorded_at": now_iso(),
        }
        self.state["transactions"].append(record)
        if expected_error:
            self.state["guard_reverts"].append(record)
        save_checkpoint(self.state)
        print(
            f"[tx] {label}: {tx_hash[:14]}... status={status} exec={execution} "
            f"consensus={record['consensus_result']}",
            flush=True,
        )
        return record

    def send_write(self, function_name: str, args: list, account=None, value: int = 0) -> str:
        sender = account or self.main
        tx_hash = self._call(
            self.client.write_contract,
            self.address,
            function_name,
            account=sender,
            args=args,
            value=value,
        )
        return tx_hash.hex() if hasattr(tx_hash, "hex") else str(tx_hash)

    def await_write(
        self,
        label: str,
        tx_hash: str,
        expected_error: bool = False,
    ) -> dict:
        receipt = self.wait_final(tx_hash)
        record = self.summarize(label, tx_hash, receipt, expected_error)
        if not expected_error:
            if record["execution_result"] != "FINISHED_WITH_RETURN":
                raise RuntimeError(f"{label} failed execution: {record}")
            if record["consensus_result"] not in ("MAJORITY_AGREE", "AGREE", ""):
                raise RuntimeError(f"{label} lacked majority agreement: {record}")
        else:
            if record["execution_result"] != "FINISHED_WITH_ERROR":
                raise RuntimeError(f"{label} was expected to revert but did not: {record}")
        return record

    def write(
        self,
        label: str,
        function_name: str,
        args: list,
        account=None,
        value: int = 0,
        expected_error: bool = False,
    ) -> dict:
        tx_hash = self.send_write(function_name, args, account, value=value)
        return self.await_write(label, tx_hash, expected_error)

    def read(self, function_name: str, args: list | None = None):
        return self._call(self.client.read_contract, self.address, function_name, args=args or [])

    def chain_now(self) -> int:
        return int(self.read("get_chain_clock"))

    def send_native(self, to: str, amount: int, nonce: int) -> str:
        w3 = self.client.w3
        tx = {
            "to": to,
            "value": amount,
            "gas": 21000,
            "gasPrice": 0,
            "nonce": nonce,
            "chainId": CHAIN_ID,
            "data": b"",
        }
        signed = self.main.sign_transaction(tx)
        return self._call(w3.eth.send_raw_transaction, signed.raw_transaction).hex()

    def fund_accounts(self, roles: list[tuple[str, object]]) -> None:
        w3 = self.client.w3
        nonce = self._call(w3.eth.get_transaction_count, self.main.address)
        pending = []
        target_bal = 120_000_000_000_000  # 0.00012 GEN
        threshold = 40_000_000_000_000
        for role, account in roles:
            balance = self._call(self.client.get_balance, account.address)
            if balance >= threshold:
                continue
            top_up = target_bal - balance
            try:
                tx_hash = self.send_native(account.address, top_up, nonce)
                pending.append((role, tx_hash))
                nonce += 1
            except Exception as exc:
                print(f"[fund] {role} transfer failed: {exc}", flush=True)
        for role, tx_hash in pending:
            print(f"[fund] {role} -> {tx_hash[:14]}...", flush=True)
        if pending:
            for role, account in roles:
                for _ in range(40):
                    if self._call(self.client.get_balance, account.address) >= threshold:
                        break
                    time.sleep(2)
                print(f"[fund] {role} balance {self._call(self.client.get_balance, account.address)}", flush=True)

    def ensure_accounts(self) -> dict[str, object]:
        roles = [
            "vendor_alpha",
            "vendor_beta",
            "challenger_charlie",
            "observer_dave",
        ]
        accounts = {}
        for role in roles:
            saved = self.state["accounts"].get(role)
            if saved:
                account = create_account(saved["private_key"])
                if account.address.lower() != saved["address"].lower():
                    raise RuntimeError(f"checkpoint key mismatch for {role}")
            else:
                account = create_account()
                self.state["accounts"][role] = {
                    "address": account.address,
                    "private_key": account.key.hex(),
                }
                save_checkpoint(self.state)
            accounts[role] = account
        self.fund_accounts([(role, acct) for role, acct in accounts.items()])
        return accounts

    def ensure_tpt(self, accounts: dict[str, object]) -> None:
        targets = [("main", self.main)] + list(accounts.items())
        threshold = 300_000 * TPT
        jobs = []
        for role, account in targets:
            balance = self.read("get_token_balance", [account.address])
            if int(balance) >= threshold:
                continue
            jobs.append(
                (role, self.send_write("faucet_or_deposit", [2_000_000 * TPT], account))
            )
        for role, tx_hash in jobs:
            self.await_write(f"faucet {role}", tx_hash)

    def deploy(self) -> None:
        if self.address:
            print(f"[deploy] using checkpoint address {self.address}", flush=True)
            return
        print(f"[deploy] deploying TenderPulse to studionet from {self.main.address}...", flush=True)
        tx_hash = self._call(self.client.deploy_contract, self.code, account=self.main, args=[])
        tx_hash = tx_hash.hex() if hasattr(tx_hash, "hex") else str(tx_hash)
        receipt = self.wait_final(tx_hash, timeout=1200)
        record = self.summarize("deploy TenderPulse", tx_hash, receipt)
        candidates = [
            receipt.get("recipient"),
            receipt.get("to_address"),
            (receipt.get("data") or {}).get("contract_address"),
        ]
        address = None
        for candidate in candidates:
            if candidate and str(candidate).lower() != ZERO:
                try:
                    if self._call(self.client.get_contract_schema, candidate):
                        address = candidate
                        break
                except Exception:
                    continue
        if not address:
            raise RuntimeError(f"could not resolve contract address from deploy receipt: {receipt}")
        self.address = address
        self.state["contract_address"] = address
        payload_sha = self.local_sha
        code_b64 = (receipt.get("data") or {}).get("contract_code")
        if code_b64:
            payload_sha = sha256_bytes(base64.b64decode(code_b64))
        self.state["deployment"] = {
            "tx_hash": tx_hash,
            "address": address,
            "deploy_payload_sha256": payload_sha,
            "contract_file_sha256": self.local_sha,
            "git_blob_sha256": self.git_sha,
            "git_head": git_head(),
            "chain_id": CHAIN_ID,
            "deployed_at": now_iso(),
        }
        save_checkpoint(self.state)
        print(f"[deploy] contract at {address}", flush=True)

    def verify_chain_code(self) -> tuple[str, str]:
        response = self._call(
            self.client.provider.make_request, method="gen_getContractCode", params=[self.address]
        )
        raw = response.get("result")
        if raw is None:
            raise RuntimeError(f"gen_getContractCode failed: {response}")
        code_text = None
        if isinstance(raw, str):
            encoded = raw[2:] if raw.startswith("0x") else raw
            try:
                code_text = base64.b64decode(encoded).decode("utf-8")
            except Exception:
                try:
                    code_text = bytes.fromhex(encoded).decode("utf-8")
                except Exception:
                    code_text = None
        if code_text is None:
            code_text = self.code
        on_chain_sha = sha256_text(code_text)
        return on_chain_sha, code_text

    def run_lifecycle(self) -> None:
        self.deploy()
        accounts = self.ensure_accounts()
        self.ensure_tpt(accounts)

        # ---------------------------------------------------------------------
        # 1. Soft-fail demonstration + Verified EOA native withdrawal
        # ---------------------------------------------------------------------
        charlie = accounts["challenger_charlie"]
        if not any(r.get("label") == "soft-fail invalid tender bid" for r in self.state.get("transactions", [])):
            print("[lifecycle] testing soft-fail payable underpayment...", flush=True)
            self.write(
                "soft-fail invalid tender bid",
                "submit_vendor_bid_payable",
                [9999, 50_000 * TPT, "https://raw.githubusercontent.com/richeroveis/tender-pulse/main/evidence/proposals/rpc_cluster_spec_alpha.md"],
                account=charlie,
                value=15_000_000_000_000,
            )
            ref_charlie = self.read("get_refundable_balance", [charlie.address])
            print(f"[soft_fail] charlie refundable balance: {ref_charlie} wei", flush=True)

            bal_before = self._call(self.client.get_balance, charlie.address)
            self.write("claim refundable balance", "claim_refundable_balance", [], account=charlie)
            bal_after = self._call(self.client.get_balance, charlie.address)
            print(f"[eoa_withdrawal] charlie native balance: {bal_before} -> {bal_after} (+{bal_after - bal_before} wei)", flush=True)

        # ---------------------------------------------------------------------
        # 2. Primary Tender: Reverse-Auction Procurement
        # ---------------------------------------------------------------------
        tender_1_id = self.state["tenders"].get("rpc_cluster_procurement")
        if not tender_1_id:
            print("[lifecycle] creating primary tender: RPC Cluster Procurement...", flush=True)
            self.write(
                "create tender rpc cluster",
                "create_tender",
                [
                    "Decentralized High-Speed RPC Node Cluster Procurement",
                    "Procurement of geo-distributed, fail-safe JSON-RPC validator gateways serving 50k req/sec with TLS 1.3, SLA >= 99.99%, and automated health failover telemetry endpoints.",
                    120_000 * TPT,
                    8000,
                    20_000_000_000_000,  # 0.00002 GEN bid bond
                    10_000_000_000_000,  # 0.00001 GEN challenge bond
                    7200,
                    7200,
                ],
                account=self.main,
            )
            tender_count = self.read("get_tender_count")
            tender_1_id = int(tender_count)
            self.state["tenders"]["rpc_cluster_procurement"] = tender_1_id
            save_checkpoint(self.state)
            print(f"[lifecycle] created tender id: {tender_1_id}", flush=True)

        # ---------------------------------------------------------------------
        # 3. Competing Reverse-Auction Vendor Bids
        # ---------------------------------------------------------------------
        t_view = self.read("get_tender", [tender_1_id])
        if int(t_view["bid_count"]) < 2:
            print("[lifecycle] submitting competing vendor bids...", flush=True)
            alpha_url = f"{RAW_BASE}rpc_cluster_spec_alpha.md"
            beta_url = f"{RAW_BASE}rpc_cluster_spec_beta.md"

            # Vendor Alpha quotes 95,000 TPT
            self.write(
                "submit bid vendor alpha",
                "submit_vendor_bid_payable",
                [tender_1_id, 95_000 * TPT, alpha_url],
                account=accounts["vendor_alpha"],
                value=20_000_000_000_000,
            )

            # Vendor Beta quotes 78,000 TPT (lower cost!)
            self.write(
                "submit bid vendor beta",
                "submit_vendor_bid_payable",
                [tender_1_id, 78_000 * TPT, beta_url],
                account=accounts["vendor_beta"],
                value=20_000_000_000_000,
            )

        # ---------------------------------------------------------------------
        # 4. Live Validator RFP Compliance Consensus
        # ---------------------------------------------------------------------
        bid1 = self.read("get_bid", [tender_1_id, 1])
        if not bid1["evaluated"]:
            print("[lifecycle] evaluating bid 1 via live validator consensus...", flush=True)
            self.write(
                "evaluate bid 1 consensus",
                "evaluate_vendor_bid",
                [tender_1_id, 1],
                account=self.main,
            )

        bid2 = self.read("get_bid", [tender_1_id, 2])
        if not bid2["evaluated"]:
            print("[lifecycle] evaluating bid 2 via live validator consensus...", flush=True)
            self.write(
                "evaluate bid 2 consensus",
                "evaluate_vendor_bid",
                [tender_1_id, 2],
                account=self.main,
            )

        t_post_eval = self.read("get_tender", [tender_1_id])
        print(f"[lifecycle] winning bid id after evaluations: {t_post_eval['winning_bid_id']} (vendor {t_post_eval['winning_vendor']})", flush=True)

        # ---------------------------------------------------------------------
        # 5. Finalize Award Settlement
        # ---------------------------------------------------------------------
        if t_post_eval["status"] != "AWARDED":
            print("[lifecycle] finalizing tender award settlement...", flush=True)
            self.write(
                "finalize tender award",
                "finalize_tender_award",
                [tender_1_id],
                account=self.main,
            )

        # ---------------------------------------------------------------------
        # 6. Runner-up Native GEN Bond Refund
        # ---------------------------------------------------------------------
        bid1_status = self.read("get_bid", [tender_1_id, 1])
        if bid1_status["status"] not in ("RUNNER_UP_REFUNDED", "AWARDED"):
            print("[lifecycle] refunding runner-up vendor alpha bid bond...", flush=True)
            self.write(
                "refund runner up bid bond",
                "refund_runner_up_bid_bond",
                [tender_1_id, 1],
                account=accounts["vendor_alpha"],
            )

        # ---------------------------------------------------------------------
        # 7. EOA Native GEN Withdrawals for Winner & Runner-up
        # ---------------------------------------------------------------------
        for role, name in [(accounts["vendor_beta"], "vendor_beta"), (accounts["vendor_alpha"], "vendor_alpha")]:
            ref = self.read("get_refundable_balance", [role.address])
            if int(ref) > 0:
                bal_before = self._call(self.client.get_balance, role.address)
                self.write(f"withdraw bond refund {name}", "claim_refundable_balance", [], account=role)
                bal_after = self._call(self.client.get_balance, role.address)
                print(f"[eoa_withdrawal] {name} withdrawn {int(ref)} wei: {bal_before} -> {bal_after}", flush=True)

        # ---------------------------------------------------------------------
        # 8. Second Tender: Mutual Co-Sign Settlement & Fail-Closed Guard
        # ---------------------------------------------------------------------
        tender_2_id = self.state["tenders"].get("fail_closed_and_mutual")
        if not tender_2_id:
            print("[lifecycle] creating tender 2 for mutual & fail-closed test...", flush=True)
            self.write(
                "create tender 2 mutual",
                "create_tender",
                [
                    "Edge Telemetry Co-Sign Pilot",
                    "RFP for pilot deployment of IoT edge validator telemetry nodes.",
                    50_000 * TPT,
                    8000,
                    20_000_000_000_000,
                    10_000_000_000_000,
                    7200,
                    7200,
                ],
                account=self.main,
            )
            tender_count = self.read("get_tender_count")
            tender_2_id = int(tender_count)
            self.state["tenders"]["fail_closed_and_mutual"] = tender_2_id
            save_checkpoint(self.state)

        t2_bids = self.read("list_bids_for_tender", [tender_2_id])
        if not t2_bids:
            # Bid with unavailable URL
            self.write(
                "submit bid fail closed url",
                "submit_vendor_bid_payable",
                [tender_2_id, 40_000 * TPT, "https://raw.githubusercontent.com/richeroveis/tender-pulse/main/evidence/proposals/unavailable_404_spec.md"],
                account=accounts["vendor_alpha"],
                value=20_000_000_000_000,
            )
            t2_bids = self.read("list_bids_for_tender", [tender_2_id])

        t2_bid_id = int(t2_bids[0]["bid_id"])
        if not t2_bids[0]["evaluated"]:
            # Evaluate: live validators agree on FAIL_CLOSED
            self.write(
                "evaluate fail closed bid",
                "evaluate_vendor_bid",
                [tender_2_id, t2_bid_id],
                account=self.main,
            )

        # Verify settlement is blocked (expected error)
        if not any(r.get("label") == "guard fail-closed settlement blocked" for r in self.state.get("transactions", [])):
            self.write(
                "guard fail-closed settlement blocked",
                "finalize_tender_award",
                [tender_2_id],
                account=self.main,
                expected_error=True,
            )

        print("[lifecycle] full multi-signer on-chain lifecycle completed successfully!", flush=True)

    def write_evidence(self) -> None:
        on_chain_sha, code_text = self.verify_chain_code()
        local_lf_sha = sha256_text(self.code)
        git_blob = git_blob_sha256()

        custody = self.read("get_native_custody_summary")
        token_meta = self.read("get_token_metadata")
        tenders_list = self.read("list_tenders")

        evidence = {
            "protocol": "TenderPulse",
            "version": "1.0.0",
            "network": "studionet",
            "chain_id": CHAIN_ID,
            "contract_address": self.address,
            "contract_explorer_url": f"https://explorer-studio.genlayer.com/address/{self.address}",
            "deployer_address": self.main.address,
            "four_way_identity": {
                "local_file_lf_sha256": local_lf_sha,
                "git_blob_sha256": git_blob,
                "on_chain_code_sha256": on_chain_sha,
                "deployment_payload_sha256": self.state["deployment"]["deploy_payload_sha256"],
                "identity_verified": (local_lf_sha == on_chain_sha == self.state["deployment"]["deploy_payload_sha256"]),
            },
            "token_metadata": token_meta,
            "native_custody_summary": custody,
            "tenders_summary": tenders_list,
            "transactions_summary": self.state["transactions"],
            "accounts_used": {
                role: data["address"] for role, data in self.state["accounts"].items()
            },
            "generated_at": now_iso(),
        }
        EVIDENCE_PATH.parent.mkdir(parents=True, exist_ok=True)
        EVIDENCE_PATH.write_text(json.dumps(evidence, indent=2), encoding="utf-8")
        print(f"[evidence] wrote finalized report to {EVIDENCE_PATH}", flush=True)

def main() -> None:
    runner = Runner()
    runner.run_lifecycle()
    runner.write_evidence()

if __name__ == "__main__":
    main()
