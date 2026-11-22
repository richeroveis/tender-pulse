import React, { useState } from "react";
import { Shield, Coins, Wallet, ArrowDownCircle, RefreshCw, ExternalLink } from "lucide-react";
import { EXPLORER_URL, CONTRACT_ADDRESS } from "../contract";

interface HeaderProps {
  currentRole: string;
  onRoleChange: (role: string) => void;
  accountAddress: string;
  tptBalance: number;
  refundableBalance: number;
  onFaucet: () => void;
  onWithdrawRefund: () => void;
  isProcessing: boolean;
  onRefresh: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  currentRole,
  onRoleChange,
  accountAddress,
  tptBalance,
  refundableBalance,
  onFaucet,
  onWithdrawRefund,
  isProcessing,
  onRefresh,
}) => {
  const formatTpt = (amt: number) => (amt / 1000000).toLocaleString(undefined, { maximumFractionDigits: 2 });
  const formatWei = (wei: number) => (wei / 1e18).toFixed(6);

  return (
    <header className="border-b border-[#1A575E] bg-[#0A2528] px-6 py-4 shadow-md sticky top-0 z-30">
      <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
        {/* Brand */}
        <div className="flex items-center gap-3">
          <img src="/tender-pulse/logo.png" alt="TenderPulse Logo" className="w-10 h-10 rounded-full border border-[#14B8A6]" />
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-bold tracking-tight text-[#F7F3E9] font-serif">TenderPulse</h1>
              <span className="text-xs px-2 py-0.5 rounded-full bg-[#123F44] text-[#2DD4BF] border border-[#1A575E] flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-[#34D399] animate-pulse"></span>
                Studionet 61999
              </span>
            </div>
            <p className="text-xs text-[#C9BA96]">AI-Audited Public Procurement & Reverse-Auction RFP Hub</p>
          </div>
        </div>

        {/* Contract Link & Live Stats */}
        <div className="hidden lg:flex items-center gap-4 text-xs">
          <a
            href={`${EXPLORER_URL}/address/${CONTRACT_ADDRESS}`}
            target="_blank"
            rel="noreferrer"
            className="flex items-center gap-1.5 text-[#5EEAD4] hover:underline bg-[#0D3135] px-3 py-1.5 rounded-md border border-[#1A575E]"
          >
            <Shield className="w-3.5 h-3.5 text-[#E5B869]" />
            <span>Contract: {CONTRACT_ADDRESS.slice(0, 6)}...{CONTRACT_ADDRESS.slice(-4)}</span>
            <ExternalLink className="w-3 h-3" />
          </a>
        </div>

        {/* User Balances & Role Selector */}
        <div className="flex flex-wrap items-center gap-3">
          {/* Refresh Button */}
          <button
            onClick={onRefresh}
            disabled={isProcessing}
            title="Refresh Ledger"
            className="p-2 rounded-md bg-[#0D3135] text-[#C9BA96] hover:text-[#F7F3E9] hover:bg-[#123F44] border border-[#1A575E] transition"
          >
            <RefreshCw className={`w-4 h-4 ${isProcessing ? "animate-spin text-[#14B8A6]" : ""}`} />
          </button>

          {/* Role Selector */}
          <div className="flex items-center gap-1 bg-[#082124] px-2.5 py-1.5 rounded-lg border border-[#1A575E]">
            <Wallet className="w-4 h-4 text-[#E5B869]" />
            <select
              value={currentRole}
              onChange={(e) => onRoleChange(e.target.value)}
              className="bg-transparent text-xs text-[#F7F3E9] focus:outline-none cursor-pointer pr-1"
            >
              <option value="Buyer">Buyer (DAO / Municipality)</option>
              <option value="Vendor Alpha">Vendor Alpha (Infrastructure)</option>
              <option value="Vendor Beta">Vendor Beta (RPC Gateways)</option>
              <option value="Challenger Charlie">Challenger Charlie (Auditor)</option>
            </select>
          </div>

          {/* TPT Escrow Balance */}
          <div className="bg-[#0D3135] px-3 py-1.5 rounded-lg border border-[#1A575E] flex items-center gap-2">
            <Coins className="w-4 h-4 text-[#F59E0B]" />
            <div className="text-right">
              <div className="text-[10px] uppercase text-[#A99870] font-medium leading-none">Domain A (TPT)</div>
              <div className="text-xs font-mono font-semibold text-[#F7F3E9] leading-tight">{formatTpt(tptBalance)} TPT</div>
            </div>
            <button
              onClick={onFaucet}
              disabled={isProcessing}
              title="Claim Faucet TPT"
              className="ml-1 text-[10px] bg-[#14B8A6] hover:bg-[#0D9488] text-[#06181A] font-semibold px-2 py-0.5 rounded transition"
            >
              +Faucet
            </button>
          </div>

          {/* Refundable Native GEN Balance */}
          {refundableBalance > 0 && (
            <div className="bg-[#123F44] px-3 py-1.5 rounded-lg border border-[#2DD4BF] flex items-center gap-2 animate-fade-in">
              <ArrowDownCircle className="w-4 h-4 text-[#2DD4BF]" />
              <div>
                <div className="text-[10px] uppercase text-[#5EEAD4] font-medium leading-none">Domain B (Refund)</div>
                <div className="text-xs font-mono font-bold text-[#F7F3E9] leading-tight">{formatWei(refundableBalance)} GEN</div>
              </div>
              <button
                onClick={onWithdrawRefund}
                disabled={isProcessing}
                className="text-[10px] bg-[#F59E0B] hover:bg-[#D97706] text-[#06181A] font-bold px-2 py-0.5 rounded transition"
              >
                Withdraw EOA
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
};
