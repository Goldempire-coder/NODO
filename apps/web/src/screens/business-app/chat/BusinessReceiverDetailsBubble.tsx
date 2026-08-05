import { useState } from "react";
import type { ReceiverDetails } from "../../../types/orders";

async function copyText(value: string) {
  if (navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(value);
    return;
  }
  const textarea = document.createElement("textarea");
  textarea.value = value;
  textarea.setAttribute("readonly", "true");
  textarea.style.position = "fixed";
  textarea.style.left = "-9999px";
  document.body.appendChild(textarea);
  textarea.select();
  try {
    if (!document.execCommand("copy")) {
      throw new Error("CLIPBOARD_COPY_FAILED");
    }
  } finally {
    document.body.removeChild(textarea);
  }
}

export function BusinessReceiverDetailsBubble({
  receiverDetails,
  canReveal,
  revealing,
  revealReceiverDetails
}: {
  receiverDetails: ReceiverDetails | null;
  canReveal: boolean;
  revealing: boolean;
  revealReceiverDetails: () => Promise<void>;
}) {
  const [copiedReceiverField, setCopiedReceiverField] = useState<string | null>(null);
  const [receiverCopyFailed, setReceiverCopyFailed] = useState(false);

  const copyReceiverDetail = async (field: string, value: string) => {
    setReceiverCopyFailed(false);
    try {
      await copyText(value);
      setCopiedReceiverField(field);
      window.setTimeout(() => setCopiedReceiverField(null), 1600);
    } catch {
      setCopiedReceiverField(null);
      setReceiverCopyFailed(true);
    }
  };

  return (
    <article className="business-order-chat-message">
      <span className="business-order-chat-message__sender">Pago Movil compartido</span>
      {receiverDetails ? (
        <div className="business-order-chat-receiver-copy">
          <p>{receiverDetails.bank}</p>
          <p>{receiverDetails.phone}</p>
          <p>{receiverDetails.document}</p>
          <p>{receiverDetails.holder}</p>
          <div className="business-order-chat-receiver-copy__actions">
            <button type="button" onClick={() => void copyReceiverDetail("telefono", receiverDetails.phone)}>
              {copiedReceiverField === "telefono" ? "Copiado" : "Copiar telefono"}
            </button>
            <button type="button" onClick={() => void copyReceiverDetail("cedula", receiverDetails.document)}>
              {copiedReceiverField === "cedula" ? "Copiado" : "Copiar cedula"}
            </button>
            <button type="button" onClick={() => void copyReceiverDetail("banco", receiverDetails.bank)}>
              {copiedReceiverField === "banco" ? "Copiado" : "Copiar banco"}
            </button>
            <button
              type="button"
              onClick={() => void copyReceiverDetail(
                "todo",
                `${receiverDetails.bank}\n${receiverDetails.phone}\n${receiverDetails.document}\n${receiverDetails.holder}`
              )}
            >
              {copiedReceiverField === "todo" ? "Copiado" : "Copiar todo"}
            </button>
          </div>
          {receiverCopyFailed ? <small>No pudimos copiar. Manten presionado el dato.</small> : null}
        </div>
      ) : (
        <p>Datos disponibles para esta orden.</p>
      )}
      {!receiverDetails && canReveal ? (
        <button
          className="business-order-chat-payment-action"
          type="button"
          disabled={revealing}
          onClick={() => void revealReceiverDetails()}
        >
          {revealing ? "Revelando..." : "Ver Pago Movil"}
        </button>
      ) : null}
    </article>
  );
}
