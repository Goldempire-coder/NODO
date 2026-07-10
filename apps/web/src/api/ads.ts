import type { AuthenticatedRequest } from "./client";

export type MarketplaceSearchParams = {
  amount_usd?: string;
  payment_method?: string;
  delivery_method?: string;
  sort?: string;
  limit?: string;
};

export function marketplaceSearchKey(params: MarketplaceSearchParams) {
  return new URLSearchParams(
    Object.entries(params).filter((entry): entry is [string, string] => Boolean(entry[1]))
  ).toString();
}

export function searchMarketplaceAds<T>(request: AuthenticatedRequest, params: MarketplaceSearchParams) {
  return request<T>(`/api/v1/ads/search?${marketplaceSearchKey(params)}`);
}

export function getMarketplaceAd<T>(request: AuthenticatedRequest, adId: string) {
  return request<T>(`/api/v1/ads/${adId}`);
}
