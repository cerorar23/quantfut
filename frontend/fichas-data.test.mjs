import assert from 'node:assert/strict';
import test from 'node:test';
import { loadAgenda, loadFicha, localDay, tzMinutes, featuredMarket } from './fichas-data.js';

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

const destacado = (extra = {}) => ({ id: 'totals:over:2.5', grupo: 'GOLES', seleccion: 'Más de 2,5 goles', prob: .66, cuota: 1.52, cuota_tipo: 'justa', locked: false, destacado: true, ...extra });

test('el destacado de la web es el que elige el servidor, validado', () => {
  assert.equal(featuredMarket({ destacado: destacado() }).seleccion, 'Más de 2,5 goles');
  assert.equal(featuredMarket({ filas: [] }), null);
  assert.equal(featuredMarket(null), null);
});

test('un destacado bloqueado o con datos inválidos no se enseña', () => {
  assert.equal(featuredMarket({ destacado: destacado({ locked: true }) }), null);
  assert.equal(featuredMarket({ destacado: destacado({ seleccion: '' }) }), null);
  assert.equal(featuredMarket({ destacado: destacado({ prob: 'alta' }) }), null);
  assert.equal(featuredMarket({ destacado: destacado({ prob: 1.2 }) }), null);
  assert.equal(featuredMarket({ destacado: destacado({ cuota: null }) }), null);
});
