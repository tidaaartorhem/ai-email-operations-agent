import { useState } from 'react';
import type { QueueRow } from '../types';
import { bucketLabel, actionLabel, intentLabel, fmtPct, shortId } from '../format';

interface Props {
  row: QueueRow;
  onBack: () => void;
  onSelectThread: (id: string) => void;
}

export function ThreadDetail({ row: r, onBack, onSelectThread }: Props) {
  const [copied, setCopied] = useState(false);

  const copyDraft = async () => {
    if (!r.draft) return;
    try {
      await navigator.clipboard.writeText(r.draft.body);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2000);
    } catch {
      /* clipboard unavailable — draft stays on screen */
    }
  };

  return (
    <div>
      <button className="btn back" onClick={onBack}>← Back to risk board</button>
      <div className="detail-grid">
        <div className="panel">
          <div className="head">
            <h2>Thread #{shortId(r.thread_id)}</h2>
            <span className="meta">{r.turn_count} turns · opened {new Date(r.created_at).toLocaleString()}</span>
          </div>
          <div className="body">
            <ul className="timeline">
              {r.turns.map((t, i) => (
                <li key={i} className={t.speaker}>
                  <div className="who">{t.speaker === 'customer' ? 'Customer' : 'Support team'}</div>
                  <div>{t.text}</div>
                  <div className="ts">{new Date(t.created_at).toLocaleString()}</div>
                </li>
              ))}
            </ul>
          </div>
        </div>

        <div>
          <div className="panel">
            <div className="head"><h2>Triage</h2></div>
            <div className="body">
              <dl className="kv">
                <dt>Intent</dt>
                <dd>{intentLabel(r.intent)} <span className="muted">({fmtPct(r.intent_confidence)} confident)</span></dd>
                <dt>Priority</dt>
                <dd><span className={`badge ${r.priority}`}>{r.priority}</span></dd>
                <dt>Risk</dt>
                <dd><span className={`badge ${r.risk_bucket}`}>{bucketLabel(r.risk_bucket)}</span> <span className="num">{fmtPct(r.breach_risk)} breach risk</span></dd>
                <dt>First response</dt>
                <dd className="num">
                  {r.first_response_human != null
                    ? `${r.first_response_human} (target ${fmtTarget(r.fr_target_min)})`
                    : `not yet replied (target ${fmtTarget(r.fr_target_min)})`}
                </dd>
                <dt>Queue age</dt>
                <dd className="num">{r.queue_age_human ?? '—'} <span className="muted">vs {fmtTarget(r.res_target_min)} resolution target</span></dd>
                {r.silent_breach && (
                  <>
                    <dt>Flag</dt>
                    <dd><span className="badge breached">Silent breach</span></dd>
                  </>
                )}
                {r.close_candidate && (
                  <>
                    <dt>Flag</dt>
                    <dd><span className="badge at_risk">Dead air — close candidate</span></dd>
                  </>
                )}
              </dl>
            </div>
          </div>

          <div className="panel">
            <div className="head">
              <h2>Recommended action</h2>
              <span className={`badge action-${r.action}`}>{actionLabel(r.action)}</span>
            </div>
            <div className="body">
              <p style={{ marginTop: 0 }}>{r.action_reason}</p>
              <p className="muted">Confidence {fmtPct(r.action_confidence)} — deterministic from intent + SLA state.</p>
              {r.merge_with && (
                <p>
                  Probable duplicate of{' '}
                  <button className="btn" onClick={() => onSelectThread(r.merge_with!)}>
                    thread #{shortId(r.merge_with)} ({fmtPct(r.merge_similarity ?? 0)} similar)
                  </button>
                </p>
              )}
            </div>
          </div>

          {r.draft && (
            <div className="panel">
              <div className="head">
                <h2>Suggested first response</h2>
                <button className="btn" onClick={copyDraft}>{copied ? 'Copied ✓' : 'Copy draft'}</button>
              </div>
              <div className="body">
                <div className="draft">{r.draft.body}</div>
                <div className="gate-note">
                  Built from the {intentLabel(r.draft.intent)} template, citing the intake message
                  (“{r.draft.cited_from.slice(0, 90)}…”). Nothing sends automatically —
                  a human reviews and sends every draft.
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function fmtTarget(mins: number): string {
  if (mins < 60) return `${mins}m`;
  if (mins < 1440) return `${mins / 60}h`;
  return `${mins / 1440}d`;
}
