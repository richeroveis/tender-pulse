import React from "react";
import { PlusCircle, Clock, Award, ShieldAlert, CheckCircle2, ArrowRight, Gavel, FileText } from "lucide-react";
import { Tender } from "../types";

interface TenderListProps {
  tenders: Tender[];
  onSelectTender: (tender: Tender) => void;
  onOpenPublishModal: () => void;
  onOpenBidModal: (tender: Tender) => void;
  onFinalizeAward: (tender: Tender) => void;
  userAddress: string;
  isProcessing: boolean;
}

export const TenderList: React.FC<TenderListProps> = ({
  tenders,
  onSelectTender,
  onOpenPublishModal,
  onOpenBidModal,
  onFinalizeAward,
  userAddress,
  isProcessing,
}) => {
  const formatTpt = (amt: number) => (amt / 1000000).toLocaleString(undefined, { maximumFractionDigits: 2 });
  const formatWei = (wei: number) => (wei / 1e18).toFixed(6);

  const getStatusBadge = (status: string, band: string) => {
    switch (status) {
      case "AWARDED":
        return <span className="bg-[#064E3B] text-[#34D399] border border-[#059669] px-2.5 py-0.5 rounded-full text-xs font-semibold flex items-center gap-1"><Award className="w-3.5 h-3.5" /> Award Finalized</span>;
      case "CHALLENGED":
        return <span className="bg-[#78350F] text-[#FCD34D] border border-[#D97706] px-2.5 py-0.5 rounded-full text-xs font-semibold flex items-center gap-1"><ShieldAlert className="w-3.5 h-3.5" /> Challenged</span>;
      case "SETTLED_ZERO_WINNERS":
        return <span className="bg-[#374151] text-[#9CA3AF] border border-[#4B5563] px-2.5 py-0.5 rounded-full text-xs font-semibold">Zero-Winner Refund</span>;
      case "MUTUAL_SETTLED":
        return <span className="bg-[#1E3A8A] text-[#93C5FD] border border-[#3B82F6] px-2.5 py-0.5 rounded-full text-xs font-semibold">Mutual Co-Signed</span>;
      case "OPEN":
      default:
        return <span className="bg-[#134E4A] text-[#2DD4BF] border border-[#14B8A6] px-2.5 py-0.5 rounded-full text-xs font-semibold flex items-center gap-1"><Clock className="w-3.5 h-3.5" /> Open for Bidding</span>;
    }
  };

  return (
    <div className="space-y-4">
      {/* List Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-[#1A575E] pb-3">
        <div>
          <h2 className="text-xl font-bold font-serif text-[#F7F3E9] flex items-center gap-2">
            <Gavel className="w-5 h-5 text-[#E5B869]" />
            Civic RFP Tenders & Reverse-Auction Room
          </h2>
          <p className="text-xs text-[#C9BA96]">AI-Audited Public Procurement Ledger with Evidence Consensus</p>
        </div>
        <button
          onClick={onOpenPublishModal}
          disabled={isProcessing}
          className="flex items-center gap-2 bg-[#14B8A6] hover:bg-[#0D9488] text-[#06181A] font-bold px-4 py-2 rounded-lg text-xs shadow-md transition disabled:opacity-50"
        >
          <PlusCircle className="w-4 h-4" /> Publish RFP Tender
        </button>
      </div>

      {/* Tenders Grid */}
      {tenders.length === 0 ? (
        <div className="ledger-card rounded-xl p-12 text-center">
          <FileText className="w-12 h-12 text-[#1A575E] mx-auto mb-3" />
          <h3 className="text-base font-serif font-semibold text-[#F7F3E9]">No RFP Tenders Found</h3>
          <p className="text-xs text-[#C9BA96] mt-1 max-w-md mx-auto">
            Publish an AI-audited public procurement RFP tender funded in TPT escrow to launch reverse-auction bidding.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4">
          {tenders.map((tender) => {
            const isBuyer = userAddress.toLowerCase() === tender.buyer.toLowerCase();
            const hasWinner = tender.winning_bid_id > 0;

            return (
              <div
                key={tender.tender_id}
                className="ledger-card rounded-xl p-5 hover:border-[#14B8A6] transition duration-200 border border-[#1A575E]"
              >
                <div className="flex flex-col md:flex-row md:items-start justify-between gap-4">
                  {/* Tender Core Info */}
                  <div className="space-y-2 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="text-xs font-mono font-bold text-[#E5B869] bg-[#082124] px-2 py-0.5 rounded border border-[#123F44]">
                        TENDER #{tender.tender_id}
                      </span>
                      {getStatusBadge(tender.status, tender.award_band)}
                      <span className="text-xs text-[#C9BA96]">
                        Buyer: {tender.buyer.slice(0, 6)}...{tender.buyer.slice(-4)}
                      </span>
                    </div>

                    <h3 className="text-lg font-serif font-bold text-[#F7F3E9] leading-snug">
                      {tender.title}
                    </h3>
                    <p className="text-xs text-[#E3D7BC] line-clamp-2 leading-relaxed">
                      {tender.rfp_spec}
                    </p>

                    {/* Metadata Badges */}
                    <div className="flex flex-wrap items-center gap-3 pt-2 text-xs">
                      <div className="bg-[#082124] px-2.5 py-1 rounded border border-[#123F44]">
                        <span className="text-[#A99870]">Max Budget: </span>
                        <span className="font-mono font-bold text-[#FCD34D]">{formatTpt(tender.max_budget_tpt)} TPT</span>
                      </div>
                      <div className="bg-[#082124] px-2.5 py-1 rounded border border-[#123F44]">
                        <span className="text-[#A99870]">Min Score: </span>
                        <span className="font-mono font-bold text-[#2DD4BF]">{tender.min_qualification_bps / 100}%</span>
                      </div>
                      <div className="bg-[#082124] px-2.5 py-1 rounded border border-[#123F44]">
                        <span className="text-[#A99870]">Bid Bond: </span>
                        <span className="font-mono font-semibold text-[#F7F3E9]">{formatWei(tender.required_bid_bond_gen)} GEN</span>
                      </div>
                      <div className="bg-[#082124] px-2.5 py-1 rounded border border-[#123F44]">
                        <span className="text-[#A99870]">Bids: </span>
                        <span className="font-mono font-bold text-[#F7F3E9]">{tender.bid_count}</span>
                      </div>
                    </div>
                  </div>

                  {/* Actions & Winning Bid Summary */}
                  <div className="flex flex-col items-end justify-between gap-3 min-w-[240px]">
                    {hasWinner ? (
                      <div className="bg-[#0A2528] p-3 rounded-lg border border-[#14B8A6] w-full text-right">
                        <div className="text-[10px] uppercase font-bold text-[#34D399]">
                          {tender.status === "AWARDED" ? "Awarded Vendor" : "Reverse-Auction Leader"}
                        </div>
                        <div className="text-sm font-mono font-bold text-[#FCD34D]">
                          {formatTpt(tender.winning_bid_amount_tpt)} TPT
                        </div>
                        <div className="text-[11px] text-[#A99870] font-mono">
                          Savings: +{formatTpt(tender.max_budget_tpt - tender.winning_bid_amount_tpt)} TPT
                        </div>
                      </div>
                    ) : (
                      <div className="bg-[#0A2528] p-3 rounded-lg border border-[#123F44] w-full text-right">
                        <div className="text-[10px] uppercase text-[#A99870]">Status</div>
                        <div className="text-xs text-[#F7F3E9]">Awaiting qualified bid evaluation</div>
                      </div>
                    )}

                    <div className="flex flex-wrap items-center justify-end gap-2 w-full pt-1">
                      {tender.status === "OPEN" && (
                        <button
                          onClick={() => onOpenBidModal(tender)}
                          disabled={isProcessing}
                          className="bg-[#E5B869] hover:bg-[#D97706] text-[#06181A] font-bold px-3 py-1.5 rounded text-xs transition shadow-sm"
                        >
                          Submit Bid
                        </button>
                      )}

                      {isBuyer && tender.status !== "AWARDED" && hasWinner && (
                        <button
                          onClick={() => onFinalizeAward(tender)}
                          disabled={isProcessing}
                          className="bg-[#059669] hover:bg-[#047857] text-[#F7F3E9] font-bold px-3 py-1.5 rounded text-xs transition flex items-center gap-1 shadow-sm"
                        >
                          <CheckCircle2 className="w-3.5 h-3.5" /> Settle Award
                        </button>
                      )}

                      <button
                        onClick={() => onSelectTender(tender)}
                        className="bg-[#0D3135] hover:bg-[#123F44] text-[#F7F3E9] font-medium px-3 py-1.5 rounded text-xs border border-[#1A575E] transition flex items-center gap-1"
                      >
                        Review Bids <ArrowRight className="w-3 h-3 text-[#14B8A6]" />
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
