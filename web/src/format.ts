/** Display helpers shared across views. Pure functions — covered by vitest. */

export function fmtInt(n: number): string {
  return n.toLocaleString('en-US');
}

export function fmtPct(x: number, digits = 1): string {
  return `${(x * 100).toFixed(digits)}%`;
}

export function bucketLabel(bucket: string): string {
  switch (bucket) {
    case 'breached':
      return 'Breached';
    case 'at_risk':
      return 'At risk';
    default:
      return 'On track';
  }
}

export function actionLabel(action: string): string {
  switch (action) {
    case 'reply':
      return 'Draft reply';
    case 'escalate':
      return 'Escalate';
    case 'merge':
      return 'Merge threads';
    case 'close':
      return 'Close thread';
    default:
      return 'Monitor';
  }
}

export function intentLabel(intent: string): string {
  return intent
    .split('_')
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(' ');
}

export function timeAgo(iso: string, nowMs: number): string {
  const mins = Math.max(0, (nowMs - new Date(iso).getTime()) / 60000);
  if (mins < 60) return `${Math.round(mins)}m ago`;
  if (mins < 1440) return `${(mins / 60).toFixed(1)}h ago`;
  return `${(mins / 1440).toFixed(1)}d ago`;
}

export function shortId(id: string): string {
  return id.length > 10 ? `${id.slice(0, 6)}…${id.slice(-3)}` : id;
}
