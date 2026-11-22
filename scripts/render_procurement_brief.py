#!/usr/bin/env python3
"""
scripts/render_procurement_brief.py
Synthesizes a 49.0s, 1280x720, subtitled TenderPulse Milestone v1 demo video
with warm civic ledger aesthetic, stereo procedural audio, and renders to
docs/demo-video-subtitled.mp4 and frontend/public/demo-video-subtitled.mp4.
"""

from __future__ import annotations
import math
import subprocess
import wave
import struct
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
WIDTH, HEIGHT = 1280, 720
FPS = 24
DURATION = 49.0
OUT_DOCS = ROOT / "docs" / "demo-video-subtitled.mp4"
OUT_PUBLIC = ROOT / "frontend" / "public" / "demo-video-subtitled.mp4"
TEMP_AUDIO = ROOT / "evidence" / "temp_procurement_audio.wav"

FONT_DIR = Path("/usr/share/fonts/truetype/dejavu")
FONT_BOLD = str(FONT_DIR / "DejaVuSans-Bold.ttf")
FONT_REGULAR = str(FONT_DIR / "DejaVuSans.ttf")
FONT_MONO = str(FONT_DIR / "DejaVuSansMono.ttf")
FONT_MONO_BOLD = str(FONT_DIR / "DejaVuSansMono-Bold.ttf")

# Civic Procurement Palette (Warm Ivory / Deep Teal / Amber Gold)
DEEP_TEAL = (8, 28, 30)
CARD_BG = (14, 42, 45)
CARD_BORDER = (24, 75, 80)
ACCENT_TEAL = (45, 212, 191)
ACCENT_MINT = (20, 184, 166)
WARM_IVORY = (244, 238, 221)
MUTED_IVORY = (185, 180, 165)
GOLD = (229, 184, 105)
CORAL_SLASH = (248, 113, 113)
EMERALD = (52, 211, 153)

T_LARGE = ImageFont.truetype(FONT_BOLD, 36)
T_MED = ImageFont.truetype(FONT_BOLD, 22)
T_SUB = ImageFont.truetype(FONT_BOLD, 17)
F_BODY = ImageFont.truetype(FONT_REGULAR, 15)
F_SMALL = ImageFont.truetype(FONT_REGULAR, 12)
F_MONO = ImageFont.truetype(FONT_MONO, 13)
F_MONO_BOLD = ImageFont.truetype(FONT_MONO_BOLD, 16)

SUBTITLES = [
    (0.0, 5.5, "TenderPulse: AI-Audited Public Procurement & Reverse-Auction RFP Award Hub."),
    (5.5, 11.5, "Strict Asset-Domain Separation: Domain A (TPT Escrow) vs Domain B (Native GEN Bonds)."),
    (11.5, 17.5, "Reverse-Auction Bidding: Competing Vendors Stake Native Bonds with Soft-Fail Protection."),
    (17.5, 24.0, "Unified AI Consensus: Validators Render Live URLs & Audit Provenance + Criteria."),
    (24.0, 30.5, "Off-Topic Rejection: Authoritative Non-Compliant Docs Disqualified; Fail-Closed on 404."),
    (30.5, 37.0, "Rule 5 Zero-Slash Invariant: Fully Qualified Bids Preserved with 0 Wei Bond Slashing."),
    (37.0, 43.0, "Lowest-Cost Qualified Winner Sync: TPT Escrow Payout & 100% Bond Conservation."),
    (43.0, 49.0, "Supported EOA Native Withdrawals via IEoaRecipient & Live Studionet Finality."),
]

