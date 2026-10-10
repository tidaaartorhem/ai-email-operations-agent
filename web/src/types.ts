export interface Turn {
  speaker: 'customer' | 'brand';
  text: string;
  created_at: string;
}

export interface Draft {
  body: string;
  intent: string;
  confidence: number;
  cited_from: string;
  human_gate: boolean;
}

export type RiskBucket = 'breached' | 'at_risk' | 'on_track';
export type ActionKind = 'reply' | 'escalate' | 'merge' | 'close' | 'monitor';
export type ThreadState = 'needs_response' | 'awaiting_customer';

export interface QueueRow {
  thread_id: string;
  intent: string;
  intent_confidence: number;
  priority: 'P1' | 'P2' | 'P3';
  state: ThreadState;
  risk_bucket: RiskBucket;
  breach_risk: number;
  first_customer: string;
  created_at: string;
  last_turn_at: string;
  turn_count: number;
  first_response_min: number | null;
  first_response_human: string | null;
  fr_target_min: number;
  res_target_min: number;
  queue_age_min: number;
  queue_age_human: string | null;
  response_clock_min: number | null;
  dead_air_min: number | null;
  close_candidate: boolean;
  silent_breach: boolean;
  action: ActionKind;
  action_confidence: number;
  action_reason: string;
  merge_with: string | null;
  merge_similarity: number | null;
  draft: Draft | null;
  turns: Turn[];
}

export interface IntentRow {
  intent: string;
  threads: number;
  open: number;
  median_first_response_min: number | null;
  median_first_response_human: string | null;
  breach_rate: number;
  priority: string;
}

export interface Analytics {
  totals: {
    threads: number;
    open: number;
    closed: number;
    breached: number;
    at_risk: number;
    on_track: number;
    needs_response: number;
    awaiting_customer: number;
    close_candidates: number;
    silent_breaches: number;
    duplicate_pairs: number;
    auto_archived_promo: number;
    actions: Record<string, number>;
  };
  by_intent: IntentRow[];
  by_hour: { hour: number; threads: number }[];
}

export interface DuplicatePair {
  thread_a: string;
  thread_b: string;
  similarity: number;
  intent_a: string;
  intent_b: string;
  same_intent: boolean;
  text_a: string;
  text_b: string;
}

export interface PasteDemo {
  text: string;
  intent: string;
  confidence: number;
}

export interface Meta {
  project: string;
  generated_at: string;
  corpus: string;
  corpus_as_of: string;
  replay_note: string;
  classifier: string;
  queue_limit: number;
  deterministic: boolean;
}
