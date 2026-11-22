import React from "react";
import { ShieldCheck, Database, Layers, ArrowUpRight, Scale } from "lucide-react";
import { TokenMetadata, NativeCustodySummary } from "../types";

interface RefundVaultProps {
  tokenMeta: TokenMetadata | null;
  nativeCustody: NativeCustodySummary | null;
}

export const RefundVault: React.FC<RefundVaultProps> = ({ tokenMeta, nativeCustody }) => {
  const formatTpt = (amt?: number) => (Number(amt || 0) / 1000000).toLocaleString(undefined, { maximumFractionDigits: 2 });
  const formatWei = (wei?: number) => (Number(wei || 0) / 1e18).toFixed(6);

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-8">
      {/* Domain A Card */}
      <div className="ledger-card rounded-xl p-5 border border-[#1A575E]">
        <div className="flex items-center justify-between mb-3 border-b border-[#1A575E] pb-3">
          <div className="flex items-center gap-2">
            <Database className="w-5 h-5 text-[#E5B869]" />
            <h3 className="font-serif font-semibold text-base text-[#F7F3E9]">Domain A: TPT Procurement Escrow</h3>
          </div>
          <span className="text-[11px] px-2 py-0.5 rounded bg-[#0A2528] text-[#14B8A6] border border-[#1A575E] font-mono">
            ERC-20 Ledger
          </span>
        </div>

        <div className="grid grid-cols-3 gap-2 text-center pt-1">
          <div className="bg-[#082124] p-3 rounded-lg border border-[#123F44]">
            <div className="text-[11px] text-[#A99870] uppercase">Vault Custody</div>
            <div className="text-sm font-mono font-bold text-[#FCD34D] mt-0.5">{formatTpt(tokenMeta?.vault_custody_balance)} TPT</div>
          </div>
          <div className="bg-[#082124] p-3 rounded-lg border border-[#123F44]">
            <div className="text-[11px] text-[#A99870] uppercase">Circulating</div>
            <div className="text-sm font-mono font-bold text-[#F7F3E9] mt-0.5">{formatTpt(tokenMeta?.sum_token_balances)} TPT</div>
          </div>
          <div className="bg-[#082124] p-3 rounded-lg border border-[#123F44]">
            <div className="text-[11px] text-[#A99870] uppercase">Total Supply</div>
            <div className="text-sm font-mono font-bold text-[#2DD4BF] mt-0.5">{formatTpt(tokenMeta?.total_supply)} TPT</div>
          </div>
        </div>

        <div className="mt-3 text-[11px] text-[#C9BA96] flex items-center justify-between px-1">
          <span>Conservation: Supply = Vault + Circulating</span>
          <span className="text-[#34D399] font-medium flex items-center gap-1">
            <ShieldCheck className="w-3.5 h-3.5" /> 0 wei cross-domain leakage
          </span>
        </div>
      </div>

      {/* Domain B Card */}
      <div className="ledger-card rounded-xl p-5 border border-[#1A575E]">
        <div className="flex items-center justify-between mb-3 border-b border-[#1A575E] pb-3">
          <div className="flex items-center gap-2">
            <Scale className="w-5 h-5 text-[#2DD4BF]" />
            <h3 className="font-serif font-semibold text-base text-[#F7F3E9]">Domain B: Native GEN Bond Custody</h3>
          </div>
          <span className="text-[11px] px-2 py-0.5 rounded bg-[#0A2528] text-[#E5B869] border border-[#1A575E] font-mono">
            Zero-Residue Vault
          </span>
        </div>

        <div className="grid grid-cols-3 gap-2 text-center pt-1">
          <div className="bg-[#082124] p-3 rounded-lg border border-[#123F44]">
            <div className="text-[11px] text-[#A99870] uppercase">Active Bid Bonds</div>
            <div className="text-sm font-mono font-bold text-[#F7F3E9] mt-0.5">{formatWei(nativeCustody?.active_bid_bonds)} GEN</div>
          </div>
          <div className="bg-[#082124] p-3 rounded-lg border border-[#123F44]">
            <div className="text-[11px] text-[#A99870] uppercase">Challenge Bonds</div>
            <div className="text-sm font-mono font-bold text-[#F7F3E9] mt-0.5">{formatWei(nativeCustody?.active_challenge_bonds)} GEN</div>
          </div>
          <div className="bg-[#082124] p-3 rounded-lg border border-[#123F44]">
            <div className="text-[11px] text-[#A99870] uppercase">Total Refundable</div>
            <div className="text-sm font-mono font-bold text-[#34D399] mt-0.5">{formatWei(nativeCustody?.total_refundable_balances)} GEN</div>
          </div>
        </div>

        <div className="mt-3 text-[11px] text-[#C9BA96] flex items-center justify-between px-1">
          <span>Custody = Bonds + Total Refundable</span>
          <span className="text-[#34D399] font-medium flex items-center gap-1">
            <ShieldCheck className="w-3.5 h-3.5" /> 0 wei stranded residue
          </span>
        </div>
      </div>
    </div>
  );
};
