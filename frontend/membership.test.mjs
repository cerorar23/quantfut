import test from 'node:test';
import assert from 'node:assert/strict';
import { DEFAULT_PLAN, membershipQuote, membershipMoney } from './membership.js';

// Mismo formato que GET /app/v1/plans (precios de db/043).
const PLANS = [
  { plan_code: 'plus_1m', name: 'Plus · 1 mes', duration_days: 30, price_cents: 1499, currency: 'USD' },
  { plan_code: 'plus_3m', name: 'Plus · 3 meses', duration_days: 90, price_cents: 3399, currency: 'USD' },
  { plan_code: 'plus_6m', name: 'Plus · 6 meses', duration_days: 180, price_cents: 5399, currency: 'USD' },
  { plan_code: 'club', name: 'Club QuantFut', duration_days: null, price_cents: 17999, currency: 'USD' },
];

test('los importes salen tal cual del servidor', () => {
  assert.deepEqual(PLANS.map(plan => [plan.plan_code, membershipQuote(PLANS, plan.plan_code).totalCents]), [
    ['plus_1m', 1499], ['plus_3m', 3399], ['plus_6m', 5399], ['club', 17999],
  ]);
  assert.equal(membershipMoney(membershipQuote(PLANS, 'plus_3m').totalCents), '$33.99');
  assert.ok(PLANS.some(plan => plan.plan_code === DEFAULT_PLAN));
});

test('el equivalente mensual deriva del total y de la duración en días', () => {
  assert.equal(membershipQuote(PLANS, 'plus_3m').months, 3);
  assert.equal(membershipMoney(membershipQuote(PLANS, 'plus_3m').monthlyCents), '$11.33');
  assert.equal(membershipMoney(membershipQuote(PLANS, 'plus_6m').monthlyCents), '$9.00');
});

test('el ahorro compara contra el mensual de la misma lista y el club no inventa un coste mensual', () => {
  assert.equal(membershipQuote(PLANS, 'plus_3m').savingsCents, 1098);
  assert.equal(membershipQuote(PLANS, 'plus_6m').savingsCents, 3595);
  assert.equal(membershipQuote(PLANS, 'plus_1m').savingsCents, 0);
  assert.equal(membershipQuote(PLANS, 'club').monthlyCents, null);
  assert.equal(membershipQuote(PLANS, 'club').savingsCents, null);
});

test('un cambio de precio en el panel se refleja sin tocar la web', () => {
  const edited = PLANS.map(plan => plan.plan_code === 'plus_3m' ? { ...plan, price_cents: 2999 } : plan);
  assert.equal(membershipQuote(edited, 'plus_3m').totalCents, 2999);
  assert.equal(membershipQuote(edited, 'plus_3m').monthlyCents, 1000);
  assert.equal(membershipQuote(edited, 'plus_3m').savingsCents, 1498);
});

test('sin plan mensual a la venta no se inventa un ahorro', () => {
  const withoutMonthly = PLANS.filter(plan => plan.plan_code !== 'plus_1m');
  assert.equal(membershipQuote(withoutMonthly, 'plus_3m').savingsCents, null);
});

test('un plan nuevo sin texto propio usa el nombre del panel', () => {
  const extra = [...PLANS, { plan_code: 'plus_12m', name: 'Plus · 12 meses', duration_days: 365, price_cents: 9999, currency: 'USD' }];
  const quote = membershipQuote(extra, 'plus_12m');
  assert.equal(quote.name, 'Plus · 12 meses');
  assert.equal(quote.months, 12);
});

test('un identificador desconocido o retirado de la venta no se convierte en un plan', () => {
  assert.throws(() => membershipQuote(PLANS, ''), RangeError);
  assert.throws(() => membershipQuote(PLANS, 'toString'), RangeError);
  assert.throws(() => membershipQuote(PLANS, 'plus_3m&price=1'), RangeError);
  assert.throws(() => membershipQuote(PLANS.filter(plan => plan.plan_code !== 'club'), 'club'), RangeError);
  assert.throws(() => membershipQuote(null, 'plus_3m'), RangeError);
});
