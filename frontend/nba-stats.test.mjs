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
  temporada: '2026-27', fecha: '2026-10-27', games_used: 40,
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

test('las estadísticas de NBA validan la respuesta y piden el partido por id a la API v2', async () => {
  let path;
  assert.equal((await loadNbaStats(1290, async p => { path = p; return { ok: true, json: async () => stats }; })).status, 'ready');
  assert.equal(path, '/nba/v1/partido/1290/estadisticas');
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

function v2Window(event, entry, marketsEntry, stateExtra = {}) {
  const st = { sport: 'nba', winDay: 0, winEvent: '', winLastEvent: null, winPane: 'pron', winSportTab: 'resumen', winSportFam: '', winAll: false, winDayPinned: false, winFormScope: 'all', ...stateExtra };
  const esc = v => String(v).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c]);
  const pass = v => String(v);
  const asked = [];
  const w = createSportWindow({ state: st, esc, badge: t => `<i>${t}</i>`, fmtPct: p => `${(p * 100).toFixed(1)}%`, fmtOdds: o => o.toFixed(2), realDate: pass, realTime: pass, dateFmt: pass,
    addDays: () => new Date(event.start), localDay: d => new Date(d).toISOString().slice(0, 10), dayLabel: () => 'Hoy', ensureSport: () => ({ status: 'ready', events: [event] }),
    ensureTennisStats: () => ({ status: 'loading', data: null }), ensureNbaStats: id => { asked.push(id); return entry; }, ensureNbaMarkets: () => marketsEntry, featuredModelMarket });
  return { view: tab => { st.winSportTab = tab; return w.view(); }, asked };
}

test('un partido v2 sin pronóstico omite la tarjeta de sellado y pide estadísticas solo al abrir esa pestaña', () => {
  const soon = new Date(Date.now() + 5 * 36e5).toISOString(), planned = new Date(Date.now() + 4 * 36e5).toISOString();
  const event = { id: 3, v2: true, sport: 'nba', home: 'Boston Celtics', away: 'Brooklyn Nets', start: soon, planned_seal: planned, league: 'NBA', status: 'scheduled', markets: [], seal: null, sealed_at: null,
    score: null, availability: null };
  const html = v2Window(event, { status: 'ready', data: stats });
  const card = html.view('resumen');
  assert.ok(!card.includes('CUÁNDO SE AGREGA EL PRONÓSTICO') && !card.includes('Pronóstico pendiente') && !card.includes('win-seal'));
  assert.ok(!card.includes('win-step') && !card.includes('Calendario recibido') && !card.includes('Sin pronóstico destacado'));
  assert.deepEqual(html.asked, []);                                                                       // el resumen no consulta estadísticas
  const compare = html.view('comparativa');
  assert.ok(compare.includes('3-1') && compare.includes('Temporada regular 2026-27') && compare.includes('40 marcadores finales') && compare.includes('Récord de la temporada pasada') && compare.includes('56-26'));
  assert.deepEqual(html.asked, [3]);
  assert.ok(html.view('registro').includes('Aún no hay sello'));
  assert.ok(html.view('h2h').includes('Solo temporada regular'));
});

test('mientras llegan las estadísticas del servidor la ventana lo dice y no inventa cifras', () => {
  const event = { id: 5, v2: true, sport: 'nba', home: 'Boston Celtics', away: 'Brooklyn Nets', start: new Date().toISOString(), planned_seal: null, league: 'NBA', status: 'scheduled', markets: [], seal: null, sealed_at: null, score: null, availability: null };
  const html = v2Window(event, { status: 'loading', data: null }).view('comparativa');
  assert.ok(html.includes('Consultando los marcadores de la temporada') && !html.includes('COMPARATIVA'));
});

test('un partido v2 ya jugado sin sello no inventa un pronóstico a posteriori', () => {
  const start = new Date(Date.now() - 5 * 36e5).toISOString();
  const event = { id: 4, v2: true, sport: 'nba', home: 'Boston Celtics', away: 'Brooklyn Nets', start, planned_seal: new Date(Date.parse(start) - 36e5).toISOString(), league: 'NBA', status: 'finished',
    markets: [], seal: null, sealed_at: null, score: '100 – 90', availability: null };
  const card = v2Window(event, { status: 'ready', data: stats }).view('resumen');
  assert.ok(!card.includes('win-seal') && !card.includes('Sin pronóstico destacado') && !card.includes('data-win-sport-fam'));
});

