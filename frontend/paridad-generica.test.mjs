import test from 'node:test';
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { readFileSync, writeFileSync, existsSync } from 'node:fs';
import { createSportWindow } from './sports-window.js';
import { createHubViews } from './ergonomic-views.js';
import { nbaV2Events, tennisEvents, loadSportWeb, loadSport, nbaCode, featuredModelMarket } from './sports-data.js';

// PARIDAD (Fase 4 · 4.4): NBA, tenis y el hub producen EXACTAMENTE el mismo marcado y las mismas peticiones que antes de añadir
// la pantalla genérica. `paridad-generica.golden.json` guarda la huella SHA-256 de cada salida, generada con el código de
// `origin/main` previo a 4.4 (`GENERAR_GOLDEN=1 node --test paridad-generica.test.mjs` la regenera: solo si el marcado cambia a propósito).
const GOLDEN = new URL('./paridad-generica.golden.json', import.meta.url);
const SELLO = 'a'.repeat(64);
const DIA = new Date('2026-10-30T18:00:00Z');
const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);
const pass = v => String(v);
const base = {
  esc, badge: (t, k) => `<i data-k="${k ?? ''}">${t}</i>`, fmtPct: p => `${(p * 100).toFixed(1)}%`, fmtOdds: o => Number(o).toFixed(2), realDate: pass, realTime: pass,
  dateFmt: d => (d instanceof Date ? d.toISOString() : String(d)), addDays: () => DIA, localDay: d => new Date(d).toISOString().slice(0, 10), dayLabel: () => 'Hoy',
};

// ── NBA (API v2) y tenis, todos el 30-oct-2026 (siempre en el pasado: el estado no depende de la hora de la prueba) ──
const partido = (id, inicio, resultado, pick) => ({ id, fecha: '2026-10-30', local: { codigo: 'BOS', nombre: 'Boston Celtics' }, visitante: { codigo: 'NYK', nombre: 'New York Knicks' },
  inicio_utc: inicio, sello_previsto: '2026-10-30T10:00:00Z', resultado, pronostico: pick });
const NBA = nbaV2Events([
  partido(11, '2026-10-30T00:30:00Z', { local: 110, visitante: 100 }, { hash: SELLO, p_local: 0.7, sellado_en: '2026-10-29T22:00:00Z', mu: [111.2, 104.5] }),
  partido(12, '2026-10-30T02:00:00Z', null, { hash: SELLO, p_local: 0.4, sellado_en: '2026-10-29T22:00:00Z' }),
  partido(13, '2026-10-30T03:00:00Z', null, null),
], new Date('2026-10-30T20:00:00Z'));
const mk = (over) => ({ id: 'x', label: 'Mercado', selection: 'Sel', probability: 0.6, price: null, reference: 'Probabilidad estadística', estimate: null, sealed_at: '2026-10-29T22:00:00Z',
  eligible: true, revised: false, outcome: null, conditional: false, market: 'winner', player: null, player_id: null, line: null, ...over });
const NBA_MERCADOS = { status: 'ready', destacado: 'winner-11', projections: [{ market: 'puntos', player_id: 7, player: 'Jayson Tatum', team: 'Boston Celtics', estimate: 27.3, p10: 20, p50: 27, p90: 34, p_juega: 0.96, sealed_at: '2026-10-29T22:00:00Z' }],
  markets: [mk({ id: 'winner-11', label: 'Ganador del partido', selection: 'Boston Celtics', probability: 0.78, outcome: 'win', price: 1.3, book: 'pinnacle' }),
    mk({ id: 'total-11', label: 'Total del partido', selection: 'Más de 215.5 puntos', probability: 0.55, market: 'game_total', line: 215.5, outcome: 'loss' }),
    mk({ id: 'pp-11', label: 'Puntos de Jayson Tatum', selection: 'Más de 24.5 puntos', probability: 0.63, market: 'player_points', player: 'Jayson Tatum', player_id: 7, team: 'Boston Celtics', line: 24.5, estimate: 27.3, price: 1.9, book: 'fanduel' }),
    mk({ id: 'pr-11', label: 'Rebotes de Jayson Tatum', selection: 'Más de 7.5 rebotes', probability: 0.51, market: 'player_rebounds', player: 'Jayson Tatum', player_id: 7, team: 'Boston Celtics', line: 7.5, push_probability: 0.05 })] };
