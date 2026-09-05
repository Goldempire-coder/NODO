"use client";

import { useRef } from "react";
import { getMarketplaceAd, marketplaceSearchKey, searchMarketplaceAds } from "../../api/ads";
import { ApiClientError, type AuthenticatedRequest } from "../../api/client";
import type { AdSummary } from "../../types/ads";
import type { PublicUser } from "../../types/auth";
import type { SearchFormState } from "../../types/client";
import { actionStartedAt, recordActionCompleted, recordActionFailed, recordActionStarted } from "../actionTelemetry";
import { appendUniqueById } from "../pagination";
import type { ClientWorkspaceState } from "./useClientWorkspaceState";

const CLIENT_MARKETPLACE_CACHE_TTL_MS = 30_000;
const CLIENT_MARKETPLACE_PAGE_SIZE = "20";

type MarketplaceSearchPage = {
  items: AdSummary[];
  next_cursor: string | null;
};

export function useClientMarketplaceModel(state: ClientWorkspaceState & { request: AuthenticatedRequest; user: PublicUser }) {
  const {
    request,
    searchForm,
    searchResults,
    searchResultsNextCursor,
    setLoadingMarketplace,
    setLoadingMoreMarketplace,
    setOpeningMarketplaceAdId,
    setSearchingMarketplace,
    setSearchForm,
    setSearchResults,
    setSearchResultsNextCursor,
    setSelectedAd,
    setNotice,
    setView
  } = state;
  const cacheRef = useRef<Record<string, { items: AdSummary[]; nextCursor: string | null; loadedAt: number }>>({});
  const activeMarketplaceParamsRef = useRef<Record<string, string> | null>(null);
  const marketplaceRequestIdRef = useRef(0);
  const adDetailRequestIdRef = useRef(0);

  function selectMarketplacePaymentMethod(paymentMethod: SearchFormState["payment_method"]) {
    if (paymentMethod === searchForm.payment_method) {
      return;
    }
    marketplaceRequestIdRef.current += 1;
    adDetailRequestIdRef.current += 1;
    activeMarketplaceParamsRef.current = null;
    setSearchForm((current) => ({ ...current, payment_method: paymentMethod }));
    setSearchResults([]);
    setSearchResultsNextCursor(null);
    setSelectedAd(null);
    setNotice("");
    setSearchingMarketplace(false);
    setLoadingMarketplace(false);
    setLoadingMoreMarketplace(false);
    setOpeningMarketplaceAdId(null);
  }

  async function searchAds() {
    const requestId = marketplaceRequestIdRef.current + 1;
    marketplaceRequestIdRef.current = requestId;
    const startedAt = actionStartedAt();
    recordActionStarted("client_marketplace_search", "marketplace-search");
    setSearchingMarketplace(true);
    setView("marketplace-search");
    setNotice("");
    setSearchResults([]);
    setSearchResultsNextCursor(null);
    setSelectedAd(null);
    const params = {
      amount_usd: searchForm.amount_usd,
      payment_method: searchForm.payment_method,
      delivery_method: searchForm.delivery_method,
      sort: searchForm.sort,
      limit: CLIENT_MARKETPLACE_PAGE_SIZE
    };
    activeMarketplaceParamsRef.current = params;
    const key = marketplaceSearchKey(params);
    const cached = cacheRef.current[key];
    if (cached && Date.now() - cached.loadedAt < CLIENT_MARKETPLACE_CACHE_TTL_MS) {
      setSearchResults(cached.items);
      setSearchResultsNextCursor(cached.nextCursor);
      setSelectedAd(null);
    }
    try {
      const data = await searchMarketplaceAds<MarketplaceSearchPage>(request, params);
      cacheRef.current[key] = { items: data.items, nextCursor: data.next_cursor, loadedAt: Date.now() };
      if (marketplaceRequestIdRef.current !== requestId) {
        return;
      }
      setSearchResults(data.items);
      setSearchResultsNextCursor(data.next_cursor);
      setSelectedAd(null);
      setNotice(data.items.length ? "" : "No encontramos negocios para ese monto. Prueba otro monto o metodo.");
      recordActionCompleted("client_marketplace_search", "marketplace-search", startedAt);
    } catch (error) {
      if (marketplaceRequestIdRef.current !== requestId) {
        return;
      }
      setNotice(error instanceof Error ? error.message : "No logramos buscar negocios en este momento.");
      recordActionFailed("client_marketplace_search", "marketplace-search", startedAt, error instanceof Error ? error.name : undefined);
    } finally {
      if (marketplaceRequestIdRef.current === requestId) {
        setSearchingMarketplace(false);
      }
    }
  }

  async function searchFreshForAmount(amountUsd: string) {
    const requestId = marketplaceRequestIdRef.current + 1;
    marketplaceRequestIdRef.current = requestId;
    const startedAt = actionStartedAt();
    recordActionStarted("client_marketplace_search", "marketplace-search");
    setSearchingMarketplace(true);
    setView("marketplace-search");
    setNotice("");
    cacheRef.current = {};
    setSearchResults([]);
    setSearchResultsNextCursor(null);
    setSelectedAd(null);
    setSearchForm((current) => ({ ...current, amount_usd: amountUsd }));
    const params = {
      amount_usd: amountUsd,
      payment_method: searchForm.payment_method,
      delivery_method: searchForm.delivery_method,
      sort: searchForm.sort,
      limit: CLIENT_MARKETPLACE_PAGE_SIZE
    };
    activeMarketplaceParamsRef.current = params;
    try {
      const data = await searchMarketplaceAds<MarketplaceSearchPage>(
        request,
        params
      );
      const key = marketplaceSearchKey(params);
      cacheRef.current[key] = { items: data.items, nextCursor: data.next_cursor, loadedAt: Date.now() };
      if (marketplaceRequestIdRef.current !== requestId) {
        return;
      }
      setSearchResults(data.items);
      setSearchResultsNextCursor(data.next_cursor);
      setNotice(
        data.items.length
          ? "Orden cancelada. Te mostramos otras ofertas disponibles para el mismo monto."
          : "Orden cancelada. No encontramos otras ofertas disponibles para el mismo monto."
      );
      recordActionCompleted(
        "client_marketplace_search",
        "marketplace-search",
        startedAt
      );
    } catch (error) {
      if (marketplaceRequestIdRef.current !== requestId) {
        return;
      }
      setNotice(
        "La orden fue cancelada, pero no logramos buscar otras ofertas. Intenta de nuevo."
      );
      recordActionFailed(
        "client_marketplace_search",
        "marketplace-search",
        startedAt,
        error instanceof Error ? error.name : undefined
      );
    } finally {
      if (marketplaceRequestIdRef.current === requestId) {
        setSearchingMarketplace(false);
      }
    }
  }

  async function loadActiveMarketplace(sort: "trust" | "rate" | "speed" = searchForm.sort) {
    const requestId = marketplaceRequestIdRef.current + 1;
    marketplaceRequestIdRef.current = requestId;
    const startedAt = actionStartedAt();
    recordActionStarted("client_marketplace_list", "marketplace-list");
    setView("marketplace-list");
    setNotice("");
    const params = {
      payment_method: searchForm.payment_method,
      sort,
      limit: CLIENT_MARKETPLACE_PAGE_SIZE
    };
    activeMarketplaceParamsRef.current = params;
    const key = marketplaceSearchKey(params);
    const cached = cacheRef.current[key];
    if (cached && Date.now() - cached.loadedAt < CLIENT_MARKETPLACE_CACHE_TTL_MS) {
      setSearchResults(cached.items);
      setSearchResultsNextCursor(cached.nextCursor);
      setSelectedAd(null);
      setLoadingMarketplace(false);
    }
    if (cached) {
      setSearchResults(cached.items);
      setSearchResultsNextCursor(cached.nextCursor);
      setSelectedAd(null);
      setLoadingMarketplace(false);
    } else {
      setLoadingMarketplace(true);
      setSearchResultsNextCursor(null);
    }
    try {
      const data = await searchMarketplaceAds<MarketplaceSearchPage>(request, params);
      cacheRef.current[key] = { items: data.items, nextCursor: data.next_cursor, loadedAt: Date.now() };
      if (marketplaceRequestIdRef.current !== requestId) {
        return;
      }
      setSearchResults(data.items);
      setSearchResultsNextCursor(data.next_cursor);
      setSelectedAd(null);
      setNotice(data.items.length ? "" : "No hay ofertas disponibles en este momento.");
      recordActionCompleted("client_marketplace_list", "marketplace-list", startedAt);
    } catch (error) {
      if (marketplaceRequestIdRef.current !== requestId) {
        return;
      }
      setNotice(error instanceof Error ? error.message : "No logramos cargar los negocios en este momento.");
      recordActionFailed("client_marketplace_list", "marketplace-list", startedAt, error instanceof Error ? error.name : undefined);
    } finally {
      if (marketplaceRequestIdRef.current === requestId) {
        setLoadingMarketplace(false);
      }
    }
  }

  async function loadMoreActiveMarketplace() {
    const cursor = searchResultsNextCursor;
    const baseParams = activeMarketplaceParamsRef.current;
    if (!cursor || !baseParams || state.loadingMoreMarketplace) {
      return;
    }
    const requestId = marketplaceRequestIdRef.current + 1;
    marketplaceRequestIdRef.current = requestId;
    const startedAt = actionStartedAt();
    recordActionStarted("client_marketplace_load_more", "marketplace-list");
    setLoadingMoreMarketplace(true);
    const params = { ...baseParams, cursor };
    try {
      const data = await searchMarketplaceAds<MarketplaceSearchPage>(request, params);
      if (marketplaceRequestIdRef.current !== requestId) {
        return;
      }
      const key = marketplaceSearchKey(baseParams);
      setSearchResults((current) => {
        const merged = appendUniqueById(current, data.items);
        cacheRef.current[key] = { items: merged, nextCursor: data.next_cursor, loadedAt: Date.now() };
        return merged;
      });
      setSearchResultsNextCursor(data.next_cursor);
      recordActionCompleted("client_marketplace_load_more", "marketplace-list", startedAt);
    } catch (error) {
      if (marketplaceRequestIdRef.current === requestId) {
        setNotice(error instanceof Error ? error.message : "No logramos cargar mas negocios.");
      }
      recordActionFailed("client_marketplace_load_more", "marketplace-list", startedAt, error instanceof Error ? error.name : undefined);
    } finally {
      if (marketplaceRequestIdRef.current === requestId) {
        setLoadingMoreMarketplace(false);
      }
    }
  }

  async function openAdDetail(adId: string) {
    const requestId = adDetailRequestIdRef.current + 1;
    adDetailRequestIdRef.current = requestId;
    const startedAt = actionStartedAt();
    recordActionStarted("client_ad_detail_open", "marketplace-detail");
    const optimisticAd = searchResults.find((ad) => ad.id === adId);
    if (optimisticAd) {
      setSelectedAd(optimisticAd);
      setView("marketplace-detail");
      setNotice("");
      setOpeningMarketplaceAdId(null);
    }
    if (!optimisticAd) {
      setOpeningMarketplaceAdId(adId);
    }
    try {
      const data = await getMarketplaceAd<{ ad: NonNullable<typeof optimisticAd> }>(request, adId);
      if (adDetailRequestIdRef.current !== requestId) {
        return;
      }
      setSelectedAd(data.ad);
      setView("marketplace-detail");
      setNotice("");
      recordActionCompleted("client_ad_detail_open", "marketplace-detail", startedAt);
    } catch (error) {
      if (adDetailRequestIdRef.current !== requestId) {
        return;
      }
      setSelectedAd(null);
      if (error instanceof ApiClientError && error.code === "AD_NOT_AVAILABLE") {
        setSearchResults((current) => current.filter((ad) => ad.id !== adId));
      }
      setNotice(error instanceof ApiClientError && error.code === "AD_NOT_AVAILABLE" ? "Ese negocio ya no esta disponible para nuevas solicitudes. Elige otra oferta activa." : error instanceof Error ? error.message : "Anuncio no disponible.");
      recordActionFailed("client_ad_detail_open", "marketplace-detail", startedAt, error instanceof Error ? error.name : undefined);
    } finally {
      if (!optimisticAd && adDetailRequestIdRef.current === requestId) {
        setOpeningMarketplaceAdId(null);
      }
    }
  }

  async function prefetchActiveMarketplace(sort: "trust" | "rate" | "speed" = "rate") {
    const params = {
      payment_method: searchForm.payment_method,
      sort,
      limit: CLIENT_MARKETPLACE_PAGE_SIZE
    };
    const key = marketplaceSearchKey(params);
    const cached = cacheRef.current[key];
    if (cached && Date.now() - cached.loadedAt < CLIENT_MARKETPLACE_CACHE_TTL_MS) {
      return;
    }
    try {
      const data = await searchMarketplaceAds<MarketplaceSearchPage>(request, params);
      cacheRef.current[key] = { items: data.items, nextCursor: data.next_cursor, loadedAt: Date.now() };
    } catch {
      // Background warmup should never interrupt the active screen.
    }
  }

  return {
    selectMarketplacePaymentMethod,
    searchAds,
    searchFreshForAmount,
    loadActiveMarketplace,
    loadMoreActiveMarketplace,
    openAdDetail,
    prefetchActiveMarketplace
  };
}
