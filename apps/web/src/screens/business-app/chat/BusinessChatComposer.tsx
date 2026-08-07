import { useRef } from "react";
import { PaperclipIcon, SendIcon } from "../../../components/nodo/ChatComposerIcons";

export function BusinessChatComposer({
  chatBody,
  canSendMessage,
  sendingChatMessage,
  uploadingChatAttachment,
  hasAttachments,
  setChatBody,
  sendChatMessage,
  uploadChatAttachment
}: {
  chatBody: string;
  canSendMessage: boolean;
  sendingChatMessage: boolean;
  uploadingChatAttachment: boolean;
  hasAttachments: boolean;
  setChatBody: (body: string) => void;
  sendChatMessage: () => Promise<void>;
  uploadChatAttachment: (file: File | null) => Promise<void>;
}) {
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const canSend = canSendMessage && !sendingChatMessage && !uploadingChatAttachment;
  const canSubmitMessage = canSend && (chatBody.trim().length > 0 || hasAttachments);

  return (
    <form
      className="business-order-chat-composer"
      onSubmit={(event) => {
        event.preventDefault();
        void sendChatMessage();
      }}
    >
      <button
        className="business-support-clip"
        type="button"
        aria-label="Adjuntar comprobante o soporte"
        disabled={!canSendMessage || uploadingChatAttachment || sendingChatMessage}
        onClick={() => fileInputRef.current?.click()}
      >
        <PaperclipIcon />
      </button>
      <textarea
        className="business-order-chat-composer__input"
        aria-label="Mensaje para cliente"
        disabled={!canSendMessage || sendingChatMessage}
        maxLength={2000}
        placeholder={uploadingChatAttachment ? "Subiendo adjunto..." : "Escribir mensaje..."}
        rows={1}
        value={chatBody}
        onChange={(event) => setChatBody(event.target.value)}
      />
      <input
        ref={fileInputRef}
        className="business-support-file-input"
        accept="image/jpeg,image/png,image/webp"
        disabled={!canSendMessage || uploadingChatAttachment || sendingChatMessage}
        type="file"
        onChange={(event) => {
          const file = event.currentTarget.files?.[0] || null;
          event.currentTarget.value = "";
          void uploadChatAttachment(file);
        }}
      />
      <button className="business-support-send" type="submit" aria-label="Enviar" disabled={!canSubmitMessage}>
        {sendingChatMessage ? "..." : <SendIcon />}
      </button>
    </form>
  );
}
