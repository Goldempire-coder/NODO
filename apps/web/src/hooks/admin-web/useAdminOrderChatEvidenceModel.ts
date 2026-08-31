import { useCallback, useRef, useState } from "react";
import { getAdminOrderChatEvidence } from "../../api/admin";
import { ApiClientError, type AuthenticatedRequest } from "../../api/client";
import type { AdminOrderChatEvidence, AdminOrderChatEvidenceMessage } from "../../types/admin";
import { actionStartedAt, recordActionCompleted, recordActionFailed, recordActionStarted } from "../actionTelemetry";

function mergeMessages(current: AdminOrderChatEvidenceMessage[], incoming: AdminOrderChatEvidenceMessage[]) {
  const merged = new Map(current.map((message) => [message.message_id, message]));
  for (const message of incoming) {
    merged.set(message.message_id, message);
  }
  return Array.from(merged.values()).sort((left, right) => left.created_at.localeCompare(right.created_at));
}

export function useAdminOrderChatEvidenceModel({
  request
}: {
  request: AuthenticatedRequest;
}) {
  const [evidence, setEvidence] = useState<AdminOrderChatEvidence | null>(null);
  const [requested, setRequested] = useState(false);
  const [loading, setLoading] = useState(false);
  const [loadingMore, setLoadingMore] = useState<"older" | "newer" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const currentRequest = useRef(0);
  const activeOrder = useRef<{ orderId: string; highlightMessageId?: string } | null>(null);
  const initialLoadInFlight = useRef(false);

  const prepareOrderChatEvidence = useCallback((orderId: string, highlightMessageId?: string) => {
    currentRequest.current += 1;
    activeOrder.current = { orderId, highlightMessageId };
    initialLoadInFlight.current = false;
    setEvidence(null);
    setRequested(false);
    setLoading(false);
    setLoadingMore(null);
    setError(null);
  }, []);

  const loadOrderChatEvidence = useCallback(async (orderId: string, highlightMessageId?: string) => {
    if (initialLoadInFlight.current && activeOrder.current?.orderId === orderId) {
      return;
    }
    const orderChanged = activeOrder.current?.orderId !== orderId;
    const requestSequence = currentRequest.current + 1;
    currentRequest.current = requestSequence;
    activeOrder.current = { orderId, highlightMessageId };
    initialLoadInFlight.current = true;
    if (orderChanged) {
      setEvidence(null);
    }
    setRequested(true);
    setLoadingMore(null);
    setLoading(true);
    setError(null);
    const startedAt = actionStartedAt();
    recordActionStarted("admin_order_chat_evidence_load", "order-detail");
    try {
      const payload = await getAdminOrderChatEvidence<AdminOrderChatEvidence>(request, orderId, { highlightMessageId });
      if (currentRequest.current !== requestSequence) {
        return;
      }
      setEvidence(payload);
      recordActionCompleted("admin_order_chat_evidence_load", "order-detail", startedAt);
    } catch (loadError) {
      if (currentRequest.current !== requestSequence) {
        return;
      }
      const errorCode = loadError instanceof ApiClientError ? loadError.code : undefined;
      setError(loadError instanceof Error ? loadError.message : "No pudimos cargar la conversacion.");
      recordActionFailed("admin_order_chat_evidence_load", "order-detail", startedAt, errorCode);
    } finally {
      if (currentRequest.current === requestSequence) {
        initialLoadInFlight.current = false;
        setLoading(false);
      }
    }
  }, [request]);

  const loadPage = useCallback(async (direction: "older" | "newer") => {
    const active = activeOrder.current;
    const cursor = direction === "older" ? evidence?.older_cursor : evidence?.newer_cursor;
    if (!active || !cursor || loadingMore) {
      return;
    }
    const requestSequence = currentRequest.current;
    setLoadingMore(direction);
    setError(null);
    try {
      const page = await getAdminOrderChatEvidence<AdminOrderChatEvidence>(request, active.orderId, { cursor, direction });
      if (currentRequest.current !== requestSequence || activeOrder.current?.orderId !== active.orderId) {
        return;
      }
      setEvidence((current) => current?.order_id === active.orderId ? {
        ...current,
        items: mergeMessages(current.items, page.items),
        older_cursor: direction === "older" ? page.older_cursor : current.older_cursor,
        newer_cursor: direction === "newer" ? page.newer_cursor : current.newer_cursor
      } : current);
    } catch (loadError) {
      if (currentRequest.current === requestSequence && activeOrder.current?.orderId === active.orderId) {
        setError(loadError instanceof Error ? loadError.message : "No pudimos cargar mas mensajes.");
      }
    } finally {
      if (currentRequest.current === requestSequence && activeOrder.current?.orderId === active.orderId) {
        setLoadingMore(null);
      }
    }
  }, [evidence?.newer_cursor, evidence?.older_cursor, loadingMore, request]);

  const retryOrderChatEvidence = useCallback(async () => {
    const active = activeOrder.current;
    if (active) {
      await loadOrderChatEvidence(active.orderId, active.highlightMessageId);
    }
  }, [loadOrderChatEvidence]);

  const showOrderChatEvidence = useCallback(async () => {
    const active = activeOrder.current;
    if (!active) {
      setError("Selecciona una orden antes de cargar la conversacion.");
      return;
    }
    await loadOrderChatEvidence(active.orderId, active.highlightMessageId);
  }, [loadOrderChatEvidence]);

  return {
    evidence,
    error,
    loading,
    loadingMore,
    orderChatEvidenceRequested: requested,
    loadNewerOrderChatEvidence: () => loadPage("newer"),
    loadOlderOrderChatEvidence: () => loadPage("older"),
    loadOrderChatEvidence,
    prepareOrderChatEvidence,
    showOrderChatEvidence,
    retryOrderChatEvidence
  };
}
