"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { AuthenticatedRequest } from "../api/client";
import { acknowledgeSurfaceAttention, getSurfaceAttentionSummary } from "../api/notifications";
import type {
  AttentionKind,
  SurfaceAttentionCounts,
  SurfaceAttentionItem,
  SurfaceAttentionTruncated
} from "../types/notifications";

export const ATTENTION_REFRESH_INTERVAL_MS = 30_000;

function newestItem(items: SurfaceAttentionItem[]): SurfaceAttentionItem | null {
  return [...items].sort((left, right) => right.occurred_at.localeCompare(left.occurred_at))[0] || null;
}

export function useSurfaceAttentionModel({
  enabled,
  request
}: {
  enabled: boolean;
  request: AuthenticatedRequest;
}) {
  const [items, setItems] = useState<SurfaceAttentionItem[]>([]);
  const [attentionAlert, setAttentionAlert] = useState<SurfaceAttentionItem | null>(null);
  const [attentionStale, setAttentionStale] = useState(false);
  const [attentionTruncated, setAttentionTruncated] = useState<SurfaceAttentionTruncated>({
    orders: false,
    support: false
  });
  const [acknowledgedVersion, setAcknowledgedVersion] = useState(0);
  const itemsRef = useRef<SurfaceAttentionItem[]>([]);
  const previousSignaturesRef = useRef<Set<string> | null>(null);
  const acknowledgedSignaturesRef = useRef(new Set<string>());
  const refreshInFlightRef = useRef(false);

  const refreshAttention = useCallback(async () => {
    if (refreshInFlightRef.current) {
      return;
    }
    refreshInFlightRef.current = true;
    try {
      const summary = await getSurfaceAttentionSummary(request);
      const nextItems = summary.items;
      const nextSignatures = new Set(nextItems.map((item) => item.signature));
      const previousSignatures = previousSignaturesRef.current;
      const alertCandidates = nextItems.filter(
        (item) => (
          !acknowledgedSignaturesRef.current.has(item.signature)
          && (previousSignatures === null || !previousSignatures.has(item.signature))
        )
      );
      const nextAlert = newestItem(alertCandidates);
      setAttentionAlert((current) => {
        if (nextAlert) {
          return nextAlert;
        }
        return current && nextSignatures.has(current.signature) ? current : null;
      });
      previousSignaturesRef.current = nextSignatures;
      for (const signature of acknowledgedSignaturesRef.current) {
        if (!nextSignatures.has(signature)) {
          acknowledgedSignaturesRef.current.delete(signature);
        }
      }
      itemsRef.current = nextItems;
      setItems(nextItems);
      setAttentionTruncated(summary.truncated);
      setAttentionStale(false);
    } catch {
      setAttentionStale(true);
    } finally {
      refreshInFlightRef.current = false;
    }
  }, [request]);

  useEffect(() => {
    if (!enabled || typeof document === "undefined") {
      return;
    }
    const refreshIfVisible = () => {
      if (document.visibilityState !== "visible") {
        return;
      }
      void refreshAttention();
    };
    refreshIfVisible();
    const interval = window.setInterval(refreshIfVisible, ATTENTION_REFRESH_INTERVAL_MS);
    document.addEventListener("visibilitychange", refreshIfVisible);
    return () => {
      window.clearInterval(interval);
      document.removeEventListener("visibilitychange", refreshIfVisible);
    };
  }, [enabled, refreshAttention]);

  const pendingItems = useMemo(
    () => items.filter(
      (item) => !acknowledgedSignaturesRef.current.has(item.signature)
    ),
    [acknowledgedVersion, items]
  );

  const attentionCounts = useMemo<SurfaceAttentionCounts>(
    () => ({
      orders: pendingItems.filter((item) => item.kind === "order").length,
      support: pendingItems.filter((item) => item.kind === "support").length,
      total: pendingItems.length
    }),
    [pendingItems]
  );

  const acknowledgeAttention = useCallback(async (kind: AttentionKind, resourceId: string) => {
    const item = itemsRef.current.find(
      (candidate) => candidate.kind === kind && candidate.resource_id === resourceId
    );
    if (!item) {
      return false;
    }
    try {
      const result = await acknowledgeSurfaceAttention(request, {
        kind,
        resource_id: resourceId,
        signature: item.signature
      });
      if (!result.acknowledged) {
        return false;
      }
    } catch {
      return false;
    }
    acknowledgedSignaturesRef.current.add(item.signature);
    setAcknowledgedVersion((current) => current + 1);
    setAttentionAlert((current) => (
      current?.kind === kind && current.resource_id === resourceId ? null : current
    ));
    return true;
  }, [request]);

  const dismissAttention = useCallback(() => {
    setAttentionAlert(null);
  }, []);

  return {
    acknowledgeAttention,
    attentionAlert,
    attentionCounts,
    attentionItems: pendingItems,
    attentionStale,
    attentionTruncated,
    dismissAttention,
    refreshAttention
  };
}
