"use client";

import { useCallback, useRef, useState } from "react";
import { releaseAdminBusinessPublicationHold } from "../../api/support";
import type { AdminBusinessPublicationHold, AdminSupportTicket } from "../../types/admin";
import { useStableIdempotencyKeys } from "../useStableIdempotencyKeys";
import type { RequestFn } from "./adminWebTypes";

type QueueCriticalAction = (
  title: string,
  detail: string,
  run: () => Promise<void>,
  options?: { requiresReason?: boolean }
) => void;

type PublicationHoldReleaseDraft = {
  ticketId: string | null;
  reason: string;
  error: string;
};

export function useAdminPublicationHoldModel({
  adminMutable,
  applyReleasedHold,
  queueCriticalAction,
  refreshTicket,
  request,
  selectedTicket
}: {
  adminMutable: boolean;
  applyReleasedHold: (ticketId: string, hold: AdminBusinessPublicationHold) => void;
  queueCriticalAction: QueueCriticalAction;
  refreshTicket: (ticketId: string) => Promise<void>;
  request: RequestFn;
  selectedTicket: AdminSupportTicket | null;
}) {
  const [releaseDraft, setReleaseDraft] = useState<PublicationHoldReleaseDraft>({
    ticketId: null,
    reason: "",
    error: ""
  });
  const [releasingPublicationHoldId, setReleasingPublicationHoldId] = useState<string | null>(null);
  const publicationHoldReleaseInFlight = useRef(false);
  const activeTicketIdRef = useRef<string | null>(selectedTicket?.id ?? null);
  const { clearIdempotencyKey, getIdempotencyKey } = useStableIdempotencyKeys();
  const selectedTicketId = selectedTicket?.id ?? null;
  const publicationHoldReleaseReason = releaseDraft.ticketId === selectedTicketId ? releaseDraft.reason : "";
  const publicationHoldReleaseError = releaseDraft.ticketId === selectedTicketId ? releaseDraft.error : "";

  activeTicketIdRef.current = selectedTicketId;

  const setPublicationHoldReleaseReason = useCallback((value: string) => {
    setReleaseDraft({ ticketId: selectedTicketId, reason: value, error: "" });
  }, [selectedTicketId]);

  const requestPublicationHoldRelease = useCallback(() => {
    const ticket = selectedTicket;
    const hold = ticket?.publication_hold;
    const reason = publicationHoldReleaseReason.trim();

    if (!adminMutable || !ticket || !hold || hold.status !== "active") {
      setReleaseDraft({
        ticketId: ticket?.id ?? null,
        reason: publicationHoldReleaseReason,
        error: "Este hold ya no esta disponible para liberacion."
      });
      return;
    }
    if (!reason) {
      setReleaseDraft({
        ticketId: ticket.id,
        reason: publicationHoldReleaseReason,
        error: "Escribe una razon para liberar la publicacion."
      });
      return;
    }

    const ticketId = ticket.id;
    const holdId = hold.id;
    const idempotencyScope = `admin_publication_hold_release:${holdId}`;

    queueCriticalAction(
      "Liberar publicacion",
      `Ticket ${ticketId}. Negocio ${hold.business_id}. El negocio podra volver a publicar si no tiene otro bloqueo activo.`,
      async () => {
        if (publicationHoldReleaseInFlight.current) {
          return;
        }
        publicationHoldReleaseInFlight.current = true;
        setReleasingPublicationHoldId(holdId);
        if (activeTicketIdRef.current === ticketId) {
          setReleaseDraft({ ticketId, reason, error: "" });
        }
        try {
          let releaseResult;
          try {
            releaseResult = await releaseAdminBusinessPublicationHold(
              request,
              holdId,
              reason,
              getIdempotencyKey(idempotencyScope, { holdId, reason })
            );
          } catch (error) {
            if (activeTicketIdRef.current === ticketId) {
              setReleaseDraft({
                ticketId,
                reason,
                error: error instanceof Error
                  ? error.message
                  : "No pudimos liberar la publicacion. Intenta nuevamente."
              });
            }
            return;
          }

          clearIdempotencyKey(idempotencyScope);
          applyReleasedHold(ticketId, releaseResult.hold);
          if (activeTicketIdRef.current === ticketId) {
            setReleaseDraft({ ticketId, reason: "", error: "" });
          }

          try {
            await refreshTicket(ticketId);
          } catch {
            if (activeTicketIdRef.current === ticketId) {
              setReleaseDraft({
                ticketId,
                reason: "",
                error: "Hold liberado. No pudimos refrescar el ticket; usa Actualizar."
              });
            }
          }
        } finally {
          publicationHoldReleaseInFlight.current = false;
          setReleasingPublicationHoldId(null);
        }
      },
      { requiresReason: false }
    );
  }, [
    adminMutable,
    applyReleasedHold,
    clearIdempotencyKey,
    getIdempotencyKey,
    publicationHoldReleaseReason,
    queueCriticalAction,
    refreshTicket,
    request,
    selectedTicket
  ]);

  return {
    publicationHoldReleaseError,
    publicationHoldReleaseReason,
    releasingPublicationHoldId,
    requestPublicationHoldRelease,
    setPublicationHoldReleaseReason
  };
}