const TENIS = tennisEvents({ state: 'ok', events: [
  { id: 't-1', sport: 'tenis', home: 'Ana Pérez', away: 'Bea Luz', start: '2026-10-30T10:00:00Z', league: 'WTA · Basilea', surface: 'Pista dura', sealed_at: '2026-10-30T06:00:00Z', seal: SELLO, status: 'finished',
    score: '6-4 6-3', actionable: false, destacado: { id: 'winner' }, markets: [
      { id: 'winner', label: 'Ganador del partido', selection: 'Ana Pérez', probability: 0.61, price: 1.55, book: 'Pinnacle', price_book: 'Pinnacle', reference: 'Pinnacle · referencia previa al sello', outcome: 'win' },
      { id: 'sets_total-1', label: 'Sets totales', selection: 'Menos de 2.5', probability: 0.62, price: null, reference: 'Probabilidad del motor', outcome: 'win' },
      { id: 'games_total-1', label: 'Juegos totales', selection: 'Más de 18.5', probability: 0.55, price: null, reference: 'Probabilidad del motor', outcome: 'loss' },
      { id: 'tiebreak-1', label: 'Tie-break en el partido', selection: 'No', probability: 0.7, price: null, reference: 'Probabilidad del motor', outcome: null }] },
  { id: 't-2', sport: 'tenis', home: 'Cy Ríos', away: 'Dan Sol', start: '2026-10-30T12:00:00Z', league: 'ATP · Basilea', surface: 'Arcilla', sealed_at: '2026-10-30T06:00:00Z', seal: SELLO, status: 'scheduled',
    score: null, actionable: false, destacado: null, markets: [{ id: 'winner', label: 'Ganador del partido', selection: 'Dan Sol', probability: 0.58, price: null, reference: 'Probabilidad del motor', outcome: null }] },
] });
const FOOT = { status: 'ready', data: { agenda: [{ match_id: 'm1', kickoff_utc: '2026-10-30T23:30:00Z', liga: { nombre: 'Ligue 1' }, local: { nombre: 'Le Havre' }, visitante: { nombre: 'PSG' } }],
  alta_probabilidad: { proximos: [{ match_id: 'm1', pick_key: 'k1', local: 'Le Havre', visitante: 'PSG', kickoff_utc: '2026-10-30T23:30:00Z', texto: 'Marca PSG', prob: 0.94, ref_price: 1.02, ref_book: 'jazzsports', chain_sha256: 'abc', batch_date: '2026-10-30' }], vip: [] } } };

function ventana(extra = {}) {
  const st = { sport: 'nba', winDay: 0, winDayPinned: true, winEvent: '', winLastEvent: extra.winEvent ?? null, winEvList: [], winSportTab: 'resumen', winSportFam: '', winFormScope: 'all', winAll: false,
    winAllOdds: false, winPlayerSearch: '', winPane: 'pron', ...extra };
  const entries = { nba: { status: 'ready', events: NBA }, tenis: { status: 'ready', events: TENIS }, ...(extra.entries || {}) };
  const w = createSportWindow({ ...base, state: st, ensureSport: s => entries[s] || { status: 'loading', events: [] }, ensureTennisStats: () => ({ status: 'loading', data: null }),
    ensureNbaStats: () => ({ status: 'loading', data: null }), ensureNbaMarkets: () => NBA_MERCADOS, featuredModelMarket, ensureImages: () => ({ status: 'ready', nba: {}, tenis: {} }), nbaCode });
  return w;
}
function hub(sport = 'todos', extra = {}) {
  const st = { dayOffset: 0, sport, homeSearch: '', homeStatus: 'todos', resultSport: 'todos', ...extra };
  const entries = { nba: { status: 'ready', events: NBA }, tenis: { status: 'ready', events: TENIS } };
  return createHubViews({ ...base, state: st, ensureHome: () => FOOT, ensureSport: s => entries[s] || { status: 'loading', events: [] }, ensureResults: () => ({ status: 'ready', items: [], featured: [] }),
    ensureMatch: () => ({ status: 'error', data: null }), ensureImages: () => ({ status: 'ready', nba: {}, tenis: {} }), ensureNbaMarkets: () => NBA_MERCADOS, nbaCode, dayRail: () => '', plansPreview: () => '' });
}

