import test from 'node:test';
import assert from 'node:assert/strict';
import { createHubViews } from './ergonomic-views.js';

// Partido de fútbol con un pick sellado de cuota 1,07 (alta probabilidad) y un destacado distinto en su ficha.
const date = new Date('2026-10-30T12:00:00Z');
const kickoff = '2026-10-30T23:30:00Z';
const pick = { match_id: 'm1', pick_key: 'k1', local: 'Le Havre', visitante: 'PSG', kickoff_utc: kickoff, texto: 'Marca PSG', prob: .94, ref_price: 1.02, ref_book: 'jazzsports', chain_sha256: 'abc', batch_date: '2026-10-30' };
const home = { status: 'ready', data: { agenda: [{ match_id: 'm1', kickoff_utc: kickoff, liga: { nombre: 'Ligue 1' }, local: { nombre: 'Le Havre' }, visitante: { nombre: 'PSG' } }], alta_probabilidad: { proximos: [pick], vip: [] } } };
const destacado = { seleccion: 'Más de 1,5 goles', prob: .72, cuota: 1.41, cuota_tipo: 'justa', titulo: 'Goles totales' };

function cards(entry) {
  const views = createHubViews({ state: { dayOffset: 0, sport: 'todos', homeSearch: '', homeStatus: 'todos' }, esc: x => String(x ?? ''), ensureHome: () => home,
    addDays: () => date, localDay: d => d.toISOString().slice(0, 10), dayLabel: () => 'Hoy', realDate: () => '30 oct', realTime: () => '17:30', fmtOdds: String, fmtPct: String,
    dayRail: () => '', liveEvidence: () => '', ensureMatch: () => entry });
  return views.home();
}

test('la tarjeta de fútbol enseña el destacado de la ficha, no el pick sellado', () => {
  const html = cards({ status: 'ready', data: { ficha: { mercados: { destacado } }, picks: [] } });
  assert.ok(html.includes('Más de 1,5 goles'));
  assert.ok(html.includes('Pronóstico destacado'));
  assert.ok(html.includes('Cuota del modelo'));
  assert.ok(!html.includes('Marca PSG'));
});

test('si el destacado es el pick sellado se conservan su cuota publicada y su casa', () => {
  const sealed = { ...destacado, seleccion: 'Marca PSG', prob: .94, cuota: 1.5, cuota_tipo: 'publicada', pick_key: 'k1' };
  const html = cards({ status: 'ready', data: { ficha: { mercados: { destacado: sealed } }, picks: [pick] } });
  assert.ok(html.includes('Cuota publicada'));
  assert.ok(html.includes('jazzsports'));
});

test('mientras se consulta no sale el pick sellado y si falla o no hay destacado vuelve a él', () => {
  const loading = cards({ status: 'loading', data: null });
  assert.ok(loading.includes('Consultando…'));
  assert.ok(!loading.includes('Marca PSG'));
  for (const entry of [{ status: 'error', data: null }, { status: 'ready', data: { ficha: { mercados: { destacado: null } }, picks: [] } }]) {
    const html = cards(entry);
    assert.ok(html.includes('Marca PSG'));
    assert.ok(html.includes('Cuota publicada'));
  }
});
