import React, { useEffect, useState, useCallback } from "react";
import { Header } from "./components/Header";
import { RefundVault } from "./components/RefundVault";
import { TenderList } from "./components/TenderList";
import { TenderDetailModal } from "./components/TenderDetailModal";
import { PublishTenderModal } from "./components/PublishTenderModal";
import { BidModal } from "./components/BidModal";
import { ChallengeModal } from "./components/ChallengeModal";
import { Tender, Bid, TokenMetadata, NativeCustodySummary } from "./types";
import {
  fetchInitialLedgerData,
  fetchBidsForTender,
  getActiveAccount,
  getAuthenticatedClient,
  CONTRACT_ADDRESS,
  EXPLORER_URL,
} from "./contract";
import {
  PlusCircle,
  Building2,
  Sparkles,
  CheckCircle2,
  AlertCircle,
  ExternalLink,
} from "lucide-react";

export const App: React.FC = () => {
  const [role, setRole] = useState<string>("Buyer");
  const [account, setAccount] = useState<any>(() => getActiveAccount("Buyer"));
  const [tenders, setTenders] = useState<Tender[]>([]);
  const [tokenMeta, setTokenMeta] = useState<TokenMetadata | null>(null);
  const [nativeCustody, setNativeCustody] = useState<NativeCustodySummary | null>(null);
  const [userTpt, setUserTpt] = useState<number>(0);
  const [userRefundable, setUserRefundable] = useState<number>(0);
  const [filterTab, setFilterTab] = useState<"all" | "open" | "awarded" | "my">("all");

  const [selectedTender, setSelectedTender] = useState<Tender | null>(null);
  const [tenderBids, setTenderBids] = useState<Bid[]>([]);
  const [isDetailOpen, setIsDetailOpen] = useState<boolean>(false);
  const [isPublishOpen, setIsPublishOpen] = useState<boolean>(false);
  const [bidTargetTender, setBidTargetTender] = useState<Tender | null>(null);
  const [challengeTarget, setChallengeTarget] = useState<{ tender: Tender; bid: Bid } | null>(null);

  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isProcessing, setIsProcessing] = useState<boolean>(false);
  const [toast, setToast] = useState<{
    message: string;
    type: "success" | "error" | "info";
    txHash?: string;
  } | null>(null);

  const handleRoleChange = (newRole: string) => {
    setRole(newRole);
    const acc = getActiveAccount(newRole);
    setAccount(acc);
  };

  const showToast = (message: string, type: "success" | "error" | "info" = "info", txHash?: string) => {
    setToast({ message, type, txHash });
    setTimeout(() => {
      setToast(null);
    }, 9000);
  };

  const refreshLedger = useCallback(async () => {
    try {
      const data = await fetchInitialLedgerData(account?.address);
      setTenders(data.tenders);
      setTokenMeta(data.tokenMetadata);
      setNativeCustody(data.nativeCustody);
      setUserTpt(data.userTptBalance);
      setUserRefundable(data.userRefundableBalance);
    } catch (err) {
      console.error("Ledger refresh error:", err);
    } finally {
      setIsLoading(false);
    }
  }, [account?.address]);

  useEffect(() => {
    refreshLedger();
    const interval = setInterval(refreshLedger, 12000);
    return () => clearInterval(interval);
  }, [refreshLedger]);

  const handleOpenTenderDetail = async (tender: Tender) => {
    setSelectedTender(tender);
    setIsDetailOpen(true);
    try {
      const bids = await fetchBidsForTender(tender.tender_id);
      setTenderBids(bids);
    } catch (err) {
      console.error("fetch bids error:", err);
    }
  };

  const handleRefreshBids = async () => {
    if (!selectedTender) return;
    try {
      const bids = await fetchBidsForTender(selectedTender.tender_id);
      setTenderBids(bids);
      refreshLedger();
    } catch (err) {
      console.error("refresh bids error:", err);
    }
  };

  // 1-Click Faucet
  const handleFaucet = async () => {
    if (!account) return;
    setIsProcessing(true);
    try {
      const client = getAuthenticatedClient(account);
      const txHash = await client.writeContract({
        address: CONTRACT_ADDRESS,
        functionName: "faucet_or_deposit",
        args: [500000 * 1000000],
        value: 0n,
      });
      showToast("Faucet transaction sent! Crediting +500,000 TPT...", "success", txHash);
      setTimeout(refreshLedger, 5000);
    } catch (err: any) {
      showToast(err?.message || "Faucet call failed", "error");
    } finally {
      setIsProcessing(false);
    }
  };

  // Claim Native Refund
  const handleClaimRefund = async () => {
    if (!account) return;
    setIsProcessing(true);
    try {
      const client = getAuthenticatedClient(account);
      const txHash = await client.writeContract({
        address: CONTRACT_ADDRESS,
        functionName: "claim_refundable_balance",
        args: [],
        value: 0n,
      });
      showToast("Refund claim sent! Dispatched via IEoaRecipient...", "success", txHash);
      setTimeout(refreshLedger, 5000);
    } catch (err: any) {
      showToast(err?.message || "Refund claim failed", "error");
    } finally {
      setIsProcessing(false);
    }
  };

  // Publish Tender
  const handlePublishTender = async (data: {
    title: string;
    rfpSpec: string;
    maxBudgetTpt: number;
    minQualificationBps: number;
    requiredBidBondGen: number;
    requiredChallengeBondGen: number;
    bidWindowSeconds: number;
    challengeWindowSeconds: number;
  }) => {
    if (!account) return;
    setIsProcessing(true);
    try {
      const client = getAuthenticatedClient(account);
      const txHash = await client.writeContract({
        address: CONTRACT_ADDRESS,
        functionName: "create_tender",
        args: [
          data.title,
          data.rfpSpec,
          data.maxBudgetTpt,
          data.minQualificationBps,
          BigInt(data.requiredBidBondGen),
          BigInt(data.requiredChallengeBondGen),
          data.bidWindowSeconds,
          data.challengeWindowSeconds,
        ],
        value: 0n,
      });
      setIsPublishOpen(false);
      showToast("RFP Tender published and escrow funded!", "success", txHash);
      setTimeout(refreshLedger, 5000);
    } catch (err: any) {
      showToast(err?.message || "Publish tender failed", "error");
    } finally {
      setIsProcessing(false);
    }
  };

  // Submit Bid
  const handleSubmitBid = async (
    tenderId: number,
    bidAmountTpt: number,
    specUrl: string,
    bondWei: bigint
  ) => {
    if (!account) return;
    setIsProcessing(true);
    try {
      const client = getAuthenticatedClient(account);
      const txHash = await client.writeContract({
        address: CONTRACT_ADDRESS,
        functionName: "submit_vendor_bid_payable",
        args: [tenderId, bidAmountTpt, specUrl],
        value: bondWei,
      });
      setBidTargetTender(null);
      showToast("Vendor reverse-auction bid submitted with bond!", "success", txHash);
      setTimeout(refreshLedger, 5000);
    } catch (err: any) {
      showToast(err?.message || "Bid submission failed", "error");
    } finally {
      setIsProcessing(false);
    }
  };

  // Challenge Bid
  const handleChallengeBid = async (
    tenderId: number,
    bidId: number,
    evidenceUrl: string,
    reason: string,
    bondWei: bigint
  ) => {
    if (!account) return;
    setIsProcessing(true);
    try {
      const client = getAuthenticatedClient(account);
      const txHash = await client.writeContract({
        address: CONTRACT_ADDRESS,
        functionName: "challenge_vendor_bid_payable",
        args: [tenderId, bidId, evidenceUrl, reason],
        value: bondWei,
      });
      setChallengeTarget(null);
      showToast("Bid challenge filed with Native GEN bond!", "success", txHash);
      setTimeout(refreshLedger, 5000);
    } catch (err: any) {
      showToast(err?.message || "Challenge submission failed", "error");
    } finally {
      setIsProcessing(false);
    }
  };

  // Evaluate Bid
  const handleEvaluateBid = async (tenderId: number, bidId: number) => {
    if (!account) return;
    setIsProcessing(true);
    try {
      const client = getAuthenticatedClient(account);
      const txHash = await client.writeContract({
        address: CONTRACT_ADDRESS,
        functionName: "evaluate_vendor_bid",
        args: [tenderId, bidId],
        value: 0n,
      });
      showToast("Bid AI compliance consensus initiated!", "info", txHash);
      setTimeout(() => {
        handleRefreshBids();
      }, 7000);
    } catch (err: any) {
      showToast(err?.message || "Evaluation call failed", "error");
    } finally {
      setIsProcessing(false);
    }
  };

  // Adjudicate Challenge
  const handleAdjudicateChallenge = async (tenderId: number, bidId: number) => {
    if (!account) return;
    setIsProcessing(true);
    try {
      const client = getAuthenticatedClient(account);
      const txHash = await client.writeContract({
        address: CONTRACT_ADDRESS,
        functionName: "adjudicate_bid_challenge",
        args: [tenderId, bidId],
        value: 0n,
      });
      showToast("Bid challenge consensus adjudication initiated!", "info", txHash);
      setTimeout(() => {
        handleRefreshBids();
      }, 7000);
    } catch (err: any) {
      showToast(err?.message || "Adjudication call failed", "error");
    } finally {
      setIsProcessing(false);
    }
  };

  // Finalize Award
  const handleFinalizeAward = async (tender: Tender) => {
    if (!account) return;
    setIsProcessing(true);
    try {
      const client = getAuthenticatedClient(account);
      const txHash = await client.writeContract({
        address: CONTRACT_ADDRESS,
        functionName: "finalize_tender_award",
        args: [tender.tender_id],
        value: 0n,
      });
      showToast("Tender award finalized & Domain A TPT distributed!", "success", txHash);
      setTimeout(refreshLedger, 5000);
    } catch (err: any) {
      showToast(err?.message || "Finalize award failed", "error");
    } finally {
      setIsProcessing(false);
    }
  };

  // Refund Runner-up
  const handleRefundRunnerUp = async (tenderId: number, bidId: number) => {
    if (!account) return;
    setIsProcessing(true);
    try {
      const client = getAuthenticatedClient(account);
      const txHash = await client.writeContract({
        address: CONTRACT_ADDRESS,
        functionName: "refund_runner_up_bid_bond",
        args: [tenderId, bidId],
        value: 0n,
      });
      showToast("Runner-up bid bond routed to refundable balances!", "success", txHash);
      setTimeout(refreshLedger, 5000);
    } catch (err: any) {
      showToast(err?.message || "Runner-up refund failed", "error");
    } finally {
      setIsProcessing(false);
    }
  };

  // Mutual Co-Sign Settlement
  const handleProposeMutualRelease = async (tenderId: number, payoutBps: number) => {
    if (!account) return;
    setIsProcessing(true);
    try {
      const client = getAuthenticatedClient(account);
      const isBuyer = role === "Buyer";
      const fn = isBuyer ? "approve_tender_payout_buyer" : "approve_tender_payout_vendor";
      const txHash = await client.writeContract({
        address: CONTRACT_ADDRESS,
        functionName: fn,
        args: [tenderId, payoutBps],
        value: 0n,
      });
      showToast(`Co-sign approval recorded (${payoutBps / 100}%)`, "success", txHash);
      setTimeout(refreshLedger, 5000);
    } catch (err: any) {
      showToast(err?.message || "Co-sign failed", "error");
    } finally {
      setIsProcessing(false);
    }
  };

  const filteredTenders = tenders.filter((t) => {
    if (filterTab === "open") return t.status === "ACTIVE";
    if (filterTab === "awarded") return t.status === "AWARDED";
    if (filterTab === "my") {
      const myAddr = account?.address?.toLowerCase();
      return (
        t.buyer.toLowerCase() === myAddr ||
        t.winning_vendor.toLowerCase() === myAddr
      );
    }
    return true;
  });

  return (
    <div className="min-h-screen bg-[#07191B] text-[#F7F3E9] flex flex-col font-sans selection:bg-[#E5B869] selection:text-[#07191B]">
      {/* Toast Notification */}
      {toast && (
        <div className="fixed bottom-6 right-6 z-50 max-w-md animate-fade-in">
          <div
            className={`p-4 rounded-xl border shadow-2xl flex items-start gap-3 ${
              toast.type === "success"
                ? "bg-[#0A2528] border-[#2DD4BF] text-[#F7F3E9]"
                : toast.type === "error"
                ? "bg-[#2A0E0E] border-[#EF4444] text-[#FCA5A5]"
                : "bg-[#0E353A] border-[#E5B869] text-[#F7F3E9]"
            }`}
          >
            {toast.type === "success" ? (
              <CheckCircle2 className="w-5 h-5 text-[#2DD4BF] shrink-0 mt-0.5" />
            ) : toast.type === "error" ? (
              <AlertCircle className="w-5 h-5 text-[#EF4444] shrink-0 mt-0.5" />
            ) : (
              <Sparkles className="w-5 h-5 text-[#E5B869] shrink-0 mt-0.5" />
            )}
            <div className="text-xs space-y-1">
              <div className="font-semibold">{toast.message}</div>
              {toast.txHash && (
                <a
                  href={`${EXPLORER_URL}/transactions/${toast.txHash}`}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-1 text-[11px] text-[#2DD4BF] hover:underline font-mono"
                >
                  View on Explorer <ExternalLink className="w-3 h-3" />
                </a>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Header */}
      <Header
        currentRole={role}
        onRoleChange={handleRoleChange}
        accountAddress={account?.address || ""}
        tptBalance={userTpt}
        refundableBalance={userRefundable}
        onFaucet={handleFaucet}
        onWithdrawRefund={handleClaimRefund}
        isProcessing={isProcessing}
        onRefresh={refreshLedger}
      />

      {/* Main Container */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
        {/* Editorial Hero Banner */}
        <section className="bg-gradient-to-r from-[#0A2528] via-[#0E353A] to-[#082124] border border-[#1A575E] rounded-3xl p-6 sm:p-8 shadow-2xl relative overflow-hidden">
          <div className="relative z-10 space-y-4 max-w-3xl">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#1A575E]/50 border border-[#2DD4BF]/30 text-[#2DD4BF] text-xs font-mono">
              <Sparkles className="w-3.5 h-3.5" />
              Intelligent Reverse-Auction Procurement Protocol
            </div>
            <h1 className="text-3xl sm:text-4xl font-serif font-bold text-[#F7F3E9] tracking-tight leading-tight">
              AI-Audited Public Procurement & Reverse-Auction RFP Award Hub
            </h1>
            <p className="text-[#C9BA96] text-sm leading-relaxed">
              TenderPulse combines competitive reverse auctions with GenLayer AI validator consensus.
              Procurement buyers lock Domain A (<span className="text-[#2DD4BF] font-semibold">TPT</span>) in escrow,
              while vendors stake Domain B (<span className="text-[#FCD34D] font-semibold">Native GEN</span>) bonds to
              guarantee proposal authenticity.
            </p>
          </div>

          {/* Metric Badges */}
          <div className="mt-6 pt-6 border-t border-[#1A575E]/60 grid grid-cols-2 sm:grid-cols-4 gap-4">
            <div className="bg-[#07191B]/60 p-3 rounded-xl border border-[#123F44]">
              <div className="text-[11px] text-[#A99870] uppercase font-bold">Domain A Escrow</div>
              <div className="text-lg font-serif font-bold text-[#2DD4BF] mt-0.5">
                {tokenMeta ? (tokenMeta.vault_custody_balance / 1000000).toLocaleString() : "..."} TPT
              </div>
              <div className="text-[10px] text-[#A99870]">Total Procurement Escrow</div>
            </div>

            <div className="bg-[#07191B]/60 p-3 rounded-xl border border-[#123F44]">
              <div className="text-[11px] text-[#A99870] uppercase font-bold">Domain B Bonds</div>
              <div className="text-lg font-serif font-bold text-[#FCD34D] mt-0.5 font-mono">
                {nativeCustody ? nativeCustody.native_custody_balance : 0} wei
              </div>
              <div className="text-[10px] text-[#A99870]">0 Wei Stranded Residue</div>
            </div>

            <div className="bg-[#07191B]/60 p-3 rounded-xl border border-[#123F44]">
              <div className="text-[11px] text-[#A99870] uppercase font-bold">Active Tenders</div>
              <div className="text-lg font-serif font-bold text-[#F7F3E9] mt-0.5">
                {tenders.length}
              </div>
              <div className="text-[10px] text-[#A99870]">Total RFPs Published</div>
            </div>

            <div className="bg-[#07191B]/60 p-3 rounded-xl border border-[#123F44]">
              <div className="text-[11px] text-[#A99870] uppercase font-bold">Validator Consensus</div>
              <div className="text-lg font-serif font-bold text-[#E5B869] mt-0.5">
                Comparative
              </div>
              <div className="text-[10px] text-[#A99870]">Fail-Closed & 250-bps Grid</div>
            </div>
          </div>
        </section>

        {/* Refund Vault Banner */}
        <RefundVault
          tokenMeta={tokenMeta}
          nativeCustody={nativeCustody}
        />

        {/* Control Bar: Filters & Actions */}
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-4">
          <div className="flex items-center gap-2 bg-[#0A2528] p-1 rounded-xl border border-[#1A575E]">
            <button
              onClick={() => setFilterTab("all")}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
                filterTab === "all"
                  ? "bg-[#1A575E] text-[#F7F3E9] shadow"
                  : "text-[#A99870] hover:text-[#F7F3E9]"
              }`}
            >
              All Tenders ({tenders.length})
            </button>
            <button
              onClick={() => setFilterTab("open")}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
                filterTab === "open"
                  ? "bg-[#1A575E] text-[#F7F3E9] shadow"
                  : "text-[#A99870] hover:text-[#F7F3E9]"
              }`}
            >
              Open for Bidding
            </button>
            <button
              onClick={() => setFilterTab("awarded")}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
                filterTab === "awarded"
                  ? "bg-[#1A575E] text-[#F7F3E9] shadow"
                  : "text-[#A99870] hover:text-[#F7F3E9]"
              }`}
            >
              Awarded
            </button>
            <button
              onClick={() => setFilterTab("my")}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
                filterTab === "my"
                  ? "bg-[#1A575E] text-[#F7F3E9] shadow"
                  : "text-[#A99870] hover:text-[#F7F3E9]"
              }`}
            >
              My Tenders
            </button>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={() => setIsPublishOpen(true)}
              className="px-4 py-2 rounded-xl bg-gradient-to-r from-[#E5B869] to-[#C9BA96] hover:from-[#F0C97F] hover:to-[#D9CBA8] text-[#07191B] font-semibold text-xs transition-all shadow-md flex items-center gap-2"
            >
              <PlusCircle className="w-4 h-4" />
              Publish New RFP Tender
            </button>
          </div>
        </div>

        {/* Tender Ledger Cards */}
        {isLoading ? (
          <div className="text-center py-20 text-[#A99870]">
            <div className="animate-spin w-8 h-8 border-2 border-[#2DD4BF] border-t-transparent rounded-full mx-auto mb-4" />
            Loading TenderPulse Ledger...
          </div>
        ) : (
          <TenderList
            tenders={filteredTenders}
            onSelectTender={handleOpenTenderDetail}
            onOpenPublishModal={() => setIsPublishOpen(true)}
            onOpenBidModal={(tender) => setBidTargetTender(tender)}
            onFinalizeAward={handleFinalizeAward}
            userAddress={account?.address || ""}
            isProcessing={isProcessing}
          />
        )}
      </main>

      {/* Modals */}
      <PublishTenderModal
        isOpen={isPublishOpen}
        onClose={() => setIsPublishOpen(false)}
        onSubmit={handlePublishTender}
        isProcessing={isProcessing}
      />

      <BidModal
        tender={bidTargetTender}
        isOpen={!!bidTargetTender}
        onClose={() => setBidTargetTender(null)}
        onSubmit={handleSubmitBid}
        isProcessing={isProcessing}
      />

      <ChallengeModal
        tender={challengeTarget?.tender || null}
        bid={challengeTarget?.bid || null}
        isOpen={!!challengeTarget}
        onClose={() => setChallengeTarget(null)}
        onSubmit={handleChallengeBid}
        isProcessing={isProcessing}
      />

      <TenderDetailModal
        tender={selectedTender}
        bids={tenderBids}
        onClose={() => setIsDetailOpen(false)}
        onEvaluateBid={handleEvaluateBid}
        onOpenChallengeModal={(t, b) => setChallengeTarget({ tender: t, bid: b })}
        onAdjudicateChallenge={handleAdjudicateChallenge}
        onRefundRunnerUpBond={handleRefundRunnerUp}
        onProposeMutualRelease={handleProposeMutualRelease}
        onFinalizeAward={handleFinalizeAward}
        userAddress={account?.address || ""}
        isProcessing={isProcessing}
      />

      {/* Footer */}
      <footer className="border-t border-[#123F44] py-8 text-center text-xs text-[#A99870]">
        <div className="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2 font-serif text-[#F7F3E9]">
            <Building2 className="w-4 h-4 text-[#2DD4BF]" />
            <span>TenderPulse Protocol &bull; Civic Procurement & Reverse-Auction Bid Room</span>
          </div>
          <div className="font-mono text-[11px] text-[#A99870]">
            Studionet Chain ID 61999 &bull; GenLayer Classic SDK
          </div>
        </div>
      </footer>
    </div>
  );
};

export default App;
