import { useEffect, useRef } from "react";
import { useBusinessChatPolling } from "../../hooks/business-mini-app/chat/useBusinessChatPolling";
import type { BusinessMiniAppModel } from "../../hooks/useBusinessMiniAppModel";
import { BusinessChatActionDock } from "./chat/BusinessChatActionDock";
import { BusinessChatComposer } from "./chat/BusinessChatComposer";
import { BusinessChatMessageList } from "./chat/BusinessChatMessageList";

function orderLabel(model: BusinessMiniAppModel): string {
  if (model.chatOrder?.id === model.chatOrderId && model.chatOrder.public_order_code) {
    return `Orden ${model.chatOrder.public_order_code}`;
  }
  const order = model.businessOrderDetail?.order;
  if (order?.id === model.chatOrderId && order.public_order_code) {
    return `Orden ${order.public_order_code}`;
  }
  return "Orden en curso";
}

export function BusinessChatScreen({ model }: { model: BusinessMiniAppModel }) {
  const {
    chatAttachments,
    chatAttachmentLink,
    chatBody,
    chatCapabilities,
    chatMessages,
    chatOrder,
    chatOrderId,
    chatRefreshError,
    businessChatAction,
    confirmBusinessPaymentInChat,
    dismissChatAttachmentLink,
    openChatAttachment,
    refreshChat,
    receiverDetails,
    revealReceiverDetails,
    revealingReceiverDetails,
    markBusinessDeliveredInChat,
    sendChatMessage,
    sendingChatMessage,
    shareConfiguredPaymentDetails,
    sharingPaymentDetails,
    setChatBody,
    uploadingChatAttachment,
    uploadChatAttachment
  } = model;
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const detailOrder = model.businessOrderDetail?.order;
  const currentOrder = chatOrder?.id === chatOrderId
    ? chatOrder
    : detailOrder?.id === chatOrderId
      ? detailOrder
      : null;
  const chatIsTerminal = currentOrder?.status === "cancelled" || currentOrder?.status === "completed";
  const canSharePaymentDetails = chatCapabilities.can_share_payment_details && currentOrder?.status === "waiting_payment";
  const canConfirmPayment = chatCapabilities.can_confirm_payment && currentOrder?.status === "payment_reported";
  const canMarkDelivered = chatCapabilities.can_mark_delivered && currentOrder?.status === "payment_confirmed";
  const hasActionDock = canSharePaymentDetails || canConfirmPayment || canMarkDelivered;

  useBusinessChatPolling({
    chatOrderId,
    isChatView: model.view === "business-chat",
    sendingChatMessage,
    uploadingChatAttachment,
    refreshChat
  });

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ block: "end" });
  }, [chatOrderId, chatMessages.length, chatAttachments.length]);

  return (
    <section className={hasActionDock ? "business-order-chat business-order-chat--has-actions" : "business-order-chat"} aria-label="Chat con cliente">
      <BusinessChatMessageList
        orderLabel={orderLabel(model)}
        currentOrder={currentOrder}
        chatMessages={chatMessages}
        chatCapabilities={chatCapabilities}
        receiverDetails={receiverDetails}
        revealingReceiverDetails={revealingReceiverDetails}
        chatAttachmentLink={chatAttachmentLink}
        attachmentCount={chatAttachments.length}
        uploadingChatAttachment={uploadingChatAttachment}
        chatRefreshError={chatRefreshError}
        notice={model.notice}
        messagesEndRef={messagesEndRef}
        openChatAttachment={openChatAttachment}
        revealReceiverDetails={revealReceiverDetails}
        dismissChatAttachmentLink={dismissChatAttachmentLink}
        refreshChat={refreshChat}
      />

      <BusinessChatActionDock
        currentOrder={currentOrder}
        canSharePaymentDetails={canSharePaymentDetails}
        canConfirmPayment={canConfirmPayment}
        canMarkDelivered={canMarkDelivered}
        businessChatAction={businessChatAction}
        sharingPaymentDetails={sharingPaymentDetails}
        shareConfiguredPaymentDetails={shareConfiguredPaymentDetails}
        confirmBusinessPaymentInChat={confirmBusinessPaymentInChat}
        markBusinessDeliveredInChat={markBusinessDeliveredInChat}
      />

      {!chatIsTerminal ? (
        <BusinessChatComposer
          chatBody={chatBody}
          canSendMessage={chatCapabilities.can_send_message}
          sendingChatMessage={sendingChatMessage}
          uploadingChatAttachment={uploadingChatAttachment}
          hasAttachments={chatAttachments.length > 0}
          setChatBody={setChatBody}
          sendChatMessage={sendChatMessage}
          uploadChatAttachment={uploadChatAttachment}
        />
      ) : null}
    </section>
  );
}
