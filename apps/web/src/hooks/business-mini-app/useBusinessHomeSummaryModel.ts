import { useCallback, useEffect, useState, type Dispatch, type SetStateAction } from "react";
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
  refreshBusinessOrders,
  refreshCreditWallet,
  refreshMyAds,
  setCurrentView,
  view
}: {
  accessState: BusinessAccessState;
  refreshBusinessOrders: HomeRefresh;
  refreshCreditWallet: HomeRefresh;
  refreshMyAds: HomeRefresh;
  setCurrentView: Dispatch<SetStateAction<BusinessMiniAppView>>;
  view: BusinessMiniAppView;
}) {
  const [homeSummaryState, setHomeSummaryState] = useState<HomeSummaryState>("idle");

  const refreshHomeSummary = useCallback(async () => {
    setHomeSummaryState("loading");
    const isReady = await runHomeSummaryRefresh([
      refreshCreditWallet,
      refreshMyAds,
      refreshBusinessOrders
    ]);
    setHomeSummaryState(isReady ? "ready" : "error");
    return isReady;
  }, [refreshBusinessOrders, refreshCreditWallet, refreshMyAds]);

  const loadHomeSummary = useCallback(async () => {
    if (accessState !== "ready") {
      return false;
    }
    setCurrentView("business-dashboard");
    return refreshHomeSummary();
  }, [accessState, refreshHomeSummary, setCurrentView]);

  useEffect(() => {
    if (accessState !== "ready" || view !== "business-dashboard") {
      return;
    }
    let active = true;
    setHomeSummaryState("loading");
    void runHomeSummaryRefresh([
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