def synthesize_soundtrack(out_path: Path, duration_s: float = 49.0, sample_rate: int = 44100):
    total_samples = int(duration_s * sample_rate)
    left_channel = np.zeros(total_samples, dtype=np.float32)
    right_channel = np.zeros(total_samples, dtype=np.float32)

    # Chord progression: Dm - F - C - G (Civic / procedural warm chords)
    chords = [
        [146.83, 220.00, 261.63, 349.23],  # Dm9
        [174.61, 220.00, 261.63, 349.23],  # Fmaj7
        [130.81, 196.00, 261.63, 329.63],  # Cmaj
        [196.00, 246.94, 293.66, 392.00],  # Gmaj
    ]
    chord_dur = 6.125  # 8 bars over 49 seconds

    t = np.arange(total_samples) / sample_rate

    # Bass drone & warm pad
    for i in range(8):
        chord = chords[i % len(chords)]
        start_idx = int(i * chord_dur * sample_rate)
        end_idx = min(total_samples, int((i + 1) * chord_dur * sample_rate))
        sub_t = t[start_idx:end_idx] - (i * chord_dur)
        sub_len = end_idx - start_idx
        env = np.sin(np.pi * (np.arange(sub_len) / sub_len)) ** 0.5

        for fi, freq in enumerate(chord):
            pan = 0.35 + 0.3 * (fi / len(chord))
            sine_wave = np.sin(2 * np.pi * freq * sub_t) * 0.12
            harm = np.sin(4 * np.pi * freq * sub_t) * 0.04
            sig = (sine_wave + harm) * env
            left_channel[start_idx:end_idx] += sig * (1.0 - pan)
            right_channel[start_idx:end_idx] += sig * pan

    # Gentle rhythmic pulse arpeggio
    arp_rate = 0.25  # sixteenth note at 120 bpm
    num_arps = int(duration_s / arp_rate)
    for a in range(num_arps):
        c_idx = int((a * arp_rate) / chord_dur) % len(chords)
        chord = chords[c_idx]
        note_freq = chord[a % len(chord)] * 2.0
        start_idx = int(a * arp_rate * sample_rate)
        note_len = int(0.22 * sample_rate)
        end_idx = min(total_samples, start_idx + note_len)
        if start_idx >= total_samples:
            break
        note_t = np.arange(end_idx - start_idx) / sample_rate
        env = np.exp(-12.0 * note_t) * 0.08
        sig = np.sin(2 * np.pi * note_freq * note_t) * env
        pan = 0.5 + 0.3 * math.sin(a * 0.4)
        left_channel[start_idx:end_idx] += sig * (1.0 - pan)
        right_channel[start_idx:end_idx] += sig * pan

    # Master envelope fade in/out
    master_env = np.ones(total_samples, dtype=np.float32)
    fade_len = int(1.5 * sample_rate)
    master_env[:fade_len] = np.linspace(0.0, 1.0, fade_len)
    master_env[-fade_len:] = np.linspace(1.0, 0.0, fade_len)

    left_channel = np.clip(left_channel * master_env, -0.95, 0.95)
    right_channel = np.clip(right_channel * master_env, -0.95, 0.95)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(out_path), "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        interleaved = np.empty((total_samples * 2,), dtype=np.int16)
        interleaved[0::2] = (left_channel * 32767).astype(np.int16)
        interleaved[1::2] = (right_channel * 32767).astype(np.int16)
        wf.writeframes(interleaved.tobytes())
    print(f"[audio] synthesized {duration_s}s soundtrack to {out_path}")

