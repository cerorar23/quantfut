import assert from 'node:assert/strict';
import test from 'node:test';
import { loadAgenda, loadFicha, localDay, tzMinutes } from './fichas-data.js';

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
