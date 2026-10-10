import type { DuplicatePair, QueueRow } from '../types';
import { fmtPct, intentLabel, shortId } from '../format';

interface Props {
  pairs: DuplicatePair[];
  byId: Map<string, QueueRow>;
  onSelect: (row: QueueRow) => void;
}

export function Duplicates({ pairs, byId, onSelect }: Props) {
  return (
    <div className="panel">
      <div className="head">
        <h2>Duplicate threads</h2>
        <span className="meta">{pairs.length} pairs · intake-text cosine similarity ≥ 0.55 · merge before anyone double-handles</span>
      </div>
      <div className="body">
        {pairs.map((p, i) => {
          const a = byId.get(p.thread_a);
          const b = byId.get(p.thread_b);
          return (
            <div className="dup-pair" key={i}>
              <div style={{ marginBottom: 8 }}>
                <span className="sim num">{fmtPct(p.similarity)} similar</span>
                {' · '}
                <span className="badge intent">{intentLabel(p.intent_a)}</span>
                {p.same_intent ? (
                  <span className="badge on_track">same intent — strong merge candidate</span>
                ) : (
                  <span className="badge at_risk">different intents — review before merging</span>
                )}
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                <div>
                  <button className="btn" onClick={() => a && onSelect(a)} disabled={!a}>
                    Thread #{shortId(p.thread_a)}
                  </button>
                  <p style={{ fontSize: 13, color: '#52707c' }}>{p.text_a}…</p>
                </div>
                <div>
                  <button className="btn" onClick={() => b && onSelect(b)} disabled={!b}>
                    Thread #{shortId(p.thread_b)}
                  </button>
                  <p style={{ fontSize: 13, color: '#52707c' }}>{p.text_b}…</p>
                </div>
              </div>
            </div>
          );
        })}
        {pairs.length === 0 && <p>No duplicate pairs above the similarity threshold.</p>}
      </div>
    </div>
  );
}
