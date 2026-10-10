import { useEffect, useMemo, useState } from 'react';
import type { Analytics, DuplicatePair, Meta, PasteDemo, QueueRow } from './types';
import { RiskBoard } from './components/RiskBoard';
import { ThreadDetail } from './components/ThreadDetail';
import { Duplicates } from './components/Duplicates';
import { AnalyticsView } from './components/Analytics';
import { TriageLab } from './components/TriageLab';

type Tab = 'board' | 'duplicates' | 'analytics' | 'lab';
type LoadState =
  | { status: 'loading' }
  | {
      status: 'ready';
      queue: QueueRow[];
      analytics: Analytics;
      duplicates: DuplicatePair[];
      samples: PasteDemo[];
      meta: Meta;
    }
  | { status: 'error'; message: string };

async function get<T>(name: string): Promise<T> {
  const res = await fetch(`./${name}`);
  if (!res.ok) throw new Error(`HTTP ${res.status} while fetching ${name}`);
  return (await res.json()) as T;
}

export function App() {
  const [state, setState] = useState<LoadState>({ status: 'loading' });
  const [tab, setTab] = useState<Tab>('board');
  const [selectedId, setSelectedId] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    Promise.all([
      get<QueueRow[]>('queue.json'),
      get<Analytics>('analytics.json'),
      get<DuplicatePair[]>('duplicates.json'),
      get<PasteDemo[]>('paste_demo.json'),
      get<Meta>('meta.json'),
    ])
      .then(([queue, analytics, duplicates, samples, meta]) => {
        if (!cancelled) setState({ status: 'ready', queue, analytics, duplicates, samples, meta });
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setState({ status: 'error', message: err instanceof Error ? err.message : String(err) });
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const byId = useMemo(() => {
    if (state.status !== 'ready') return new Map<string, QueueRow>();
    return new Map(state.status === 'ready' ? state.queue.map((r) => [r.thread_id, r]) : []);
  }, [state]);

  if (state.status === 'loading') return <div className="container loading">Loading the queue…</div>;
  if (state.status === 'error')
    return <div className="container error">Couldn’t load the pipeline bundle: {state.message}</div>;

  const selected = selectedId ? byId.get(selectedId) ?? null : null;
  const replayDate = new Date(state.meta.corpus_as_of).toLocaleDateString('en-US', {
    month: 'short', day: 'numeric', year: 'numeric',
  });

  return (
    <>
      <header className="top">
        <div className="container">
          <h1>Triage <span className="accent">Radar</span></h1>
          <p className="sub">
            The shared-inbox SLA radar — every open thread scored against its first-response and
            resolution clocks. Replaying the queue as it stood on <strong>{replayDate}</strong>,
            from 3,084 real support threads.
          </p>
          <nav className="tabs">
            <button className={tab === 'board' ? 'active' : ''} onClick={() => { setTab('board'); setSelectedId(null); }}>Risk board</button>
            <button className={tab === 'duplicates' ? 'active' : ''} onClick={() => { setTab('duplicates'); setSelectedId(null); }}>
              Duplicates ({state.duplicates.length})
            </button>
            <button className={tab === 'analytics' ? 'active' : ''} onClick={() => { setTab('analytics'); setSelectedId(null); }}>Analytics</button>
            <button className={tab === 'lab' ? 'active' : ''} onClick={() => { setTab('lab'); setSelectedId(null); }}>Triage lab</button>
          </nav>
        </div>
      </header>

      <main className="container">
        {selected ? (
          <ThreadDetail
            row={selected}
            onBack={() => setSelectedId(null)}
            onSelectThread={(id) => setSelectedId(id)}
          />
        ) : tab === 'board' ? (
          <RiskBoard queue={state.queue} analytics={state.analytics} onSelect={(r) => setSelectedId(r.thread_id)} />
        ) : tab === 'duplicates' ? (
          <Duplicates pairs={state.duplicates} byId={byId} onSelect={(r) => setSelectedId(r.thread_id)} />
        ) : tab === 'analytics' ? (
          <AnalyticsView analytics={state.analytics} />
        ) : (
          <TriageLab samples={state.samples} />
        )}
      </main>

      <footer className="foot">
        <div className="container">
          Deterministic pipeline — TF-IDF + Naive Bayes intent triage, rule-based SLA scoring, no LLM calls.
          Corpus: 4,000 real @SpotifyCares support threads (Customer Support on Twitter, via pandarudra/csa).
          Drafts are suggestions only; a human sends every reply.
        </div>
      </footer>
    </>
  );
}
