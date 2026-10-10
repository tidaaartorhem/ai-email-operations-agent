import { describe, expect, it } from 'vitest';
import { bucketLabel, actionLabel, intentLabel, fmtPct, shortId } from './format';

describe('format helpers', () => {
  it('labels risk buckets', () => {
    expect(bucketLabel('breached')).toBe('Breached');
    expect(bucketLabel('at_risk')).toBe('At risk');
    expect(bucketLabel('on_track')).toBe('On track');
  });

  it('labels actions', () => {
    expect(actionLabel('reply')).toBe('Draft reply');
    expect(actionLabel('escalate')).toBe('Escalate');
    expect(actionLabel('merge')).toBe('Merge threads');
    expect(actionLabel('close')).toBe('Close thread');
    expect(actionLabel('monitor')).toBe('Monitor');
  });

  it('humanizes intent names', () => {
    expect(intentLabel('account_access')).toBe('Account Access');
    expect(intentLabel('billing')).toBe('Billing');
  });

  it('formats percentages', () => {
    expect(fmtPct(0.087)).toBe('8.7%');
    expect(fmtPct(1)).toBe('100.0%');
  });

  it('shortens long thread ids', () => {
    expect(shortId('2302674')).toBe('2302674');
    expect(shortId('1234567890123')).toBe('123456…123');
  });
});
