import { useEffect, useRef, useState } from "react";
import { Button, Text } from "@telegram-apps/telegram-ui";
import type { BusinessMiniAppModel } from "../../hooks/useBusinessMiniAppModel";
import { useVisibleSurfacePolling } from "../../hooks/useVisibleSurfacePolling";
import { SurfaceSupportInbox, SurfaceSupportThread } from "../support/SurfaceSupportPrimitives";

const BUSINESS_SUPPORT_REFRESH_MS = 5000;

export function BusinessSupportScreen({ model }: { model: BusinessMiniAppModel }) {
  const {
    creatingSupportTicket,
    closingSupportTicketId,
    loadingSupportFilter,
    loadingSupportTickets,
    loadSupportTickets,
    loadMoreSupportTickets,
    openSupportTicket,
    openingSupportTicketId,
    refreshSupportWorkspace,
    selectedSupportTicket,
    sendingSupportReply,
    setSelectedSupportTicket,
    setSupportForm,
    supportForm,
    supportFilter,
    supportReply,
    supportTickets,
    supportTicketsLoadingMore,
    supportTicketsNextCursor,
    setSupportReply,
    submitSupportReply,
    submitSupportTicket,
    closeOwnSupportTicket,
    uploadingSupportAttachment,
    uploadTicketAttachment
  } = model;
  const [showNewConversation, setShowNewConversation] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement | null>(null);
  const ticketMessages = selectedSupportTicket?.messages || [];
  const emptyCopy = supportFilter === "archived" ? "No tienes conversaciones archivadas." : "No tienes conversaciones activas.";
  const conversationLabel = loadingSupportFilter === supportFilter ? "Actualizando..." : supportFilter === "archived" ? "Archivadas" : "Activas";

  useEffect(() => {
    void loadSupportTickets("active");
  }, [loadSupportTickets]);

  useVisibleSurfacePolling({
    enabled: true,
    intervalMs: BUSINESS_SUPPORT_REFRESH_MS,
    poll: refreshSupportWorkspace
  });

  useEffect(() => {
    if (selectedSupportTicket) {
      setShowNewConversation(false);
    }
  }, [selectedSupportTicket]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ block: "end" });
  }, [selectedSupportTicket?.id, ticketMessages.length]);

  const startNewConversation = () => {
    setSelectedSupportTicket(null);
    setSupportReply("");
    setShowNewConversation(true);
  };

  const returnToConversationList = () => {
    setSelectedSupportTicket(null);
    setSupportReply("");
    setShowNewConversation(false);
  };

  const selectFilter = (filter: "active" | "archived") => {
    setSelectedSupportTicket(null);
    setSupportReply("");
    setShowNewConversation(false);
    void loadSupportTickets(filter);
  };

  return (
    <section className="surface-support" aria-label="Soporte NODO">
      {showNewConversation && !selectedSupportTicket ? (
        <form
          className="surface-support-new"
          onSubmit={(event) => {
            event.preventDefault();
            void submitSupportTicket();
          }}
        >
          <div className="surface-support-new__heading">
            <div>
              <Text className="business-card__label">Nuevo tema</Text>
              <strong>Cuentanos que necesitas</strong>
            </div>
            <Button mode="outline" size="s" type="button" disabled={creatingSupportTicket} onClick={returnToConversationList}>Cancelar</Button>
          </div>
          <div className="business-grid">
            <label className="business-field">
              <span>Tipo</span>
              <select disabled={creatingSupportTicket} value={supportForm.scope} onChange={(event) => setSupportForm((current) => ({ ...current, scope: event.target.value as typeof supportForm.scope }))}>
                <option value="business_general">Soporte general</option>
                <option value="business_order">Orden</option>
                <option value="business_ad">Anuncio</option>
                <option value="business_credit">Creditos</option>
              </select>
            </label>
            <label className="business-field">
              <span>Categoria</span>
              <select disabled={creatingSupportTicket} value={supportForm.category} onChange={(event) => setSupportForm((current) => ({ ...current, category: event.target.value as typeof supportForm.category }))}>
                <option value="technical_issue">Problema tecnico</option>
                <option value="business_access">Acceso negocio</option>
                <option value="credits_help">Creditos</option>
                <option value="order_help">Orden</option>
                <option value="other">Otro</option>
              </select>
            </label>
          </div>
          <label className="business-field">
            <span>Asunto</span>
            <input disabled={creatingSupportTicket} maxLength={140} value={supportForm.subject} onChange={(event) => setSupportForm((current) => ({ ...current, subject: event.target.value }))} />
          </label>
          <label className="business-field">
            <span>Mensaje</span>
            <textarea disabled={creatingSupportTicket} maxLength={2000} rows={4} value={supportForm.message} onChange={(event) => setSupportForm((current) => ({ ...current, message: event.target.value }))} />
          </label>
          <Button mode="filled" size="s" type="submit" disabled={creatingSupportTicket || loadingSupportTickets || supportForm.subject.trim().length < 3 || supportForm.message.trim().length < 3}>
            {creatingSupportTicket ? "Creando..." : "Crear conversacion"}
          </Button>
        </form>
      ) : null}

      {selectedSupportTicket ? (
        <SurfaceSupportThread
          archivedBody="Puedes consultar el historial, pero este caso ya no recibe respuestas."
          archivedTitle="Conversacion archivada"
          closing={closingSupportTicketId === selectedSupportTicket.id}
          emptyMessagesCopy="Aun no hay mensajes en esta conversacion."
          messagesEndRef={messagesEndRef}
          notice={model.notice}
          ownRole="business_owner"
          reply={supportReply}
          sending={sendingSupportReply}
          ticket={selectedSupportTicket}
          uploading={uploadingSupportAttachment}
          waitingUserLabel="Esperando tu respuesta"
          onClose={() => void closeOwnSupportTicket()}
          onReplyChange={setSupportReply}
          onSend={() => void submitSupportReply()}
          onUpload={(file) => void uploadTicketAttachment(file)}
        />
      ) : null}

      {!showNewConversation && !selectedSupportTicket ? (
        <SurfaceSupportInbox
          activeLabel="Activas"
          archivedLabel="Archivadas"
          collectionLabel="conversaciones"
          conversationLabel={conversationLabel}
          creating={creatingSupportTicket}
          emptyCopy={emptyCopy}
          filter={supportFilter === "all" ? "active" : supportFilter}
          loading={loadingSupportTickets}
          loadingMore={supportTicketsLoadingMore}
          nextCursor={supportTicketsNextCursor}
          openingTicketId={openingSupportTicketId}
          tickets={supportTickets}
          waitingUserLabel="Esperando tu respuesta"
          onFilterChange={selectFilter}
          onLoadMore={() => void loadMoreSupportTickets()}
          onNew={startNewConversation}
          onOpen={(ticketId) => void openSupportTicket(ticketId)}
          onRefresh={() => void refreshSupportWorkspace()}
        />
      ) : null}
    </section>
  );
}
