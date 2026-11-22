import React, { useState } from "react";
import { X, ExternalLink, ShieldCheck, ShieldAlert, Award, RefreshCw, CheckCircle, AlertTriangle, Users } from "lucide-react";
import { Tender, Bid } from "../types";

interface TenderDetailModalProps {
  tender: Tender | null;
  bids: Bid[];
  onClose: () => void;
  onEvaluateBid: (tenderId: number, bidId: number) => void;
  onOpenChallengeModal: (tender: Tender, bid: Bid) => void;
  onAdjudicateChallenge: (tenderId: number, bidId: number) => void;
  onRefundRunnerUpBond: (tenderId: number, bidId: number) => void;
  onProposeMutualRelease: (tenderId: number, payoutBps: number) => void;
  onFinalizeAward: (tender: Tender) => void;
  userAddress: string;
  isProcessing: boolean;
}

export const TenderDetailModal: React.FC<TenderDetailModalProps> = ({
  tender,
  bids,
  onClose,
  onEvaluateBid,
  onOpenChallengeModal,
  onAdjudicateChallenge,
  onRefundRunnerUpBond,
  onProposeMutualRelease,
  onFinalizeAward,
  userAddress,
  isProcessing,
}) => {
  const [mutualBps, setMutualBps] = useState<number>(7500);

  if (!tender) return null;

  const formatTpt = (amt: number) => (amt / 1000000).toLocaleString(undefined, { maximumFractionDigits: 2 });
  const formatWei = (wei: number) => (wei / 1e18).toFixed(6);
  const isBuyer = userAddress.toLowerCase() === tender.buyer.toLowerCase();

  const getAwardBandBadge = (band: string) => {
    switch (band) {
      case "QUALIFIED_AWARD_ELIGIBLE":
        return <span className="text-xs bg-[#064E3B] text-[#34D399] border border-[#059669] px-2 py-0.5 rounded font-mono font-bold">QUALIFIED_AWARD_ELIGIBLE</span>;
      case "NON_COMPLIANT_DISQUALIFIED":
        return <span className="text-xs bg-[#7F1D1D] text-[#F87171] border border-[#DC2626] px-2 py-0.5 rounded font-mono font-bold">NON_COMPLIANT_DISQUALIFIED</span>;
      case "PARTIAL_REMEDIATION_HOLD":
        return <span className="text-xs bg-[#78350F] text-[#FCD34D] border border-[#D97706] px-2 py-0.5 rounded font-mono font-bold">PARTIAL_REMEDIATION_HOLD</span>;
      case "EVIDENCE_UNAVAILABLE_FAIL_CLOSED":
        return <span className="text-xs bg-[#451A03] text-[#F97316] border border-[#EA580C] px-2 py-0.5 rounded font-mono font-bold">EVIDENCE_UNAVAILABLE_FAIL_CLOSED</span>;
      default:
        return <span className="text-xs bg-[#1F2937] text-[#9CA3AF] px-2 py-0.5 rounded font-mono">AWAITING_CONSENSUS</span>;
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-fade-in">
      <div className="bg-[#0A2528] border border-[#1A575E] rounded-2xl max-w-4xl w-full max-h-[90vh] overflow-y-auto shadow-2xl p-6 space-y-6">
        {/* Header */}
        <div className="flex items-start justify-between border-b border-[#1A575E] pb-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-mono font-bold text-[#E5B869] bg-[#082124] px-2 py-0.5 rounded border border-[#123F44]">
                TENDER #{tender.tender_id}
              </span>
              <span className="text-xs text-[#2DD4BF] font-mono font-medium">Status: {tender.status}</span>
            </div>
            <h2 className="text-2xl font-serif font-bold text-[#F7F3E9] mt-1">{tender.title}</h2>
          </div>
          <button onClick={onClose} className="p-1.5 rounded-lg text-[#C9BA96] hover:text-[#F7F3E9] hover:bg-[#123F44] transition">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Tender Specification Box */}
        <div className="bg-[#082124] p-4 rounded-xl border border-[#123F44] space-y-2">
          <h4 className="text-xs uppercase font-bold text-[#A99870] tracking-wider">RFP Technical Specification & SLA</h4>
          <p className="text-xs text-[#E3D7BC] leading-relaxed">{tender.rfp_spec}</p>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-2 text-xs">
            <div>
              <div className="text-[10px] text-[#A99870]">Max Budget Ceiling</div>
              <div className="font-mono font-bold text-[#FCD34D]">{formatTpt(tender.max_budget_tpt)} TPT</div>
            </div>
            <div>
              <div className="text-[10px] text-[#A99870]">Qualification Floor</div>
              <div className="font-mono font-bold text-[#2DD4BF]">{tender.min_qualification_bps / 100}% ({tender.min_qualification_bps} bps)</div>
            </div>
            <div>
              <div className="text-[10px] text-[#A99870]">Required Bid Bond</div>
              <div className="font-mono font-bold text-[#F7F3E9]">{formatWei(tender.required_bid_bond_gen)} GEN</div>
            </div>
            <div>
              <div className="text-[10px] text-[#A99870]">Winning Vendor</div>
              <div className="font-mono text-xs text-[#34D399] truncate">
                {tender.winning_vendor !== "0x0000000000000000000000000000000000000000"
                  ? `${tender.winning_vendor.slice(0, 6)}...${tender.winning_vendor.slice(-4)}`
                  : "None"}
              </div>
            </div>
          </div>
        </div>

        {/* Reverse-Auction Bids Room */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="font-serif font-bold text-lg text-[#F7F3E9] flex items-center gap-2">
              <Award className="w-5 h-5 text-[#E5B869]" />
              Reverse-Auction Bids & AI Validator Consensus ({bids.length})
            </h3>
            {isBuyer && tender.winning_bid_id > 0 && tender.status !== "AWARDED" && (
              <button
                onClick={() => onFinalizeAward(tender)}
                disabled={isProcessing}
                className="bg-[#059669] hover:bg-[#047857] text-[#F7F3E9] font-bold px-4 py-1.5 rounded-lg text-xs transition shadow-md"
              >
                Finalize & Release TPT Escrow
              </button>
            )}
          </div>

          {bids.length === 0 ? (
            <div className="p-8 text-center text-xs text-[#C9BA96] bg-[#082124] rounded-xl border border-[#123F44]">
              No vendor bids submitted yet for this RFP tender.
            </div>
          ) : (
            <div className="space-y-3">
              {bids.map((bid) => {
                const isWinning = tender.winning_bid_id === bid.bid_id;
                const isDisqualified = bid.status === "DISQUALIFIED";

                return (
                  <div
                    key={bid.bid_id}
                    className={`p-4 rounded-xl border transition ${
                      isWinning
                        ? "bg-[#0A3035] border-[#14B8A6] shadow-lg"
                        : isDisqualified
                        ? "bg-[#181D22] border-[#7F1D1D]"
                        : "bg-[#0D3135] border-[#1A575E]"
                    }`}
                  >
                    <div className="flex flex-col md:flex-row md:items-start justify-between gap-3">
                      <div className="space-y-1.5 flex-1">
                        <div className="flex flex-wrap items-center gap-2">
                          <span className="text-xs font-mono font-bold text-[#E5B869] bg-[#082124] px-2 py-0.5 rounded border border-[#123F44]">
                            BID #{bid.bid_id}
                          </span>
                          {isWinning && (
                            <span className="text-xs bg-[#059669] text-[#F7F3E9] px-2 py-0.5 rounded-full font-bold flex items-center gap-1">
                              <Award className="w-3.5 h-3.5" /> REVERSE-AUCTION WINNER
                            </span>
                          )}
                          {getAwardBandBadge(bid.award_band)}
                          <span className="text-xs text-[#C9BA96] font-mono">
                            Vendor: {bid.vendor.slice(0, 6)}...{bid.vendor.slice(-4)}
                          </span>
                        </div>

                        <div className="flex flex-wrap items-center gap-4 text-xs pt-1">
                          <div>
                            <span className="text-[#A99870]">Quote: </span>
                            <span className="font-mono font-bold text-[#FCD34D] text-sm">{formatTpt(bid.bid_amount_tpt)} TPT</span>
                          </div>
                          <div>
                            <span className="text-[#A99870]">Bid Bond: </span>
                            <span className="font-mono font-semibold text-[#F7F3E9]">{formatWei(bid.bid_bond_gen)} GEN</span>
                          </div>
                          {bid.evaluated && (
                            <div>
                              <span className="text-[#A99870]">Score: </span>
                              <span className="font-mono font-bold text-[#2DD4BF]">{bid.quantized_compliance_bps / 100}% ({bid.quantized_compliance_bps} bps)</span>
                            </div>
                          )}
                        </div>

                        {/* Proposal URL Link */}
                        <div className="pt-1 flex items-center gap-2 text-xs">
                          <span className="text-[#A99870]">Technical Proposal URL:</span>
                          <a
                            href={bid.proposal_spec_url}
                            target="_blank"
                            rel="noreferrer"
                            className="text-[#5EEAD4] hover:underline flex items-center gap-1 font-mono truncate max-w-md"
                          >
                            {bid.proposal_spec_url}
                            <ExternalLink className="w-3 h-3 flex-shrink-0" />
                          </a>
                        </div>

                        {/* AI Auditor Summary */}
                        {bid.evaluated && bid.summary && (
                          <div className="mt-2 text-xs text-[#E3D7BC] bg-[#082124] p-2.5 rounded border border-[#123F44] italic">
                            <span className="font-semibold text-[#14B8A6] not-italic">AI Consensus Summary: </span>
                            "{bid.summary}"
                          </div>
                        )}
                      </div>

                      {/* Action buttons */}
                      <div className="flex flex-wrap md:flex-col items-end gap-2 min-w-[170px]">
                        {!bid.evaluated && (
                          <button
                            onClick={() => onEvaluateBid(tender.tender_id, bid.bid_id)}
                            disabled={isProcessing}
                            className="bg-[#14B8A6] hover:bg-[#0D9488] text-[#06181A] font-bold px-3 py-1.5 rounded text-xs transition shadow-sm w-full text-center"
                          >
                            Run AI Consensus Audit
                          </button>
                        )}

                        {tender.status !== "AWARDED" && !bid.challenger && (
                          <button
                            onClick={() => onOpenChallengeModal(tender, bid)}
                            disabled={isProcessing}
                            className="bg-[#78350F] hover:bg-[#92400E] text-[#FCD34D] font-semibold px-3 py-1.5 rounded text-xs transition w-full text-center"
                          >
                            Challenge Proposal
                          </button>
                        )}

                        {bid.challenger && !bid.adjudicated && (
                          <button
                            onClick={() => onAdjudicateChallenge(tender.tender_id, bid.bid_id)}
                            disabled={isProcessing}
                            className="bg-[#D97706] hover:bg-[#B45309] text-[#06181A] font-bold px-3 py-1.5 rounded text-xs transition w-full text-center"
                          >
                            Adjudicate Challenge
                          </button>
                        )}

                        {tender.status === "AWARDED" && !isWinning && bid.status !== "RUNNER_UP_REFUNDED" && !isDisqualified && (
                          <button
                            onClick={() => onRefundRunnerUpBond(tender.tender_id, bid.bid_id)}
                            disabled={isProcessing}
                            className="bg-[#123F44] hover:bg-[#1A575E] text-[#34D399] font-bold px-3 py-1.5 rounded text-xs border border-[#14B8A6] transition w-full text-center"
                          >
                            Refund Runner-Up Bond
                          </button>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* 2-Party Mutual Co-Sign Settlement Bay */}
        {tender.winning_vendor !== "0x0000000000000000000000000000000000000000" && tender.status !== "AWARDED" && tender.status !== "MUTUAL_SETTLED" && (
          <div className="bg-[#082124] p-4 rounded-xl border border-[#123F44] space-y-3">
            <h4 className="text-xs uppercase font-bold text-[#E5B869] tracking-wider flex items-center gap-1.5">
              <Users className="w-4 h-4" /> 2-Party Buyer & Vendor Mutual Co-Sign Settlement Bay
            </h4>
            <p className="text-xs text-[#C9BA96]">
              Both Buyer and Winning Vendor may co-sign a proportional release of TPT escrow without waiting for deadlines.
            </p>
            <div className="flex flex-wrap items-center gap-3">
              <label className="text-xs text-[#F7F3E9]">Vendor Payout BPS:</label>
              <input
                type="number"
                min="0"
                max="10000"
                step="250"
                value={mutualBps}
                onChange={(e) => setMutualBps(Number(e.target.value))}
                className="ledger-input px-3 py-1 rounded text-xs font-mono w-28"
              />
              <span className="text-xs text-[#2DD4BF]">({(mutualBps / 100).toFixed(2)}% to vendor)</span>
              <button
                onClick={() => onProposeMutualRelease(tender.tender_id, mutualBps)}
                disabled={isProcessing}
                className="bg-[#2563EB] hover:bg-[#1D4ED8] text-white font-bold px-3 py-1 rounded text-xs transition"
              >
                Co-Sign Mutual Release
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
