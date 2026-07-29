import type { AdminInvestigationCaseFile } from "../../types/admin";

const ACTIVE_SUPPORT_STATUSES = new Set(["open", "waiting_support", "waiting_user", "escalated"]);
const ARCHIVED_SUPPORT_STATUSES = new Set(["resolved", "closed"]);

type PlaybookCheck = {
  code: string;
  label: string;
  status: string;
  actionRoute?: string | null;
  actionLabel?: string;
};

function ticketStatus(file: AdminInvestigationCaseFile): string {
  if (file.support_tickets.status !== "ok") {
    return "No revisado";
  }
  const hasActive = file.support_tickets.items.some((ticket) => ACTIVE_SUPPORT_STATUSES.has(ticket.status));
  const hasArchived = file.support_tickets.items.some((ticket) => ARCHIVED_SUPPORT_STATUSES.has(ticket.status));
  if (hasActive && hasArchived) {
    return "Activo y archivado";
  }
  if (hasActive) {
    return "Activo";
  }
  if (hasArchived) {
    return "Archivado";
  }
  return file.summary.counts.support_tickets > 0 ? "Relacionado" : "No encontrado";
}

function evidenceStatus(file: AdminInvestigationCaseFile): string {
  if (file.evidence.status !== "ok") {
    return "No revisado";
  }
  const evidenceCount = file.evidence.total_count ?? file.evidence.documents.length + file.evidence.attachments.length;
  return evidenceCount > 0 ? "Disponible" : "No encontrada";
}

function availableScreen(file: AdminInvestigationCaseFile): Pick<PlaybookCheck, "status" | "actionRoute" | "actionLabel"> {
  const activeTicket = file.support_tickets.items.find((ticket) => ACTIVE_SUPPORT_STATUSES.has(ticket.status));
  if (activeTicket) {
    return { status: "Ticket activo", actionRoute: activeTicket.action_route, actionLabel: "Abrir ticket" };
  }
  const order = file.orders.items[0];
  if (order) {
    return { status: "Orden relacionada", actionRoute: order.action_route, actionLabel: "Abrir orden" };
  }
  const ticket = file.support_tickets.items[0];
  if (ticket) {
    return { status: "Ticket archivado", actionRoute: ticket.action_route, actionLabel: "Abrir ticket" };
  }
  const intake = file.business_intakes.items[0];
  if (intake) {
    return { status: "Intake relacionado", actionRoute: intake.action_route, actionLabel: "Abrir intake" };
  }
  return { status: "Origen del caso", actionRoute: file.anchor.action_route, actionLabel: "Abrir origen" };
}

export function AdminInvestigationCasePlaybookPanel({
  file,
  onOpenRoute
}: {
  file: AdminInvestigationCaseFile;
  onOpenRoute: (route: string) => void;
}) {
  const firstOrder = file.orders.items[0];
  const firstTicket = file.support_tickets.items[0];
  const firstIntake = file.business_intakes.items[0];
  const evidenceReady = file.evidence.status === "ok";
  const nextScreen = availableScreen(file);
  const checks: PlaybookCheck[] = [
    {
      code: "related_order",
      label: "Orden relacionada",
      status: file.summary.counts.orders > 0 ? "Encontrada" : "No encontrada",
      actionRoute: firstOrder?.action_route,
      actionLabel: "Abrir orden"
    },
    {
      code: "payment_report",
      label: "Reporte de pago",
      status: evidenceReady ? (file.evidence.payment_report_present ? "Presente" : "No encontrado") : "No revisado"
    },
    {
      code: "support_ticket",
      label: "Ticket relacionado",
      status: ticketStatus(file),
      actionRoute: firstTicket?.action_route,
      actionLabel: "Abrir ticket"
    },
    {
      code: "order_chat",
      label: "Chat de orden",
      status: evidenceReady ? (file.evidence.chat_evidence_available ? "Disponible" : "No encontrado") : "No revisado",
      actionRoute: file.evidence.chat_action_routes[0],
      actionLabel: "Abrir chat"
    },
    {
      code: "related_evidence",
      label: "Evidencia relacionada",
      status: evidenceStatus(file)
    },
    {
      code: "related_intake",
      label: "Intake relacionado",
      status: file.summary.counts.business_intakes > 0 ? "Encontrado" : "No encontrado",
      actionRoute: firstIntake?.action_route,
      actionLabel: "Abrir intake"
    },
    {
      code: "available_screen",
      label: "Pantalla disponible",
      ...nextScreen
    }
  ];

  return (
    <section className="admin-case-file-section admin-case-file-playbook" aria-label="Revision guiada del caso">
      <div className="admin-case-file-section__header">
        <h3>Revision guiada</h3>
        <span>Solo lectura</span>
      </div>
      <div className="admin-case-file-playbook__checks">
        {checks.map((check) => (
          <div data-playbook-check={check.code} key={check.code}>
            <span>{check.label}</span>
            <strong>{check.status}</strong>
            {check.actionRoute ? (
              <button type="button" onClick={() => onOpenRoute(check.actionRoute!)}>
                {check.actionLabel || "Abrir"}
              </button>
            ) : null}
          </div>
        ))}
      </div>
    </section>
  );
}
