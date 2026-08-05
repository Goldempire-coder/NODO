import { useCallback, useRef, useState } from "react";
import { shareConfiguredPaymentDetails as shareConfiguredPaymentDetailsRequest } from "../../../api/chat";
import type { AuthenticatedRequest } from "../../../api/client";
import { revealOrderReceiverDetails } from "../../../api/orders";
import type { ChatCapabilities } from "../../../types/chat";
import type { ReceiverDetails } from "../../../types/orders";
import { useStableIdempotencyKeys } from "../../useStableIdempotencyKeys";
import type { BusinessChatSessionScope } from "./businessChatShared";

export function useBusinessPaymentShareActions({
  request,
  session,
  chatCapabilities,
  setNotice
}: {
  request: AuthenticatedRequest;
  session: BusinessChatSessionScope;
  chatCapabilities: ChatCapabilities;
  setNotice: (notice: string) => void;
}) {
  const [sharingPaymentDetails, setSharingPaymentDetails] = useState(false);
  const [revealingReceiverDetails, setRevealingReceiverDetails] = useState(false);
  const [receiverDetailsState, setReceiverDetailsState] = useState<{
    orderId: string;
    value: ReceiverDetails;
  } | null>(null);
  const sharingPaymentDetailsRef = useRef(new Set<string>());
  const revealingReceiverDetailsRef = useRef(new Set<string>());
  const { clearIdempotencyKey, getIdempotencyKey } = useStableIdempotencyKeys();

  const receiverDetails = receiverDetailsState?.orderId === session.chatOrderId
    ? receiverDetailsState.value
    : null;

  const activateOrder = useCallback((orderId: string) => {
    setSharingPaymentDetails(sharingPaymentDetailsRef.current.has(orderId));
    setRevealingReceiverDetails(revealingReceiverDetailsRef.current.has(orderId));
    setReceiverDetailsState(null);
  }, []);

  const shareConfiguredPaymentDetails = useCallback(async () => {
    const targetOrderId = session.chatOrderIdRef.current;
    const targetSessionEpoch = session.chatSessionEpochRef.current;
    if (
      !targetOrderId
      || sharingPaymentDetailsRef.current.has(targetOrderId)
      || session.chatCapabilitiesOrderIdRef.current !== targetOrderId
      || !chatCapabilities.can_share_payment_details
    ) {
      return;
    }
    sharingPaymentDetailsRef.current.add(targetOrderId);
    setSharingPaymentDetails(true);
    const idempotencyScope = `share_payment_details_${targetOrderId}`;
    try {
      await shareConfiguredPaymentDetailsRequest(
        request,
        targetOrderId,
        getIdempotencyKey(idempotencyScope, { orderId: targetOrderId })
      );
      clearIdempotencyKey(idempotencyScope);
      if (session.isCurrentChatSession(targetOrderId, targetSessionEpoch)) {
        await session.refreshChatSession(targetOrderId, targetSessionEpoch, { silent: true });
      }
      if (session.isCurrentChatSession(targetOrderId, targetSessionEpoch)) {
        setNotice("Datos de pago compartidos en el chat.");
      }
    } catch (error) {
      if (session.isCurrentChatSession(targetOrderId, targetSessionEpoch)) {
        setNotice(error instanceof Error ? error.message : "No pudimos compartir los datos de pago.");
      }
    } finally {
      sharingPaymentDetailsRef.current.delete(targetOrderId);
      if (session.chatOrderIdRef.current === targetOrderId) {
        setSharingPaymentDetails(false);
      }
    }
  }, [
    chatCapabilities.can_share_payment_details,
    clearIdempotencyKey,
    getIdempotencyKey,
    request,
    session,
    setNotice
  ]);

  const revealReceiverDetails = useCallback(async () => {
    const targetOrderId = session.chatOrderIdRef.current;
    const targetSessionEpoch = session.chatSessionEpochRef.current;
    if (
      !targetOrderId
      || revealingReceiverDetailsRef.current.has(targetOrderId)
      || session.chatCapabilitiesOrderIdRef.current !== targetOrderId
      || !chatCapabilities.can_reveal_receiver_details
    ) {
      return;
    }
    revealingReceiverDetailsRef.current.add(targetOrderId);
    setRevealingReceiverDetails(true);
    try {
      const data = await revealOrderReceiverDetails<ReceiverDetails>(request, targetOrderId);
      if (!session.isCurrentChatSession(targetOrderId, targetSessionEpoch)) {
        return;
      }
      setReceiverDetailsState({ orderId: targetOrderId, value: data });
      setNotice("Pago Movil revelado para esta orden.");
    } catch (error) {
      if (session.isCurrentChatSession(targetOrderId, targetSessionEpoch)) {
        setNotice(error instanceof Error ? error.message : "No pudimos revelar el Pago Movil.");
      }
    } finally {
      revealingReceiverDetailsRef.current.delete(targetOrderId);
      if (session.chatOrderIdRef.current === targetOrderId) {
        setRevealingReceiverDetails(false);
      }
    }
  }, [chatCapabilities.can_reveal_receiver_details, request, session, setNotice]);

  return {
    activateOrder,
    receiverDetails,
    revealReceiverDetails,
    revealingReceiverDetails,
    shareConfiguredPaymentDetails,
    sharingPaymentDetails
  };
}
