"use client";

import { useState } from "react";
import type { PaymentInstructions } from "../../../types/payments";

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

export function ClientPaymentDetailsBubble({
  instructions
}: {
  instructions: PaymentInstructions;
}) {
  const [copied, setCopied] = useState(false);
  const [copyFailed, setCopyFailed] = useState(false);
  const methodLabel = instructions.payment_instructions.method_type === "usdt_trc20" ? "USDT" : "Zelle";

  const copyPaymentAccount = async () => {
    setCopyFailed(false);
    try {
      await copyText(instructions.payment_instructions.account_value);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1600);
    } catch {
      setCopied(false);
      setCopyFailed(true);
    }
  };

  return (
    <article className="business-order-chat-message business-order-chat-message--system business-order-chat-payment-details">
      <span className="business-order-chat-message__sender">NODO</span>
      <p>{methodLabel} del negocio</p>
      <div className="business-order-chat-payment-details__value">
        <code>{instructions.payment_instructions.account_value}</code>
        <button type="button" onClick={() => void copyPaymentAccount()}>
          {copied ? "Copiado" : "Copiar"}
        </button>
      </div>
      <small>
        Monto: {instructions.order.amount_usd} USD
        {instructions.payment_instructions.network
          ? ` - Red ${instructions.payment_instructions.network}`
          : ""}
      </small>
      {copyFailed ? (
        <span className="business-order-chat-payment-details__error">
          No pudimos copiar. Manten presionado el dato.
        </span>
      ) : null}
    </article>
  );
}