async function peticiones(sport, contrato) {
  const urls = [];
  // el desfase horario (tz=) depende de la zona de quien corre la prueba: se normaliza
  const fetcher = async url => { urls.push(String(url).replace(/tz=-?\d+/, 'tz=N')); return { ok: false, status: 503, json: async () => ({}) }; };
  const aviso = console.warn; console.warn = () => {};
  try { await loadSportWeb(sport, fetcher, new Date(2026, 10, 12, 12), contrato ? { contrato } : undefined); } finally { console.warn = aviso; }
  return urls;
}

async function salidas() {
  const out = {};
  for (const tab of ['resumen', 'comparativa', 'forma', 'h2h', 'clasificacion', 'disponibilidad', 'resultado', 'registro']) {
    out[`nba:ventana:${tab}`] = ventana({ sport: 'nba', winSportTab: tab, winEvent: 'nba:11' }).view();
  }
  out['nba:ventana:sin-pronostico'] = ventana({ sport: 'nba', winEvent: 'nba:13' }).view();
  out['nba:ventana:revision'] = ventana({ sport: 'nba', winEvent: 'nba:12', winSportFam: 'Puntos', winAllOdds: true }).view();
  out['nba:ventana:jugadores'] = ventana({ sport: 'nba', winEvent: 'nba:11', winSportFam: 'Puntos' }).view();
  out['nba:ventana:cargando'] = ventana({ sport: 'nba', entries: { nba: { status: 'loading', events: [] } } }).view();
  out['nba:ventana:error'] = ventana({ sport: 'nba', entries: { nba: { status: 'error', events: [] } } }).view();
  for (const tab of ['resumen', 'forma', 'superficie', 'h2h', 'modelo', 'resultado']) {
    out[`tenis:ventana:${tab}`] = ventana({ sport: 'tenis', winSportTab: tab, winEvent: 'tenis:t-1' }).view();
  }
  out['tenis:ventana:otro-partido'] = ventana({ sport: 'tenis', winEvent: 'tenis:t-2', winSportFam: 'Ganador' }).view();
  out['tenis:ventana:vacio'] = ventana({ sport: 'tenis', entries: { tenis: { status: 'ready', events: [] } } }).view();
  for (const sport of ['todos', 'futbol', 'nba', 'tenis']) {
    out[`hub:home:${sport}`] = hub(sport).home();
    out[`hub:picks:${sport}`] = hub(sport).picks();
  }
  out['hub:home:proximos'] = hub('todos', { homeStatus: 'proximos' }).home();
  out['hub:history'] = hub('todos').history();
  out['hub:detail:nba'] = hub('todos', { sportEvent: 'nba:11' }).detail();
  out['hub:detail:tenis'] = hub('todos', { sportEvent: 'tenis:t-1', sportMarket: 'todos' }).detail();
  out['peticiones:nba'] = JSON.stringify(await peticiones('nba'));
  out['peticiones:tenis'] = JSON.stringify(await peticiones('tenis'));
  out['peticiones:nba-contrato'] = JSON.stringify(await peticiones('nba', { nba: true, tenis: false }));
  out['peticiones:tenis-contrato'] = JSON.stringify(await peticiones('tenis', { nba: true, tenis: true }));
  return out;
}
const huella = texto => createHash('sha256').update(texto).digest('hex').slice(0, 16);

test('NBA, tenis y el hub producen el mismo marcado y las mismas peticiones que antes de la pantalla genérica', async () => {
  const actual = Object.fromEntries(Object.entries(await salidas()).map(([k, v]) => [k, `${v.length}:${huella(v)}`]));
  if (process.env.GENERAR_GOLDEN === '1' || !existsSync(GOLDEN)) { writeFileSync(GOLDEN, `${JSON.stringify(actual, null, 1)}\n`); return; }
  const golden = JSON.parse(readFileSync(GOLDEN, 'utf8'));
  assert.deepEqual(Object.keys(actual), Object.keys(golden));
  for (const clave of Object.keys(golden)) assert.equal(actual[clave], golden[clave], `cambió la salida de ${clave}`);
});

test('las salidas de la prueba de paridad no están vacías ni son todas iguales', async () => {
  const salida = await salidas();
  assert.ok(Object.values(salida).every(v => v.length > 20), 'una salida vacía no demuestra nada');
  assert.ok(salida['nba:ventana:resumen'].includes('Boston Celtics') && salida['tenis:ventana:resumen'].includes('Ana Pérez'));
  assert.ok(salida['hub:home:todos'].includes('Marca PSG') && salida['hub:home:todos'].includes('data-sport-event="nba:11"'));
  assert.ok(new Set(Object.values(salida)).size > 30);
});
