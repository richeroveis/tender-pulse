# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

from genlayer import *
from dataclasses import dataclass
from datetime import datetime, timezone
import json, re

@gl.evm.contract_interface
class IEoaRecipient:
    class View: pass
    class Write: pass
    def emit_transfer() -> None: pass

TOKEN_NAME, TOKEN_SYMBOL, TOKEN_DECIMALS = "TenderPulse Token", "TPT", 6
BPS_DENOMINATOR, GRID_STEP_BPS, MAX_FAUCET_PER_USER = 10000, 250, 10_000_000 * 10**6
MIN_SUBSTANTIVE_CHARS, MAX_SPEC_CHARS = 32, 12000

STATUS_OPEN, STATUS_EVALUATING, STATUS_CHALLENGED = "OPEN", "EVALUATING", "CHALLENGED"
STATUS_AWARDED, STATUS_SETTLED_ZERO_WINNERS = "AWARDED", "SETTLED_ZERO_WINNERS"
STATUS_EXPIRED_REFUNDED, STATUS_MUTUAL_SETTLED = "EXPIRED_REFUNDED", "MUTUAL_SETTLED"

BID_STATUS_SUBMITTED, BID_STATUS_EVALUATED = "SUBMITTED", "EVALUATED"
BID_STATUS_CHALLENGED, BID_STATUS_AWARDED = "CHALLENGED", "AWARDED"
BID_STATUS_DISQUALIFIED, BID_STATUS_RUNNER_UP_REFUNDED = "DISQUALIFIED", "RUNNER_UP_REFUNDED"

BAND_QUALIFIED, BAND_REMEDIATION = "QUALIFIED_AWARD_ELIGIBLE", "PARTIAL_REMEDIATION_HOLD"
BAND_DISQUALIFIED, BAND_FAIL_CLOSED = "NON_COMPLIANT_DISQUALIFIED", "EVIDENCE_UNAVAILABLE_FAIL_CLOSED"
BAND_ZERO_WINNERS, BAND_MUTUAL = "REFUNDABLE_ZERO_WINNERS", "MUTUAL_RELEASE_CO_SIGNED"

ERROR_EXPECTED, ERROR_LLM = "[EXPECTED]", "[LLM_ERROR]"
def _err(msg: str): raise gl.vm.UserError(f"{ERROR_EXPECTED} {msg}")
def _llm_err(msg: str): raise gl.vm.UserError(f"{ERROR_LLM} {msg}")

ZERO_ADDRESS, z256 = Address(b"\x00" * 20), u256(0)
RFP_AUDIT_PRINCIPLE = "Validators agree on: source_fetch_ok, provenance_valid, supports_rfp_criteria, quantized_compliance_bps, award_band, echoed_bid_id."

def _now_seconds() -> int:
    try:
        r = str(gl.message_raw["datetime"]).strip()
        if r.endswith("Z"): r = r[:-1] + "+00:00"
        return int(datetime.fromisoformat(r).timestamp())
    except Exception: return int(datetime.now(timezone.utc).timestamp())

def _as_address(v) -> Address:
    if isinstance(v, Address): return v
    if isinstance(v, bytes) and len(v) == 20: return Address(v)
    t = str(v).strip()
    if t.startswith("0x") and len(t) == 42:
        try: return Address(t)
        except Exception: pass
    _err("malformed hex address")

def _validate_spec_url(url: str) -> str:
    t = str(url).strip()
    if not (12 <= len(t) <= 300) or not t.startswith("https://") or any(c in t for c in " \t\n\r\\`"):
        if not t.startswith("https://"): _err("must use https")
        _err("invalid specification URL")
    hp = t[8:].split("/")[0].split("?")[0]
    if "@" in hp: _err("credentials not allowed")
    if ":" in hp: _err("port not allowed")
    h = hp.lower().strip(".")
    if h in ("localhost", "127.0.0.1", "::1", "169.254.169.254") or h.endswith((".local", ".internal", ".lan", ".home")) or h.startswith(("10.", "127.", "192.168.", "172.")):
        _err("private host not allowed")
    if "." not in hp: _err("invalid URL host")
    return t

def _sanitize_text(raw) -> str:
    t = str(raw).replace("\r\n", "\n").replace("\r", "\n")
    return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", " ", t)[:MAX_SPEC_CHARS]

def _coerce_bool(raw):
    if isinstance(raw, bool): return raw
    if isinstance(raw, int) and raw in (0, 1): return bool(raw)
    t = str(raw).strip().lower()
    if t in ("true", "yes", "1", "valid", "compliant", "approved", "pass"): return True
    if t in ("false", "no", "0", "invalid", "non_compliant", "rejected", "fail"): return False
    return None

def _coerce_number(raw):
    if isinstance(raw, bool): return None
    if isinstance(raw, (int, float)): return float(raw)
    m = re.search(r"-?\d+(?:\.\d+)?", str(raw).strip().replace(",", "."))
    return float(m.group(0)) if m else None

