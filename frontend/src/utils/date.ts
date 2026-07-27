/**
 * Shared date formatting utility.
 * Keeps formatting consistent across pages without pulling in a heavy library.
 */

/**
 * Format an ISO 8601 date string to a human-readable date/time.
 * Examples: "Jan 15, 2025" or "Jan 15, 2025, 14:32"
 */
export function format(
  iso: string | undefined | null,
  includeTime = true,
): string {
  if (!iso) return '—';
  try {
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return iso;

    const dateStr = d.toLocaleDateString(undefined, {
      year:  'numeric',
      month: 'short',
      day:   'numeric',
    });

    if (!includeTime) return dateStr;

    const timeStr = d.toLocaleTimeString(undefined, {
      hour:   '2-digit',
      minute: '2-digit',
    });

    return `${dateStr}, ${timeStr}`;
  } catch {
    return iso;
  }
}

/**
 * Return a relative time string, e.g. "2 hours ago", "3 days ago".
 */
export function fromNow(iso: string | undefined | null): string {
  if (!iso) return '—';
  try {
    const seconds = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
    if (seconds < 60)    return 'just now';
    if (seconds < 3600)  return `${Math.floor(seconds / 60)}m ago`;
    if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
    if (seconds < 604800) return `${Math.floor(seconds / 86400)}d ago`;
    return format(iso, false);
  } catch {
    return iso ?? '—';
  }
}
