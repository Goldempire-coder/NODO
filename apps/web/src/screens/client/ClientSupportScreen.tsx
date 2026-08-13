import { useEffect, useRef, useState } from "react";
import { Button, Text } from "@telegram-apps/telegram-ui";
import type { ClientWorkspaceModel } from "../../hooks/useClientWorkspaceModel";
import { useVisibleSurfacePolling } from "../../hooks/useVisibleSurfacePolling";
import { SurfaceSupportInbox, SurfaceSupportThread } from "../support/SurfaceSupportPrimitives";

const CLIENT_SUPPORT_REFRESH_MS = 8000;

export function ClientSupportScreen({ model }: { model: ClientWorkspaceModel }) {
  const {
    creatingSupportTicket,
    closingSupportTicketId,
    loadSupportTickets,
    loadMoreSupportTickets,
    loadMoreSupportMessages,
    loadingSupportTickets,
    openSupportTicket,
    openingSupportTicketId,
    refreshSupportWorkspace,
    selectedSupportTicket,
    setSelectedSupportTicket,
    setSupportForm,
    supportForm,
    supportFilter,
    supportReply,
    supportTickets,
    supportTicketsLoadingMore,
    supportMessagesLoadingMore,
    supportTicketsNextCursor,
    setSupportReply,
    sendingSupportReply,
    submitSupportReply,
    submitSupportTicket,
    closeOwnSupportTicket,
    uploadingSupportAttachment,
    uploadTicketAttachment
  } = model;
  const [showNewConversation, setShowNewConversation] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement | null>(null);
  const ticketMessages = selectedSupportTicket?.messages || [];
  const latestMessageId = ticketMessages[ticketMessages.length - 1]?.id;
  const emptyCopy = supportFilter === "archived" ? "No tienes tickets archivados." : "No tienes tickets activos.";
  const conversationLabel = loadingSupportTickets ? "Actualizando..." : supportFilter === "archived" ? "Archivados" : "Activos";

  useEffect(() => {
    void loadSupportTickets("active");
  }, [loadSupportTickets]);

  useVisibleSurfacePolling({
    enabled: true,
    intervalMs: CLIENT_SUPPORT_REFRESH_MS,
    poll: refreshSupportWorkspace
  });

  useEffect(() => {
    if (selectedSupportTicket) {
      setShowNewConversation(false);
    }
  }, [selectedSupportTicket]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ block: "end" });
  }, [latestMessageId, selectedSupportTicket?.id]);

  const startNewConversation = () => {
    setSelectedSupportTicket(null);
    setSupportReply("");
    setSupportForm((current) => ({ ...current, scope: "client_general", subject: "", message: "", order_id: null }));
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
              <Text className="business-card__label">Nuevo ticket</Text>
              <strong>Cuentanos que necesitas</strong>
            </div>
            <Button mode="outline" size="s" type="button" disabled={creatingSupportTicket} onClick={returnToConversationList}>Cancelar</Button>
          </div>
          <label className="business-field">
            <span>Categoria</span>
            <select disabled={creatingSupportTicket} value={supportForm.category} onChange={(event) => setSupportForm((current) => ({ ...current, category: event.target.value as typeof supportForm.category }))}>
              <option value="technical_issue">Problema tecnico</option>
              <option value="account_access">Acceso a cuenta</option>
              <option value="order_help">Ayuda con orden</option>
              <option value="payment_report_help">Reporte de pago</option>
              <option value="other">Otro</option>
            </select>
          </label>
          <label className="business-field">
            <span>Asunto</span>
            <input disabled={creatingSupportTicket} maxLength={140} value={supportForm.subject} onChange={(event) => setSupportForm((current) => ({ ...current, subject: event.target.value }))} />
          </label>
          <label className="business-field">
            <span>Mensaje</span>
            <textarea disabled={creatingSupportTicket} maxLength={2000} rows={4} value={supportForm.message} onChange={(event) => setSupportForm((current) => ({ ...current, message: event.target.value }))} />
          </label>
          <Text className="auth-entry__session-meta">
            Soporte revisa el caso sin cambiar automaticamente el estado de la orden o del pago.
          </Text>
          <Button mode="filled" size="s" type="submit" disabled={creatingSupportTicket || loadingSupportTickets || supportForm.subject.trim().length < 3 || supportForm.message.trim().length < 3}>
            {creatingSupportTicket ? "Creando..." : "Crear ticket"}
          </Button>
        </form>
      ) : null}

      {selectedSupportTicket ? (
        <SurfaceSupportThread
          archivedBody="Puedes verlo cuando lo necesites, pero ya no recibe respuestas."
          archivedTitle="Este ticket esta archivado."
          closing={closingSupportTicketId === selectedSupportTicket.id}
          emptyMessagesCopy="Aun no hay mensajes en este ticket."
          messagesEndRef={messagesEndRef}
          loadingOlderMessages={supportMessagesLoadingMore}
          notice={model.notice}
          ownRole="remitter"
          reply={supportReply}
          sending={sendingSupportReply}
          ticket={selectedSupportTicket}
          uploading={uploadingSupportAttachment}
          waitingUserLabel="Tu respuesta pendiente"
          onClose={() => void closeOwnSupportTicket()}
          onLoadOlderMessages={() => void loadMoreSupportMessages()}
          onReplyChange={setSupportReply}
          onSend={() => void submitSupportReply()}
          onUpload={(file) => void uploadTicketAttachment(file)}
        />
      ) : null}

      {!showNewConversation && !selectedSupportTicket ? (
        <SurfaceSupportInbox
          activeLabel="Activos"
          archivedLabel="Archivados"
          collectionLabel="tickets"
          conversationLabel={conversationLabel}
          creating={creatingSupportTicket}
          emptyCopy={emptyCopy}
          filter={supportFilter === "all" ? "active" : supportFilter}
          loading={loadingSupportTickets}
          loadingMore={supportTicketsLoadingMore}
          nextCursor={supportTicketsNextCursor}
          openingTicketId={openingSupportTicketId}
          tickets={supportTickets}
          waitingUserLabel="Tu respuesta pendiente"
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