def _parse_audit_result(raw) -> dict:
    if isinstance(raw, dict):
        p, s = raw.get("provenance_valid"), raw.get("supports_rfp", raw.get("supports_rfp_criteria"))
        sc = raw.get("compliance_score_bps", raw.get("compliance_bps", raw.get("quantized_compliance_bps")))
        sm = str(raw.get("summary", ""))
    else:
        text = str(raw).strip()
        if text.startswith("{") and text.endswith("}"):
            try: return _parse_audit_result(json.loads(text))
            except Exception: pass
        cand = [p for l in text.splitlines() for p in [[x.strip() for x in l.split("|")]] if len(p) >= 4]
        if not cand: _llm_err("expected PROVENANCE|SUPPORTS_RFP|COMPLIANCE_BPS|SUMMARY attestation")
        p, s, sc, sm = cand[0][0], cand[0][1], cand[0][2], cand[0][3]
    pv, sr, score = _coerce_bool(p), _coerce_bool(s), _coerce_number(sc)
    if pv is None: _llm_err("missing or ambiguous provenance_valid")
    if sr is None: _llm_err("missing or ambiguous supports_rfp")
    if score is None: _llm_err("missing or non-numeric compliance score")
    return {"provenance_valid": bool(pv), "supports_rfp": bool(sr), "raw_score": int(score), "summary": sm}

@allow_storage
@dataclass
class Bid:
    bid_id: u256; tender_id: u256; vendor: Address; bid_amount_tpt: u256; proposal_spec_url: str; bid_bond_gen: u256; created_at: u256
    evaluated: bool = False; source_fetch_ok: bool = False; provenance_valid: bool = False; supports_rfp_criteria: bool = False
    quantized_compliance_bps: u256 = u256(0); award_band: str = ""; slash_amount: u256 = u256(0); status: str = BID_STATUS_SUBMITTED
    summary: str = ""; challenger: Address = ZERO_ADDRESS; challenge_bond_gen: u256 = u256(0); challenge_reason: str = ""
    counter_evidence_url: str = ""; challenged_at: u256 = u256(0); adjudicated: bool = False

@allow_storage
@dataclass
class Tender:
    tender_id: u256; title: str; rfp_spec: str; buyer: Address; max_budget_tpt: u256; min_qualification_bps: u256
    required_bid_bond_gen: u256; required_challenge_bond_gen: u256; bid_deadline: u256; challenge_deadline: u256; created_at: u256
    status: str = STATUS_OPEN; winning_bid_id: u256 = u256(0); winning_vendor: Address = ZERO_ADDRESS; winning_bid_amount_tpt: u256 = u256(0)
    buyer_refund_tpt: u256 = u256(0); bid_count: u256 = u256(0); settled_at: u256 = u256(0); award_band: str = ""
    buyer_approved: bool = False; vendor_approved: bool = False; buyer_bps: u256 = u256(0); vendor_bps: u256 = u256(0)

