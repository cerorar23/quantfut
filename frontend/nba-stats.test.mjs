import test from 'node:test';
import assert from 'node:assert/strict';
import { loadNbaStats, featuredModelMarket } from './sports-data.js';
import { createSportWindow } from './sports-window.js';

const rec = (won, lost) => ({ won, lost, rate: won + lost ? won / (won + lost) : null });
const row = (date, opponent, home, points, opponent_points) => ({ date, opponent, home, points, opponent_points, won: points > opponent_points });
const team = (name, extra = {}) => ({
  name, conference: 'este', season: rec(3, 1), home: rec(2, 0), away: rec(1, 1), scoring: { games: 4, points_for: 120.3, points_against: 101.5 },
  last6: { ...rec(4, 2), games: 6, points_for: 118, points_against: 105 }, streak: 3, rest_days: 0, back_to_back: true,
  last_season: { ...rec(56, 26), games: 82, points_for: 114.9, points_against: 107.2 }, standing: { rank: 2, of: 15, conference: 'este' },
  form: { all: [row('2026-10-26', 'Chicago <b>Bulls</b>', true, 134, 99), row('2026-10-23', 'New York Knicks', false, 107, 103)],
    home: [row('2026-10-26', 'Chicago <b>Bulls</b>', true, 134, 99)], away: [row('2026-10-23', 'New York Knicks', false, 107, 103)] }, ...extra });
const stats = {
  generated_at: '2026-10-27T11:00:00+00:00', source: 'NBA.com (marcadores oficiales)', as_of: '2026-10-27',
  teams: [team('Boston Celtics'), team('Brooklyn Nets', { season: rec(0, 3), streak: -3, rest_days: 2, back_to_back: false, standing: { rank: 13, of: 15, conference: 'este' } })],
  h2h: { matches: [{ date: '2026-02-27', home: 'Boston Celtics', away: 'Brooklyn Nets', home_points: 148, away_points: 111 }], home_wins: 1, away_wins: 0, average_total: 259 },
};

function windowFor(data, stateExtra = {}, status = 'ready') {
  const start = new Date().toISOString();
  const event = { id: '0022600130', sport: 'nba', home: 'Boston Celtics', away: 'Brooklyn Nets', start, league: 'NBA', status: 'scheduled', seal: 'abc', sealed_at: start, markets: [{ id: 'winner', label: 'Ganador', selection: 'Boston Celtics', market: 'winner', probability: .76, price: null }] };
  const st = { sport: 'nba', winDay: 0, winEvent: '', winLastEvent: null, winPane: 'stats', winSportTab: 'resumen', winSportFam: '', winAll: false, winDayPinned: false, winFormScope: 'all', ...stateExtra };
  const pass = v => String(v);
  const esc = v => String(v).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c]);
  const w = createSportWindow({ state: st, esc, badge: t => `<i>${t}</i>`, fmtPct: p => `${(p * 100).toFixed(1)}%`, fmtOdds: o => o.toFixed(2), realDate: pass, realTime: pass, dateFmt: pass,
    addDays: () => new Date(), localDay: d => new Date(d).toISOString().slice(0, 10), dayLabel: () => 'Hoy', ensureSport: () => ({ status: 'ready', events: [event] }),
    ensureTennisStats: () => ({ status: 'loading', data: null }), ensureNbaStats: () => ({ status, data }), featuredModelMarket });
  return tab => { st.winSportTab = tab; return w.view(); };
}

test('las estadísticas de NBA validan la respuesta y piden el partido por id', async () => {
  let path;
  assert.equal((await loadNbaStats('0022600130', async p => { path = p; return { ok: true, json: async () => stats }; })).status, 'ready');
  assert.equal(path, '/web/deportes/nba/estadisticas/0022600130');
  assert.equal((await loadNbaStats('1', async () => ({ ok: true, json: async () => ({ ...stats, teams: [stats.teams[0]] }) }))).status, 'error');
  assert.equal((await loadNbaStats('1', async () => ({ ok: true, json: async () => ({ ...stats, h2h: {} }) }))).status, 'error');
  assert.equal((await loadNbaStats('1', async () => ({ ok: true, json: async () => ({ ...stats, teams: [{ ...stats.teams[0], form: { all: [] } }, stats.teams[1]] }) }))).status, 'error');
  assert.equal((await loadNbaStats('1', async () => ({ ok: false, status: 404 }))).status, 'error');
  assert.equal((await loadNbaStats('1', async () => { throw new Error('red'); })).status, 'error');
});

test('la ventana de NBA ofrece comparativa, forma, cara a cara y clasificación con datos reales', () => {
  const view = windowFor(stats);
  const tabs = view('resumen');
  for (const label of ['Comparativa', 'Forma', 'Cara a cara', 'Clasificación', 'Disponibilidad', 'Resultado', 'Registro']) assert.ok(tabs.includes(label), label);
  const compare = view('comparativa');
  assert.ok(compare.includes('COMPARATIVA') && compare.includes('Récord de la temporada') && compare.includes('3-1') && compare.includes('0-3'));
  assert.ok(compare.includes('Back-to-back') && compare.includes('2 días libres') && compare.includes('3 victorias') && compare.includes('3 derrotas'));
  assert.ok(compare.includes('#2 Este') && compare.includes('#13 Este') && compare.includes('+18.8'));
  const form = view('forma');
  assert.ok(form.includes('FORMA RECIENTE') && form.includes('134-99') && form.includes('26/10/26') && form.includes('@ New York Knicks'));
  const h2h = view('h2h');
  assert.ok(h2h.includes('CARA A CARA') && h2h.includes('148-111') && h2h.includes('259'));
  const table = view('clasificacion');
  assert.ok(table.includes('CLASIFICACIÓN') && table.includes('Conferencia Este') && table.includes('3V') && table.includes('3D'));
});

test('el filtro de forma muestra solo casa o solo fuera y escapa los nombres', () => {
  const view = windowFor(stats, { winFormScope: 'home' });
  const home = view('forma');
  assert.ok(home.includes('vs Chicago &lt;b&gt;Bulls&lt;/b&gt;') && !home.includes('<b>Bulls</b>') && !home.includes('@ New York Knicks'));
  assert.ok(home.includes('data-win-form-scope="away"') && home.includes('aria-pressed="true"'));
  assert.ok(windowFor(stats, { winFormScope: 'away' })('forma').includes('@ New York Knicks'));
});

test('con el orden invertido en el feed la ficha sigue mostrando local y visitante correctos', () => {
  const swapped = { ...stats, teams: [stats.teams[1], stats.teams[0]], h2h: { ...stats.h2h, home_wins: 0, away_wins: 1 } };
  const view = windowFor(swapped);
  assert.ok(view('comparativa').includes('<b class="is-better">3-1'));                              // el récord 3-1 de Boston sigue en el lado local
  assert.match(view('h2h'), /<strong>1<\/strong><span>Boston Celtics<\/span><span>Brooklyn Nets<\/span><strong>0<\/strong>/);
});

test('sin estadísticas la ventana lo dice y no inventa cifras', () => {
  for (const status of ['loading', 'error']) {
    const html = windowFor(null, {}, status)('forma');
    assert.ok(html.includes('ESTADÍSTICAS DE LOS EQUIPOS') && !html.includes('FORMA RECIENTE'));
  }
  assert.ok(windowFor(null, {}, 'error')('clasificacion').includes('Todavía no hay estadísticas'));
});
