import type { SurfaceAttentionItem } from "../../types/notifications";

export function AttentionBadge({
  count,
  label,
  truncated = false
}: {
  count: number;
  label: string;
  truncated?: boolean;
}) {
  if (count < 1 && !truncated) {
    return null;
  }
  const displayCount = truncated ? "50+" : count > 99 ? "99+" : String(count);
  return (
    <span className="attention-badge" aria-label={`${displayCount} ${label}`}>
      {displayCount}
    </span>
  );
}

export function AttentionBanner({
  item,
  stale,
  onDismiss,
  onOpen
}: {
  item: SurfaceAttentionItem | null;
  stale: boolean;
  onDismiss: () => void;
  onOpen: () => void;
}) {
  if (!item && !stale) {
    return null;
  }
  return (
    <div className={item ? "attention-strip" : "attention-strip attention-strip--stale"} role="status">
      <span>{item?.message || "Pendientes sin actualizar"}</span>
      {item ? (
        <span className="attention-strip__actions">
          <button type="button" onClick={onOpen}>Abrir</button>
          <button type="button" aria-label="Cerrar aviso" onClick={onDismiss}>&times;</button>
        </span>
      ) : null}
      {item && stale ? <small>Sin actualizar</small> : null}
    </div>
  );
}
