"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  connectInjectedWallet,
  firstConnectedAddress,
  getInjectedEthereumProvider,
  maskWalletAddress,
  parseEip1193ChainId,
  readInjectedWallet,
  signInjectedWalletChallenge,
  switchInjectedWalletNetwork,
  type Eip1193Provider,
  type InjectedWalletSnapshot,
  type WalletNetworkProfile,
} from "../../lib/wallet/eip1193";

type WalletProviderStatus = "checking" | "available" | "unavailable";

function injectedWalletErrorMessage(error: unknown): string {
  if (error && typeof error === "object" && "code" in error && error.code === 4001) {
    return "La conexión fue cancelada en tu wallet.";
  }
  return "No pudimos conectar la wallet. Intenta de nuevo.";
}

export function useInjectedWallet(
  onWalletContextChanged: () => void,
  expectedNetwork: WalletNetworkProfile | null,
) {
  const [provider, setProvider] = useState<Eip1193Provider | null>(null);
  const [providerStatus, setProviderStatus] = useState<WalletProviderStatus>("checking");
  const [connectedWalletAddress, setConnectedWalletAddress] = useState<string | null>(null);
  const [walletChainId, setWalletChainId] = useState<number | null>(null);
  const [connectingWallet, setConnectingWallet] = useState(false);
  const [switchingWalletNetwork, setSwitchingWalletNetwork] = useState(false);
  const [walletError, setWalletError] = useState<string | null>(null);
  const snapshotRef = useRef<InjectedWalletSnapshot>({ address: null, chainId: null });
  const onWalletContextChangedRef = useRef(onWalletContextChanged);
  onWalletContextChangedRef.current = onWalletContextChanged;

  const applySnapshot = useCallback((snapshot: InjectedWalletSnapshot) => {
    snapshotRef.current = snapshot;
    setConnectedWalletAddress(snapshot.address);
    setWalletChainId(snapshot.chainId);
  }, []);

  useEffect(() => {
    const injectedProvider = getInjectedEthereumProvider();
    setProvider(injectedProvider);
    setProviderStatus(injectedProvider ? "available" : "unavailable");
  }, []);

  useEffect(() => {
    if (!provider) {
      return;
    }

    let active = true;
    const handleAccountsChanged = (accounts: unknown) => {
      if (!active) {
        return;
      }
      applySnapshot({
        address: firstConnectedAddress(accounts),
        chainId: snapshotRef.current.chainId,
      });
      setWalletError(null);
      onWalletContextChangedRef.current();
    };
    const handleChainChanged = (chainId: unknown) => {
      if (!active) {
        return;
      }
      applySnapshot({
        address: snapshotRef.current.address,
        chainId: parseEip1193ChainId(chainId),
      });
      setWalletError(null);
      onWalletContextChangedRef.current();
    };

    provider.on("accountsChanged", handleAccountsChanged);
    provider.on("chainChanged", handleChainChanged);
    void readInjectedWallet(provider)
      .then((snapshot) => {
        if (active) {
          applySnapshot(snapshot);
        }
      })
      .catch(() => {
        if (active) {
          applySnapshot({ address: null, chainId: null });
        }
      });

    return () => {
      active = false;
      provider.removeListener("accountsChanged", handleAccountsChanged);
      provider.removeListener("chainChanged", handleChainChanged);
    };
  }, [applySnapshot, provider]);

  const connectWallet = useCallback(async () => {
    const injectedProvider = provider || getInjectedEthereumProvider();
    if (!injectedProvider) {
      setProviderStatus("unavailable");
      setWalletError(null);
      return false;
    }
    setProvider(injectedProvider);
    setProviderStatus("available");
    setConnectingWallet(true);
    setWalletError(null);
    try {
      applySnapshot(await connectInjectedWallet(injectedProvider));
      return true;
    } catch (error) {
      setWalletError(injectedWalletErrorMessage(error));
      return false;
    } finally {
      setConnectingWallet(false);
    }
  }, [applySnapshot, provider]);

  const switchWalletToExpectedNetwork = useCallback(async () => {
    const injectedProvider = provider || getInjectedEthereumProvider();
    if (!injectedProvider || !expectedNetwork) {
      setProviderStatus("unavailable");
      setWalletError(null);
      return false;
    }
    setProvider(injectedProvider);
    setProviderStatus("available");
    setSwitchingWalletNetwork(true);
    setWalletError(null);
    try {
      applySnapshot(await switchInjectedWalletNetwork(injectedProvider, expectedNetwork));
      return true;
    } catch (error) {
      setWalletError(injectedWalletErrorMessage(error));
      return false;
    } finally {
      setSwitchingWalletNetwork(false);
    }
  }, [applySnapshot, expectedNetwork, provider]);

  const getConnectedWalletSnapshot = useCallback(() => snapshotRef.current, []);

  const signWalletChallenge = useCallback(async (challenge: string) => {
    const injectedProvider = provider || getInjectedEthereumProvider();
    const snapshot = snapshotRef.current;
    if (
      !injectedProvider
      || !snapshot.address
      || !expectedNetwork
      || snapshot.chainId !== expectedNetwork.chainId
    ) {
      throw new Error("WALLET_NOT_READY");
    }
    return signInjectedWalletChallenge(injectedProvider, snapshot.address, challenge);
  }, [expectedNetwork, provider]);

  return {
    connectWallet,
    connectedWalletAddress,
    connectedWalletAddressMasked: maskWalletAddress(connectedWalletAddress),
    connectingWallet,
    getConnectedWalletSnapshot,
    signWalletChallenge,
    switchWalletToExpectedNetwork,
    switchingWalletNetwork,
    walletChainId,
    walletError,
    walletIsExpectedNetwork: Boolean(expectedNetwork) && walletChainId === expectedNetwork?.chainId,
    walletProviderStatus: providerStatus,
  };
}
