import type { SupportEvent, SupportMessage, SupportTicket } from "../types/support";

type PageMergeOptions = {
  preserveHistoryCursor?: boolean;
};

function mergeChronological<T extends { created_at: string; id: string }>(current: T[] = [], incoming: T[] = []): T[] {
  const byId = new Map(current.map((item) => [item.id, item]));
  incoming.forEach((item) => byId.set(item.id, item));
  return [...byId.values()].sort((left, right) => (
    left.created_at.localeCompare(right.created_at) || left.id.localeCompare(right.id)
  ));
}

export function mergeSupportTicketPage<T extends SupportTicket>(
  current: T,
  incoming: T,
  options: PageMergeOptions = {}
): T {
  const messages = mergeChronological<SupportMessage>(current.messages, incoming.messages);
  const events = mergeChronological<SupportEvent>(current.events, incoming.events);
  return {
    ...current,
    ...incoming,
    messages,
    events,
    messages_next_cursor: options.preserveHistoryCursor
      ? current.messages_next_cursor
      : incoming.messages_next_cursor,
    events_next_cursor: options.preserveHistoryCursor
      ? current.events_next_cursor
      : incoming.events_next_cursor
  };
}
