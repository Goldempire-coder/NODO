"use client";

import { useRef } from "react";
import { getMarketplaceAd, marketplaceSearchKey, searchMarketplaceAds } from "../../api/ads";
import { ApiClientError, type AuthenticatedRequest } from "../../api/client";
import type { PublicUser } from "../../types/auth";
import { actionStartedAt, recordActionCompleted, recordActionFailed, recordActionStarted } from "../actionTelemetry";
import type { ClientWorkspaceState } from "./useClientWorkspaceState";

const CLIENT_MARKETPLACE_CACHE_TTL_MS = 30_000;

export function useClientMarketplaceModel(state: ClientWorkspaceState & { request: AuthenticatedRequest; user: PublicUser }) {
  const {
    request,
    searchForm,
    searchResults,
    setLoadingMarketplace,
    setOpeningMarketplaceAdId,
    setSearchingMarketplace,
    setSearchResults,
    setSelectedAd,
    setNotice,
    setView
  } = state;
  const cacheRef = useRef<Record<string, { items: typeof searchResults; loadedAt: number }>>({});

  async function searchAds() {
    const startedAt = actionStartedAt();
    recordActionStarted("client_marketplace_search", "marketplace-search");
    setSearchingMarketplace(true);
    setView("marketplace-search");
    setNotice("");
    const params = {
      amount_usd: searchForm.amount_usd,
      payment_method: searchForm.payment_method,
      delivery_method: searchForm.delivery_method,
      sort: searchForm.sort
    };
    const key = marketplaceSearchKey(params);
    const cached = cacheRef.current[key];
    if (cached && Date.now() - cached.loadedAt < CLIENT_MARKETPLACE_CACHE_TTL_MS) {
      setSearchResults(cached.items);
      setSelectedAd(null);
    }
    try {
      const data = await searchMarketplaceAds<{ items: typeof searchResults }>(request, params);
      cacheRef.current[key] = { items: data.items, loadedAt: Date.now() };
      setSearchResults(data.items);
      setSelectedAd(null);
      setNotice(data.items.length ? "" : "No encontramos negocios para ese monto. Prueba otro monto o metodo.");
      recordActionCompleted("client_marketplace_search", "marketplace-search", startedAt);
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "No logramos buscar negocios en este momento.");
      recordActionFailed("client_marketplace_search", "marketplace-search", startedAt, error instanceof Error ? error.name : undefined);
    } finally {
      setSearchingMarketplace(false);
    }
  }

  async function loadActiveMarketplace(sort: "trust" | "rate" | "speed" = searchForm.sort) {
    const startedAt = actionStartedAt();
    recordActionStarted("client_marketplace_list", "marketplace-list");
    setView("marketplace-list");
    setNotice("");
    const params = { sort, limit: "50" };
    const key = marketplaceSearchKey(params);
    const cached = cacheRef.current[key];
    if (cached && Date.now() - cached.loadedAt < CLIENT_MARKETPLACE_CACHE_TTL_MS) {
      setSearchResults(cached.items);
      setSelectedAd(null);
      setLoadingMarketplace(false);
    }
    if (cached) {
      setSearchResults(cached.items);
      setSelectedAd(null);
      setLoadingMarketplace(false);
    } else {
      setLoadingMarketplace(true);
    }
    try {
      const data = await searchMarketplaceAds<{ items: typeof searchResults }>(request, params);
      cacheRef.current[key] = { items: data.items, loadedAt: Date.now() };
      setSearchResults(data.items);
      setSelectedAd(null);
      setNotice(data.items.length ? "" : "No hay negocios activos disponibles en este momento.");
      recordActionCompleted("client_marketplace_list", "marketplace-list", startedAt);
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "No logramos cargar los negocios en este momento.");
      recordActionFailed("client_marketplace_list", "marketplace-list", startedAt, error instanceof Error ? error.name : undefined);
    } finally {
      setLoadingMarketplace(false);
    }
  }

  async function openAdDetail(adId: string) {
    const startedAt = actionStartedAt();
    recordActionStarted("client_ad_detail_open", "marketplace-detail");
    const optimisticAd = searchResults.find((ad) => ad.id === adId);
    if (optimisticAd) {
      setSelectedAd(optimisticAd);
      setView("marketplace-detail");
      setNotice("");
    }
    if (!optimisticAd) {
      setOpeningMarketplaceAdId(adId);
    }
    try {
      const data = await getMarketplaceAd<{ ad: NonNullable<typeof optimisticAd> }>(request, adId);
      setSelectedAd(data.ad);
      setView("marketplace-detail");
      setNotice("");
      recordActionCompleted("client_ad_detail_open", "marketplace-detail", startedAt);
    } catch (error) {
      setSelectedAd(null);
      if (error instanceof ApiClientError && error.code === "AD_NOT_AVAILABLE") {
        setSearchResults((current) => current.filter((ad) => ad.id !== adId));
      }
      setNotice(error instanceof ApiClientError && error.code === "AD_NOT_AVAILABLE" ? "Ese negocio ya no esta recibiendo ofertas. Elige otro negocio online." : error instanceof Error ? error.message : "Anuncio no disponible.");
      recordActionFailed("client_ad_detail_open", "marketplace-detail", startedAt, error instanceof Error ? error.name : undefined);
    } finally {
      if (!optimisticAd) {
        setOpeningMarketplaceAdId(null);
      }
    }
  }

  async function prefetchActiveMarketplace(sort: "trust" | "rate" | "speed" = "trust") {
    const key = marketplaceSearchKey({ sort, limit: "50" });
    const cached = cacheRef.current[key];
    if (cached && Date.now() - cached.loadedAt < CLIENT_MARKETPLACE_CACHE_TTL_MS) {
      return;
    }
    try {
      const data = await searchMarketplaceAds<{ items: typeof searchResults }>(request, { sort, limit: "50" });
      cacheRef.current[key] = { items: data.items, loadedAt: Date.now() };
    } catch {
      // Background warmup should never interrupt the active screen.
    }
  }

  return { searchAds, loadActiveMarketplace, openAdDetail, prefetchActiveMarketplace };
}
