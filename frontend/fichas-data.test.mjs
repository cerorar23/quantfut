import assert from 'node:assert/strict';
import test from 'node:test';
import { loadAgenda, loadFicha, localDay, tzMinutes, featuredPick } from './fichas-data.js';

test('la agenda pide el día LOCAL con el desfase del visitante', async () => {
  const date = new Date(2026, 8, 27, 12);
  let called;
  const result = await loadAgenda(date, async path => {
    called = path;
    return { ok: true, json: async () => ({ partidos: [] }) };
  });
  const url = new URL(called, 'http://x');
  assert.equal(url.pathname, '/web/partidos');
  assert.equal(url.searchParams.get('fecha'), '2026-09-27');
  assert.equal(url.searchParams.get('tz'), String(tzMinutes(date)));
  assert.equal(result.status, 'ready');
  assert.equal(localDay(date), '2026-09-27');
});

test('la ficha escapa el id y rechaza respuestas incompletas', async () => {
  let called;
  const result = await loadFicha('es.laliga:2627:a/b', async path => {
    called = path;
    return { ok: true, json: async () => ({ partido: {} }) };
  });
  assert.equal(called, '/web/partidos/es.laliga%3A2627%3Aa%2Fb');
  assert.equal(result.status, 'error');
});

test('un fallo de red no se convierte en una agenda vacía', async () => {
  const result = await loadAgenda(new Date(), async () => { throw new Error('red'); });
  assert.deepEqual(result, { status: 'error', data: null });
});

const pick = (id, prob, ref_price, extra = {}) => ({ pick_key: id, match_id: 'm', chain_sha256: 'a'.repeat(64), prob, ref_price, ...extra });

test('el destacado es el de mayor probabilidad con cuota de 1,30 a 1,80', () => {
  const chosen = featuredPick([pick('a', .90, 1.08), pick('b', .74, 1.43), pick('c', .70, 1.55), pick('d', .60, 1.77)]);
  assert.equal(chosen.pick_key, 'b');
});

test('los extremos 1,30 y 1,80 cuentan y lo que queda fuera no', () => {
  assert.equal(featuredPick([pick('lo', .71, 1.30), pick('hi', .60, 1.80)]).pick_key, 'lo');
  assert.equal(featuredPick([pick('bajo', .90, 1.29), pick('alto', .55, 1.81)]), null);
});

test('un pronóstico bloqueado o sin sello nunca es el destacado', () => {
  assert.equal(featuredPick([pick('x', .80, 1.5, { locked: true }), pick('y', .80, 1.5, { chain_sha256: '' })]), null);
  assert.equal(featuredPick(undefined), null);
  assert.equal(featuredPick([pick('z', 'alta', 1.5), pick('w', .7, null)]), null);
});
