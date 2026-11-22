import React, { useState } from "react";
import { X, ShieldAlert, AlertTriangle, ExternalLink } from "lucide-react";
import { Tender, Bid } from "../types";

interface ChallengeModalProps {
  tender: Tender | null;
  bid: Bid | null;
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (tenderId: number, bidId: number, evidenceUrl: string, reason: string, bondWei: bigint) => void;
  isProcessing: boolean;
}

const PRESET_COUNTER_EVIDENCE = [
  {
    label: "Counter-Evidence: Off-Topic / Non-Conforming Spec",
    url: "https://raw.githubusercontent.com/richeroveis/tender-pulse/main/evidence/proposals/off_topic_spec.md",
  },
  {
    label: "Counter-Evidence: Missing Failover Architecture",
    url: "https://raw.githubusercontent.com/richeroveis/tender-pulse/main/evidence/proposals/unavailable_404_spec.md",
  },
];

export const ChallengeModal: React.FC<ChallengeModalProps> = ({
  tender,
  bid,
  isOpen,
  onClose,
  onSubmit,
  isProcessing,
}) => {
  const [evidenceUrl, setEvidenceUrl] = useState<string>(PRESET_COUNTER_EVIDENCE[0].url);
  const [reason, setReason] = useState<string>("Proposal fails to meet geo-distributed 50k req/sec multi-region SLA specification.");

  if (!isOpen || !tender || !bid) return null;

  const bondWei = BigInt(tender.required_challenge_bond_gen);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit(tender.tender_id, bid.bid_id, evidenceUrl, reason, bondWei);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-fade-in">
      <div className="bg-[#0A2528] border border-[#B91C1C]/60 rounded-2xl max-w-lg w-full shadow-2xl p-6 space-y-4">
        <div className="flex items-center justify-between border-b border-[#1A575E] pb-3">
          <h3 className="text-lg font-serif font-bold text-[#F7F3E9] flex items-center gap-2">
            <ShieldAlert className="w-5 h-5 text-[#EF4444]" />
            File Bid-Integrity Challenge
          </h3>
          <button onClick={onClose} className="p-1 rounded text-[#C9BA96] hover:text-[#F7F3E9]">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="bg-[#1C1414] p-3 rounded-lg border border-[#7F1D1D] text-xs space-y-1">
          <div className="text-[#FCA5A5] font-semibold flex items-center gap-1.5">
            <AlertTriangle className="w-4 h-4 text-[#EF4444]" />
            Challenging Bid #{bid.bid_id} by Vendor {bid.vendor.slice(0, 10)}...
          </div>
          <div className="text-[#E5B869] font-mono">
            Quoted: {(bid.bid_amount_tpt / 1000000).toLocaleString()} TPT | Required Challenge Bond: {bondWei.toString()} wei (Domain B)
          </div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4 text-xs">
          <div>
            <label className="block text-[#A99870] font-semibold mb-1">Challenge Grounds / Reason</label>
            <textarea
              required
              rows={2}
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              className="ledger-input w-full p-2.5 rounded-lg text-xs"
              placeholder="Explain why the submitted proposal fails the RFP technical criteria..."
            />
          </div>

          <div>
            <div className="flex items-center justify-between mb-1">
              <label className="block text-[#A99870] font-semibold">Counter-Evidence HTTPS URL</label>
              <span className="text-[10px] text-[#E5B869]">HTTPS Only</span>
            </div>
            <input
              type="url"
              required
              value={evidenceUrl}
              onChange={(e) => setEvidenceUrl(e.target.value)}
              className="ledger-input w-full p-2.5 rounded-lg font-mono text-[11px]"
            />
          </div>

          <div>
            <span className="text-[10px] text-[#A99870] uppercase font-bold block mb-1">Preset Counter-Evidence:</span>
            <div className="space-y-1.5">
              {PRESET_COUNTER_EVIDENCE.map((preset, idx) => (
                <button
                  key={idx}
                  type="button"
                  onClick={() => setEvidenceUrl(preset.url)}
                  className="w-full text-left p-2 rounded bg-[#082124] hover:bg-[#0E353A] border border-[#123F44] transition-colors flex items-center justify-between text-[11px]"
                >
                  <span className="text-[#F7F3E9] truncate mr-2">{preset.label}</span>
                  <ExternalLink className="w-3.5 h-3.5 text-[#2DD4BF] shrink-0" />
                </button>
              ))}
            </div>
          </div>

          <div className="bg-[#082124] p-3 rounded-lg border border-[#123F44] text-[11px] text-[#C9BA96] space-y-1">
            <div className="text-[#E5B869] font-bold">Consensus Adjudication Invariant:</div>
            <div>
              If the challenge is upheld by validator AI consensus, the vendor bid bond is slashed 50% to the challenger and 50% to the tender award pool. If rejected, your challenge bond is forfeited to the vendor.
            </div>
          </div>

          <div className="flex items-center justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-lg border border-[#1A575E] text-[#C9BA96] hover:bg-[#0E353A] transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isProcessing}
              className="px-4 py-2 rounded-lg bg-[#B91C1C] hover:bg-[#DC2626] text-white font-semibold transition-colors disabled:opacity-50 flex items-center gap-2"
            >
              {isProcessing ? "Filing On-Chain..." : `Post Challenge (${bondWei.toString()} wei)`}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
