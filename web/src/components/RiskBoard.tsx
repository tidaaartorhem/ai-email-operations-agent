import { useMemo, useState } from 'react';
import type { Analytics, QueueRow, RiskBucket } from '../types';
import { fmtInt, fmtPct, bucketLabel, actionLabel, intentLabel, shortId } from '../format';

interface Props {
  queue: QueueRow[];
  analytics: Analytics;
  onSelect: (row: QueueRow) => void;
}

const RANK: Record<RiskBucket, number> = { breached: 0, at_risk: 1, on_track: 2 };

export function RiskBoard({ queue, analytics, onSelect }: Props) {
  const t = analytics.totals;
  const [bucket, setBucket] = useState<string>('all');
  const [action, setAction] = useState<string>('all');
  const [intent, setIntent] = useState<string>('all');

  const intents = useMemo(
    () => [...new Set(queue.map((r) => r.intent))].sort(),
    [queue],
  );

  const rows = useMemo(() => {
    return queue
      .filter((r) => bucket === 'all' || r.risk_bucket === bucket)
      .filter((r) => action === 'all' || r.action === action)
      .filter((r) => intent === 'all' || r.intent === intent)
      .sort((a, b) => RANK[a.risk_bucket] - RANK[b.risk_bucket] || b.breach_risk - a.breach_risk);
  }, [queue, bucket, action, intent]);

  const clock = (r: QueueRow): string => {
    if (r.state === 'needs_response') {
      if (r.response_clock_min == null) return '—';
      const left = r.fr_target_min - r.response_clock_min;
      return left >= 0 ? `${fmtDur(left)} left` : `${fmtDur(-left)} overdue`;
    }
    return r.dead_air_min != null ? `${fmtDur(r.dead_air_min)} dead air` : '—';
  };

  return (
    <>
      <div className="grid-cards">
        <div className="stat-card danger">
          <div className="v num">{fmtInt(t.breached)}</div>
          <div className="l">SLA breached</div>
          <div className="note">{t.silent_breaches} silent — customer still waiting past resolution</div>
        </div>
        <div className="stat-card warn">
          <div className="v num">{fmtInt(t.needs_response)}</div>
          <div className="l">First-response clocks ticking</div>
          <div className="note">last turn is the customer — nobody has replied yet</div>
        </div>
        <div className="stat-card warn">
          <div className="v num">{fmtInt(t.close_candidates)}</div>
          <div className="l">Dead-air close candidates</div>
          <div className="note">brand replied, customer never came back</div>
        </div>
        <div className="stat-card ok">
          <div className="v num">{fmtInt(t.duplicate_pairs)}</div>
          <div className="l">Duplicate pairs</div>
          <div className="note">same request filed twice — merge before double-handling</div>
        </div>
        <div className="stat-card">
          <div className="v num">{fmtInt(t.open)}</div>
          <div className="l">Open threads</div>
          <div className="note">{t.awaiting_customer} awaiting customer · {t.auto_archived_promo} promo auto-archived</div>
        </div>
      </div>

      <div className="panel">
        <div className="head">
          <h2>Risk board</h2>
          <div className="filters">
            <select value={bucket} onChange={(e) => setBucket(e.target.value)} aria-label="Risk filter">
              <option value="all">All risk</option>
              <option value="breached">Breached</option>
              <option value="at_risk">At risk</option>
              <option value="on_track">On track</option>
            </select>
            <select value={action} onChange={(e) => setAction(e.target.value)} aria-label="Action filter">
              <option value="all">All actions</option>
              <option value="escalate">Escalate</option>
              <option value="reply">Draft reply</option>
              <option value="merge">Merge</option>
              <option value="close">Close</option>
              <option value="monitor">Monitor</option>
            </select>
            <select value={intent} onChange={(e) => setIntent(e.target.value)} aria-label="Intent filter">
              <option value="all">All intents</option>
              {intents.map((i) => (
                <option key={i} value={i}>{intentLabel(i)}</option>
              ))}
            </select>
            <span className="meta">{rows.length} of {queue.length} shown</span>
          </div>
        </div>
        <div style={{ overflowX: 'auto' }}>
          <table className="queue">
            <thead>
              <tr>
                <th>Thread</th>
                <th>Intent</th>
                <th>Pri</th>
                <th>Risk</th>
                <th>SLA clock</th>
                <th>Recommended action</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.thread_id} className="row" onClick={() => onSelect(r)}>
                  <td>
                    <div className="snippet">
                      {r.first_customer.slice(0, 140)}{r.first_customer.length > 140 ? '…' : ''}
                      <span className="muted">#{shortId(r.thread_id)} · {r.turn_count} turns</span>
                    </div>
                  </td>
                  <td><span className="badge intent">{intentLabel(r.intent)}</span></td>
                  <td><span className={`badge ${r.priority}`}>{r.priority}</span></td>
                  <td>
                    <span className={`badge ${r.risk_bucket}`}>{bucketLabel(r.risk_bucket)}</span>
                    <div className="riskbar" title={`Breach risk ${fmtPct(r.breach_risk)}`}>
                      <div style={{ width: `${Math.round(r.breach_risk * 100)}%`, background: riskColor(r.risk_bucket) }} />
                    </div>
                  </td>
                  <td className="num" style={{ whiteSpace: 'nowrap' }}>{clock(r)}</td>
                  <td><span className={`badge action-${r.action}`}>{actionLabel(r.action)}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
}

function riskColor(bucket: RiskBucket): string {
  return bucket === 'breached' ? '#e76f51' : bucket === 'at_risk' ? '#f4a261' : '#2a9d8f';
}

function fmtDur(mins: number): string {
  if (mins < 60) return `${Math.round(mins)}m`;
  if (mins < 1440) return `${(mins / 60).toFixed(1)}h`;
  return `${(mins / 1440).toFixed(1)}d`;
}
