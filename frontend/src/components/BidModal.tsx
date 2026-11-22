import React, { useState } from "react";
import { X, Gavel, ExternalLink, ShieldCheck } from "lucide-react";
import { Tender } from "../types";

interface BidModalProps {
  tender: Tender | null;
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (tenderId: number, bidAmountTpt: number, specUrl: string, bondWei: bigint) => void;
  isProcessing: boolean;
}

const PRESET_URLS = [
  {
    label: "Alpha Proposal Spec (Compliant Anycast)",
    url: "https://raw.githubusercontent.com/richeroveis/tender-pulse/main/evidence/proposals/rpc_cluster_spec_alpha.md",
  },
  {
    label: "Beta Proposal Spec (High-Throughput eBPF)",
    url: "https://raw.githubusercontent.com/richeroveis/tender-pulse/main/evidence/proposals/rpc_cluster_spec_beta.md",
  },
  {
    label: "Off-Topic Document (Bread Recipe - Expected Disqualification)",
    url: "https://raw.githubusercontent.com/richeroveis/tender-pulse/main/evidence/proposals/off_topic_spec.md",
  },
];

export const BidModal: React.FC<BidModalProps> = ({
  tender,
  isOpen,
  onClose,
  onSubmit,
  isProcessing,
}) => {
  const [quoteTpt, setQuoteTpt] = useState<number>(85000);
  const [specUrl, setSpecUrl] = useState<string>(PRESET_URLS[0].url);

  if (!isOpen || !tender) return null;

  const maxBudget = tender.max_budget_tpt / 1000000;
  const bondWei = BigInt(tender.required_bid_bond_gen);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit(tender.tender_id, quoteTpt * 1000000, specUrl, bondWei);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-fade-in">
      <div className="bg-[#0A2528] border border-[#1A575E] rounded-2xl max-w-lg w-full shadow-2xl p-6 space-y-4">
        <div className="flex items-center justify-between border-b border-[#1A575E] pb-3">
          <h3 className="text-lg font-serif font-bold text-[#F7F3E9] flex items-center gap-2">
            <Gavel className="w-5 h-5 text-[#E5B869]" />
            Submit Reverse-Auction Bid
          </h3>
          <button onClick={onClose} className="p-1 rounded text-[#C9BA96] hover:text-[#F7F3E9]">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="bg-[#082124] p-3 rounded-lg border border-[#123F44] text-xs">
          <div className="text-[#A99870]">Tender: #{tender.tender_id} - {tender.title}</div>
          <div className="text-[#FCD34D] font-mono mt-0.5">Budget Ceiling: {maxBudget.toLocaleString()} TPT</div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4 text-xs">
          <div>
            <label className="block text-[#A99870] font-semibold mb-1">Your Quote Amount (TPT)</label>
            <input
              type="number"
              min="100"
              max={maxBudget}
              required
              value={quoteTpt}
              onChange={(e) => setQuoteTpt(Number(e.target.value))}
              className="ledger-input w-full p-2.5 rounded-lg font-mono text-sm"
            />
            <span className="text-[11px] text-[#2DD4BF] mt-1 block">
              Savings for Buyer: +{(maxBudget - quoteTpt).toLocaleString()} TPT
            </span>
          </div>

          <div>
            <div className="flex items-center justify-between mb-1">
              <label className="block text-[#A99870] font-semibold">Live Proposal Specification URL</label>
              <span className="text-[10px] text-[#E5B869]">HTTPS Only</span>
            </div>
            <input
              type="url"
              required
              value={specUrl}
              onChange={(e) => setSpecUrl(e.target.value)}
              className="ledger-input w-full p-2.5 rounded-lg font-mono text-[11px]"
            />
          </div>

          {/* Quick Preset Selector */}
          <div>
            <span className="text-[10px] text-[#A99870] uppercase font-bold block mb-1">Sample Proposal Presets:</span>
            <div className="space-y-1.5">
              {PRESET_URLS.map((preset, idx) => (
                <button
                  key={idx}
                  type="button"
                  onClick={() => setSpecUrl(preset.url)}
                  className={`w-full text-left p-2 rounded text-[11px] border transition flex items-center justify-between ${
                    specUrl === preset.url
                      ? "bg-[#123F44] border-[#14B8A6] text-[#F7F3E9]"
                      : "bg-[#082124] border-[#1A575E] text-[#C9BA96] hover:bg-[#0D3135]"
                  }`}
                >
                  <span className="truncate">{preset.label}</span>
                  <ExternalLink className="w-3 h-3 flex-shrink-0 ml-2" />
                </button>
              ))}
            </div>
          </div>

          <div className="bg-[#082124] p-3 rounded-lg border border-[#123F44] text-[11px] text-[#C9BA96] flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-[#34D399] flex-shrink-0" />
            <span>
              Stakes Domain B Bid Bond: {(Number(bondWei) / 1e18).toFixed(6)} GEN. Protected by Rule 5 Zero-Slash Invariant upon passing criteria.
            </span>
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-lg text-[#C9BA96] hover:bg-[#123F44] transition"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isProcessing}
              className="bg-[#E5B869] hover:bg-[#D97706] text-[#06181A] font-bold px-5 py-2 rounded-lg transition disabled:opacity-50"
            >
              Stake Bond & Submit Bid
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
