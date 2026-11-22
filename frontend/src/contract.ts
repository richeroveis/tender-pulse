import { createClient, createAccount } from "genlayer-js";
import { studionet } from "genlayer-js/chains";
import { Tender, Bid, TokenMetadata, NativeCustodySummary } from "./types";

export let CONTRACT_ADDRESS = "0xc48cbf6D7D4B3ddFFe496f8046D37c9C64717acF" as `0x${string}`;
export const CHAIN_ID = 61999;
export const RPC_URL = "https://studio.genlayer.com/api";
export const EXPLORER_URL = "https://explorer-studio.genlayer.com";

export function setContractAddress(addr: string) {
  CONTRACT_ADDRESS = addr as `0x${string}`;
}

// Public RPC Client
export const rpcClient = createClient({
  chain: studionet,
});

// Local Burner Wallets for immediate 1-click test driving
const PRESET_KEYS: Record<string, string> = {
  Buyer: "0x154a452b0755ee812014c1405b15d905ba06f9c7000000000000000000000001",
  "Vendor Alpha": "0x81b637d8fcd2c6da6359e6963113a1170de795e4000000000000000000000002",
  "Vendor Beta": "0xb9dd960c1753459a78115d3cb845a57d924b6877000000000000000000000003",
  "Challenger Charlie": "0x2bd806c97f0e00af1a1fc3328fa763a9269723c8000000000000000000000004",
};

export function getActiveAccount(role: string = "Buyer", customKey?: string) {
  let pk = customKey || localStorage.getItem(`tenderpulse_pk_${role}`) || PRESET_KEYS[role];
  if (!pk) {
    const acc = createAccount();
    pk = (acc as any).key || (acc as any).privateKey || "0x01";
    localStorage.setItem(`tenderpulse_pk_${role}`, pk);
    return acc;
  }
  return createAccount(pk as `0x${string}`);
}

export function getAuthenticatedClient(account: any) {
  return createClient({
    chain: studionet,
    account: account,
  });
}

// Read helpers (Batched to enforce <= 4-6 initial RPC calls)
export async function fetchInitialLedgerData(userAddress?: string): Promise<{
  tenders: Tender[];
  tokenMetadata: TokenMetadata;
  nativeCustody: NativeCustodySummary;
  userTptBalance: number;
  userRefundableBalance: number;
}> {
  try {
    const [tendersRes, tokenMetaRes, nativeRes, userTptRes, userRefRes] = await Promise.all([
      rpcClient.readContract({
        address: CONTRACT_ADDRESS,
        functionName: "list_tenders",
        args: [],
      }),
      rpcClient.readContract({
        address: CONTRACT_ADDRESS,
        functionName: "get_token_metadata",
        args: [],
      }),
      rpcClient.readContract({
        address: CONTRACT_ADDRESS,
        functionName: "get_native_custody_summary",
        args: [],
      }),
      userAddress
        ? rpcClient.readContract({
            address: CONTRACT_ADDRESS,
            functionName: "get_token_balance",
            args: [userAddress as `0x${string}`],
          })
        : Promise.resolve(0),
      userAddress
        ? rpcClient.readContract({
            address: CONTRACT_ADDRESS,
            functionName: "get_refundable_balance",
            args: [userAddress as `0x${string}`],
          })
        : Promise.resolve(0),
    ]);

    return {
      tenders: (tendersRes as unknown as Tender[]) || [],
      tokenMetadata: tokenMetaRes as unknown as TokenMetadata,
      nativeCustody: nativeRes as unknown as NativeCustodySummary,
      userTptBalance: Number(userTptRes || 0),
      userRefundableBalance: Number(userRefRes || 0),
    };
  } catch (err) {
    console.error("fetchInitialLedgerData error:", err);
    throw err;
  }
}

export async function fetchBidsForTender(tenderId: number): Promise<Bid[]> {
  try {
    const res = await rpcClient.readContract({
      address: CONTRACT_ADDRESS,
      functionName: "list_bids_for_tender",
      args: [tenderId],
    });
    return (res as unknown as Bid[]) || [];
  } catch (err) {
    console.error(`fetchBidsForTender(${tenderId}) error:`, err);
    return [];
  }
}
