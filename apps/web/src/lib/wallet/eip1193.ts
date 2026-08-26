export const BASE_MAINNET_CHAIN_ID = 8453;
export const BASE_MAINNET_CHAIN_ID_HEX = "0x2105";
export const BASE_SEPOLIA_CHAIN_ID = 84532;
export const BASE_SEPOLIA_CHAIN_ID_HEX = "0x14a34";

export type WalletNetworkProfile = {
  network: "base_mainnet" | "base_sepolia";
  chainId: number;
  chainIdHex: string;
  chainName: string;
  rpcUrl: string;
  blockExplorerUrl: string;
  isTestnet: boolean;
};

export const BASE_MAINNET_WALLET_NETWORK: WalletNetworkProfile = {
  network: "base_mainnet",
  chainId: BASE_MAINNET_CHAIN_ID,
  chainIdHex: BASE_MAINNET_CHAIN_ID_HEX,
  chainName: "Base",
  rpcUrl: "https://mainnet.base.org",
  blockExplorerUrl: "https://basescan.org",
  isTestnet: false,
};

export const BASE_SEPOLIA_WALLET_NETWORK: WalletNetworkProfile = {
  network: "base_sepolia",
  chainId: BASE_SEPOLIA_CHAIN_ID,
  chainIdHex: BASE_SEPOLIA_CHAIN_ID_HEX,
  chainName: "Base Sepolia",
  rpcUrl: "https://sepolia.base.org",
  blockExplorerUrl: "https://sepolia.basescan.org",
  isTestnet: true,
};

export function resolveWalletNetworkProfile(
  network: string,
  chainId: number,
): WalletNetworkProfile | null {
  const profiles = [BASE_MAINNET_WALLET_NETWORK, BASE_SEPOLIA_WALLET_NETWORK];
  return profiles.find((profile) => profile.network === network && profile.chainId === chainId) || null;
}

type Eip1193RequestArguments = {
  readonly method: string;
  readonly params?: readonly unknown[] | object;
};

type Eip1193Listener = (payload: unknown) => void;

export type Eip1193Provider = {
  request(arguments_: Eip1193RequestArguments): Promise<unknown>;
  on(event: "accountsChanged" | "chainChanged", listener: Eip1193Listener): void;
  removeListener(event: "accountsChanged" | "chainChanged", listener: Eip1193Listener): void;
};

export type InjectedWalletSnapshot = {
  address: string | null;
  chainId: number | null;
};

function isEip1193Provider(value: unknown): value is Eip1193Provider {
  if (!value || typeof value !== "object") {
    return false;
  }
  const candidate = value as Partial<Eip1193Provider>;
  return typeof candidate.request === "function"
    && typeof candidate.on === "function"
    && typeof candidate.removeListener === "function";
}

export function getInjectedEthereumProvider(): Eip1193Provider | null {
  if (typeof window === "undefined") {
    return null;
  }
  const candidate = (window as Window & { ethereum?: unknown }).ethereum;
  return isEip1193Provider(candidate) ? candidate : null;
}

export function normalizeConnectedAddress(value: unknown): string | null {
  return typeof value === "string" && /^0x[a-fA-F0-9]{40}$/.test(value)
    ? value.toLowerCase()
    : null;
}

export function firstConnectedAddress(value: unknown): string | null {
  return Array.isArray(value) ? normalizeConnectedAddress(value[0]) : null;
}

export function parseEip1193ChainId(value: unknown): number | null {
  if (typeof value !== "string" || !/^0x[0-9a-fA-F]+$/.test(value)) {
    return null;
  }
  const chainId = Number.parseInt(value, 16);
  return Number.isSafeInteger(chainId) && chainId > 0 ? chainId : null;
}

export function maskWalletAddress(value: string | null): string {
  return value ? `${value.slice(0, 6)}...${value.slice(-4)}` : "No conectada";
}

export async function readInjectedWallet(provider: Eip1193Provider): Promise<InjectedWalletSnapshot> {
  const accounts = await provider.request({ method: "eth_accounts" });
  const chainId = await provider.request({ method: "eth_chainId" });
  return {
    address: firstConnectedAddress(accounts),
    chainId: parseEip1193ChainId(chainId),
  };
}

export async function connectInjectedWallet(provider: Eip1193Provider): Promise<InjectedWalletSnapshot> {
  const accounts = await provider.request({ method: "eth_requestAccounts" });
  const chainId = await provider.request({ method: "eth_chainId" });
  const address = firstConnectedAddress(accounts);
  if (!address) {
    throw new Error("WALLET_ACCOUNT_UNAVAILABLE");
  }
  return {
    address,
    chainId: parseEip1193ChainId(chainId),
  };
}

export async function switchInjectedWalletNetwork(
  provider: Eip1193Provider,
  expectedNetwork: WalletNetworkProfile,
): Promise<InjectedWalletSnapshot> {
  try {
    await provider.request({
      method: "wallet_switchEthereumChain",
      params: [{ chainId: expectedNetwork.chainIdHex }],
    });
  } catch (error) {
    if (error && typeof error === "object" && "code" in error && error.code === 4902) {
      await provider.request({
        method: "wallet_addEthereumChain",
        params: [{
          blockExplorerUrls: [expectedNetwork.blockExplorerUrl],
          chainId: expectedNetwork.chainIdHex,
          chainName: expectedNetwork.chainName,
          nativeCurrency: {
            decimals: 18,
            name: "Ether",
            symbol: "ETH",
          },
          rpcUrls: [expectedNetwork.rpcUrl],
        }],
      });
      await provider.request({
        method: "wallet_switchEthereumChain",
        params: [{ chainId: expectedNetwork.chainIdHex }],
      });
    } else {
      throw error;
    }
  }
  return readInjectedWallet(provider);
}

function utf8Hex(value: string): string {
  const bytes = new TextEncoder().encode(value);
  return `0x${Array.from(bytes, (byte) => byte.toString(16).padStart(2, "0")).join("")}`;
}

export async function signInjectedWalletChallenge(
  provider: Eip1193Provider,
  address: string,
  challenge: string,
): Promise<string> {
  const normalizedAddress = normalizeConnectedAddress(address);
  if (!normalizedAddress || !challenge.trim()) {
    throw new Error("WALLET_CHALLENGE_INVALID");
  }
  const signature = await provider.request({
    method: "personal_sign",
    params: [utf8Hex(challenge), normalizedAddress],
  });
  if (typeof signature !== "string" || !/^0x[a-fA-F0-9]{130}$/.test(signature)) {
    throw new Error("WALLET_SIGNATURE_INVALID");
  }
  return signature;
}
