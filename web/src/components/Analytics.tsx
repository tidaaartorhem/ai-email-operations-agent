import { Fragment } from 'react';
import type { Analytics } from '../types';
import { fmtInt, fmtPct, intentLabel } from '../format';

export function AnalyticsView({ analytics: a }: { analytics: Analytics }) {
  const maxVol = Math.max(...a.by_hour.map((h) => h.threads), 1);
  const actionEntries = Object.entries(a.totals.actions).sort((x, y) => y[1] - x[1]);

  return (
    <>
      <div className="panel">
        <div className="head">
          <h2>Intent breakdown</h2>
          <span className="meta">median first-response time and open-queue breach rate per intent</span>
        </div>
        <div style={{ overflowX: 'auto' }}>
          <table className="queue">
            <thead>
              <tr>
                <th>Intent</th><th>Priority</th><th>Threads</th><th>Open</th>
                <th>Median first response</th><th>Open breach rate</th>
              </tr>
            </thead>
            <tbody>
              {a.by_intent.filter((r) => r.intent !== 'promo').map((r) => (
                <tr key={r.intent}>
                  <td><span className="badge intent">{intentLabel(r.intent)}</span></td>
                  <td><span className={`badge ${r.priority}`}>{r.priority}</span></td>
                  <td className="num">{fmtInt(r.threads)}</td>
                  <td className="num">{fmtInt(r.open)}</td>
                  <td className="num">{r.median_first_response_human ?? '—'}</td>
                  <td className="num">{fmtPct(r.breach_rate)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="detail-grid">
        <div className="panel">
          <div className="head">
            <h2>Volume by hour of day</h2>
            <span className="meta">intake timestamps, UTC</span>
          </div>
          <div className="body">
            <div className="bars">
              {a.by_hour.map((h) => (
                <div
                  key={h.hour}
                  className="bar"
                  style={{ height: `${Math.max(2, (h.threads / maxVol) * 100)}%` }}
                  title={`${h.hour}:00 — ${h.threads} threads`}
                />
              ))}
            </div>
            <div className="hour-labels">
              {a.by_hour.map((h) => (
                <span key={h.hour}>{h.hour % 6 === 0 ? `${h.hour}h` : ''}</span>
              ))}
            </div>
          </div>
        </div>

        <div className="panel">
          <div className="head"><h2>Recommended actions</h2><span className="meta">across the open queue</span></div>
          <div className="body">
            <dl className="kv">
              {actionEntries.map(([kind, n]) => (
                <Fragment key={kind}>
                  <dt style={{ textTransform: 'capitalize' }}>{kind}</dt>
                  <dd className="num">{fmtInt(n)}</dd>
                </Fragment>
              ))}
            </dl>
            <p className="muted">
              {fmtInt(a.totals.close_candidates)} dead-air threads are ready to auto-close with a
              courtesy note — the cheapest queue hygiene there is.
            </p>
          </div>
        </div>
      </div>
    </>
  );
}
