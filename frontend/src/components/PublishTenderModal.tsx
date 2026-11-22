import React, { useState } from "react";
import { X, PlusCircle, AlertCircle } from "lucide-react";

interface PublishTenderModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (data: {
    title: string;
    rfpSpec: string;
    maxBudgetTpt: number;
    minQualificationBps: number;
    requiredBidBondGen: number;
    requiredChallengeBondGen: number;
    bidWindowSeconds: number;
    challengeWindowSeconds: number;
  }) => void;
  isProcessing: boolean;
}

export const PublishTenderModal: React.FC<PublishTenderModalProps> = ({
  isOpen,
  onClose,
  onSubmit,
  isProcessing,
}) => {
  const [title, setTitle] = useState("Decentralized High-Speed RPC Node Cluster Procurement");
  const [rfpSpec, setRfpSpec] = useState(
    "Procurement of geo-distributed, fail-safe JSON-RPC validator gateways serving 50k req/sec with TLS 1.3, SLA >= 99.99%, and automated health failover telemetry endpoints."
  );
  const [budgetTpt, setBudgetTpt] = useState<number>(100000);
  const [minBps, setMinBps] = useState<number>(8000);
  const [bidBondEth, setBidBondEth] = useState<number>(0.00002);
  const [challengeBondEth, setChallengeBondEth] = useState<number>(0.00001);

  if (!isOpen) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit({
      title,
      rfpSpec,
      maxBudgetTpt: budgetTpt * 1000000,
      minQualificationBps: minBps,
      requiredBidBondGen: Math.round(bidBondEth * 1e18),
      requiredChallengeBondGen: Math.round(challengeBondEth * 1e18),
      bidWindowSeconds: 7200,
      challengeWindowSeconds: 7200,
    });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-fade-in">
      <div className="bg-[#0A2528] border border-[#1A575E] rounded-2xl max-w-lg w-full shadow-2xl p-6 space-y-4">
        <div className="flex items-center justify-between border-b border-[#1A575E] pb-3">
          <h3 className="text-lg font-serif font-bold text-[#F7F3E9] flex items-center gap-2">
            <PlusCircle className="w-5 h-5 text-[#14B8A6]" />
            Publish RFP Procurement Tender
          </h3>
          <button onClick={onClose} className="p-1 rounded text-[#C9BA96] hover:text-[#F7F3E9]">
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4 text-xs">
          <div>
            <label className="block text-[#A99870] font-semibold mb-1">Tender Title</label>
            <input
              type="text"
              required
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="ledger-input w-full p-2.5 rounded-lg font-medium"
            />
          </div>

          <div>
            <label className="block text-[#A99870] font-semibold mb-1">Technical Specification (RFP Criteria)</label>
            <textarea
              required
              rows={3}
              value={rfpSpec}
              onChange={(e) => setRfpSpec(e.target.value)}
              className="ledger-input w-full p-2.5 rounded-lg font-mono text-[11px]"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-[#A99870] font-semibold mb-1">Max Budget (TPT)</label>
              <input
                type="number"
                min="1000"
                step="1000"
                required
                value={budgetTpt}
                onChange={(e) => setBudgetTpt(Number(e.target.value))}
                className="ledger-input w-full p-2 rounded-lg font-mono"
              />
            </div>
            <div>
              <label className="block text-[#A99870] font-semibold mb-1">Min Qualification Floor</label>
              <select
                value={minBps}
                onChange={(e) => setMinBps(Number(e.target.value))}
                className="ledger-input w-full p-2 rounded-lg font-mono cursor-pointer"
              >
                <option value={7000}>70.00% (7,000 bps)</option>
                <option value={7500}>75.00% (7,500 bps)</option>
                <option value={8000}>80.00% (8,000 bps)</option>
                <option value={8500}>85.00% (8,500 bps)</option>
                <option value={9000}>90.00% (9,000 bps)</option>
              </select>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-[#A99870] font-semibold mb-1">Required Bid Bond (GEN)</label>
              <input
                type="number"
                step="0.00001"
                min="0"
                required
                value={bidBondEth}
                onChange={(e) => setBidBondEth(Number(e.target.value))}
                className="ledger-input w-full p-2 rounded-lg font-mono"
              />
            </div>
            <div>
              <label className="block text-[#A99870] font-semibold mb-1">Challenge Bond (GEN)</label>
              <input
                type="number"
                step="0.00001"
                min="0"
                required
                value={challengeBondEth}
                onChange={(e) => setChallengeBondEth(Number(e.target.value))}
                className="ledger-input w-full p-2 rounded-lg font-mono"
              />
            </div>
          </div>

          <div className="bg-[#082124] p-3 rounded-lg border border-[#123F44] text-[11px] text-[#C9BA96] flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-[#E5B869] flex-shrink-0" />
            <span>Publishing locks {budgetTpt.toLocaleString()} TPT into Domain A vault escrow until awarded or refunded.</span>
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
              className="bg-[#14B8A6] hover:bg-[#0D9488] text-[#06181A] font-bold px-5 py-2 rounded-lg transition disabled:opacity-50"
            >
              Confirm & Lock Escrow
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