class TenderPulse(gl.Contract):
    token_name: str; token_symbol: str; token_decimals: u256; total_supply: u256; vault_custody_balance: u256; sum_token_balances: u256
    token_balances: TreeMap[Address, u256]; faucet_minted: TreeMap[Address, u256]
    native_custody_balance: u256; active_bid_bonds: u256; active_challenge_bonds: u256; total_refundable_balances: u256
    refundable_balances: TreeMap[Address, u256]; last_payable_rejection: TreeMap[Address, str]
    tender_count: u256; tenders: TreeMap[u256, Tender]; tender_order: DynArray[u256]
    bid_count: u256; bids: TreeMap[u256, Bid]; bid_order: DynArray[u256]

    def __init__(self) -> None:
        self.token_name, self.token_symbol, self.token_decimals = TOKEN_NAME, TOKEN_SYMBOL, u256(TOKEN_DECIMALS)
        self.total_supply, self.vault_custody_balance, self.sum_token_balances = u256(0), u256(0), u256(0)
        self.native_custody_balance, self.active_bid_bonds, self.active_challenge_bonds, self.total_refundable_balances = u256(0), u256(0), u256(0), u256(0)
        self.tender_count = u256(0)
        self.bid_count = u256(0)

    def _balance_of(self, a: Address) -> u256: return self.token_balances.get(a, u256(0))
    def _credit_tpt(self, a: Address, amt: int) -> None:
        if amt > 0: self.token_balances[a] = u256(int(self._balance_of(a)) + amt); self.sum_token_balances = u256(int(self.sum_token_balances) + amt)
    def _debit_tpt(self, a: Address, amt: int) -> None:
        if amt > 0:
            cur = int(self._balance_of(a))
            if cur < amt: _err("insufficient TPT balance")
            self.token_balances[a] = u256(cur - amt); self.sum_token_balances = u256(int(self.sum_token_balances) - amt)
    def _lock_into_vault(self, s: Address, amt: int) -> None: self._debit_tpt(s, amt); self.vault_custody_balance = u256(int(self.vault_custody_balance) + amt)
    def _pay_from_vault(self, r: Address, amt: int) -> None:
        if amt > 0:
            vb = int(self.vault_custody_balance)
            if vb < amt: _err("vault custody underflow")
            self.vault_custody_balance = u256(vb - amt); self._credit_tpt(r, amt)

    def _soft_fail(self, s: Address, val: int, reason: str) -> dict:
        if val > 0:
            self.refundable_balances[s] = u256(int(self.refundable_balances.get(s, u256(0))) + val)
            self.total_refundable_balances = u256(int(self.total_refundable_balances) + val)
            self.native_custody_balance = u256(int(self.native_custody_balance) + val)
        self.last_payable_rejection[s] = reason
        return {"ok": False, "soft_fail": True, "reason": reason, "refunded_wei": val}

    def _route_native_bond(self, r: Address, amt: int) -> None:
        if amt > 0:
            self.refundable_balances[r] = u256(int(self.refundable_balances.get(r, u256(0))) + amt)
            self.total_refundable_balances = u256(int(self.total_refundable_balances) + amt)

    def _dispatch_refund(self, s: Address, amt: int) -> dict:
        avail = int(self.refundable_balances.get(s, u256(0)))
        if avail <= 0: _err("no refundable balance available")
        amt = avail if amt <= 0 else amt
        if amt > avail: _err("requested amount exceeds refundable balance")
        if int(self.native_custody_balance) < amt: _err("insufficient native custody balance")
        try: IEoaRecipient(s).emit_transfer(value=u256(amt))
        except Exception as exc: raise gl.vm.UserError(f"{ERROR_EXPECTED} native transfer failed: {exc}")
        self.refundable_balances[s] = u256(avail - amt); self.total_refundable_balances = u256(int(self.total_refundable_balances) - amt)
        self.native_custody_balance = u256(int(self.native_custody_balance) - amt); self.last_payable_rejection[s] = ""
        return {"recipient": str(s), "amount_wei": amt, "remaining_refundable_wei": avail - amt}

    def _require_tender(self, tid: u256) -> Tender:
        k = u256(int(tid))
        if k not in self.tenders: _err("tender does not exist")
        return self.tenders[k]

    def _require_bid(self, tid: u256, bid_id: u256) -> Bid:
        bk = u256(int(bid_id))
        if bk not in self.bids: _err("bid does not exist")
        b = self.bids[bk]
        if b.tender_id != u256(int(tid)): _err("bid does not belong to tender")
        return b

    def _save_bid(self, tid: u256, b: Bid) -> None:
        self.bids[b.bid_id] = b

    def _sync_winning_bid_if_evaluated(self, t: Tender, b: Bid) -> None:
        if b.award_band != BAND_QUALIFIED: return
        if t.winning_bid_id == z256:
            t.winning_bid_id, t.winning_vendor, t.winning_bid_amount_tpt = b.bid_id, b.vendor, b.bid_amount_tpt
            return
        curr = self._require_bid(t.tender_id, t.winning_bid_id)
        if int(b.bid_amount_tpt) < int(curr.bid_amount_tpt):
            t.winning_bid_id, t.winning_vendor, t.winning_bid_amount_tpt = b.bid_id, b.vendor, b.bid_amount_tpt
        elif int(b.bid_amount_tpt) == int(curr.bid_amount_tpt):
            if int(b.quantized_compliance_bps) > int(curr.quantized_compliance_bps):
                t.winning_bid_id, t.winning_vendor, t.winning_bid_amount_tpt = b.bid_id, b.vendor, b.bid_amount_tpt

    def _tender_view(self, t: Tender) -> dict:
        return {
            "tender_id": int(t.tender_id), "title": t.title, "rfp_spec": t.rfp_spec, "buyer": str(t.buyer),
            "max_budget_tpt": int(t.max_budget_tpt), "min_qualification_bps": int(t.min_qualification_bps),
            "required_bid_bond_gen": int(t.required_bid_bond_gen), "required_challenge_bond_gen": int(t.required_challenge_bond_gen),
            "bid_deadline": int(t.bid_deadline), "challenge_deadline": int(t.challenge_deadline), "created_at": int(t.created_at),
            "status": t.status, "winning_bid_id": int(t.winning_bid_id), "winning_vendor": str(t.winning_vendor),
            "winning_bid_amount_tpt": int(t.winning_bid_amount_tpt), "buyer_refund_tpt": int(t.buyer_refund_tpt),
            "bid_count": int(t.bid_count), "settled_at": int(t.settled_at), "award_band": t.award_band,
            "buyer_approved": bool(t.buyer_approved), "vendor_approved": bool(t.vendor_approved),
            "buyer_bps": int(t.buyer_bps), "vendor_bps": int(t.vendor_bps)
        }

    def _bid_view(self, b: Bid) -> dict:
        return {
            "bid_id": int(b.bid_id), "tender_id": int(b.tender_id), "vendor": str(b.vendor),
            "bid_amount_tpt": int(b.bid_amount_tpt), "proposal_spec_url": b.proposal_spec_url,
            "bid_bond_gen": int(b.bid_bond_gen), "created_at": int(b.created_at), "evaluated": bool(b.evaluated),
            "source_fetch_ok": bool(b.source_fetch_ok), "provenance_valid": bool(b.provenance_valid),
            "supports_rfp_criteria": bool(b.supports_rfp_criteria), "quantized_compliance_bps": int(b.quantized_compliance_bps),
            "award_band": b.award_band, "slash_amount": int(b.slash_amount), "status": b.status, "summary": b.summary,
            "challenger": str(b.challenger), "challenge_bond_gen": int(b.challenge_bond_gen),
            "challenge_reason": b.challenge_reason, "counter_evidence_url": b.counter_evidence_url,
            "challenged_at": int(b.challenged_at), "adjudicated": bool(b.adjudicated)
        }

    def _run_rfp_compliance_audit_nondet(self, t: Tender, b: Bid, is_challenge: bool) -> dict:
        rfp_spec, min_qual_bps, spec_url, bid_id = t.rfp_spec, int(t.min_qualification_bps), b.proposal_spec_url, int(b.bid_id)

        def fetch_and_audit():
            fetch_ok, raw_text = False, ""
            try:
                rendered = _sanitize_text(gl.nondet.web.render(spec_url, mode="text"))
                if len(rendered.strip()) >= MIN_SUBSTANTIVE_CHARS: fetch_ok, raw_text = True, rendered
            except Exception: pass
            if not fetch_ok:
                return {"source_fetch_ok": False, "provenance_valid": False, "supports_rfp_criteria": False, "quantized_compliance_bps": 0, "award_band": BAND_FAIL_CLOSED, "echoed_bid_id": bid_id, "summary": "FAIL_CLOSED: live evidence unavailable"}
            audit_prompt = f"AI Public Procurement Auditor: UNTRUSTED PROPOSAL DATA.\nRFP Spec: {rfp_spec}\nVendor Doc URL: {spec_url}\nVendor Content:\n{raw_text[:MAX_SPEC_CHARS]}\nReturn format: PROVENANCE_VALID|SUPPORTS_RFP|COMPLIANCE_BPS|SUMMARY\nExample: true|true|9250|Valid architecture and conforming RFP endpoints."
            raw_llm = gl.nondet.exec_prompt(audit_prompt, response_format="text")
            parsed = _parse_audit_result(raw_llm)
            prov, supp, raw_score = bool(parsed["provenance_valid"]), bool(parsed["supports_rfp"]), int(parsed["raw_score"])
            if not prov or not supp:
                prov_ok, supp_ok, quantized_bps, band = prov, False, 0, BAND_DISQUALIFIED
            else:
                prov_ok, supp_ok = True, True
                clamped = max(0, min(10000, raw_score))
                quantized_bps = (clamped // GRID_STEP_BPS) * GRID_STEP_BPS
                band = BAND_QUALIFIED if quantized_bps >= min_qual_bps else BAND_REMEDIATION
            return {"source_fetch_ok": True, "provenance_valid": prov_ok, "supports_rfp_criteria": supp_ok, "quantized_compliance_bps": quantized_bps, "award_band": band, "echoed_bid_id": bid_id, "summary": str(parsed["summary"])[:240]}

        c = gl.eq_principle.prompt_comparative(fetch_and_audit, RFP_AUDIT_PRINCIPLE)
        if not isinstance(c, dict): _llm_err("consensus payload is not an object")
        if int(c.get("echoed_bid_id", -1)) != bid_id: _err("consensus echoed bid_id mismatch")
        return c

    @gl.public.view
    def get_token_metadata(self) -> dict:
        return {"name": self.token_name, "symbol": self.token_symbol, "decimals": int(self.token_decimals), "total_supply": int(self.total_supply), "vault_custody_balance": int(self.vault_custody_balance), "sum_token_balances": int(self.sum_token_balances)}
    @gl.public.view
    def get_token_balance(self, a: str) -> int: return int(self._balance_of(_as_address(a)))
    @gl.public.view
    def get_refundable_balance(self, a: str) -> int: return int(self.refundable_balances.get(_as_address(a), z256))
    @gl.public.view
    def get_last_payable_rejection(self, a: str) -> str: return str(self.last_payable_rejection.get(_as_address(a), ""))
    @gl.public.view
    def get_native_custody_summary(self) -> dict:
        nc, ab, ac, tr = int(self.native_custody_balance), int(self.active_bid_bonds), int(self.active_challenge_bonds), int(self.total_refundable_balances)
        return {"native_custody_balance": nc, "active_bid_bonds": ab, "active_challenge_bonds": ac, "total_refundable_balances": tr, "conservation_ok": (nc == ab + ac + tr)}
    @gl.public.view
    def get_governance_boundary(self) -> dict: return {"has_owner": False, "has_admin": False, "protocol": "TenderPulse", "version": "1.0.0"}
    @gl.public.view
    def get_chain_clock(self) -> int: return _now_seconds()
    @gl.public.view
    def get_tender_count(self) -> int: return int(self.tender_count)
    @gl.public.view
    def get_tender(self, tid: u256) -> dict: return self._tender_view(self._require_tender(tid))
    @gl.public.view
    def list_tenders(self) -> list: return [self._tender_view(self.tenders[i]) for i in self.tender_order]
    @gl.public.view
    def get_bid(self, tid: u256, bid_id: u256) -> dict: return self._bid_view(self._require_bid(tid, bid_id))
    @gl.public.view
    def list_bids_for_tender(self, tid: u256) -> list:
        k = u256(int(tid))
        return [self._bid_view(self.bids[i]) for i in self.bid_order if self.bids[i].tender_id == k]
    @gl.public.view
    def preview_tender_award(self, tid: u256) -> dict:
        t = self._require_tender(tid); r = self._tender_view(t)
        if t.winning_bid_id != z256:
            w = self._require_bid(tid, t.winning_bid_id); r["winning_bid"] = self._bid_view(w)
            r["vendor_payout_tpt"] = int(w.bid_amount_tpt); r["buyer_savings_tpt"] = int(t.max_budget_tpt) - int(w.bid_amount_tpt)
        else: r["winning_bid"], r["vendor_payout_tpt"], r["buyer_savings_tpt"] = None, 0, 0
        return r

    @gl.public.write
    def faucet_or_deposit(self, amount: u256) -> dict:
        s, amt = gl.message.sender_address, int(amount)
        if amt <= 0: _err("amount must be positive")
        cur_minted = int(self.faucet_minted.get(s, z256))
        if cur_minted + amt > MAX_FAUCET_PER_USER: _err("exceeds faucet allowance")
        self.faucet_minted[s] = u256(cur_minted + amt); self.total_supply = u256(int(self.total_supply) + amt); self._credit_tpt(s, amt)
        return {"recipient": str(s), "amount_tpt": amt, "balance_tpt": int(self._balance_of(s))}

    @gl.public.write
    def create_tender(self, title: str, rfp_spec: str, max_budget_tpt: u256, min_qualification_bps: u256, required_bid_bond_gen: u256, required_challenge_bond_gen: u256, bid_window_seconds: u256, challenge_window_seconds: u256) -> dict:
        s, t_clean, spec_clean, budget = gl.message.sender_address, str(title).strip(), str(rfp_spec).strip(), int(max_budget_tpt)
        if not (3 <= len(t_clean) <= 120): _err("invalid tender title length")
        if not (10 <= len(spec_clean) <= MAX_SPEC_CHARS): _err("invalid rfp specification length")
        if budget <= 0: _err("max budget must be positive")
        q_bps, b_bond, c_bond = int(min_qualification_bps), int(required_bid_bond_gen), int(required_challenge_bond_gen)
        if not (GRID_STEP_BPS <= q_bps <= BPS_DENOMINATOR) or (q_bps % GRID_STEP_BPS != 0): _err("min qualification score must be on 250-bps grid")
        if b_bond < 0 or c_bond < 0: _err("bonds cannot be negative")
        b_win, c_win = int(bid_window_seconds), int(challenge_window_seconds)
        if b_win < 60 or c_win < 60: _err("window seconds must be at least 60")
        self._lock_into_vault(s, budget)
        now = _now_seconds(); tid = u256(int(self.tender_count) + 1); self.tender_count = tid
        t = Tender(tender_id=tid, title=t_clean, rfp_spec=spec_clean, buyer=s, max_budget_tpt=max_budget_tpt, min_qualification_bps=min_qualification_bps, required_bid_bond_gen=required_bid_bond_gen, required_challenge_bond_gen=required_challenge_bond_gen, bid_deadline=u256(now + b_win), challenge_deadline=u256(now + b_win + c_win), created_at=u256(now))
        self.tenders[tid] = t; self.tender_order.append(tid)
        return self._tender_view(t)

    @gl.public.write.payable
    def submit_vendor_bid_payable(self, tender_id: u256, bid_amount_tpt: u256, proposal_spec_url: str) -> dict:
        s, val, k = gl.message.sender_address, int(gl.message.value), u256(int(tender_id))
        if k not in self.tenders: return self._soft_fail(s, val, "tender does not exist")
        t = self.tenders[k]
        if t.status != STATUS_OPEN: return self._soft_fail(s, val, "tender is not open for bidding")
        now = _now_seconds()
        if now > int(t.bid_deadline): return self._soft_fail(s, val, "bidding window has expired")
        b_amt = int(bid_amount_tpt)
        if b_amt <= 0 or b_amt > int(t.max_budget_tpt): return self._soft_fail(s, val, "bid amount must be positive and within budget")
        try: valid_url = _validate_spec_url(proposal_spec_url)
        except Exception as e: return self._soft_fail(s, val, f"invalid proposal URL: {e}")
        req_bond = int(t.required_bid_bond_gen)
        if val < req_bond: return self._soft_fail(s, val, "insufficient native bid bond value")
        surplus = val - req_bond
        self.active_bid_bonds = u256(int(self.active_bid_bonds) + req_bond)
        self.native_custody_balance = u256(int(self.native_custody_balance) + val)
        if surplus > 0:
            self.refundable_balances[s] = u256(int(self.refundable_balances.get(s, z256)) + surplus)
            self.total_refundable_balances = u256(int(self.total_refundable_balances) + surplus)
        bid_num = int(self.bid_count) + 1; self.bid_count = u256(bid_num)
        t.bid_count = u256(int(t.bid_count) + 1); self.tenders[k] = t
        b = Bid(bid_id=u256(bid_num), tender_id=k, vendor=s, bid_amount_tpt=bid_amount_tpt, proposal_spec_url=valid_url, bid_bond_gen=t.required_bid_bond_gen, created_at=u256(now))
        self.bids[u256(bid_num)] = b; self.bid_order.append(u256(bid_num))
        return {"ok": True, "bid_id": bid_num, "tender_id": int(k), "bid_amount_tpt": b_amt, "surplus_credited_wei": surplus}

    @gl.public.write.payable
    def challenge_vendor_bid_payable(self, tender_id: u256, bid_id: u256, challenge_reason: str, counter_evidence_url: str) -> dict:
        s, val, k = gl.message.sender_address, int(gl.message.value), u256(int(tender_id))
        if k not in self.tenders: return self._soft_fail(s, val, "tender does not exist")
        t = self.tenders[k]
        if t.status in (STATUS_AWARDED, STATUS_SETTLED_ZERO_WINNERS, STATUS_EXPIRED_REFUNDED, STATUS_MUTUAL_SETTLED): return self._soft_fail(s, val, "tender is already finalized")
        now = _now_seconds()
        if now > int(t.challenge_deadline): return self._soft_fail(s, val, "challenge window has closed")
        try: b = self._require_bid(k, bid_id)
        except Exception: return self._soft_fail(s, val, "bid does not exist")
        if b.challenger != ZERO_ADDRESS or b.adjudicated: return self._soft_fail(s, val, "bid already has an active or adjudicated challenge")
        req_bond = int(t.required_challenge_bond_gen)
        if val < req_bond: return self._soft_fail(s, val, "insufficient native challenge bond value")
        surplus = val - req_bond
        self.active_challenge_bonds = u256(int(self.active_challenge_bonds) + req_bond)
        self.native_custody_balance = u256(int(self.native_custody_balance) + val)
        if surplus > 0:
            self.refundable_balances[s] = u256(int(self.refundable_balances.get(s, z256)) + surplus)
            self.total_refundable_balances = u256(int(self.total_refundable_balances) + surplus)
        b.challenger, b.challenge_bond_gen, b.challenge_reason, b.counter_evidence_url, b.challenged_at, b.status = s, t.required_challenge_bond_gen, str(challenge_reason)[:300], str(counter_evidence_url)[:300], u256(now), BID_STATUS_CHALLENGED
        self._save_bid(k, b); t.status = STATUS_CHALLENGED; self.tenders[k] = t
        return {"ok": True, "tender_id": int(k), "bid_id": int(bid_id), "challenger": str(s), "surplus_credited_wei": surplus}

    @gl.public.write
    def evaluate_vendor_bid(self, tender_id: u256, bid_id: u256) -> dict:
        t, b = self._require_tender(tender_id), self._require_bid(tender_id, bid_id)
        if b.evaluated and b.award_band != BAND_FAIL_CLOSED: _err("bid is already evaluated")
        c = self._run_rfp_compliance_audit_nondet(t, b, is_challenge=False)
        b.source_fetch_ok, b.provenance_valid, b.supports_rfp_criteria = bool(c.get("source_fetch_ok")), bool(c.get("provenance_valid")), bool(c.get("supports_rfp_criteria"))
        b.quantized_compliance_bps, b.award_band, b.summary, b.evaluated = u256(int(c.get("quantized_compliance_bps", 0))), str(c.get("award_band", "")), str(c.get("summary", "")), True
        if b.award_band == BAND_QUALIFIED:
            b.status = BID_STATUS_EVALUATED; self._sync_winning_bid_if_evaluated(t, b)
        elif b.award_band == BAND_DISQUALIFIED: b.status = BID_STATUS_DISQUALIFIED
        elif b.award_band == BAND_FAIL_CLOSED: b.status = "EVIDENCE_UNAVAILABLE"
        else: b.status = BID_STATUS_EVALUATED
        self._save_bid(tender_id, b); self.tenders[tender_id] = t
        return self._bid_view(b)

    @gl.public.write
    def adjudicate_bid_challenge(self, tender_id: u256, bid_id: u256) -> dict:
        t, b = self._require_tender(tender_id), self._require_bid(tender_id, bid_id)
        if b.challenger == ZERO_ADDRESS: _err("bid has not been challenged")
        if b.adjudicated: _err("challenge is already adjudicated")
        c = self._run_rfp_compliance_audit_nondet(t, b, is_challenge=True)
        b.source_fetch_ok, b.provenance_valid, b.supports_rfp_criteria = bool(c.get("source_fetch_ok")), bool(c.get("provenance_valid")), bool(c.get("supports_rfp_criteria"))
        b.quantized_compliance_bps, b.award_band, b.summary = u256(int(c.get("quantized_compliance_bps", 0))), str(c.get("award_band", "")), str(c.get("summary", ""))
        b.evaluated, b.adjudicated = True, True
        c_bond, v_bond = int(b.challenge_bond_gen), int(b.bid_bond_gen)
        if b.award_band == BAND_DISQUALIFIED:
            b.status, b.slash_amount = BID_STATUS_DISQUALIFIED, b.bid_bond_gen
            self.active_challenge_bonds = u256(int(self.active_challenge_bonds) - c_bond)
            self.active_bid_bonds = u256(int(self.active_bid_bonds) - v_bond)
            self._route_native_bond(b.challenger, c_bond + v_bond)
            if t.winning_bid_id == b.bid_id:
                t.winning_bid_id, t.winning_vendor, t.winning_bid_amount_tpt = z256, ZERO_ADDRESS, z256
                for other_id in self.bid_order:
                    if other_id != b.bid_id:
                        other_b = self.bids[other_id]
                        if other_b.tender_id == tender_id and other_b.evaluated and other_b.award_band == BAND_QUALIFIED and not other_b.adjudicated:
                            self._sync_winning_bid_if_evaluated(t, other_b)
        elif b.award_band == BAND_QUALIFIED:
            b.slash_amount, b.status = z256, BID_STATUS_EVALUATED
            self.active_challenge_bonds = u256(int(self.active_challenge_bonds) - c_bond)
            self._route_native_bond(b.vendor, c_bond)
            self._sync_winning_bid_if_evaluated(t, b)
        else:
            self.active_challenge_bonds = u256(int(self.active_challenge_bonds) - c_bond)
            self._route_native_bond(b.challenger, c_bond)
        self._save_bid(tender_id, b); self.tenders[tender_id] = t
        return self._bid_view(b)

    @gl.public.write
    def finalize_tender_award(self, tender_id: u256) -> dict:
        t = self._require_tender(tender_id)
        if t.status in (STATUS_AWARDED, STATUS_SETTLED_ZERO_WINNERS, STATUS_EXPIRED_REFUNDED, STATUS_MUTUAL_SETTLED): _err("tender is already settled")
        if t.winning_bid_id == z256: _err("no qualified winning bid to award")
        w_bid = self._require_bid(tender_id, t.winning_bid_id)
        if not w_bid.evaluated or w_bid.award_band != BAND_QUALIFIED: _err("winning bid is not verified as qualified")
        win_amt, max_bud = int(w_bid.bid_amount_tpt), int(t.max_budget_tpt)
        savings = max_bud - win_amt
        self._pay_from_vault(w_bid.vendor, win_amt)
        if savings > 0:
            self._pay_from_vault(t.buyer, savings); t.buyer_refund_tpt = u256(savings)
        w_bond = int(w_bid.bid_bond_gen)
        if w_bond > 0 and int(self.active_bid_bonds) >= w_bond:
            self.active_bid_bonds = u256(int(self.active_bid_bonds) - w_bond)
            self._route_native_bond(w_bid.vendor, w_bond)
        w_bid.status = BID_STATUS_AWARDED; self._save_bid(tender_id, w_bid)
        t.status, t.award_band, t.settled_at = STATUS_AWARDED, BAND_QUALIFIED, u256(_now_seconds())
        self.tenders[tender_id] = t
        return {"tender_id": int(t.tender_id), "status": t.status, "winning_bid_id": int(t.winning_bid_id), "winning_vendor": str(t.winning_vendor), "winning_bid_amount_tpt": win_amt, "buyer_savings_tpt": savings, "winner_bond_refunded_wei": w_bond}

    @gl.public.write
    def refund_runner_up_bid_bond(self, tender_id: u256, bid_id: u256) -> dict:
        t, b = self._require_tender(tender_id), self._require_bid(tender_id, bid_id)
        if b.bid_id == t.winning_bid_id and t.status == STATUS_AWARDED: _err("winning bid bond is refunded via finalize_tender_award")
        if b.status in (BID_STATUS_RUNNER_UP_REFUNDED, BID_STATUS_DISQUALIFIED): _err("bid bond already refunded or slashed")
        bond = int(b.bid_bond_gen)
        if bond <= 0 or int(self.active_bid_bonds) < bond: _err("no active bid bond available")
        self.active_bid_bonds = u256(int(self.active_bid_bonds) - bond)
        self._route_native_bond(b.vendor, bond)
        b.status = BID_STATUS_RUNNER_UP_REFUNDED; self._save_bid(tender_id, b)
        return {"tender_id": int(tender_id), "bid_id": int(bid_id), "vendor": str(b.vendor), "refunded_wei": bond}

    @gl.public.write
    def claim_zero_winner_tender_refund(self, tender_id: u256) -> dict:
        t = self._require_tender(tender_id)
        if t.status in (STATUS_AWARDED, STATUS_SETTLED_ZERO_WINNERS, STATUS_EXPIRED_REFUNDED, STATUS_MUTUAL_SETTLED): _err("tender is already settled")
        now = _now_seconds()
        if now < int(t.challenge_deadline): _err("challenge deadline has not passed")
        if t.winning_bid_id != z256: _err("tender has a qualified winning bid")
        budget = int(t.max_budget_tpt); self._pay_from_vault(t.buyer, budget)
        t.buyer_refund_tpt, t.status, t.award_band, t.settled_at = t.max_budget_tpt, STATUS_SETTLED_ZERO_WINNERS, BAND_ZERO_WINNERS, u256(now)
        self.tenders[tender_id] = t
        return {"tender_id": int(tender_id), "status": t.status, "refunded_budget_tpt": budget}

    @gl.public.write
    def claim_expired_tender_refund(self, tender_id: u256) -> dict:
        s, t = gl.message.sender_address, self._require_tender(tender_id)
        if s != t.buyer: _err("only the buyer can claim expired tender refund")
        if t.status in (STATUS_AWARDED, STATUS_SETTLED_ZERO_WINNERS, STATUS_EXPIRED_REFUNDED, STATUS_MUTUAL_SETTLED): _err("tender is already settled")
        now = _now_seconds()
        if now < int(t.bid_deadline): _err("bidding deadline has not passed")
        if int(t.bid_count) > 0: _err("tender received bids; use standard award or zero-winner refund")
        budget = int(t.max_budget_tpt); self._pay_from_vault(t.buyer, budget)
        t.buyer_refund_tpt, t.status, t.settled_at = t.max_budget_tpt, STATUS_EXPIRED_REFUNDED, u256(now)
        self.tenders[tender_id] = t
        return {"tender_id": int(tender_id), "status": t.status, "refunded_budget_tpt": budget}

    @gl.public.write
    def propose_mutual_release(self, tender_id: u256, vendor_payout_bps: u256) -> dict:
        s, t = gl.message.sender_address, self._require_tender(tender_id)
        if t.status in (STATUS_AWARDED, STATUS_SETTLED_ZERO_WINNERS, STATUS_EXPIRED_REFUNDED, STATUS_MUTUAL_SETTLED): _err("tender is already settled")
        if t.winning_vendor == ZERO_ADDRESS: _err("no nominated or winning vendor for mutual settlement")
        if s != t.buyer and s != t.winning_vendor: _err("only the buyer or nominated vendor can co-sign mutual release")
        bps = int(vendor_payout_bps)
        if not (0 <= bps <= BPS_DENOMINATOR): _err("payout bps out of range")
        if s == t.buyer: t.buyer_approved, t.buyer_bps = True, u256(bps)
        else: t.vendor_approved, t.vendor_bps = True, u256(bps)
        res = {"tender_id": int(t.tender_id), "status": t.status, "settled": False, "buyer_approved": bool(t.buyer_approved), "vendor_approved": bool(t.vendor_approved), "buyer_bps": int(t.buyer_bps), "vendor_bps": int(t.vendor_bps)}
        if not (t.buyer_approved and t.vendor_approved):
            self.tenders[tender_id] = t; return res
        if t.buyer_bps != t.vendor_bps:
            self.tenders[tender_id] = t; res["reason"] = "co-signature bps mismatch"; return res
        budget = int(t.max_budget_tpt); v_payout = budget * bps // BPS_DENOMINATOR; b_refund = budget - v_payout
        self._pay_from_vault(t.winning_vendor, v_payout); self._pay_from_vault(t.buyer, b_refund)
        if t.winning_bid_id != z256:
            w_bid = self._require_bid(tender_id, t.winning_bid_id); w_bond = int(w_bid.bid_bond_gen)
            if w_bond > 0 and int(self.active_bid_bonds) >= w_bond:
                self.active_bid_bonds = u256(int(self.active_bid_bonds) - w_bond)
                self._route_native_bond(t.winning_vendor, w_bond)
        t.status, t.award_band, t.settled_at = STATUS_MUTUAL_SETTLED, BAND_MUTUAL, u256(_now_seconds())
        self.tenders[tender_id] = t
        res.update({"settled": True, "status": t.status, "vendor_payout_tpt": v_payout, "buyer_refund_tpt": b_refund})
        return res

    @gl.public.write
    def withdraw_refundable_native(self, amount: u256) -> dict: return self._dispatch_refund(gl.message.sender_address, int(amount))
    @gl.public.write
    def claim_refundable_balance(self) -> dict: return self._dispatch_refund(gl.message.sender_address, 0)
