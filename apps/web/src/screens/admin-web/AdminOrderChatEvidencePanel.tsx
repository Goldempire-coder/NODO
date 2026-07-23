"use client";

import { useEffect, useRef } from "react";
import type { AdminWebModel } from "../../hooks/useAdminWebModel";
import type { AdminOrderChatEvidenceMessage } from "../../types/admin";
import { dateText } from "./AdminWebPrimitives";

function messageClass(message: AdminOrderChatEvidenceMessage) {
  const actorClass = message.sender_role === "business_owner" ? " is-business" : message.sender_role === "remitter" ? " is-client" : " is-internal";
  return `admin-order-chat-evidence__message${actorClass}${message.highlighted ? " is-highlighted" : ""}`;
}

export function AdminOrderChatEvidencePanel({ model }: { model: AdminWebModel }) {
  const highlightedMessage = useRef<HTMLElement | null>(null);
  const evidence = model.orderChatEvidence;

  useEffect(() => {
    if (evidence?.highlight_found) {
      highlightedMessage.current?.scrollIntoView({ block: "center", behavior: "smooth" });
    }
  }, [evidence?.highlight_found, evidence?.highlight_message_id]);

  return (
    <section className="admin-web-panel admin-order-chat-evidence" aria-label="Evidencia del chat de la orden">
      <div className="admin-order-chat-evidence__header">
        <div>
          <h3>Conversacion de la orden</h3>
          <p className="admin-web-muted">Lectura administrativa. La conversacion no puede editarse desde esta pantalla.</p>
        </div>
        {evidence?.highlight_found ? <span className="admin-order-chat-evidence__flag">Mensaje señalado</span> : null}
      </div>

      {model.orderChatEvidenceLoading ? <p className="admin-web-muted" role="status">Cargando conversacion...</p> : null}
      {model.orderChatEvidenceError ? (
        <div className="admin-order-chat-evidence__error" role="alert">
          <span>{model.orderChatEvidenceError}</span>
          <button type="button" onClick={() => void model.retryOrderChatEvidence()}>Reintentar</button>
        </div>
      ) : null}

      {evidence?.older_cursor ? (
        <button className="admin-order-chat-evidence__page" type="button" disabled={model.orderChatEvidenceLoadingMore !== null} onClick={() => void model.loadOlderOrderChatEvidence()}>
          {model.orderChatEvidenceLoadingMore === "older" ? "Cargando..." : "Cargar mensajes anteriores"}
        </button>
      ) : null}

      {!model.orderChatEvidenceLoading && !model.orderChatEvidenceError && evidence?.items.length === 0 ? (
        <p className="admin-web-muted">Esta orden no tiene mensajes registrados.</p>
      ) : null}

      {evidence?.items.length ? (
        <div className="admin-order-chat-evidence__messages" role="log" aria-live="polite">
          {evidence.items.map((message) => (
            <article
              className={messageClass(message)}
              key={message.message_id}
              ref={message.highlighted ? highlightedMessage : undefined}
              aria-label={message.highlighted ? "Mensaje señalado por la alerta" : undefined}
            >
              <header>
                <strong>{message.sender_label}</strong>
                <time dateTime={message.created_at}>{dateText(message.created_at)}</time>
              </header>
              {message.body ? <p>{message.body}</p> : <p className="admin-web-muted">Mensaje con adjunto.</p>}
              {message.attachments.length ? (
                <div className="admin-order-chat-evidence__attachments">
                  {message.attachments.map((attachment) => (
                    <span key={attachment.attachment_id}>
                      Adjunto {attachment.mime_type} · {Math.ceil(attachment.size_bytes / 1024)} KB
                    </span>
                  ))}
                </div>
              ) : null}
            </article>
          ))}
        </div>
      ) : null}

      {evidence?.newer_cursor ? (
        <button className="admin-order-chat-evidence__page" type="button" disabled={model.orderChatEvidenceLoadingMore !== null} onClick={() => void model.loadNewerOrderChatEvidence()}>
          {model.orderChatEvidenceLoadingMore === "newer" ? "Cargando..." : "Cargar mensajes posteriores"}
        </button>
      ) : null}
    </section>
  );
}
