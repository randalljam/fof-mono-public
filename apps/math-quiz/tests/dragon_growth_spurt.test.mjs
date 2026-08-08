import assert from 'node:assert/strict';
import { describe, it } from 'node:test';
import {
  GROWTH_SPURT_BANDS, adultGrowthScale, growthCameraMul, growthSpurtBandFor, growthSpurtLineFor,
  growthSpurtEligible, growthSpurtPhaseActive, zoomiesPhaseActive,
  resolveGrowthSpurtQuiz, ensureGrowthSpurt,
} from '../dragon/sim/growth_spurt.js';

describe('adultGrowthScale', () => {
  it('stays at 1.0 below 90%', () => {
    assert.equal(adultGrowthScale(80), 1);
    assert.equal(adultGrowthScale(89), 1);
    assert.equal(adultGrowthScale(90), 1);
  });
  it('adds 0.5 per point above 90', () => {
    assert.equal(adultGrowthScale(91), 1.5);
    assert.equal(adultGrowthScale(95), 3.5);
    assert.equal(adultGrowthScale(100), 6);
  });
});
describe('growthCameraMul', () => {
  it('adds 25% of scale growth to camera/follow distance', () => {
    assert.equal(growthCameraMul(1), 1);
    assert.equal(growthCameraMul(1.5), 1.125);
    assert.equal(growthCameraMul(6), 2.25);
  });
});

describe('growth spurt bands', () => {
  it('covers 91–100 with one default line each', () => {
    const bands = Object.keys(GROWTH_SPURT_BANDS).map(Number).sort((a, b) => a - b);
    assert.deepEqual(bands, [91, 92, 93, 94, 95, 96, 97, 98, 99, 100]);
    for (const b of bands) assert.equal(GROWTH_SPURT_BANDS[b].length, 1, `band ${b}`);
  });
  it('clamps band selection', () => {
    assert.equal(growthSpurtBandFor(90), 91);
    assert.equal(growthSpurtBandFor(91), 91);
    assert.equal(growthSpurtBandFor(95.7), 95);
    assert.equal(growthSpurtBandFor(100), 100);
    assert.equal(growthSpurtBandFor(999), 100);
  });
  it('cycles lines within a band', () => {
    const overrides = { 91: ['A', 'B'] };
    assert.equal(growthSpurtLineFor(91, 0, 'Pipa', overrides), 'A');
    assert.equal(growthSpurtLineFor(91, 1, 'Pipa', overrides), 'B');
    assert.equal(growthSpurtLineFor(91, 2, 'Pipa', overrides), 'A');
  });
  it('fills dragon name placeholder', () => {
    const line = growthSpurtLineFor(91, 0, 'Pipa');
    assert.ok(typeof line === 'string' && line.length > 20);
  });
});

describe('growth spurt eligibility', () => {
  it('requires fire milestone and pct >= 91', () => {
    const base = { hatched: true, celebratedIds: ['jump', 'fire'], growthSpurt: { shown: 0 } };
    assert.equal(growthSpurtEligible(base, 90), false);
    assert.equal(growthSpurtEligible(base, 91), true);
    assert.equal(growthSpurtEligible({ hatched: true, celebratedIds: ['jump'] }, 91), false);
  });
  it('detects active phases for GM', () => {
    assert.equal(zoomiesPhaseActive({ hatched: true, celebratedIds: ['jump'] }), true);
    assert.equal(zoomiesPhaseActive({ hatched: true, celebratedIds: ['jump', 'fire'] }), false);
    assert.equal(growthSpurtPhaseActive({ hatched: true, celebratedIds: ['fire'] }), true);
  });
});

describe('resolveGrowthSpurtQuiz', () => {
  it('returns a line on list-complete when eligible', () => {
    const state = { hatched: true, celebratedIds: ['fire'], growthSpurt: { shown: 0 } };
    const r = resolveGrowthSpurtQuiz(state, 'list-complete', 91, 'Pipa');
    assert.equal(r.shown, true);
    assert.ok(r.text);
    assert.equal(ensureGrowthSpurt(state).shown, 1);
  });
  it('skips early quits and low percent', () => {
    const state = { hatched: true, celebratedIds: ['fire'], growthSpurt: { shown: 0 } };
    assert.equal(resolveGrowthSpurtQuiz(state, 'quit', 91, 'Pipa').shown, false);
    assert.equal(resolveGrowthSpurtQuiz(state, 'list-complete', 90, 'Pipa').shown, false);
  });
});