test('la ficha muestra el destacado de jugadores, sus mercados y proyecciones sin la tarjeta de sellado', () => {
  const start = new Date().toISOString();
  const market = { id: 'player-1', market: 'player_points', player: 'Jugador <b>', player_id: 10, label: 'Puntos del jugador', selection: 'Jugador <b> · Más de 20.5',
    probability: .702, price: 1.44, book: 'bovada', line: 20.5, conditional: true, sealed_at: new Date(Date.now() - 3600000).toISOString(), eligible: true, revised: false, outcome: 'loss' };
  const event = { id: 4, v2: true, sport: 'nba', home: 'Boston Celtics', away: 'Brooklyn Nets', start, league: 'NBA', status: 'scheduled', markets: [], seal: 'abc', sealed_at: market.sealed_at };
  const entry = { status: 'ready', markets: [market], projections: [{ player: 'Jugador <b>', team: 'Boston Celtics', market: 'rebotes', estimate: 7.5, p10: 3, p90: 11, p_juega: .95 }] };
  const html = v2Window(event, { status: 'ready', data: stats }, entry).view('resumen');
  assert.ok(html.includes('PRONÓSTICO DESTACADO') && html.includes('Más de 20.5') && html.includes('Proyecciones de jugadores') && html.includes('Rebotes'));
  assert.ok(html.includes('Jugador &lt;b&gt;') && !html.includes('Jugador <b>'));
  const table = html.match(/<tbody>([\s\S]*?)<\/tbody>/)[1];
  assert.ok(table.includes('70.2%') && table.includes('1.44') && table.includes('Bovada') && table.includes('Falló'));
  assert.ok(table.includes('Pronóstico destacado') && !table.includes('>Destacado</'));
  assert.ok(html.includes('Cuota de la casa') && !html.includes('>1.42<'));
  assert.ok(!html.includes('win-seal') && !html.includes('CUÁNDO SE AGREGA EL PRONÓSTICO'));
  for (const status of ['loading', 'error']) {
    const pending = v2Window(event, { status: 'ready', data: stats }, { status }).view('resumen');
    assert.ok(pending.includes(status === 'loading' ? 'Cargando mercados' : 'No se pudieron cargar los mercados'));
    assert.ok(!pending.includes('Sin pronóstico destacado') && !pending.includes('Ningún mercado'));
  }
});

test('Partido filtra desde cuota 1,20 y ordena por probabilidad sin limitar el destacado', () => {
  const start = new Date().toISOString(), sealed_at = new Date(Date.now() - 3600000).toISOString();
  const event = { id: 4, v2: true, sport: 'nba', home: 'Boston Celtics', away: 'Brooklyn Nets', start, league: 'NBA', status: 'scheduled', markets: [], seal: 'abc', sealed_at };
  const m = (id, probability, price) => ({ id, market: 'handicap', label: 'Hándicap', selection: id, probability, price, book: 'fanduel', sealed_at });
  const entry = { status: 'ready', markets: [m('demasiado-baja', .995, 1.001), m('antes-de-redondear', .98, 1.199), m('probabilidad-alta', .83, 1.2), m('probabilidad-menor', .75, 1.3), m('destacado-sin-tope', .7, 5.5)], projections: [] };
  const html = v2Window(event, { status: 'ready', data: stats }, entry).view('resumen');
  const table = html.match(/<tbody>([\s\S]*?)<\/tbody>/)[1];
  assert.ok(!table.includes('demasiado-baja') && !table.includes('antes-de-redondear'));
  assert.ok(table.indexOf('probabilidad-alta') < table.indexOf('probabilidad-menor'));
  assert.ok(html.includes('5.50') && html.includes('Cuotas ≥ 1,20') && html.includes('Todas las cuotas'));
  const all = v2Window(event, { status: 'ready', data: stats }, entry, { winAllOdds: true }).view('resumen');
  assert.ok(all.includes('demasiado-baja') && all.includes('antes-de-redondear'));
});

test('los mercados de jugadores agrupan líneas, usan el id oficial de foto y permiten buscar', () => {
  const start = new Date().toISOString(), sealed_at = new Date(Date.now() - 3600000).toISOString();
  const event = { id: 4, v2: true, sport: 'nba', home: 'Boston Celtics', away: 'Brooklyn Nets', start, league: 'NBA', status: 'scheduled', markets: [], seal: 'abc', sealed_at };
  const m = (id, player, player_id, photo_id, probability) => ({ id, player, player_id, photo_id, probability, market: 'player_points', label: 'Puntos', selection: `Más de ${id} puntos`, price: 1.8, book: 'fanduel', sealed_at, estimate: 25, conditional: true });
  const entry = { status: 'ready', markets: [m(1, 'LeBron James', 10, 2544, .75), m(2, 'LeBron James', 10, 2544, .7), m(3, 'LeBron James', 10, 2544, .68), m(4, 'LeBron James', 10, 2544, .66), m(5, 'Otro Jugador', 11, 201939, .65)], projections: [] };
  const extra = { winEvent: 'nba:4', winLastEvent: 'nba:4', winSportFam: 'Puntos' };
  const html = v2Window(event, { status: 'ready', data: stats }, entry, extra).view('resumen');
  assert.equal(html.split('<h4>LeBron James</h4>').length - 1, 1);
  assert.ok(html.includes('/web/imagenes/jugadores/nba/2544.png') && !html.includes('/web/imagenes/jugadores/nba/10.png'));
  assert.ok(html.includes('Ver 1 línea más') && html.includes('Más de 4 puntos') && html.includes('Buscar jugador o equipo'));
  const search = v2Window(event, { status: 'ready', data: stats }, entry, { ...extra, winPlayerSearch: 'lébron' }).view('resumen');
  assert.ok(search.includes('<h4>LeBron James</h4>') && !search.includes('<h4>Otro Jugador</h4>'));
});