def render_frame(time_s: float) -> Image.Image:
    img = Image.new("RGBA", (WIDTH, HEIGHT), DEEP_TEAL)
    draw = ImageDraw.Draw(img)

    # Background subtle radial/horizontal gradient
    for y in range(0, HEIGHT, 4):
        f = y / HEIGHT
        shade = (
            int(DEEP_TEAL[0] + f * 6),
            int(DEEP_TEAL[1] + f * 14),
            int(DEEP_TEAL[2] + f * 16),
            255,
        )
        draw.rectangle([(0, y), (WIDTH, y + 4)], fill=shade)

    # Top Brand Header Bar
    draw.rectangle([(0, 0), (WIDTH, 56)], fill=(12, 36, 39, 255))
    draw.line([(0, 56), (WIDTH, 56)], fill=CARD_BORDER, width=2)
    draw.text((36, 14), "TENDERPULSE", font=T_MED, fill=WARM_IVORY)
    draw.text((215, 19), "AI-AUDITED PUBLIC PROCUREMENT LEDGER", font=F_SMALL, fill=ACCENT_TEAL)

    # Network badge
    draw.rounded_rectangle([(WIDTH - 250, 12), (WIDTH - 36, 44)], radius=6, fill=(18, 55, 59, 255), outline=ACCENT_MINT)
    draw.ellipse([(WIDTH - 238, 24), (WIDTH - 228, 34)], fill=EMERALD)
    draw.text((WIDTH - 220, 19), "GenLayer Studionet (61999)", font=F_SMALL, fill=WARM_IVORY)

    # Time progress indicator
    progress = time_s / DURATION
    draw.line([(0, 57), (int(WIDTH * progress), 57)], fill=GOLD, width=3)

    # Scene Routing
    if time_s < 5.5:
        # Scene 1: Overview & Dual-Domain Architecture
        draw.text((60, 95), "Decentralized Reverse-Auction Procurement Protocol", font=T_LARGE, fill=WARM_IVORY)
        draw.text((60, 145), "AI Validator Consensus with Evidence Provenance on GenLayer Studionet", font=T_SUB, fill=ACCENT_TEAL)

        # Domain A Card
        draw.rounded_rectangle([(60, 195), (610, 485)], radius=12, fill=CARD_BG, outline=CARD_BORDER, width=2)
        draw.rectangle([(60, 195), (610, 245)], fill=(18, 55, 59, 255))
        draw.text((85, 210), "DOMAIN A: TPT PROCUREMENT ESCROW", font=T_MED, fill=GOLD)
        draw.text((85, 265), "- ERC-20 Ledger: TenderPulse Token (TPT)", font=F_BODY, fill=WARM_IVORY)
        draw.text((85, 305), "- Buyer RFP Budget Vault Custody", font=F_BODY, fill=WARM_IVORY)
        draw.text((85, 345), "- Automated Winner Award & Budget Savings Rebates", font=F_BODY, fill=WARM_IVORY)
        draw.text((85, 385), "- Zero Cross-Domain Leakage Invariant (0 wei)", font=F_BODY, fill=EMERALD)
        draw.text((85, 430), "STATUS: VERIFIED ISOLATED ESCROW", font=F_MONO_BOLD, fill=ACCENT_MINT)

        # Domain B Card
        draw.rounded_rectangle([(670, 195), (1220, 485)], radius=12, fill=CARD_BG, outline=CARD_BORDER, width=2)
        draw.rectangle([(670, 195), (1220, 245)], fill=(18, 55, 59, 255))
        draw.text((695, 210), "DOMAIN B: NATIVE GEN BOND CUSTODY", font=T_MED, fill=ACCENT_TEAL)
        draw.text((695, 265), "- Native GEN Vendor Bid Bonds (Anti-Sybil)", font=F_BODY, fill=WARM_IVORY)
        draw.text((695, 305), "- Native GEN Bid-Integrity Challenge Bonds", font=F_BODY, fill=WARM_IVORY)
        draw.text((695, 345), "- 100% Non-Trapping Soft-Fail Rejection Handling", font=F_BODY, fill=WARM_IVORY)
        draw.text((695, 385), "- Direct EOA Payouts via IEoaRecipient.emit_transfer", font=F_BODY, fill=EMERALD)
        draw.text((695, 430), "CONSERVATION: 0 WEI STRANDED RESIDUE", font=F_MONO_BOLD, fill=ACCENT_MINT)

    elif time_s < 11.5:
        # Scene 2: Tender Publishing
        draw.text((60, 95), "Step 1: Public RFP Tender Publication", font=T_LARGE, fill=WARM_IVORY)
        draw.text((60, 145), "Buyers lock budget ceiling in TPT vault with strict qualification floors", font=T_SUB, fill=ACCENT_TEAL)

        draw.rounded_rectangle([(60, 195), (1220, 500)], radius=12, fill=CARD_BG, outline=CARD_BORDER, width=2)
        draw.text((90, 225), "TENDER SPECIFICATION: Decentralized RPC Node Cluster Procurement", font=T_MED, fill=GOLD)
        draw.line([(90, 260), (1190, 260)], fill=CARD_BORDER, width=1)

        draw.text((90, 280), "Max Budget Escrow:", font=F_BODY, fill=MUTED_IVORY)
        draw.text((320, 280), "120,000 TPT (Locked in Vault Custody)", font=F_MONO_BOLD, fill=WARM_IVORY)

        draw.text((90, 320), "Min Qualification Floor:", font=F_BODY, fill=MUTED_IVORY)
        draw.text((320, 320), "8,000 bps (80.00% Discrete 250-bps Grid)", font=F_MONO_BOLD, fill=ACCENT_MINT)

        draw.text((90, 360), "Required Bid Bond:", font=F_BODY, fill=MUTED_IVORY)
        draw.text((320, 360), "0.00002 GEN (Native Escrow Bond)", font=F_MONO_BOLD, fill=WARM_IVORY)

        draw.text((90, 400), "RFP Technical Criteria:", font=F_BODY, fill=MUTED_IVORY)
        draw.text((320, 400), "Geo-distributed JSON-RPC, 50k req/s, TLS 1.3 RFC 8446, 99.99% SLA", font=F_BODY, fill=ACCENT_TEAL)

        draw.text((90, 440), "Consensus Rule Enforcement:", font=F_BODY, fill=MUTED_IVORY)
        draw.text((320, 440), "gl.message_raw['datetime'] On-Chain Deadlines (Zero Clock Backdoors)", font=F_MONO_BOLD, fill=EMERALD)

    elif time_s < 17.5:
        # Scene 3: Competing Bids & Soft-Fail
        draw.text((60, 95), "Step 2: Competing Reverse-Auction Vendor Bids", font=T_LARGE, fill=WARM_IVORY)
        draw.text((60, 145), "Vendors submit quotes and live proposal URLs; lowest qualified cost wins", font=T_SUB, fill=ACCENT_TEAL)

        # Bid Alpha Card
        draw.rounded_rectangle([(60, 195), (610, 485)], radius=12, fill=CARD_BG, outline=CARD_BORDER, width=2)
        draw.text((85, 220), "VENDOR ALPHA (Initial Bid)", font=T_MED, fill=WARM_IVORY)
        draw.text((85, 265), "Quote Amount: 95,000 TPT", font=F_MONO_BOLD, fill=GOLD)
        draw.text((85, 305), "Native Bond: 0.00002 GEN [STAKED]", font=F_BODY, fill=EMERALD)
        draw.text((85, 345), "Spec URL: raw.githubusercontent.com/.../alpha.md", font=F_SMALL, fill=MUTED_IVORY)
        draw.text((85, 385), "Soft-Fail Protection: Verified Active", font=F_BODY, fill=ACCENT_TEAL)
        draw.text((85, 430), "STATUS: BID REGISTERED #1", font=F_MONO_BOLD, fill=WARM_IVORY)

        # Bid Beta Card
        draw.rounded_rectangle([(670, 195), (1220, 485)], radius=12, fill=CARD_BG, outline=CARD_BORDER, width=2)
        draw.text((695, 220), "VENDOR BETA (Competitive Quote)", font=T_MED, fill=ACCENT_TEAL)
        draw.text((695, 265), "Quote Amount: 78,000 TPT (-17,000 Savings)", font=F_MONO_BOLD, fill=EMERALD)
        draw.text((695, 305), "Native Bond: 0.00002 GEN [STAKED]", font=F_BODY, fill=EMERALD)
        draw.text((695, 345), "Spec URL: raw.githubusercontent.com/.../beta.md", font=F_SMALL, fill=MUTED_IVORY)
        draw.text((695, 385), "Overpayment Surplus: 100% Refundable", font=F_BODY, fill=ACCENT_TEAL)
        draw.text((695, 430), "STATUS: REVERSE-AUCTION LEADER", font=F_MONO_BOLD, fill=GOLD)

    elif time_s < 24.0:
        # Scene 4: AI Consensus Evidence Provenance
        draw.text((60, 95), "Step 3: Multi-Validator AI Consensus Audit", font=T_LARGE, fill=WARM_IVORY)
        draw.text((60, 145), "Validators render proposal HTTPS endpoints & audit technical compliance", font=T_SUB, fill=ACCENT_TEAL)

        draw.rounded_rectangle([(60, 195), (1220, 500)], radius=12, fill=CARD_BG, outline=CARD_BORDER, width=2)
        draw.text((90, 225), "EVIDENCE CONSENSUS HELPER: _run_rfp_compliance_audit_nondet", font=T_MED, fill=ACCENT_MINT)
        draw.line([(90, 260), (1190, 260)], fill=CARD_BORDER, width=1)

        draw.text((90, 280), "Live Web Fetch:", font=F_BODY, fill=MUTED_IVORY)
        draw.text((340, 280), "gl.nondet.web.render(spec_url, mode='text') (Sanitized)", font=F_MONO_BOLD, fill=WARM_IVORY)

        draw.text((90, 320), "Evidence Provenance:", font=F_BODY, fill=MUTED_IVORY)
        draw.text((340, 320), "provenance_valid = True (Authentic GitHub / RFC Documentation)", font=F_MONO_BOLD, fill=EMERALD)

        draw.text((90, 360), "RFP Criteria Fit:", font=F_BODY, fill=MUTED_IVORY)
        draw.text((340, 360), "supports_rfp_criteria = True (Addresses throughput, TLS, failover)", font=F_MONO_BOLD, fill=EMERALD)

        draw.text((90, 400), "Quantized Score:", font=F_BODY, fill=MUTED_IVORY)
        draw.text((340, 400), "9,250 bps (92.50% - Discrete 250-bps Grid Compliance)", font=F_MONO_BOLD, fill=GOLD)

        draw.text((90, 440), "Validator Agreement:", font=F_BODY, fill=MUTED_IVORY)
        draw.text((340, 440), "gl.eq_principle.prompt_comparative -> MAJORITY_AGREE", font=F_MONO_BOLD, fill=ACCENT_TEAL)

    elif time_s < 30.5:
        # Scene 5: Off-Topic Rejection & Fail-Closed Guard
        draw.text((60, 95), "Step 4: Off-Topic Rejection & Fail-Closed Guard", font=T_LARGE, fill=WARM_IVORY)
        draw.text((60, 145), "Authoritative hosts with off-topic content are strictly disqualified", font=T_SUB, fill=ACCENT_TEAL)

        # Off-Topic Disqualification
        draw.rounded_rectangle([(60, 195), (610, 485)], radius=12, fill=CARD_BG, outline=CARD_BORDER, width=2)
        draw.text((85, 220), "OFF-TOPIC AUTHORITATIVE REJECT", font=T_MED, fill=CORAL_SLASH)
        draw.text((85, 265), "URL: legitimate w3.org / culinary repo", font=F_SMALL, fill=MUTED_IVORY)
        draw.text((85, 305), "- Provenance Check: PASS", font=F_BODY, fill=WARM_IVORY)
        draw.text((85, 345), "- Criteria Relevance: FAIL (Off-topic)", font=F_BODY, fill=CORAL_SLASH)
        draw.text((85, 385), "- Compliance Score: FORCED 0 BPS", font=F_MONO_BOLD, fill=CORAL_SLASH)
        draw.text((85, 430), "BAND: NON_COMPLIANT_DISQUALIFIED", font=F_MONO_BOLD, fill=CORAL_SLASH)

        # Fail-Closed Guard
        draw.rounded_rectangle([(670, 195), (1220, 485)], radius=12, fill=CARD_BG, outline=CARD_BORDER, width=2)
        draw.text((695, 220), "FAIL-CLOSED SECURITY GUARD", font=T_MED, fill=GOLD)
        draw.text((695, 265), "Trigger: 404 Fetch / Content < 32 Chars", font=F_SMALL, fill=MUTED_IVORY)
        draw.text((695, 305), "- source_fetch_ok = False", font=F_BODY, fill=CORAL_SLASH)
        draw.text((695, 345), "- Settlement Release: STRICTLY BLOCKED", font=F_MONO_BOLD, fill=CORAL_SLASH)
        draw.text((695, 385), "- Zero Premature Escrow Extraction", font=F_BODY, fill=EMERALD)
        draw.text((695, 430), "BAND: EVIDENCE_UNAVAILABLE_FAIL_CLOSED", font=F_MONO_BOLD, fill=GOLD)

    elif time_s < 37.0:
        # Scene 6: Rule 5 Zero-Slash & Challenges
        draw.text((60, 95), "Step 5: Rule 5 Zero-Slash & Bid Integrity Challenges", font=T_LARGE, fill=WARM_IVORY)
        draw.text((60, 145), "Honest vendors are protected; malicious challenges forfeit bond", font=T_SUB, fill=ACCENT_TEAL)

        draw.rounded_rectangle([(60, 195), (1220, 500)], radius=12, fill=CARD_BG, outline=CARD_BORDER, width=2)
        draw.text((90, 225), "BID CHALLENGE ADJUDICATION (Rule 5 Zero-Slash Invariant)", font=T_MED, fill=GOLD)
        draw.line([(90, 260), (1190, 260)], fill=CARD_BORDER, width=1)

        draw.text((90, 280), "Honest Vendor (Meets Criteria):", font=F_BODY, fill=MUTED_IVORY)
        draw.text((400, 280), "slash_amount = 0 (100% Bond Preserved Intact)", font=F_MONO_BOLD, fill=EMERALD)

        draw.text((90, 320), "Frivolous Challenger Penalty:", font=F_BODY, fill=MUTED_IVORY)
        draw.text((400, 320), "Challenge bond forfeited and awarded to honest vendor", font=F_MONO_BOLD, fill=ACCENT_TEAL)

        draw.text((90, 360), "Non-Compliant Vendor Penalty:", font=F_BODY, fill=MUTED_IVORY)
        draw.text((400, 360), "Vendor bid bond slashed; challenger receives 2x reward", font=F_MONO_BOLD, fill=CORAL_SLASH)

        draw.text((90, 400), "Terminal Bond Accounting:", font=F_BODY, fill=MUTED_IVORY)
        draw.text((400, 400), "Active Bonds -> Total Refundable Balances (0 Wei Lost)", font=F_MONO_BOLD, fill=EMERALD)

        draw.text((90, 440), "Consensus Adjudication:", font=F_BODY, fill=MUTED_IVORY)
        draw.text((400, 440), "MAJORITY_AGREE on Evaluated Criteria & Compliance Band", font=F_MONO_BOLD, fill=WARM_IVORY)

    elif time_s < 43.0:
        # Scene 7: Award Settlement & Bond Refunds
        draw.text((60, 95), "Step 6: Tender Award & Zero-Residue Settlement", font=T_LARGE, fill=WARM_IVORY)
        draw.text((60, 145), "Lowest qualified quote awarded; runner-ups claim 100% bond refunds", font=T_SUB, fill=ACCENT_TEAL)

        draw.rounded_rectangle([(60, 195), (610, 485)], radius=12, fill=CARD_BG, outline=CARD_BORDER, width=2)
        draw.text((85, 220), "WINNER AWARD: VENDOR BETA", font=T_MED, fill=EMERALD)
        draw.text((85, 265), "Winning Payout: 78,000 TPT", font=F_MONO_BOLD, fill=WARM_IVORY)
        draw.text((85, 305), "Buyer Budget Savings: 42,000 TPT (Refunded)", font=F_MONO_BOLD, fill=GOLD)
        draw.text((85, 345), "Winner Bid Bond: 0.00002 GEN (100% Refunded)", font=F_BODY, fill=EMERALD)
        draw.text((85, 385), "Vault Custody Post-Settlement: 0 TPT", font=F_BODY, fill=ACCENT_TEAL)
        draw.text((85, 430), "STATUS: AWARD FINALIZED", font=F_MONO_BOLD, fill=EMERALD)

        draw.rounded_rectangle([(670, 195), (1220, 485)], radius=12, fill=CARD_BG, outline=CARD_BORDER, width=2)
        draw.text((695, 220), "RUNNER-UP: VENDOR ALPHA", font=T_MED, fill=ACCENT_TEAL)
        draw.text((695, 265), "Quote: 95,000 TPT (Qualified Runner-Up)", font=F_BODY, fill=WARM_IVORY)
        draw.text((695, 305), "Bid Bond Recovery: 0.00002 GEN Credited", font=F_MONO_BOLD, fill=EMERALD)
        draw.text((695, 345), "Refund Path: refund_runner_up_bid_bond", font=F_SMALL, fill=MUTED_IVORY)
        draw.text((695, 385), "Native Custody Balance Conservation: 100%", font=F_BODY, fill=EMERALD)
        draw.text((695, 430), "STATUS: RUNNER_UP_REFUNDED", font=F_MONO_BOLD, fill=ACCENT_MINT)

    else:
        # Scene 8: EOA Payouts & Finality
        draw.text((60, 95), "Step 7: Supported EOA Payouts & Live Finality", font=T_LARGE, fill=WARM_IVORY)
        draw.text((60, 145), "Real native GEN dispatched to EOAs via IEoaRecipient.emit_transfer", font=T_SUB, fill=ACCENT_TEAL)

        draw.rounded_rectangle([(60, 195), (1220, 500)], radius=12, fill=CARD_BG, outline=CARD_BORDER, width=2)
        draw.text((90, 225), "PRODUCTION ATTESTATION & EXPLORER FINALITY", font=T_MED, fill=GOLD)
        draw.line([(90, 260), (1190, 260)], fill=CARD_BORDER, width=1)

        draw.text((90, 280), "Contract Address:", font=F_BODY, fill=MUTED_IVORY)
        draw.text((320, 280), "0x75Ca06c1305d439BE35Bd31CFBD159ba8B25B443", font=F_MONO_BOLD, fill=ACCENT_TEAL)

        draw.text((90, 320), "Live Network:", font=F_BODY, fill=MUTED_IVORY)
        draw.text((320, 320), "GenLayer Studionet (Chain ID 61999)", font=F_MONO_BOLD, fill=WARM_IVORY)

        draw.text((90, 360), "EOA Native Withdrawal:", font=F_BODY, fill=MUTED_IVORY)
        draw.text((320, 360), "IEoaRecipient(recipient).emit_transfer(value=amount) [VERIFIED]", font=F_MONO_BOLD, fill=EMERALD)

        draw.text((90, 400), "Zero-Residue Invariant:", font=F_BODY, fill=MUTED_IVORY)
        draw.text((320, 400), "native_custody == active_bonds + total_refundable (0 wei residue)", font=F_MONO_BOLD, fill=EMERALD)

        draw.text((90, 440), "Frontend dApp:", font=F_BODY, fill=MUTED_IVORY)
        draw.text((320, 440), "https://richeroveis.github.io/tender-pulse/", font=F_MONO_BOLD, fill=GOLD)

    # Subtitle Bar (Bottom)
    draw.rectangle([(0, HEIGHT - 76), (WIDTH, HEIGHT)], fill=(6, 18, 20, 245))
    draw.line([(0, HEIGHT - 76), (WIDTH, HEIGHT - 76)], fill=CARD_BORDER, width=1)

    # Find matching subtitle
    active_sub = ""
    for s_start, s_end, text in SUBTITLES:
        if s_start <= time_s < s_end:
            active_sub = text
            break
    if not active_sub and SUBTITLES:
        active_sub = SUBTITLES[-1][2]

    sub_bbox = draw.textbbox((0, 0), active_sub, font=F_BODY)
    sub_w = sub_bbox[2] - sub_bbox[0]
    draw.text((WIDTH // 2 - sub_w // 2, HEIGHT - 52), active_sub, font=F_BODY, fill=WARM_IVORY)

    return img.convert("RGB")

def render_video():
    synthesize_soundtrack(TEMP_AUDIO, DURATION)

    cmd = [
        "ffmpeg", "-y",
        "-f", "rawvideo",
        "-vcodec", "rawvideo",
        "-s", f"{WIDTH}x{HEIGHT}",
        "-pix_fmt", "rgb24",
        "-r", str(FPS),
        "-i", "-",
        "-i", str(TEMP_AUDIO),
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "23",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        str(OUT_DOCS),
    ]

    print(f"[video] launching ffmpeg to render {DURATION}s ({int(DURATION * FPS)} frames)...")
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)

    total_frames = int(DURATION * FPS)
    for frame_idx in range(total_frames):
        t_sec = frame_idx / FPS
        frame_img = render_frame(t_sec)
        proc.stdin.write(frame_img.tobytes())
        if frame_idx % 120 == 0:
            print(f"[video] rendered frame {frame_idx}/{total_frames} ({t_sec:.1f}s)", flush=True)

    proc.stdin.close()
    proc.wait()
    if proc.returncode != 0:
        raise RuntimeError("ffmpeg failed to encode video")

    # Copy to frontend/public
    OUT_PUBLIC.parent.mkdir(parents=True, exist_ok=True)
    import shutil
    shutil.copyfile(OUT_DOCS, OUT_PUBLIC)
    print(f"[video] successfully generated {OUT_DOCS} and {OUT_PUBLIC}")

if __name__ == "__main__":
    render_video()
