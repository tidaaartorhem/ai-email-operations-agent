import { useState } from 'react';
import type { PasteDemo } from '../types';
import { fmtPct, intentLabel } from '../format';

/**
 * Triage lab: pick one of the pre-computed intake samples and see exactly
 * what the pipeline does with a brand-new message — intent, confidence, SLA
 * targets, and the draft it would attach. Live classification of arbitrary
 * pasted text runs in the Python service (`intents.classify`); the static
 * demo ships the pre-computed outputs so the page works with zero backend.
 */
export function TriageLab({ samples }: { samples: PasteDemo[] }) {
  const [idx, setIdx] = useState(0);
  const s = samples[idx];

  return (
    <div className="panel">
      <div className="head">
        <h2>Triage lab</h2>
        <span className="meta">what the pipeline does with a new intake message</span>
      </div>
      <div className="body">
        <div className="sample-btns">
          {samples.map((p, i) => (
            <button
              key={i}
              className={`btn${i === idx ? ' active' : ''}`}
              onClick={() => setIdx(i)}
            >
              Sample {i + 1}: {intentLabel(p.intent)}
            </button>
          ))}
        </div>
        <div className="draft" style={{ background: '#fff' }}>{s.text}</div>
        <dl className="kv" style={{ marginTop: 14 }}>
          <dt>Intent</dt>
          <dd>
            <span className="badge intent">{intentLabel(s.intent)}</span>{' '}
            <span className="num">{fmtPct(s.confidence)} confident</span>
          </dd>
          <dt>Priority</dt>
          <dd>
            <span className={`badge ${priorityFor(s.intent)}`}>{priorityFor(s.intent)}</span>
          </dd>
          <dt>First-response target</dt>
          <dd className="num">{targetFor(s.intent)}</dd>
          <dt>Draft</dt>
          <dd style={{ fontWeight: 400, color: '#52707c' }}>
            The {intentLabel(s.intent)} template reply is attached for human review — nothing sends automatically.
          </dd>
        </dl>
        <p className="gate-note">
          In production this runs per message as it lands in the shared inbox: classify → score the
          SLA clocks → recommend the action. The classifier is TF-IDF + MultinomialNB trained on
          deterministic keyword seed labels — reproducible on every run, no LLM required.
        </p>
      </div>
    </div>
  );
}

function priorityFor(intent: string): string {
  if (['billing', 'account_access', 'cancellation'].includes(intent)) return 'P1';
  if (['technical', 'dm_handoff'].includes(intent)) return 'P2';
  return 'P3';
}

function targetFor(intent: string): string {
  const p = priorityFor(intent);
  return p === 'P1' ? '1 hour' : p === 'P2' ? '4 hours' : '24 hours';
}
