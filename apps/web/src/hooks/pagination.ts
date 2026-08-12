export function appendUniqueById<T extends { id: string }>(current: T[], incoming: T[]): T[] {
  const knownIds = new Set(current.map((item) => item.id));
  return [...current, ...incoming.filter((item) => !knownIds.has(item.id))];
}
