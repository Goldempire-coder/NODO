import { useCallback, useEffect, useState } from "react";
import type { BusinessMiniAppView } from "../../constants/businessViews";
import type { BusinessAccessState } from "./helpers";

export type HomeSummaryState = "idle" | "loading" | "ready" | "error";

type HomeRefresh = () => Promise<unknown>;

async function runHomeSummaryRefresh(refreshes: HomeRefresh[]) {
  const results = await Promise.all(refreshes.map(async (refresh) => {
    try {
      return await refresh();
    } catch {
      return null;
    }
  }));
  return results.every(Boolean);
}

export function useBusinessHomeSummaryModel({
  accessState,
  refreshBusinessCapacity,
  refreshBusinessOrders,
  refreshCreditWallet,
  refreshMyAds,
  setView,
  view
}: {
  accessState: BusinessAccessState;
  refreshBusinessCapacity: HomeRefresh;
  refreshBusinessOrders: HomeRefresh;
  refreshCreditWallet: HomeRefresh;
  refreshMyAds: HomeRefresh;
  setView: (view: BusinessMiniAppView) => void;
  view: BusinessMiniAppView;
}) {
  const [homeSummaryState, setHomeSummaryState] = useState<HomeSummaryState>("idle");

  const refreshHomeSummary = useCallback(async () => {
    setHomeSummaryState("loading");
    const isReady = await runHomeSummaryRefresh([
      refreshBusinessCapacity,
      refreshCreditWallet,
      refreshMyAds,
      refreshBusinessOrders
    ]);
    setHomeSummaryState(isReady ? "ready" : "error");
    return isReady;
  }, [refreshBusinessCapacity, refreshBusinessOrders, refreshCreditWallet, refreshMyAds]);

  const loadHomeSummary = useCallback(async () => {
    if (accessState !== "ready") {
      return false;
    }
    setView("business-dashboard");
    return refreshHomeSummary();
  }, [accessState, refreshHomeSummary, setView]);

  useEffect(() => {
    if (accessState !== "ready" || view !== "business-dashboard") {
      return;
    }
    let active = true;
    setHomeSummaryState("loading");
    void runHomeSummaryRefresh([
      refreshBusinessCapacity,
      refreshCreditWallet,
      refreshMyAds,
      refreshBusinessOrders
    ]).then((isReady) => {
      if (!active) {
        return;
      }
      setHomeSummaryState(isReady ? "ready" : "error");
    });
    return () => {
      active = false;
    };
  }, [
    accessState,
    refreshBusinessCapacity,
    refreshBusinessOrders,
    refreshCreditWallet,
    refreshMyAds,
    view
  ]);

  return {
    homeSummaryState,
    loadHomeSummary
  };
}
