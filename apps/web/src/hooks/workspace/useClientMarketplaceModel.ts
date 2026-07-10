"use client";

import { useRef } from "react";
import { getMarketplaceAd, marketplaceSearchKey, searchMarketplaceAds } from "../../api/ads";
import type { AuthenticatedRequest } from "../../api/client";
import type { PublicUser } from "../../types/auth";
import type { ClientWorkspaceState } from "./useClientWorkspaceState";

export function useClientMarketplaceModel(state: ClientWorkspaceState & { request: AuthenticatedRequest; user: PublicUser }) {
  const { request, searchForm, searchResults, setSearchResults, setSelectedAd, setNotice, setBusy, setView } = state;
  const cacheRef = useRef<Record<string, { items: typeof searchResults; loadedAt: number }>>({});

  async function searchAds() {
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
    if (cached && Date.now() - cached.loadedAt < 30_000) {
      setSearchResults(cached.items);
      setSelectedAd(null);
    }
    try {
      const data = await searchMarketplaceAds<{ items: typeof searchResults }>(request, params);
      cacheRef.current[key] = { items: data.items, loadedAt: Date.now() };
      setSearchResults(data.items);
      setSelectedAd(null);
      setNotice(data.items.length ? "" : "No encontramos negocios para ese monto. Prueba otro monto o metodo.");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "No logramos buscar negocios en este momento.");
    }
  }

  async function loadActiveMarketplace(sort: "trust" | "rate" | "speed" = searchForm.sort) {
    setView("marketplace-list");
    setNotice("");
    const params = { sort, limit: "50" };
    const key = marketplaceSearchKey(params);
    const cached = cacheRef.current[key];
    if (cached && Date.now() - cached.loadedAt < 30_000) {
      setSearchResults(cached.items);
      setSelectedAd(null);
    }
    try {
      const data = await searchMarketplaceAds<{ items: typeof searchResults }>(request, params);
      cacheRef.current[key] = { items: data.items, loadedAt: Date.now() };
      setSearchResults(data.items);
      setSelectedAd(null);
      setNotice(data.items.length ? "" : "No hay negocios activos disponibles en este momento.");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "No logramos cargar los negocios en este momento.");
    }
  }

  async function openAdDetail(adId: string) {
    const optimisticAd = searchResults.find((ad) => ad.id === adId);
    if (optimisticAd) {
      setSelectedAd(optimisticAd);
      setView("marketplace-detail");
      setNotice("");
    }
    if (!optimisticAd) {
      setBusy(true);
    }
    try {
      const data = await getMarketplaceAd<{ ad: NonNullable<typeof optimisticAd> }>(request, adId);
      setSelectedAd(data.ad);
      setView("marketplace-detail");
      setNotice("");
    } catch (error) {
      if (!optimisticAd) {
        setSelectedAd(null);
      }
      setNotice(error instanceof Error ? error.message : "Anuncio no disponible.");
    } finally {
      if (!optimisticAd) {
        setBusy(false);
      }
    }
  }

  async function prefetchActiveMarketplace(sort: "trust" | "rate" | "speed" = "trust") {
    const key = marketplaceSearchKey({ sort, limit: "50" });
    const cached = cacheRef.current[key];
    if (cached && Date.now() - cached.loadedAt < 30_000) {
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
