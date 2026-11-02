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

// --- el destacado sale de TODOS los mercados del partido y la fecha dice si acertó o falló ---------------------------------

// Partido cuyo único pick es de pago (candado): no tiene mercado publicado, pero su destacado sale de todos los mercados y es gratis.
const vipPick = { match_id: 'm1', local: 'Le Havre', visitante: 'PSG', kickoff_utc: kickoff, league_id: 'fr.ligue_1', locked: true };
const sinPicks = { status: 'ready', data: { agenda: home.data.agenda, alta_probabilidad: { proximos: [], vip: [vipPick] }, escalera: null, parley: null } };

function cardsSinPicks(entry, extra = {}) {
  const views = createHubViews({ state: { dayOffset: 0, sport: 'todos', homeSearch: '', homeStatus: 'todos' }, esc: x => String(x ?? ''), ensureHome: () => sinPicks,
    addDays: () => date, localDay: d => d.toISOString().slice(0, 10), dayLabel: () => 'Hoy', realDate: () => '30 oct', realTime: () => '17:30', fmtOdds: String, fmtPct: String,
    dayRail: () => '', liveEvidence: () => '', ensureMatch: () => entry, ...extra });
  return views.home();
}

test('un partido con pick solo de pago enseña igual el destacado de la ficha (todos los mercados son opción)', () => {
  const html = cardsSinPicks({ status: 'ready', data: { ficha: { mercados: { destacado } }, picks: [] } });
  assert.ok(html.includes('Más de 1,5 goles'), 'sin destacado en la tarjeta');
  assert.ok(html.includes('Pronóstico destacado'));
  assert.ok(!html.includes('Contenido reservado'));
});

test('con pick solo de pago: mientras se consulta dice Consultando… y si no hay destacado queda reservado como antes', () => {
  assert.ok(cardsSinPicks({ status: 'loading', data: null }).includes('Consultando…'));
  assert.ok(!cardsSinPicks({ status: 'loading', data: null }).includes('Contenido reservado'));
  for (const entry of [{ status: 'error', data: null }, { status: 'ready', data: { ficha: { mercados: { destacado: null } }, picks: [] } }]) {
    assert.ok(cardsSinPicks(entry).includes('Contenido reservado'));
  }
});

test('la fecha de la tarjeta lleva Acertó, Falló o Devolución cuando el partido ya terminó, y nada si no', () => {
  const con = resultado => cardsSinPicks({ status: 'ready', data: { ficha: { mercados: { destacado: { ...destacado, resultado } } }, picks: [] } });
  for (const [r, texto, clase] of [['win', 'Acertó', 'good'], ['loss', 'Falló', 'warn'], ['push', 'Devolución', 'muted']]) {
    const html = con(r);
    const cabecera = html.slice(html.indexOf('win-pk-when'), html.indexOf('</header>'));
    assert.ok(cabecera.includes('30 oct · 17:30'), 'la fecha sigue en la cabecera');
    assert.ok(cabecera.includes(`<span class="badge ${clase}">${texto}</span>`), `${texto} junto a la fecha`);
  }
  const pendiente = con(undefined);
  assert.ok(!/Acertó|Falló|Devolución/.test(pendiente));
});

test('el pick sellado de un partido ya liquidado también marca el estado en la fecha', () => {
  const sellado = { status: 'ready', data: { ficha: { mercados: { destacado: null } }, picks: [] } };
  const html = cards(sellado);   // cae al pick sellado (sin `outcome`): sin insignia, sin romper la cabecera
  assert.ok(html.includes('win-pk-when') && !/Acertó|Falló/.test(html));
});
