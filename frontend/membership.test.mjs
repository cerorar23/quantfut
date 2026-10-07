import test from 'node:test';
import assert from 'node:assert/strict';
import { MEMBERSHIP_PLANS, membershipQuote, membershipMoney } from './membership.js';

test('los importes del resumen conservan el total de referencia en centavos', () => {
  assert.deepEqual(MEMBERSHIP_PLANS.map(plan => [plan.id, membershipQuote(plan.id).totalCents]), [
    ['basic', 1499], ['standard', 3399], ['premium', 5399], ['club', 17999],
  ]);
  assert.equal(membershipMoney(membershipQuote('standard').totalCents), '$33.99');
});

test('el equivalente mensual deriva del total, con redondeo de un centavo', () => {
  for (const plan of MEMBERSHIP_PLANS.filter(item => item.months)) {
    const quote = membershipQuote(plan.id);
    assert.ok(Math.abs(quote.monthlyCents * quote.months - quote.totalCents) <= quote.months / 2);
  }
  assert.equal(membershipMoney(membershipQuote('standard').monthlyCents), '$11.33');
  assert.equal(membershipMoney(membershipQuote('premium').monthlyCents), '$9.00');
});

test('el ahorro compara periodos iguales y el club no inventa un coste mensual', () => {
  assert.equal(membershipQuote('standard').savingsCents, 1098);
  assert.equal(membershipQuote('premium').savingsCents, 3595);
  assert.equal(membershipQuote('basic').savingsCents, 0);
  assert.equal(membershipQuote('club').monthlyCents, null);
  assert.equal(membershipQuote('club').savingsCents, null);
});

test('un identificador desconocido no se convierte en un plan cobrable', () => {
  assert.throws(() => membershipQuote(''), RangeError);
  assert.throws(() => membershipQuote('toString'), RangeError);
  assert.throws(() => membershipQuote('standard&price=1'), RangeError);
});
