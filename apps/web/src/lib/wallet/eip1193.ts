export const BASE_MAINNET_CHAIN_ID = 8453;
export const BASE_MAINNET_CHAIN_ID_HEX = "0x2105";

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

export async function switchInjectedWalletToBase(provider: Eip1193Provider): Promise<InjectedWalletSnapshot> {
  try {
    await provider.request({
      method: "wallet_switchEthereumChain",
      params: [{ chainId: BASE_MAINNET_CHAIN_ID_HEX }],
    });
  } catch (error) {
    if (error && typeof error === "object" && "code" in error && error.code === 4902) {
      await provider.request({
        method: "wallet_addEthereumChain",
        params: [{
          blockExplorerUrls: ["https://basescan.org"],
          chainId: BASE_MAINNET_CHAIN_ID_HEX,
          chainName: "Base",
          nativeCurrency: {
            decimals: 18,
            name: "Ether",
            symbol: "ETH",
          },
          rpcUrls: ["https://mainnet.base.org"],
        }],
      });
      await provider.request({
        method: "wallet_switchEthereumChain",
        params: [{ chainId: BASE_MAINNET_CHAIN_ID_HEX }],
      });
    } else {
      throw error;
    }
  }
  return readInjectedWallet(provider);
}
