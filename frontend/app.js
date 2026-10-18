import { loadPublicData, isPublicationActive, probabilityLabel, expectedHitRate } from './public-data.js?v=5d460d0b0c91';
import { loadAgenda, loadFicha } from './fichas-data.js?v=ab675b7ad4ad';
import { createMembershipUI } from './membership.js?v=6d8c9cd2cacf';

// Datos intencionalmente ficticios. Nunca se mezclan con la API de producción.
// Los precios de la demo se derivan de dos lambdas por partido (Poisson
// independiente) para que la mesa, los picks y la ficha cuadren entre sí.
const now = new Date();
const today = new Date(now);
today.setHours(0, 0, 0, 0);
const HOUR = 3600e3;

const addDays = (offset, hour = 20) => {
  const date = new Date(today);
  date.setDate(date.getDate() + offset);
  date.setHours(hour, 0, 0, 0);
  return date;
};
const inHours = hours => new Date(Math.floor((now.getTime() + hours * HOUR) / (15 * 60e3)) * 15 * 60e3);
const dayOf = date => { const start = new Date(date); start.setHours(0, 0, 0, 0); return Math.round((start - today) / 864e5); };

// Mismo criterio que publish/picks.py, con los valores por defecto de config.py.
const SOFT_MIN_EDGE = 0.02;
const MAX_SHARP_DEVIATION = 0.03;
const SHARP_MARGIN = 0.025;
const BOOKS = [
  { id: 'bet365', name: 'Bet365', margin: 0.052, persistence: 0.62 },
  { id: 'betano', name: 'Betano', margin: 0.061, persistence: 0.48 },
  { id: '1xbet', name: '1xBet', margin: 0.047, persistence: 0.35 },
  { id: 'william_hill', name: 'William Hill', margin: 0.068, persistence: 0.55 },
  { id: '888sport', name: '888sport', margin: 0.064, persistence: 0.41 },
  { id: 'betway', name: 'Betway', margin: 0.058, persistence: 0.44 },
];
const LEAGUES = ['Liga Atlántica · demo', 'Liga Continental · demo', 'Copa Europa · demo'];

const fixtures = [
  { id: 'qf-099', kickoff: addDays(-1, 20), league: 'Liga Continental · demo', home: 'Estrella Azul', away: 'Real Bahía', xg: [1.35, 1.22], note: 'Partido ya disputado: la mesa conserva el último snapshot antes del inicio, que es contra el que se mide el CLV.' },
  { id: 'qf-098', kickoff: inHours(-2), league: 'Liga Atlántica · demo', home: 'Club Faro', away: 'Deportivo Vega', xg: [1.08, 1.41], note: 'El visitante llega con más goles esperados; el mercado ya se cerró al empezar el partido.' },
  { id: 'qf-101', kickoff: inHours(1.5), league: 'Liga Atlántica · demo', home: 'Puerto Norte', away: 'Unión del Sur', xg: [1.64, 0.98], note: 'El modelo favorece al local, pero su opinión no elige picks: manda el precio justo de Pinnacle.' },
  { id: 'qf-106', kickoff: inHours(3), league: 'Copa Europa · demo', home: 'Olímpico Brisa', away: 'Ciudad Alta', xg: [1.52, 1.26], sharpDistort: true, note: 'Pinnacle se aparta del consenso de las demás casas. El criterio trata ese precio como roto y descarta el partido.' },
  { id: 'qf-102', kickoff: inHours(4.5), league: 'Liga Continental · demo', home: 'Real Bahía', away: 'Atlético Sierra', xg: [1.30, 1.11], note: 'Partido de márgenes estrechos: el empate conserva una probabilidad relevante.' },
  { id: 'qf-103', kickoff: addDays(1, 19), league: 'Copa Europa · demo', home: 'Aurora FC', away: 'Sporting Prado', xg: [1.78, 0.91], note: 'La lectura dependerá de las alineaciones confirmadas y del precio disponible antes del inicio.' },
  { id: 'qf-104', kickoff: addDays(1, 21), league: 'Liga Atlántica · demo', home: 'Deportivo Cumbre', away: 'Marina CF', xg: [1.21, 1.18], note: 'Las tres salidas son cercanas; una pantalla real debe comunicar esta incertidumbre.' },
  { id: 'qf-105', kickoff: addDays(2, 18), league: 'Liga Continental · demo', home: 'Río Central', away: 'Estrella Azul', xg: [1.48, 1.07], note: 'Ejemplo de cómo se presentaría el desglose de un mercado de goles.' },
  { id: 'qf-107', kickoff: addDays(2, 20), league: 'Liga Atlántica · demo', home: 'Deportivo Vega', away: 'Puerto Norte', xg: [1.12, 1.36], note: 'Con dos días de antelación los precios aún se moverán; el snapshot manda.' },
];

const archive = [
  { date: addDays(-2, 19), publishedAt: addDays(-3, 13), league: 'Liga Atlántica · demo', match: 'Marina CF · Puerto Norte', market: '1X2', selection: 'Marina CF', book: 'Bet365', price: 2.10, minPrice: 2.04, closePrice: 2.06, result: 'Ganado' },
  { date: addDays(-3, 21), publishedAt: addDays(-4, 14), league: 'Liga Continental · demo', match: 'Atlético Sierra · Río Central', market: '1X2', selection: 'Empate', book: 'Betano', price: 3.45, minPrice: 3.36, closePrice: 3.52, result: 'Perdido' },
  { date: addDays(-4, 20), publishedAt: addDays(-5, 12), league: 'Copa Europa · demo', match: 'Sporting Prado · Aurora FC', market: '1X2', selection: 'Empate', book: 'William Hill', price: 3.30, minPrice: 3.22, closePrice: 3.27, result: 'Perdido' },
  { date: addDays(-5, 18), publishedAt: addDays(-6, 11), league: 'Liga Atlántica · demo', match: 'Unión del Sur · Deportivo Cumbre', market: '1X2', selection: 'Unión del Sur', book: '1xBet', price: 2.05, minPrice: 2.00, closePrice: 2.04, result: 'Ganado' },
  { date: addDays(-6, 20), publishedAt: addDays(-7, 15), league: 'Liga Continental · demo', match: 'Real Bahía · Estrella Azul', market: '1X2', selection: 'Estrella Azul', book: 'Bet365', price: 3.10, minPrice: 3.02, closePrice: 2.95, result: 'Perdido' },
  { date: addDays(-7, 19), publishedAt: addDays(-8, 12), league: 'Copa Europa · demo', match: 'Ciudad Alta · Olímpico Brisa', market: '1X2', selection: 'Ciudad Alta', book: 'Betway', price: 2.62, minPrice: 2.55, closePrice: 2.66, result: 'Perdido' },
  { date: addDays(-8, 21), publishedAt: addDays(-9, 14), league: 'Liga Atlántica · demo', match: 'Deportivo Vega · Club Faro', market: '1X2', selection: 'Deportivo Vega', book: 'Betano', price: 2.38, minPrice: 2.31, closePrice: 2.30, result: 'Ganado' },
];

// ---------------------------------------------------------------- precios

// Generador determinista: la demo enseña los mismos números en cada visita.
function seeded(key) {
  let h = 2166136261;
  for (const char of key) h = Math.imul(h ^ char.charCodeAt(0), 16777619);
  return () => {
    h += 0x6D2B79F5;
    let t = h;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

const sum = values => values.reduce((total, value) => total + value, 0);
const round2 = value => Math.round(value * 100) / 100;

function scoreGrid([lh, la], size = 11) {
  const pmf = lambda => { const out = [Math.exp(-lambda)]; for (let k = 1; k < size; k++) out.push(out[k - 1] * lambda / k); return out; };
  const home = pmf(lh);
  const away = pmf(la);
  return home.map(ph => away.map(pa => ph * pa));
}
const gridProb = (grid, test) => sum(grid.flatMap((row, i) => row.map((p, j) => (test(i, j) ? p : 0))));

function marketGroups(fx, grid) {
  const p = test => gridProb(grid, test);
  const [h, d, a] = [p((i, j) => i > j), p((i, j) => i === j), p((i, j) => i < j)];
  const groups = [
    { family: '1X2', market: '1X2', total: 1, sels: [[fx.home, h], ['Empate', d], [fx.away, a]] },
    { family: 'Doble oportunidad', market: 'Doble oportunidad', total: 2, derived: true, sels: [['1X', h + d], ['12', h + a], ['X2', d + a]] },
  ];
  for (const line of [1.5, 2.5, 3.5]) {
    const over = p((i, j) => i + j > line);
    groups.push({ family: 'Goles', market: `Total ${line}`, total: 1, sels: [[`Más de ${line}`, over], [`Menos de ${line}`, 1 - over]] });
  }
  const btts = p((i, j) => i > 0 && j > 0);
  groups.push({ family: 'Ambos marcan', market: 'Ambos marcan', total: 1, sels: [['Sí', btts], ['No', 1 - btts]] });
  [[fx.home, 0], [fx.away, 1]].forEach(([team, side]) => {
    const line = fx.xg[side] >= 1.3 ? 1.5 : 0.5;
    const over = p((i, j) => (side ? j : i) > line);
    groups.push({ family: 'Por equipo', market: `Goles ${team} ${line}`, total: 1, sels: [[`Más de ${line}`, over], [`Menos de ${line}`, 1 - over]] });
  });
  // Hándicap asiático ±1: ganar por uno exacto devuelve la apuesta.
  const fav = fx.xg[0] >= fx.xg[1] ? 0 : 1;
  const margin = (i, j) => (fav ? j - i : i - j);
  const win = p((i, j) => margin(i, j) >= 2);
  const lose = p((i, j) => margin(i, j) <= 0);
  const [favName, dogName] = fav ? [fx.away, fx.home] : [fx.home, fx.away];
  groups.push({ family: 'Hándicap', market: 'Hándicap asiático ±1', total: 1, sels: [[`${favName} −1`, win / (win + lose)], [`${dogName} +1`, lose / (win + lose)]] });
  return groups;
}

function buildFixture(fx) {
  const rnd = seeded(fx.id);
  fx.grid = scoreGrid(fx.xg);
  fx.closed = fx.kickoff <= now;
  fx.day = dayOf(fx.kickoff);
  fx.snapshot = fx.closed ? new Date(fx.kickoff.getTime() - 5 * 60e3) : new Date(now.getTime() - (4 + Math.floor(rnd() * 30)) * 60e3);
  const rows = [];
  let sharp1x2;
  for (const group of marketGroups(fx, fx.grid)) {
    const model = group.sels.map(sel => sel[1]);
    let truth;
    if (group.derived) {
      truth = [sharp1x2[0] + sharp1x2[1], sharp1x2[0] + sharp1x2[2], sharp1x2[1] + sharp1x2[2]];
    } else {
      const raw = model.map(q => q * Math.exp(0.16 * (rnd() - 0.5)));
      truth = raw.map(q => q / sum(raw) * group.total);
    }
    if (group.market === '1X2') sharp1x2 = truth;
    const pinnacle = truth.map((q, i) => round2(1 / (q * (1 + SHARP_MARGIN)) * (fx.sharpDistort && group.market === '1X2' && i === 0 ? 1.22 : 1)));
    const implied = pinnacle.map(price => 1 / price);
    const fair = implied.map(q => q / sum(implied) * group.total);
    group.sels.forEach(([selection], i) => {
      const quotes = BOOKS.map(book => {
        if (rnd() < 0.14) return { book, price: null };
        const lag = 0.14 * ((rnd() + rnd() + rnd()) / 3 - 0.5) * 2;
        return { book, price: Math.max(1.01, round2(1 / (truth[i] * (1 + book.margin)) * (1 + lag))) };
      });
      rows.push({ key: `${fx.id}:${group.market}:${i}`, fx, family: group.family, market: group.market, selection, pModel: model[i], pFair: fair[i], pinnacle: pinnacle[i], quotes });
    });
  }

  // Pinnacle contra el consenso de las demás casas del mismo snapshot.
  const x12 = rows.filter(row => row.market === '1X2');
  const complete = BOOKS.filter(book => x12.every(row => row.quotes.find(q => q.book === book).price));
  const consensus = x12.map((row, i) => sum(complete.map(book => {
    const inv = x12.map(r => 1 / r.quotes.find(q => q.book === book).price);
    return inv[i] / sum(inv);
  })) / complete.length);
  fx.sharpDeviation = Math.max(...x12.map((row, i) => Math.abs(row.pFair - consensus[i])));
  fx.excluded = fx.sharpDeviation > MAX_SHARP_DEVIATION;

  for (const row of rows) {
    row.best = row.quotes.filter(q => q.price).sort((a, b) => b.price - a.price)[0] || null;
    row.edge = row.best ? row.best.price * row.pFair - 1 : null;
    row.expectedEdge = row.best ? row.edge * row.best.book.persistence : null;
    row.minPrice = (1 + SOFT_MIN_EDGE) / row.pFair;
    row.history = [];
    if (row.best) {
      const start = row.best.price * (1 + 0.07 * (rnd() - 0.5));
      for (let k = 0; k < 8; k++) row.history.push(k === 7 ? row.best.price : start + (row.best.price - start) * k / 7 + 0.012 * (rnd() - 0.5) * row.best.price);
    }
    row.status = fx.closed ? 'cerrado'
      : fx.excluded ? 'excluido'
        : !row.best ? 'sin-cuota'
          : row.family !== '1X2' ? 'referencia'
            : row.edge >= SOFT_MIN_EDGE ? 'candidata' : 'debajo';
  }
  const pct = values => { const out = values.map(v => Math.round(v * 100)); out[1] += 100 - sum(out); return out; };
  fx.probs = pct(x12.map(row => row.pModel));
  fx.marketProbs = pct(x12.map(row => row.pFair));
  fx.rows = rows;
  return rows;
}

const allRows = fixtures.flatMap(buildFixture);
const rowByKey = new Map(allRows.map(row => [row.key, row]));
const fixtureById = new Map(fixtures.map(fx => [fx.id, fx]));

// Sombra del criterio: un pick por partido, la mejor candidata 1X2. El reparto
// gratis/Plus es ilustrativo; el real lo decide picks.assign_tiers() en servidor.
const shadowPicks = fixtures
  .map(fx => fx.rows.filter(row => row.status === 'candidata').sort((a, b) => b.edge - a.edge)[0])
  .filter(Boolean)
  .sort((a, b) => a.fx.kickoff - b.fx.kickoff)
  .map((row, index) => ({ row, tier: index % 2 ? 'plus' : 'free' }));
const pickFor = fx => shadowPicks.find(pick => pick.row.fx === fx);

// ---------------------------------------------------------------- estado

const PREFS_KEY = 'quantfut-demo-prefs';
function loadPrefs() {
  try {
    const raw = JSON.parse(localStorage.getItem(PREFS_KEY)) || {};
    return {
      oddsFormat: raw.oddsFormat === 'us' ? 'us' : 'dec',
      followed: Array.isArray(raw.followed) ? raw.followed.filter(league => LEAGUES.includes(league)) : [...LEAGUES],
    };
  } catch {
    return { oddsFormat: 'dec', followed: [...LEAGUES] };
  }
}
function savePrefs() {
  try { localStorage.setItem(PREFS_KEY, JSON.stringify({ oddsFormat: state.oddsFormat, followed: state.followed })); } catch { /* sin almacenamiento: vale hasta recargar */ }
}

const cyberIcon = body => `<svg class="cyber-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="square" stroke-linejoin="miter" focusable="false">${body}</svg>`;
const NAV_ICONS = {
  home: cyberIcon('<path d="M3 10.5 12 3l9 7.5"/><path d="M5.5 9.5V21h13V9.5M9 21v-7h6v7"/>'),
  clock: cyberIcon('<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3.5 2"/>'),
  grid: cyberIcon('<rect x="3" y="4" width="18" height="16"/><path d="M3 10h18M9 4v16M15 4v16"/>'),
  pick: cyberIcon('<path d="m12 3 8 9-8 9-8-9 8-9Z"/><path d="m8.5 12 2.2 2.2 4.8-5"/>'),
  target: cyberIcon('<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="4"/><path d="M12 1v4M23 12h-4M12 23v-4M1 12h4"/>'),
  rise: cyberIcon('<path d="M4 19V5M4 19h16M7 15l4-4 3 2 6-7"/><path d="M16 6h4v4"/>'),
  combine: cyberIcon('<path d="M12 3v18M3 12h18"/><path d="m5 5 14 14M19 5 5 19" opacity=".35"/>'),
  file: cyberIcon('<path d="M6 3h8l4 4v14H6z"/><path d="M14 3v5h5M9 12h6M9 16h6"/>'),
  history: cyberIcon('<path d="M4 7v5h5"/><path d="M5.5 17a8 8 0 1 0-1-8"/><path d="M12 8v5l3 2"/>'),
  package: cyberIcon('<path d="m4 7 8-4 8 4-8 4-8-4Z"/><path d="M4 7v10l8 4 8-4V7M12 11v10"/>'),
  shield: cyberIcon('<path d="M12 3 20 6v5c0 5-3.4 8.4-8 10-4.6-1.6-8-5-8-10V6l8-3Z"/><path d="m9 12 2 2 4-5"/>'),
  user: cyberIcon('<circle cx="12" cy="8" r="4"/><path d="M4 21c.8-5 3.5-7 8-7s7.2 2 8 7"/>'),
};

const nav = [
  { route: 'inicio', label: 'Inicio', short: 'Inicio', icon: NAV_ICONS.home, group: 'EXPLORAR' },
  { route: 'partidos', label: 'Partidos', short: 'Partidos', icon: NAV_ICONS.clock, group: 'EXPLORAR' },
  { route: 'mercados', label: 'Mercados', short: 'Mesa', icon: NAV_ICONS.grid, group: 'EXPLORAR' },
  { route: 'picks', label: 'Picks', short: 'Picks', icon: NAV_ICONS.pick, group: 'EXPLORAR' },
  { route: 'alta', label: 'Alta probabilidad', short: 'Alta prob.', icon: NAV_ICONS.target, group: 'EXPLORAR' },
  { route: 'escalera', label: 'Reto escalera', short: 'Escalera', icon: NAV_ICONS.rise, group: 'EXPLORAR' },
  { route: 'parley', label: 'Parley del día', short: 'Parley', icon: NAV_ICONS.combine, group: 'EXPLORAR' },
  { route: 'partido', label: 'Ficha demo', short: 'Demo', icon: NAV_ICONS.file, group: 'EXPLORAR' },
  { route: 'historial', label: 'Historial', short: 'Historial', icon: NAV_ICONS.history, group: 'EVIDENCIA' },
  { route: 'paquetes', label: 'Paquetes de picks', short: 'Paquetes', icon: NAV_ICONS.package, group: 'ACCESO' },
  { route: 'planes', label: 'Suscripciones', short: 'Planes', icon: NAV_ICONS.shield, group: 'ACCESO' },
  { route: 'cuenta', label: 'Mi cuenta', short: 'Mi cuenta', icon: NAV_ICONS.user, group: 'ACCESO' },
];
const MOBILE_PRIMARY = ['inicio', 'partidos', 'mercados', 'picks'];
const routeTitle = { inicio: 'Portada', partidos: 'Partidos y estadísticas', mercados: 'Mesa de mercados', picks: 'Picks', alta: 'Alta probabilidad', escalera: 'Reto escalera', parley: 'Parley del día', partido: 'Ficha de mercado · demo', historial: 'Historial', planes: 'Suscripciones', cuenta: 'Mi cuenta', paquetes: 'Paquetes de picks', acceso: 'Acceso', checkout: 'Revisar pedido' };
const validRoute = route => Object.hasOwn(routeTitle, route);
const FAMILIES = ['Todos', '1X2', 'Doble oportunidad', 'Goles', 'Ambos marcan', 'Por equipo', 'Hándicap'];
// Accesos rápidos de la mesa. «Top probabilidad» y no «top confianza»: ordena
// por probabilidad justa, que no dice nada de si la cuota compensa.
const DESK_MODES = [
  { id: 'dia', icon: '★', label: 'Pick del día' },
  { id: 'todas', icon: '▦', label: 'Todas' },
  { id: 'ventaja', icon: '↗', label: 'Top ventaja' },
  { id: 'probables', icon: '◎', label: 'Top probabilidad' },
  { id: 'combinadas', icon: '⊕', label: 'Combinadas' },
];
// Combinadas armadas por cuota total, como las ~2X/~3X de la competencia,
// pero cada una cotizada entera en una sola casa.
const COMBO_TABS = [
  { id: 'todas', label: 'Todas', min: 1.5, max: 3.6 },
  { id: '2x', label: '~2X', min: 1.8, max: 2.6 },
  { id: '3x', label: '~3X', min: 2.6, max: 3.6 },
  { id: 'cortas', label: 'Cortas 1,50–2,30', min: 1.5, max: 2.3 },
  { id: 'manual', label: 'Arma la tuya' },
];
const COMBOS_SHOWN = 6;
const TOP_N = 10;
const MAX_LEGS = 6;
const MATCH_TABS = [['resumen', 'Resumen'], ['mercados', 'Mercados'], ['casas', 'Casas 1X2'], ['modelo', 'Modelo'], ['registro', 'Registro']];
const DRAWER_TABS = [['resumen', 'Resumen'], ['casas', 'Casas'], ['modelo', 'Modelo'], ['registro', 'Registro']];

const prefs = loadPrefs();
const state = {
  route: 'inicio',
  selectedMatch: 'qf-101',
  statsDay: 0,
  statsLeague: 'Todas',
  statsMatch: null,
  statsTab: 'resumen',
  statsSplit: 'todos',
  matchTab: 'resumen',
  dayOffset: 0,
  homeSearch: '',
  homeStatus: 'todos',
  homeLeague: 'Todas',
  homeSort: 'hora',
  pickLeague: 'Todas',
  recordFilter: 'Todos',
  recordLeague: 'Todas',
  deskDay: 0,
  deskStatus: 'todos',
  deskMatch: '',
  deskFamily: 'Todos',
  deskOnlyCandidates: false,
  deskMine: false,
  deskSearch: '',
  deskSort: { key: 'edge', dir: 'desc' },
  deskMode: 'todas',
  comboTab: 'todas',
  parlay: [],
  drawer: null,
  drawerTab: 'resumen',
  oddsFormat: prefs.oddsFormat,
  followed: prefs.followed,
  mobileMenuOpen: false,
  session: null,
  membershipPlan: 'plus_3m',
  plans: { status: 'loading' },
  authMode: 'login',
  authReturn: 'cuenta',
  authMessage: '',
  authError: false,
  authBusy: false,
  authEmail: '',
  authName: '',
  accountMessage: '',
  accountError: false,
  accountSection: 'overview',
  savedDemoMatches: [],
  couponOpen: false,
  couponMessage: '',
  accessStep: 0,
  modal: null,
};
let publicData = null;
let publicRequest = 0;

// ---------------------------------------------------------------- formato

const app = document.getElementById('app');
const esc = text => String(text).replace(/[&<>"']/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[char]);
const fold = text => text.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
const dateFmt = (date, options = {}) => new Intl.DateTimeFormat('es-MX', options).format(date);
const dayLabel = offset => offset === 0 ? 'Hoy' : offset === -1 ? 'Ayer' : offset === 1 ? 'Mañana' : dateFmt(addDays(offset), { weekday: 'short', day: 'numeric' });
const timeLabel = date => dateFmt(date, { hour: '2-digit', minute: '2-digit', hourCycle: 'h23' });
const stamp = date => `${dateFmt(date, { day: 'numeric', month: 'short' })} · ${timeLabel(date)}`;
const kickoffLabel = fx => `${dayLabel(fx.day)} · ${timeLabel(fx.kickoff)}`;
const fmtOdds = decimal => {
  if (decimal == null) return '—';
  if (state.oddsFormat === 'us') return decimal >= 2 ? `+${Math.round((decimal - 1) * 100)}` : `−${Math.round(100 / (decimal - 1))}`;
  return decimal.toFixed(2);
};
const fmtPct = (p, digits = 1) => `${(p * 100).toFixed(digits)}%`;
const probText = p => probabilityLabel(p)?.text ?? '—';
const fmtEdge = edge => edge == null ? '—' : `${edge >= 0 ? '+' : '−'}${Math.abs(edge * 100).toFixed(1)}%`;
const edgeClass = edge => edge == null ? '' : edge >= SOFT_MIN_EDGE ? 'pos' : edge >= 0 ? 'near' : 'neg';
const clvValue = item => item.price / item.closePrice - 1;
const minutesAgo = date => Math.max(1, Math.round((now - date) / 60e3));
const realNumber = (value, digits = 0) => value == null || !Number.isFinite(Number(value)) ? '—' : Number(value).toLocaleString('es-MX', { minimumFractionDigits: digits, maximumFractionDigits: digits });
const realPercent = (value, digits = 1) => value == null || !Number.isFinite(Number(value)) ? '—' : `${Number(value) > 0 ? '+' : ''}${realNumber(value, digits)}%`;
const realDate = value => {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? '—' : dateFmt(date, { day: '2-digit', month: 'short', year: 'numeric' });
};
const realTime = value => {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? '' : timeLabel(date);
};

const STATUS = {
  candidata: { label: 'Candidata ≥ +2%', kind: 'good' },
  debajo: { label: 'Bajo el umbral', kind: '' },
  referencia: { label: 'Solo referencia', kind: 'muted' },
  'sin-cuota': { label: 'Sin cuota blanda', kind: 'muted' },
  excluido: { label: 'Excluido · Pinnacle', kind: 'warn' },
  cerrado: { label: 'Mercado cerrado', kind: 'muted' },
};

function statusText(row) {
  const fair = fmtOdds(1 / row.pFair);
  switch (row.status) {
    case 'candidata': return `${row.best.book.name} paga ${fmtOdds(row.best.price)} y el precio justo de Pinnacle en el mismo snapshot es ${fair}: ${fmtEdge(row.edge)} bruto. Pasaría el criterio si la publicación estuviera activa.`;
    case 'debajo': return `La mejor casa de la lista paga ${fmtOdds(row.best.price)} frente a un justo de ${fair}. No supera el 2% exigido: no hay nada que recomendar.`;
    case 'referencia': return 'El criterio en sombra solo evalúa 1X2. Este mercado se enseña como precio justo de referencia, no como candidata.';
    case 'sin-cuota': return 'Ninguna casa de la lista cotiza esta selección en el snapshot.';
    case 'excluido': return `Pinnacle se aparta ${fmtPct(row.fx.sharpDeviation)} del consenso de las demás casas (máximo ${fmtPct(MAX_SHARP_DEVIATION, 0)}). Un precio así se trata como roto y el partido entero queda fuera.`;
    default: return 'El partido ya empezó. Se muestra el último snapshot antes del inicio: es el cierre contra el que se mide el CLV.';
  }
}

function badge(text, kind = '') { return `<span class="badge ${kind}">${text}</span>`; }
const statusBadge = status => badge(STATUS[status].label, STATUS[status].kind);
const teamMark = (name, away = false, large = false) => `<span class="${large ? 'large-team-mark' : 'team-mark'} ${away ? 'away' : ''}" aria-hidden="true">${name.charAt(0)}</span>`;

function spark(points, width = 64, height = 22) {
  if (points.length < 2) return '<span class="spark-empty" aria-hidden="true">—</span>';
  const min = Math.min(...points);
  const span = Math.max(...points) - min || 1;
  const coords = points.map((value, i) => `${(1 + i / (points.length - 1) * (width - 2)).toFixed(1)},${(height - 1 - (value - min) / span * (height - 2)).toFixed(1)}`).join(' ');
  return `<svg class="spark ${points.at(-1) >= points[0] ? 'up' : 'down'}" viewBox="0 0 ${width} ${height}" width="${width}" height="${height}" aria-hidden="true" focusable="false"><polyline points="${coords}"/></svg>`;
}

function probBar(values, label) {
  return `<div class="prob-bar" data-segments="${values.join(',')}" role="img" aria-label="${label}: local ${values[0]}%, empate ${values[1]}%, visita ${values[2]}%"><span></span><span></span><span></span></div>`;
}

// ---------------------------------------------------------------- navegación

function navigate(route) {
  state.route = validRoute(route) ? route : 'inicio';
  state.modal = null;
  state.drawer = null;
  state.mobileMenuOpen = false;
  location.hash = state.route;
  render();
  app.querySelector('#main-content')?.focus({ preventScroll: true });
  window.scrollTo({ top: 0, behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth' });
}

function openMatch(id, tab = 'resumen') {
  state.selectedMatch = id;
  state.matchTab = tab;
  navigate('partido');
}

function sportNavMarkup() {
  return '<nav class="sport-nav" aria-label="Deporte"><a href="/" class="active" aria-current="page">Fútbol</a><a href="/nba">NBA</a></nav>';
}

function navMarkup() {
  const groups = [...new Set(nav.map(item => item.group))];
  return groups.map(group => `<div class="top-nav-group" role="group" aria-label="${group.charAt(0)}${group.slice(1).toLowerCase()}"><span class="top-nav-label" aria-hidden="true">${group}</span>${nav.filter(item => item.group === group).map(item => {
    const active = state.route === item.route;
    return `<button type="button" class="top-link ${active ? 'active' : ''}" data-route="${item.route}" ${active ? 'aria-current="page"' : ''}><span class="nav-icon" aria-hidden="true">${item.icon}</span><span>${item.label}</span></button>`;
  }).join('')}</div>`).join('');
}

function mobileNavMarkup() {
  const primary = nav.filter(item => MOBILE_PRIMARY.includes(item.route));
  const extra = nav.filter(item => !MOBILE_PRIMARY.includes(item.route));
  const link = item => `<button type="button" class="mobile-nav-link ${state.route === item.route ? 'active' : ''}" data-route="${item.route}" ${state.route === item.route ? 'aria-current="page"' : ''}><span aria-hidden="true">${item.icon}</span><small>${item.short}</small></button>`;
  const drawer = state.mobileMenuOpen ? `<div class="mobile-menu-layer"><button type="button" class="mobile-menu-backdrop" data-action="close-menu" aria-label="Cerrar menú adicional"></button><div id="mobile-extra-menu" class="mobile-drawer" role="dialog" aria-modal="true" aria-label="Más secciones"><div class="mobile-drawer-head"><div><p class="eyebrow">QUANTFUT / EXPLORAR</p><h2>Más secciones</h2></div><button type="button" class="mobile-drawer-close" data-action="close-menu" aria-label="Cerrar menú">×</button></div>${extra.map(item => `<button type="button" class="mobile-drawer-link" data-route="${item.route}" ${state.route === item.route ? 'aria-current="page"' : ''}><span aria-hidden="true">${item.icon}</span><span>${item.label}</span><span aria-hidden="true">↗</span></button>`).join('')}<p>Planes y acceso son demostraciones. No hay pagos ni cuentas reales.</p></div></div>` : '';
  return `<nav class="mobile-bottom-nav" aria-label="Navegación móvil">${primary.map(link).join('')}<button type="button" class="mobile-nav-link mobile-more ${extra.some(item => item.route === state.route) ? 'active' : ''}" data-action="toggle-menu" aria-expanded="${state.mobileMenuOpen}"><span aria-hidden="true">☰</span><small>Más</small></button></nav>${drawer}`;
}

function oddsToggle(extraClass = '') {
  return `<div class="segmented odds-toggle ${extraClass}" role="group" aria-label="Formato de cuota">${[['dec', 'Decimal'], ['us', 'Americana']].map(([value, label]) => `<button type="button" data-odds="${value}" class="${state.oddsFormat === value ? 'selected' : ''}" aria-pressed="${state.oddsFormat === value}">${label}</button>`).join('')}</div>`;
}

function dayRail() {
  return `<nav class="date-rail" aria-label="Seleccionar fecha de partidos">${[-3, -2, -1, 0, 1, 2, 3].map(offset => `<button type="button" class="date-button ${state.dayOffset === offset ? 'active' : ''}" data-day="${offset}" aria-label="${dateFmt(addDays(offset), { weekday: 'long', day: 'numeric', month: 'long' })}" aria-pressed="${state.dayOffset === offset}"><small>${offset === 0 ? 'HOY' : dateFmt(addDays(offset), { weekday: 'short' }).replace('.', '').toUpperCase()}</small><strong>${dateFmt(addDays(offset), { day: 'numeric' })}</strong></button>`).join('')}</nav>`;
}

// ---------------------------------------------------------------- piezas compartidas

function kpiStrip(dayFixtures) {
  const rows = dayFixtures.flatMap(fx => fx.rows);
  const candidates = rows.filter(row => row.status === 'candidata').length;
  const open = dayFixtures.filter(fx => !fx.closed);
  const latest = open.length ? new Date(Math.max(...open.map(fx => fx.snapshot))) : null;
  return `<div class="kpi-strip">
    <div><span>PARTIDOS</span><strong>${dayFixtures.length}</strong><small>${open.length} con mercado abierto</small></div>
    <div><span>PRECIOS JUSTOS</span><strong>${rows.length}</strong><small>selecciones en ${new Set(rows.map(row => `${row.fx.id}${row.market}`)).size} mercados</small></div>
    <div><span>CANDIDATAS 1X2</span><strong class="${candidates ? 'pos' : ''}">${candidates}</strong><small>≥ +2% sobre Pinnacle sin margen</small></div>
    <div><span>ÚLTIMO SNAPSHOT</span><strong>${latest ? timeLabel(latest) : '—'}</strong><small>${latest ? `hace ${minutesAgo(latest)} min · demo` : 'sin mercados abiertos'}</small></div>
  </div>`;
}

function shadowList(picks, { limit = 5, heading = true } = {}) {
  const items = picks.slice(0, limit);
  const list = items.length ? `<ol class="shadow-list">${items.map(({ row }, index) => `<li><button type="button" class="shadow-item" data-row="${row.key}"><span class="shadow-rank">${index + 1}</span><span class="shadow-body"><strong>${row.fx.home} × ${row.fx.away}</strong><span>${row.selection} · ${row.best.book.name} <b>${fmtOdds(row.best.price)}</b></span><small>prob. real ${fmtPct(row.pFair, 0)} · mín. ${fmtOdds(row.minPrice)} · ${kickoffLabel(row.fx)}</small></span><span class="shadow-edge pos">${fmtEdge(row.edge)}</span></button></li>`).join('')}</ol>` : '<p class="rail-empty">Ninguna casa de la lista supera hoy el precio justo en un 2%. Es un resultado válido: el criterio no fuerza picks.</p>';
  return `<section class="rail-panel">${heading ? `<div class="rail-head"><p class="eyebrow">SOMBRA DEL CRITERIO</p>${badge('Publicación pausada', 'warn')}</div><h2>Lo que se habría elegido</h2>` : ''}${list}<p class="rail-note">Una por partido, solo 1X2, precio de casa blanda contra Pinnacle en el mismo snapshot. Sin hash: la demo no escribe en la cadena.</p></section>`;
}

function sortedRows(rows) {
  const { key, dir } = state.deskSort;
  const value = {
    edge: row => row.edge ?? -Infinity,
    model: row => row.pModel,
    fair: row => row.pFair,
    best: row => row.best?.price ?? -Infinity,
    kickoff: row => row.fx.kickoff.getTime(),
  }[key];
  const sign = dir === 'asc' ? 1 : -1;
  // Al ordenar por diferencia, primero lo que el criterio aceptaría; un +10% de
  // un partido excluido o cerrado no es comprable y va siempre al final.
  const tier = row => (key !== 'edge' ? 0 : row.status === 'candidata' ? 0 : ['excluido', 'cerrado', 'sin-cuota'].includes(row.status) ? 2 : 1);
  return [...rows].sort((a, b) => tier(a) - tier(b) || sign * (value(a) - value(b)) || a.key.localeCompare(b.key));
}

function marketTable(rows, { showMatch = true, caption }) {
  const sortTh = (key, label, cls = '') => {
    const active = state.deskSort.key === key;
    return `<th scope="col" class="${cls}" aria-sort="${active ? (state.deskSort.dir === 'asc' ? 'ascending' : 'descending') : 'none'}"><button type="button" class="sort-button" data-sort="${key}">${label}<span aria-hidden="true">${active ? (state.deskSort.dir === 'asc' ? '↑' : '↓') : '↕'}</span></button></th>`;
  };
  const body = rows.map(row => `<tr class="${row.status === 'candidata' ? 'is-candidate' : ''}">
    <td class="cell-main"><button type="button" class="row-open" data-row="${row.key}"><strong>${showMatch ? `${row.fx.home} × ${row.fx.away}` : row.market}</strong><small>${showMatch ? `${row.market} · ${timeLabel(row.fx.kickoff)}` : row.family}</small></button></td>
    <td><strong>${row.selection}</strong></td>
    <td class="num">${fmtPct(row.pModel)}</td>
    <td class="num"><strong>${fmtOdds(1 / row.pFair)}</strong><small>${fmtPct(row.pFair)}</small></td>
    <td class="num">${row.best ? `<strong class="price">${fmtOdds(row.best.price)}</strong><small>${row.best.book.name}</small>` : '—'}</td>
    <td class="num edge ${edgeClass(row.edge)}">${fmtEdge(row.edge)}</td>
    <td class="num">${row.family === '1X2' ? fmtOdds(row.minPrice) : '—'}</td>
    <td>${spark(row.history)}${row.history.length ? `<span class="sr-only">De ${fmtOdds(row.history[0])} a ${fmtOdds(row.best.price)}</span>` : ''}</td>
    <td>${statusBadge(row.status)}</td>
    <td class="slip-cell">${slipToggle(row)}</td>
  </tr>`).join('');
  return `<div class="table-wrap market-wrap" tabindex="0" role="region" aria-label="Tabla de mercados, desplazable horizontalmente"><table class="market-table"><caption class="sr-only">${caption}</caption><thead><tr>
    ${showMatch ? sortTh('kickoff', 'Partido · mercado', 'cell-main') : '<th scope="col" class="cell-main">Mercado</th>'}
    <th scope="col">Selección</th>
    ${sortTh('model', 'Modelo', 'num')}
    ${sortTh('fair', 'Justo Pinnacle', 'num')}
    ${sortTh('best', 'Mejor casa', 'num')}
    ${sortTh('edge', 'vs justo', 'num')}
    <th scope="col" class="num">Mínimo</th>
    <th scope="col">Movimiento</th>
    <th scope="col">Estado</th>
    <th scope="col" class="slip-cell"><span class="sr-only">Combinada</span><span aria-hidden="true">⊕</span></th>
  </tr></thead><tbody>${body}</tbody></table></div>`;
}

// ---------------------------------------------------------------- combinadas

const tradable = row => Boolean(row.best) && !row.fx.closed && !row.fx.excluded;
const product = values => values.reduce((total, value) => total * value, 1);

function slipToggle(row) {
  const on = state.parlay.includes(row.key);
  const why = row.fx.closed ? 'mercado cerrado' : row.fx.excluded ? 'partido excluido' : 'sin cuota blanda';
  return `<button type="button" class="slip-toggle ${on ? 'on' : ''}" data-parlay="${row.key}" aria-pressed="${on}" ${tradable(row) ? '' : `disabled title="No combinable: ${why}"`} aria-label="${on ? 'Quitar de' : 'Añadir a'} la combinada: ${row.selection} en ${row.fx.home} contra ${row.fx.away}">${on ? '✓' : '+'}</button>`;
}

// Una selección por partido: dos del mismo partido están correlacionadas y el
// producto de sus probabilidades sería un precio justo falso.
function toggleLeg(key) {
  const row = rowByKey.get(key);
  if (state.parlay.includes(key)) state.parlay = state.parlay.filter(item => item !== key);
  else if (tradable(row)) state.parlay = [...state.parlay.filter(item => rowByKey.get(item).fx !== row.fx), key].slice(-MAX_LEGS);
}

function parlayLegs() { return state.parlay.map(key => rowByKey.get(key)).filter(row => row && tradable(row)); }

function parlayPanel() {
  const legs = parlayLegs();
  const shadowToday = shadowPicks.filter(pick => pick.row.fx.day === state.deskDay && tradable(pick.row));
  const loadButton = `<button type="button" class="secondary-button" data-action="load-shadow" ${shadowToday.length ? '' : 'disabled'}>Cargar candidatas del día (${shadowToday.length})</button>`;
  if (!legs.length) {
    return `<section class="panel slip-panel"><p class="eyebrow">COMBINADA</p><h2>Añade selecciones con <span class="slip-inline">+</span> en la tabla</h2><p class="body-copy muted">Una por partido, hasta ${MAX_LEGS}. Se calcula en cada casa por separado, porque una combinada se juega entera en la misma casa.</p><div class="slip-actions">${loadButton}</div></section>`;
  }
  const pAll = product(legs.map(row => row.pFair));
  const books = BOOKS.map(book => {
    const prices = legs.map(row => row.quotes.find(q => q.book === book).price);
    const missing = prices.filter(price => !price).length;
    const price = missing ? null : product(prices);
    return { book, price, missing, edge: price ? price * pAll - 1 : null };
  }).sort((a, b) => (b.price ?? 0) - (a.price ?? 0));
  const best = books.find(item => item.price);
  const below = legs.filter(row => row.edge < 0).length;
  const callout = below
    ? `<strong>${below} de ${legs.length} selecciones pagan por debajo del justo incluso en su mejor casa.</strong> En una combinada esas desventajas se multiplican, no se compensan.`
    : '<strong>Todas las selecciones pagan por encima del justo en su mejor casa,</strong> pero la combinada solo se puede jugar en una casa: mira abajo cuál la cotiza entera y a qué precio.';
  return `<section class="panel slip-panel">
    <div class="panel-heading"><div><p class="eyebrow">COMBINADA · ${legs.length} SELECCIÓN${legs.length > 1 ? 'ES' : ''}</p><h2>Tu combinada</h2></div><div class="slip-actions">${loadButton}<button type="button" class="text-link" data-action="clear-parlay">Vaciar</button></div></div>
    <ol class="slip-legs">${legs.map(row => `<li><div><strong>${row.selection}</strong><small>${row.fx.home} × ${row.fx.away} · ${row.market}</small></div><span class="num">${fmtOdds(row.best.price)}<small>${row.best.book.name}</small></span><span class="num">${fmtOdds(1 / row.pFair)}<small>justo</small></span><span class="num edge ${edgeClass(row.edge)}">${fmtEdge(row.edge)}</span><button type="button" class="slip-remove" data-parlay="${row.key}" aria-label="Quitar ${row.selection} de la combinada">×</button></li>`).join('')}</ol>
    <div class="slip-metrics">
      <div><span>ACERTAR TODAS</span><strong>${fmtPct(pAll)}</strong><small>probabilidad justa conjunta</small></div>
      <div><span>CUOTA JUSTA</span><strong>${fmtOdds(1 / pAll)}</strong><small>producto de los justos</small></div>
      <div><span>MEJOR CASA</span><strong class="price">${best ? fmtOdds(best.price) : '—'}</strong><small>${best ? best.book.name : 'ninguna la cotiza entera'}</small></div>
      <div><span>VS JUSTO</span><strong class="edge ${edgeClass(best ? best.edge : null)}">${fmtEdge(best ? best.edge : null)}</strong><small>en esa casa</small></div>
    </div>
    <div class="drawer-note ${best && best.edge >= 0 ? 'candidata' : 'excluido'}"><p>${callout}</p></div>
    <div class="table-wrap"><table class="books-table"><caption class="sr-only">Cuota combinada por casa</caption><thead><tr><th scope="col">Casa</th><th scope="col" class="num">Cuota combinada</th><th scope="col" class="num">vs justo</th></tr></thead><tbody>${books.map(item => `<tr class="${item === best ? 'is-best' : ''}"><td><strong>${item.book.name}</strong>${item.price ? '' : `<small>no cotiza ${item.missing} selección${item.missing > 1 ? 'es' : ''}</small>`}</td><td class="num">${fmtOdds(item.price)}</td><td class="num edge ${edgeClass(item.edge)}">${fmtEdge(item.edge)}</td></tr>`).join('')}</tbody></table></div>
    <p class="panel-foot">Probabilidad conjunta = producto de las justas, válido porque son partidos distintos. El criterio publica selecciones sueltas; una combinada no crea ventaja, solo multiplica la que ya tenga cada selección.</p>
  </section>`;
}

function deskRowsForMode() {
  const rows = deskFilteredRows();
  if (state.deskMode === 'ventaja') return sortedRows(rows.filter(row => tradable(row) && row.edge > 0).sort((a, b) => b.edge - a.edge).slice(0, TOP_N));
  if (state.deskMode === 'probables') return sortedRows(rows.filter(tradable).sort((a, b) => b.pFair - a.pFair).slice(0, TOP_N));
  return sortedRows(rows);
}

// Pick del día: la mejor candidata 1X2 del criterio, con ventana de venta que
// se cierra al inicio del partido y su historial completo debajo.
function pickOfDayPanel() {
  const row = shadowPicks.map(pick => pick.row).filter(item => item.fx.day === state.deskDay).sort((a, b) => b.edge - a.edge)[0];
  const won = archive.filter(item => item.result === 'Ganado').length;
  const units = sum(archive.map(item => (item.result === 'Ganado' ? item.price - 1 : -1)));
  const clv = sum(archive.map(clvValue)) / archive.length;
  let body;
  if (!row) {
    body = `<div class="pod-closed"><span class="pod-lock" aria-hidden="true">◇</span><div><strong>Hoy no hay pick del día</strong><p>Ninguna casa de la lista paga un 2% por encima del precio justo en 1X2. No se fuerza uno: mañana a las 12:00 se vuelve a mirar.</p></div></div>`;
  } else {
    const minutes = Math.max(0, Math.round((row.fx.kickoff - now) / 60e3));
    const left = minutes >= 60 ? `${Math.floor(minutes / 60)} h ${minutes % 60} min` : `${minutes} min`;
    body = `<div class="pod-window"><span class="side-live-dot"></span><span>Disponible hasta el inicio, <strong>${stamp(row.fx.kickoff)}</strong> · faltan ${left}. Al empezar el partido se cierra: no se entra a última hora.</span></div>
      <article class="pod-card">
        <div class="pod-main"><p class="pod-league">${row.fx.league} · ${kickoffLabel(row.fx)}</p><h3>${row.fx.home} <span>vs</span> ${row.fx.away}</h3><p class="pod-selection"><span>${row.market}</span><strong>${row.selection}</strong></p></div>
        <div class="pod-price"><strong>${fmtOdds(row.best.price)}</strong><small>${row.best.book.name}</small></div>
      </article>
      <div class="drawer-metrics pod-metrics">
        <div><span>JUSTO PINNACLE</span><strong>${fmtOdds(1 / row.pFair)}</strong><small>prob. real ${probText(row.pFair)}</small></div>
        <div><span>VS JUSTO</span><strong class="edge ${edgeClass(row.edge)}">${fmtEdge(row.edge)}</strong><small>bruto en ${row.best.book.name}</small></div>
        <div><span>ESPERADO AL CIERRE</span><strong>${fmtEdge(row.expectedEdge)}</strong><small>persistencia ${Math.round(row.best.book.persistence * 100)}%</small></div>
        <div><span>PRECIO MÍNIMO</span><strong>${fmtOdds(row.minPrice)}</strong><small>por debajo ya no vale</small></div>
        <div><span>SNAPSHOT</span><strong>${timeLabel(row.fx.snapshot)}</strong><small>Pinnacle y casa en la misma respuesta</small></div>
        <div><span>HASH</span><strong>—</strong><small>se sella antes del partido · demo</small></div>
      </div>
      <div class="slip-actions pod-actions"><button type="button" class="primary-button" data-row="${row.key}">Ver todas las casas</button><button type="button" class="secondary-button" data-match="${row.fx.id}">Ficha del partido</button></div>`;
  }
  const history = `<section class="pod-history"><div class="pod-history-head"><p class="eyebrow">PICK DEL DÍA — HISTORIAL</p><span>${won}G ${archive.length - won}P · ${units >= 0 ? '+' : '−'}${Math.abs(units).toFixed(2)}u · CLV medio ${fmtEdge(clv)}</span></div>
    <ol class="pod-list">${archive.map(item => `<li class="${item.result === 'Ganado' ? 'won' : 'lost'}"><span class="pod-mark" aria-hidden="true">${item.result === 'Ganado' ? '✓' : '✗'}</span><div><strong>${item.selection} · ${item.market}</strong><small>${item.match} · ${dateFmt(item.date, { day: 'numeric', month: 'short' })} · ${item.book} · <span class="result ${item.result === 'Ganado' ? 'won' : 'lost'}">${item.result}</span></small></div><span class="num">@${fmtOdds(item.price)}<small>cierre ${fmtOdds(item.closePrice)}</small></span><span class="num edge ${clvValue(item) >= 0 ? 'pos' : 'neg'}">${fmtEdge(clvValue(item))}<small>CLV</small></span></li>`).join('')}</ol>
    <p class="panel-foot">Muestra ficticia. En la versión real cada entrada se sella en la cadena de hashes antes del partido: ganados y perdidos a la vista, nada editado. <button type="button" class="text-link" data-route="historial">Ver historial completo ↗</button></p></section>`;
  return `<section class="panel pod-panel"><div class="pod-head"><div><p class="eyebrow">PICK DEL DÍA</p><h2>Un pick, con su precio mínimo y su historial</h2></div>${badge('Demo · sin venta real', 'warn')}</div>${body}${history}</section>`;
}

const comboCache = new Map();
// Todas las combinadas de 2 a 5 partidos distintos cuyas selecciones pagan el
// justo o más en la MISMA casa; si varias casas la cotizan, se queda la mejor.
function readyCombos(day) {
  if (comboCache.has(day)) return comboCache.get(day);
  const open = allRows.filter(row => row.fx.day === day && tradable(row));
  const matches = [...new Set(open.map(row => row.fx.id))];
  const bestByLegs = new Map();
  for (const book of BOOKS) {
    const legsByMatch = matches.map(id => open.filter(row => row.fx.id === id)
      .map(row => ({ row, price: row.quotes.find(q => q.book === book).price }))
      .filter(leg => leg.price && leg.price * leg.row.pFair >= 1));
    const walk = (i, chosen) => {
      if (i === legsByMatch.length) {
        if (chosen.length < 2) return;
        const price = product(chosen.map(leg => leg.price));
        const p = product(chosen.map(leg => leg.row.pFair));
        const id = chosen.map(leg => leg.row.key).join('|');
        if (!bestByLegs.has(id) || bestByLegs.get(id).price < price) bestByLegs.set(id, { id, book, legs: chosen, price, p, edge: price * p - 1 });
        return;
      }
      walk(i + 1, chosen);
      if (chosen.length < 5) legsByMatch[i].forEach(leg => walk(i + 1, [...chosen, leg]));
    };
    walk(0, []);
  }
  const combos = [...bestByLegs.values()];
  comboCache.set(day, combos);
  return combos;
}

function comboCard(combo) {
  const tag = combo.price < 1.8 ? 'Corta' : combo.price < 2.6 ? '~2X' : '~3X';
  return `<article class="combo-card"><header><span class="combo-tag">${tag}</span><span>${combo.legs.length} partidos · ${combo.book.name}</span></header>
    <ol class="combo-legs">${combo.legs.map(leg => { const edge = leg.price * leg.row.pFair - 1; return `<li><div><strong>${leg.row.selection}</strong><small>${leg.row.fx.home} × ${leg.row.fx.away} · ${leg.row.market}</small></div><span class="num">${fmtOdds(leg.price)}</span><span class="num">${fmtOdds(1 / leg.row.pFair)}<small>justo</small></span><span class="num edge ${edgeClass(edge)}">${fmtEdge(edge)}</span></li>`; }).join('')}</ol>
    <footer><div><span>CUOTA TOTAL</span><strong class="price">${fmtOdds(combo.price)}</strong></div><div><span>PROB. JUSTA</span><strong>${fmtPct(combo.p)}</strong></div><div><span>VS JUSTO</span><strong class="edge ${edgeClass(combo.edge)}">${fmtEdge(combo.edge)}</strong></div><button type="button" class="secondary-button" data-load-combo="${esc(combo.id)}">Cargar en mi combinada</button></footer>
  </article>`;
}

function comboPanel() {
  const tab = COMBO_TABS.find(item => item.id === state.comboTab) || COMBO_TABS[0];
  const bar = `<div class="tab-bar combo-tabs" role="tablist" aria-label="Tipo de combinada">${COMBO_TABS.map(item => `<button type="button" role="tab" aria-selected="${item.id === tab.id}" class="${item.id === tab.id ? 'selected' : ''}" data-combo-tab="${item.id}">${item.label}${item.id === 'manual' && state.parlay.length ? ` (${state.parlay.length})` : ''}</button>`).join('')}</div>`;
  if (tab.id === 'manual') return bar + parlayPanel();
  const combos = readyCombos(state.deskDay).filter(combo => combo.price >= tab.min && combo.price <= tab.max).sort((a, b) => b.edge - a.edge).slice(0, COMBOS_SHOWN);
  const intro = '<p class="mode-note">Armadas solas con selecciones que pagan al menos el precio justo en la <strong>misma casa</strong>, una por partido. La probabilidad es la justa de Pinnacle, no una nota. El criterio publica selecciones sueltas: esto es referencia.</p>';
  const list = combos.length
    ? `<div class="combo-grid">${combos.map(comboCard).join('')}</div>`
    : `<div class="empty-state"><span class="empty-symbol">⊕</span><h3>Sin combinadas ${tab.label} este día</h3><p>Solo entra una combinada si todas sus selecciones pagan el justo o más en la misma casa. Si no la hay, no se inventa.</p></div>`;
  return bar + intro + list;
}

function quickBar() {
  const note = {
    ventaja: `Las ${TOP_N} selecciones abiertas que más pagan por encima del precio justo. Solo las 1X2 con ≥ +2% pasan el criterio; el resto es referencia.`,
    probables: `Las ${TOP_N} selecciones abiertas con mayor probabilidad justa (Pinnacle sin margen). Más probable no significa mejor apuesta: la cuota ya lo descuenta, mira «vs justo».`,
  }[state.deskMode];
  return `<div class="quick-bar" role="group" aria-label="Vistas rápidas">${DESK_MODES.map(mode => `<button type="button" class="quick-btn ${state.deskMode === mode.id ? 'selected' : ''}" data-desk-mode="${mode.id}" aria-pressed="${state.deskMode === mode.id}"><span aria-hidden="true">${mode.icon}</span>${mode.label}${mode.id === 'combinadas' && state.parlay.length ? `<b>${state.parlay.length}</b>` : ''}</button>`).join('')}</div>${note ? `<p class="mode-note">${note}</p>` : ''}`;
}

function heatGrid(fx, size = 6) {
  const cells = [];
  for (let i = 0; i < size; i++) {
    cells.push(`<th scope="row">${i}</th>`);
    for (let j = 0; j < size; j++) {
      const p = fx.grid[i][j];
      cells.push(`<td class="heat-${Math.min(5, Math.floor(p * 100 / 2.5))}">${(p * 100).toFixed(1)}</td>`);
    }
  }
  const rows = [];
  for (let i = 0; i < size; i++) rows.push(`<tr>${cells.slice(i * (size + 1), (i + 1) * (size + 1)).join('')}</tr>`);
  return `<div class="heat-wrap"><table class="heat-grid"><caption>Probabilidad del marcador exacto (%). Filas: goles de ${fx.home}; columnas: goles de ${fx.away}.</caption><thead><tr><th scope="col"><span class="sr-only">Local \\ Visita</span></th>${Array.from({ length: size }, (_, j) => `<th scope="col">${j}</th>`).join('')}</tr></thead><tbody>${rows.join('')}</tbody></table></div>`;
}

function modelPanel(fx) {
  const x12 = fx.rows.filter(row => row.market === '1X2');
  return `<div class="model-grid">
    <section class="panel"><p class="eyebrow">MODELO / DIAGNÓSTICO</p><h2>Dos lambdas, todos los mercados</h2>
      <div class="lambda-pair"><div><span>${fx.home}</span><strong>${fx.xg[0].toFixed(2)}</strong><small>goles esperados</small></div><div><span>${fx.away}</span><strong>${fx.xg[1].toFixed(2)}</strong><small>goles esperados</small></div></div>
      <div class="compare-list">${x12.map(row => `<div class="compare-row"><span>${row.selection}</span><div class="compare-bars"><span class="bar model" data-width="${(row.pModel * 100).toFixed(1)}"></span><span class="bar fair" data-width="${(row.pFair * 100).toFixed(1)}"></span></div><small>${fmtPct(row.pModel)} · ${fmtPct(row.pFair)}</small></div>`).join('')}</div>
      <p class="legend"><span class="key model"></span>Modelo <span class="key fair"></span>Pinnacle sin margen</p>
      <p class="panel-foot">El modelo es diagnóstico: la selección usa el precio justo de Pinnacle, no la opinión del modelo. Que discrepen no es, por sí solo, una ventaja.</p>
    </section>
    <section class="panel"><p class="eyebrow">MARCADOR EXACTO</p><h2>Dónde se reparte la probabilidad</h2>${heatGrid(fx)}</section>
  </div>`;
}

function traceSteps(fx) {
  const pick = pickFor(fx);
  return `<ol class="trace-steps">
    <li><span>01 / SNAPSHOT</span><strong>${stamp(fx.snapshot)}</strong><small>Pinnacle y casas blandas de la misma respuesta del proveedor.</small></li>
    <li><span>02 / PUBLICACIÓN</span><strong>${pick ? 'En sombra' : 'Sin candidata'}</strong><small>${pick ? 'El criterio la registra, pero la publicación está pausada. Sin hash real.' : 'Nada supera el umbral; no se publica nada.'}</small></li>
    <li><span>03 / INICIO</span><strong>${stamp(fx.kickoff)}</strong><small>Toda publicación debe preceder al partido.</small></li>
    <li><span>04 / CIERRE Y CLV</span><strong>${fx.closed ? 'Cierre registrado' : 'Pendiente'}</strong><small>${fx.closed ? 'El último snapshot antes del inicio es la vara del CLV.' : 'Se liquida contra el cierre sin margen, no contra el resultado.'}</small></li>
  </ol>`;
}

function booksTable(row) {
  const quotes = [...row.quotes].sort((a, b) => (b.price ?? 0) - (a.price ?? 0));
  return `<div class="table-wrap"><table class="books-table"><caption class="sr-only">Cuotas por casa para ${row.selection}</caption><thead><tr><th scope="col">Casa</th><th scope="col" class="num">Cuota</th><th scope="col" class="num">vs justo</th><th scope="col" class="num">Persistencia · demo</th><th scope="col" class="num">Esperado al cierre</th></tr></thead><tbody>
    <tr class="sharp-row"><td><strong>Pinnacle</strong><small>referencia sharp</small></td><td class="num">${fmtOdds(row.pinnacle)}</td><td class="num">justo ${fmtOdds(1 / row.pFair)}</td><td class="num">—</td><td class="num">—</td></tr>
    ${quotes.map(q => { const edge = q.price ? q.price * row.pFair - 1 : null; return `<tr class="${q === row.best ? 'is-best' : ''}"><td><strong>${q.book.name}</strong>${q === row.best ? '<small>mejor precio</small>' : ''}</td><td class="num">${fmtOdds(q.price)}</td><td class="num edge ${edgeClass(edge)}">${fmtEdge(edge)}</td><td class="num">${q.price ? `${Math.round(q.book.persistence * 100)}%` : '—'}</td><td class="num">${edge == null ? '—' : fmtEdge(edge * q.book.persistence)}</td></tr>`; }).join('')}
  </tbody></table></div><p class="panel-foot">Persistencia: la parte del margen sobre el justo que, históricamente, sigue ahí al cierre en esa casa. El stake real sale del esperado al cierre, no del bruto.</p>`;
}

function bookMatrix(fx) {
  const x12 = fx.rows.filter(row => row.market === '1X2');
  const cell = (row, price) => {
    if (!price) return '<td class="num">—</td>';
    const edge = price * row.pFair - 1;
    return `<td class="num ${price === row.best?.price ? 'is-best' : ''}"><strong>${fmtOdds(price)}</strong><small class="edge ${edgeClass(edge)}">${fmtEdge(edge)}</small></td>`;
  };
  return `<section class="panel"><div class="panel-heading"><div><p class="eyebrow">CASAS / 1X2</p><h2>Precio por casa en el mismo snapshot</h2></div>${badge(`Snapshot ${timeLabel(fx.snapshot)}`, 'muted')}</div>
    <div class="table-wrap"><table class="books-table"><caption class="sr-only">Cuotas 1X2 por casa</caption><thead><tr><th scope="col">Casa</th>${x12.map(row => `<th scope="col" class="num">${row.selection}</th>`).join('')}</tr></thead><tbody>
      <tr class="sharp-row"><td><strong>Pinnacle</strong><small>con margen</small></td>${x12.map(row => `<td class="num">${fmtOdds(row.pinnacle)}</td>`).join('')}</tr>
      <tr class="sharp-row"><td><strong>Justo</strong><small>Pinnacle sin margen</small></td>${x12.map(row => `<td class="num"><strong>${fmtOdds(1 / row.pFair)}</strong><small>${fmtPct(row.pFair)}</small></td>`).join('')}</tr>
      ${BOOKS.map(book => `<tr><td><strong>${book.name}</strong></td>${x12.map(row => cell(row, row.quotes.find(q => q.book === book).price)).join('')}</tr>`).join('')}
    </tbody></table></div>
    <p class="panel-foot">${fx.excluded ? `Pinnacle se aparta ${fmtPct(fx.sharpDeviation)} del consenso (máximo ${fmtPct(MAX_SHARP_DEVIATION, 0)}): el partido queda fuera del criterio.` : `Desviación de Pinnacle frente al consenso: ${fmtPct(fx.sharpDeviation)} (máximo ${fmtPct(MAX_SHARP_DEVIATION, 0)}).`} El porcentaje bajo cada cuota es su diferencia con el justo.</p>
  </section>`;
}

// ---------------------------------------------------------------- vistas

function matchCard(fx) {
  const candidates = fx.rows.filter(row => row.status === 'candidata').length;
  const tag = fx.closed ? badge('Cerrado', 'muted') : fx.excluded ? badge('Excluido', 'warn') : candidates ? badge(`${candidates} candidata${candidates > 1 ? 's' : ''}`, 'good') : badge('Sin candidata', 'muted');
  return `<article class="match-card">
    <div class="match-card-top"><span>${fx.league}</span><span>${kickoffLabel(fx)}</span></div>
    <div class="match-teams">${teamMark(fx.home)}<strong>${fx.home}</strong><span class="versus">VS</span><strong>${fx.away}</strong>${teamMark(fx.away, true)}</div>
    <div class="dual-bars"><div><small>Modelo</small>${probBar(fx.probs, 'Modelo')}</div><div><small>Pinnacle sin margen</small>${probBar(fx.marketProbs, 'Pinnacle sin margen')}</div></div>
    <div class="prob-labels"><span>L ${fx.probs[0]} · ${fx.marketProbs[0]}%</span><span>E ${fx.probs[1]} · ${fx.marketProbs[1]}%</span><span>V ${fx.probs[2]} · ${fx.marketProbs[2]}%</span></div>
    <div class="match-card-bottom">${tag}<span class="card-links"><button type="button" class="text-link" data-desk-open="${fx.id}">Mercados</button><button type="button" class="text-link" data-match="${fx.id}">Ficha <span aria-hidden="true">↗</span></button></span></div>
  </article>`;
}

// Evidencia real y maqueta viven en secciones distintas. Un error de red no
// transforma ejemplos en resultados ni permite inferir que la puerta abrió.
function liveStatus() {
  const gate = publicData?.gate;
  const status = gate?.status === 'ready' ? gate.data.puerta_comercial : null;
  const active = isPublicationActive(gate);
  const shadow = status?.sombra_criterio_sharp;
  const reasons = Array.isArray(shadow?.motivos) ? shadow.motivos : [];
  const measured = shadow?.publicables?.n_with_fair_close;
  const candidates = shadow?.publicables?.n;
  const captured = shadow?.ofertas_registradas;
  return `<section class="live-panel" aria-label="Estado real de publicación"><div class="live-head"><div><p class="eyebrow">ESTADO REAL · API PÚBLICA</p><h2>${!gate ? 'Consultando el sistema…' : !status ? 'Estado no disponible' : active ? 'Publicación activa' : 'Publicación pausada'}</h2></div>${badge(active ? 'Verificado por servidor' : 'Sin venta activa', active ? 'good' : 'muted')}</div>
    <p>${!gate ? 'Cargando la puerta comercial desde QuantFut.' : !status ? 'No se pudo verificar la puerta comercial. No se mostrarán picks como publicados.' : active ? 'El servidor confirma que la puerta está autorizada y la publicación activa.' : 'El servidor todavía no autoriza vender picks. Los partidos y precios que aparecen más abajo son solo una maqueta.'}</p>
    ${status ? `<div class="live-facts"><div><span>CIERRES JUSTOS EN SOMBRA</span><strong>${realNumber(measured)}</strong><small>${realNumber(candidates)} candidatas · ${realNumber(captured)} ofertas capturadas</small></div><div><span>PUERTA DEL CRITERIO</span><strong>${shadow?.autorizada ? 'Autorizada' : 'Cerrada'}</strong><small>decisión calculada por el servidor</small></div><div><span>PUBLICACIÓN</span><strong>${active ? 'Activa' : 'Pausada'}</strong><small>sin cobros ni acceso premium</small></div></div>${reasons.length ? `<p class="live-reason"><strong>Motivo:</strong> ${esc(reasons.join(' · '))}</p>` : ''}` : ''}
    <div class="live-links"><button type="button" class="text-link" data-route="historial">Ver evidencia pública ↗</button><button type="button" class="text-link" data-action="refresh-public">Actualizar estado ↻</button></div></section>`;
}

function livePicks() {
  const gate = publicData?.gate;
  const picks = publicData?.picks;
  const active = isPublicationActive(gate);
  let body;
  if (!gate || !picks) body = '<p>Consultando picks públicos y autorización del servidor…</p>';
  else if (gate.status !== 'ready') body = '<p>No se pudo verificar la puerta comercial. Por seguridad no se muestran recomendaciones.</p>';
  else if (!active) body = '<p>La publicación real está pausada. No hay recomendaciones nuevas a la venta ni acceso premium habilitado.</p>';
  else if (picks.status !== 'ready') body = '<p>No se pudieron consultar los picks públicos. Inténtalo de nuevo más tarde.</p>';
  else if (!picks.data.length) body = '<p>No hay picks gratuitos publicados para los próximos partidos. Si el criterio no encuentra valor, la lista queda vacía.</p>';
  else {
    const hit = expectedHitRate(picks.data);
    const hitNote = hit == null ? '' : `<p class="live-reason">Acierto esperado de esta lista: <strong>${realNumber(hit * 100)}%</strong>, con la probabilidad real de cada pick (Pinnacle sin margen). Con cuotas altas se pierde a menudo aunque el pick tenga valor: lo que cuenta es cobrar más de lo que vale el resultado.</p>`;
    body = `${hitNote}<div class="live-pick-list">${picks.data.map(pick => `<article class="live-pick"><div><span>${esc(pick.league_id ?? 'Liga')} · ${realDate(pick.kickoff_utc)}</span><h3>${esc(pick.local ?? 'Local')} <small>vs</small> ${esc(pick.visitante ?? 'Visitante')}</h3><p>${esc(pick.market ?? '1X2')} · ${esc(pick.selection ?? 'Selección')}</p><small class="live-prob">Probabilidad real: ${esc(probabilityLabel(pick.fair_prob)?.text ?? 'sin dato')}</small></div><div><span>${esc(pick.bookmaker ?? 'Casa')}</span><strong>${realNumber(pick.advised_price, 2)}</strong><small>Mínimo ${realNumber(pick.min_price, 2)}</small></div></article>`).join('')}</div>`;
  }
  return `<section class="live-panel" aria-label="Picks públicos reales"><div class="live-head"><div><p class="eyebrow">PUBLICACIÓN REAL · /PICKS/FREE</p><h2>Picks gratuitos publicados</h2></div>${badge(active ? 'Datos del servidor' : 'En pausa', active ? 'good' : 'muted')}</div>${body}<button type="button" class="text-link" data-action="refresh-public">Actualizar ↻</button></section>`;
}

function liveEvidence() {
  const record = publicData?.record;
  const calibration = publicData?.calibration;
  const chain = publicData?.chain;
  const monthly = record?.status === 'ready' ? record.data.mensual : null;
  const last30 = record?.status === 'ready' ? record.data.ultimos_30d : null;
  const runs = calibration?.status === 'ready' ? calibration.data.runs : null;
  const batches = chain?.status === 'ready' ? chain.data.lotes : null;
  const settled = Number(last30?.n || 0);
  return `<section class="live-panel" aria-label="Historial público real"><div class="live-head"><div><p class="eyebrow">EVIDENCIA REAL · SIN DATOS DE EJEMPLO</p><h2>Registro público de QuantFut</h2></div>${badge('Fuente: API pública', 'accent')}</div>
    <div class="live-facts"><div><span>LIQUIDADOS · 30 DÍAS</span><strong>${last30 ? realNumber(settled) : '—'}</strong><small>${record ? record.status === 'error' ? 'No disponible' : 'picks publicados' : 'Cargando…'}</small></div><div><span>EV AL CIERRE JUSTO</span><strong>${settled ? realPercent(last30.avg_ev_close, 2) : '—'}</strong><small>${settled ? 'Pinnacle sin margen' : 'Sin muestra; no se estima'}</small></div><div><span>ROI · 30 DÍAS</span><strong>${settled ? realPercent(last30.roi, 2) : '—'}</strong><small>${settled && Array.isArray(last30.roi_ci95) ? `IC95 ${realPercent(last30.roi_ci95[0], 2)} a ${realPercent(last30.roi_ci95[1], 2)}` : 'Sin intervalo publicable'}</small></div></div>
    <div class="live-evidence-grid"><div><h3>Historial mensual</h3>${monthly ? monthly.length ? `<div class="table-wrap" tabindex="0" role="region" aria-label="Historial mensual real"><table><thead><tr><th>Mes</th><th>Picks</th><th>EV cierre</th><th>ROI</th></tr></thead><tbody>${monthly.map(row => `<tr><td>${realDate(row.month)}</td><td>${realNumber(row.n_picks)}</td><td>${realPercent(row.avg_ev_close_pct, 2)}</td><td>${realPercent(row.roi_pct, 2)}</td></tr>`).join('')}</tbody></table></div>` : '<p>Sin picks liquidados publicados todavía.</p>' : `<p>${record ? 'No se pudo consultar.' : 'Cargando…'}</p>`}<a href="/track-record" target="_blank" rel="noopener">Consultar JSON original ↗</a></div>
    <div><h3>Calibración</h3>${runs ? runs.length ? `<p>Última ventana: ${realNumber(runs[0].n_obs)} partidos · RPS ${realNumber(runs[0].rps, 4)} · mercado ${realNumber(runs[0].rps_market, 4)}.</p><small>${realDate(runs[0].window_start)} – ${realDate(runs[0].window_end)}</small>` : '<p>No hay corridas de calibración públicas.</p>' : `<p>${calibration ? 'No se pudo consultar.' : 'Cargando…'}</p>`}<a href="/calibration" target="_blank" rel="noopener">Consultar JSON original ↗</a></div>
    <div><h3>Cadena de hashes</h3>${batches ? batches.length ? `<p>${realNumber(batches.length)} lotes recientes. Último: ${realDate(batches[0].batch_date)}.</p><code>${esc(batches[0].chain_sha256 ?? 'Hash no disponible')}</code>` : '<p>Aún no hay lotes públicos para verificar.</p>' : `<p>${chain ? 'No se pudo consultar.' : 'Cargando…'}</p>`}<a href="/chain" target="_blank" rel="noopener">Consultar JSON original ↗</a></div></div>
    <p class="live-reason">El historial de picks publicados es distinto de la muestra en sombra que evalúa la puerta comercial. El CLV con margen no sustituye al EV al cierre sin margen.</p><button type="button" class="text-link" data-action="refresh-public">Actualizar evidencia ↻</button></section>`;
}

function homeView() {
  return redesignedHome();
}

// Agenda editorial: adapta la jerarquía de TennisPredictions al criterio propio.
function redesignedHome() {
  const dayFixtures = fixtures.filter(fx => fx.day === state.dayOffset);
  const query = fold(state.homeSearch.trim());
  const visible = dayFixtures.filter(fx =>
    (state.homeLeague === 'Todas' || fx.league === state.homeLeague)
    && (state.homeStatus === 'todos' || (state.homeStatus === 'proximos' ? !fx.closed : fx.closed))
    && (!query || fold(`${fx.home} ${fx.away} ${fx.league}`).includes(query)));
  const bestRow = fx => [...fx.rows.filter(row => row.family === '1X2')].sort((a, b) => (b.edge ?? -Infinity) - (a.edge ?? -Infinity))[0];
  visible.sort((a, b) => state.homeSort === 'precio'
    ? (bestRow(b)?.edge ?? -Infinity) - (bestRow(a)?.edge ?? -Infinity)
    : a.kickoff - b.kickoff);
  const open = dayFixtures.filter(fx => !fx.closed).length;
  const count = status => status === 'todos' ? dayFixtures.length : status === 'proximos' ? open : dayFixtures.length - open;
  const rowMarkup = fx => {
    const row = bestRow(fx);
    return `<article class="schedule-row"><div class="schedule-time"><strong>${timeLabel(fx.kickoff)}</strong><small>${fx.closed ? 'Cerrado' : 'Próximo'}</small></div>
      <button type="button" class="schedule-teams" data-match="${fx.id}" aria-label="Ver análisis de ${esc(fx.home)} contra ${esc(fx.away)}"><span>${teamMark(fx.home)}<strong>${esc(fx.home)}</strong></span><span>${teamMark(fx.away, true)}<strong>${esc(fx.away)}</strong></span></button>
      <div class="schedule-prob"><span>1 <b>${fx.probs[0]}%</b></span><span>X <b>${fx.probs[1]}%</b></span><span>2 <b>${fx.probs[2]}%</b></span><small>Probabilidad del modelo</small></div>
      <div class="schedule-price"><strong>${fmtOdds(row.best?.price)}</strong><small>${esc(row.best?.book.name ?? 'Sin cuota')}</small></div>
      <div class="schedule-selection"><strong>${esc(row.selection)}</strong><small>Justo ${fmtOdds(1 / row.pFair)} · ${fmtEdge(row.edge)} bruto</small></div>
      <div class="schedule-state">${statusBadge(row.status)}</div><button type="button" class="schedule-arrow" data-match="${fx.id}" aria-label="Abrir ficha de ${esc(fx.home)} contra ${esc(fx.away)}">↗</button></article>`;
  };
  const leagues = [...new Set(visible.map(fx => fx.league))];
  const matchCountLabel = n => `${n} ${n === 1 ? 'partido' : 'partidos'}`;
  const latest = dayFixtures.length ? new Date(Math.max(...dayFixtures.map(fx => fx.snapshot))) : null;
  const gate = publicData?.gate;
  const active = isPublicationActive(gate);
  const systemLabel = !gate ? 'Consultando publicación' : gate.status !== 'ready' ? 'Publicación sin verificar' : active ? 'Publicación activa' : 'Publicación pausada';
  return `<section class="forecast-hero" aria-labelledby="forecast-title"><div class="forecast-copy"><p class="eyebrow">FÚTBOL / ANÁLISIS Y PRECIO JUSTO</p><h1 id="forecast-title">Lee el partido.<br><em>Entiende la cuota.</em></h1><p>El contexto del encuentro, la probabilidad del modelo y el precio de mercado. Todo a la vista, antes de decidir.</p><div class="hero-actions"><button type="button" class="primary-button" data-route="partidos">Explorar partidos <span aria-hidden="true">↗</span></button><button type="button" class="text-link" data-route="historial">Ver historial verificable ↗</button></div></div>
    <aside class="forecast-summary" aria-label="Resumen de la agenda ficticia"><span class="summary-icon" aria-hidden="true">Q.</span><div><span class="eyebrow">AGENDA DE DEMOSTRACIÓN</span><strong>${dayFixtures.length}<small> partidos · ${dayLabel(state.dayOffset).toLowerCase()}</small></strong><p>Ejemplos ficticios para explorar la nueva interfaz.</p></div><div class="summary-bottom"><span>${open} mercados abiertos</span><span>${latest ? `Captura ${timeLabel(latest)}` : 'Sin captura'} · demo</span></div></aside></section>
    <div class="publication-strip"><span class="publication-dot ${active ? 'active' : ''}" aria-hidden="true"></span><strong>${systemLabel}</strong><span>Los ejemplos de esta agenda no son picks publicados.</span><button type="button" class="text-link" data-action="refresh-public">Actualizar ↻</button></div>
    <div class="forecast-shortcuts" aria-label="Accesos rápidos"><button type="button" class="active" data-route="inicio" aria-current="page">Todos los partidos <span>↗</span></button><button type="button" data-route="mercados" data-home-market-mode="dia">Pick del día <span>↗</span></button><button type="button" data-route="mercados" data-home-market-mode="ventaja">Comparar cuotas <span>↗</span></button><button type="button" data-route="mercados" data-home-market-mode="combinadas">Combinadas <span>↗</span></button></div>
    <section class="forecast-board" aria-labelledby="forecast-board-title"><div class="board-heading"><div><p class="eyebrow">EL TABLERO / DATOS FICTICIOS</p><h2 id="forecast-board-title">Agenda de partidos</h2></div><span>${dateFmt(addDays(state.dayOffset), { weekday: 'long', day: 'numeric', month: 'long' })}</span></div>
      ${dayRail()}
      <div class="board-toolbar"><div class="board-status" aria-label="Estado de los partidos">${[['todos', 'Todos'], ['proximos', 'Próximos'], ['cerrados', 'Cerrados']].map(([key, label]) => `<button type="button" data-home-status="${key}" aria-pressed="${state.homeStatus === key}" class="${state.homeStatus === key ? 'active' : ''}">${label}<span>${count(key)}</span></button>`).join('')}</div><label class="board-search"><span aria-hidden="true">⌕</span><input id="home-search" type="search" data-input="home-search" aria-label="Buscar equipo o liga en la agenda demo" placeholder="Buscar equipo o liga…" value="${esc(state.homeSearch)}" /></label><label class="sr-only" for="home-sort">Ordenar partidos</label><select id="home-sort"><option value="hora" ${state.homeSort === 'hora' ? 'selected' : ''}>Por hora</option><option value="precio" ${state.homeSort === 'precio' ? 'selected' : ''}>Por diferencia de precio</option></select></div>
      <div class="board-layout"><aside class="board-leagues" aria-label="Filtrar agenda por liga"><p class="eyebrow">COMPETICIONES</p>${['Todas', ...LEAGUES].map((league, i) => `<button type="button" data-home-league="${esc(league)}" aria-pressed="${state.homeLeague === league}" class="${state.homeLeague === league ? 'active' : ''}"><span class="league-symbol" aria-hidden="true">${i === 0 ? '◎' : '◇'}</span><span>${i === 0 ? 'Todas las ligas' : esc(league.replace(' · demo', ''))}</span><b>${i === 0 ? dayFixtures.length : dayFixtures.filter(fx => fx.league === league).length}</b></button>`).join('')}<div class="league-note"><strong>Tu evidencia, abierta.</strong><p>Revisa resultados, precio de cierre y validación desde el historial público.</p><button type="button" class="text-link" data-route="historial">Consultar historial ↗</button></div></aside>
      <div class="board-matches"><div class="schedule-columns" aria-hidden="true"><span>HORA</span><span>PARTIDO</span><span>MODELO · 1X2</span><span>MEJOR CUOTA¹</span><span>SELECCIÓN · REFERENCIA</span><span>ESTADO</span><span></span></div>
      ${visible.length ? leagues.map(league => `<section class="schedule-group" aria-label="${esc(league)}"><h3><span aria-hidden="true">◇</span>${esc(league)}<small>${matchCountLabel(visible.filter(fx => fx.league === league).length)}</small></h3>${visible.filter(fx => fx.league === league).map(rowMarkup).join('')}</section>`).join('') : '<div class="empty-state"><h3>No hay partidos con estos filtros</h3><p>Cambia la fecha o limpia los filtros para seguir explorando.</p></div>'}
      <div class="board-foot"><span role="status">${visible.length} de ${dayFixtures.length} partidos de ejemplo</span><button type="button" class="text-link" data-action="clear-home">Limpiar filtros ↻</button></div></div></div><p class="board-disclaimer">¹ Mejor cuota entre las casas de la demo para la selección mostrada. Modelo, precio justo y diferencia de precio son medidas distintas. «Cerrado» significa que el partido ya empezó; no acredita su resultado.</p></section>
    <div class="home-public-data">${homeRealStrip()}<details class="publication-details"><summary>Ver el estado de publicación y su evidencia</summary>${liveStatus()}</details></div>
    <div class="proof-rail" aria-label="Cómo se presentará la evidencia"><div><span>01 / CONTEXTO</span><strong>El partido completo</strong><small>Forma, cara a cara, estadísticas y alineaciones.</small></div><div><span>02 / PRECIO</span><strong>Una referencia comparable</strong><small>Cuota, justo y mínimo del mismo instante.</small></div><div><span>03 / EVIDENCIA</span><strong>Resultados a la vista</strong><small>Historial, muestra y validación del servidor.</small></div></div>`;
}

function deskFilteredRows() {
  const query = fold(state.deskSearch.trim());
  return allRows.filter(row => row.fx.day === state.deskDay
    && (state.deskStatus === 'todos' || (state.deskStatus === 'abiertos' ? !row.fx.closed : row.fx.closed))
    && (!state.deskMatch || row.fx.id === state.deskMatch)
    && (state.deskFamily === 'Todos' || row.family === state.deskFamily)
    && (!state.deskOnlyCandidates || row.status === 'candidata')
    && (!state.deskMine || state.followed.includes(row.fx.league))
    && (!query || fold(`${row.fx.home} ${row.fx.away} ${row.fx.league} ${row.market} ${row.selection}`).includes(query)));
}

function deskView() {
  const days = [...new Set(fixtures.map(fx => fx.day))].sort((a, b) => a - b);
  const dayIndex = days.indexOf(state.deskDay);
  const dayFixtures = fixtures.filter(fx => fx.day === state.deskDay).sort((a, b) => a.kickoff - b.kickoff);
  const visibleFixtures = dayFixtures.filter(fx => state.deskStatus === 'todos' || (state.deskStatus === 'abiertos' ? !fx.closed : fx.closed));
  const rows = deskRowsForMode();
  const showTable = ['todas', 'ventaja', 'probables'].includes(state.deskMode) || (state.deskMode === 'combinadas' && state.comboTab === 'manual');
  const statusChip = (value, label, count) => `<button type="button" class="chip ${state.deskStatus === value ? 'selected' : ''}" data-desk-status="${value}" aria-pressed="${state.deskStatus === value}">${label} <b>${count}</b></button>`;
  const matchButton = fx => {
    const candidates = fx.rows.filter(row => row.status === 'candidata').length;
    const tag = fx.closed ? '<small class="tag muted">Cerrado</small>'
      : fx.excluded ? '<small class="tag warn">Excluido</small>'
        : candidates ? `<small class="tag good">${candidates} cand.</small>`
          : `<small class="tag plain">${fx.rows.length} precios</small>`;
    const team = (name, away) => `<span>${teamMark(name, away)}<span class="team-name">${name}</span></span>`;
    return `<button type="button" class="desk-match ${state.deskMatch === fx.id ? 'active' : ''}" data-desk-match="${fx.id}" aria-pressed="${state.deskMatch === fx.id}"><span class="desk-when"><span class="desk-time">${timeLabel(fx.kickoff)}</span>${tag}</span><span class="desk-teams">${team(fx.home)}${team(fx.away, true)}</span></button>`;
  };
  const byLeague = LEAGUES.map(league => [league, visibleFixtures.filter(fx => fx.league === league)]).filter(([, list]) => list.length);
  const matchLabel = state.deskMatch ? (fx => `${fx.home} × ${fx.away}`)(fixtureById.get(state.deskMatch)) : 'todos los partidos';
  return `<div class="view-title compact"><div><p class="eyebrow">MESA DE MERCADOS / PRECIO JUSTO CONTRA CASAS</p><h1>Mesa de mercados</h1><p class="lead">Cada fila compara la mejor casa de la lista con el precio justo de Pinnacle en el mismo snapshot. El modelo aparece como diagnóstico; no ordena ni elige.</p></div>${badge('Precios ficticios', 'accent')}</div>
    ${quickBar()}
    <div class="desk">
      <aside class="desk-side" aria-label="Partidos">
        <div class="side-head"><span>PARTIDOS</span><b>${dayFixtures.length}</b></div>
        <div class="day-stepper"><button type="button" data-desk-day="${days[dayIndex - 1] ?? ''}" aria-label="Día anterior" ${dayIndex <= 0 ? 'disabled' : ''}>‹</button><strong>${dayLabel(state.deskDay)} · ${dateFmt(addDays(state.deskDay), { day: 'numeric', month: 'short' })}</strong><button type="button" data-desk-day="${days[dayIndex + 1] ?? ''}" aria-label="Día siguiente" ${dayIndex >= days.length - 1 ? 'disabled' : ''}>›</button></div>
        <div class="chip-row" role="group" aria-label="Estado de los partidos">${statusChip('todos', 'Todos', dayFixtures.length)}${statusChip('abiertos', 'Abiertos', dayFixtures.filter(fx => !fx.closed).length)}${statusChip('cerrados', 'Cerrados', dayFixtures.filter(fx => fx.closed).length)}</div>
        <div class="desk-match-list"><button type="button" class="desk-match all ${state.deskMatch ? '' : 'active'}" data-desk-match="" aria-pressed="${!state.deskMatch}"><span>Todos los partidos</span><b>${visibleFixtures.length}</b></button>
        ${byLeague.map(([league, list]) => `<p class="desk-league">${league}</p>${list.map(matchButton).join('')}`).join('') || '<p class="rail-empty">No hay partidos con este filtro.</p>'}</div>
      </aside>
      <section class="desk-main" aria-label="Mercados">
        ${state.deskMode === 'dia' ? pickOfDayPanel() : state.deskMode === 'combinadas' ? comboPanel() : kpiStrip(dayFixtures)}
        ${showTable ? `<div class="desk-toolbar">
          <div class="chip-row scroll" role="group" aria-label="Familia de mercado">${FAMILIES.map(family => `<button type="button" class="chip ${state.deskFamily === family ? 'selected' : ''}" data-desk-family="${family}" aria-pressed="${state.deskFamily === family}">${family}</button>`).join('')}</div>
          <div class="toolbar-line">
            <label class="search"><span class="sr-only">Buscar equipo, liga o mercado</span><input id="desk-search" type="search" placeholder="Buscar equipo, liga o mercado" value="${esc(state.deskSearch)}" data-input="desk-search" autocomplete="off"></label>
            <button type="button" class="chip ${state.deskOnlyCandidates ? 'selected' : ''}" data-desk-toggle="deskOnlyCandidates" aria-pressed="${state.deskOnlyCandidates}">Solo candidatas</button>
            <button type="button" class="chip ${state.deskMine ? 'selected' : ''}" data-desk-toggle="deskMine" aria-pressed="${state.deskMine}">Mis ligas</button>
            <span class="result-count" aria-live="polite">${rows.length} filas · ${matchLabel}</span>
          </div>
        </div>
        ${rows.length ? marketTable(rows, { caption: 'Mercados del día: modelo, precio justo de Pinnacle, mejor casa, diferencia y estado.' }) : '<div class="empty-state"><span class="empty-symbol">◇</span><h3>Ninguna fila con estos filtros</h3><p>Quita «Solo candidatas» o cambia de día: que no haya candidatas es un resultado normal.</p></div>'}
        <p class="bottom-note">Justo = Pinnacle sin margen. «vs justo» = mejor cuota × probabilidad justa − 1. Mínimo = cuota a partir de la cual el pick sigue superando el 2%. Solo el 1X2 entra en el criterio; el resto es referencia.</p>` : ''}
      </section>
      <aside class="desk-rail">${shadowList(shadowPicks.filter(pick => pick.row.fx.day === state.deskDay))}
        <section class="rail-panel legend-panel"><p class="eyebrow">CÓMO LEER LA MESA</p><dl>
          <div><dt>${badge('Candidata ≥ +2%', 'good')}</dt><dd>Casa de la lista que paga al menos un 2% sobre el justo. Solo 1X2.</dd></div>
          <div><dt>${badge('Excluido · Pinnacle', 'warn')}</dt><dd>Pinnacle se aparta más de un 3% del consenso: precio roto, partido fuera.</dd></div>
          <div><dt>${badge('Solo referencia', 'muted')}</dt><dd>Mercado con precio justo calculado, fuera del criterio de picks.</dd></div>
        </dl></section>
      </aside>
    </div>`;
}

function picksView() {
  const leagues = ['Todas', ...LEAGUES];
  const visible = shadowPicks.filter(pick => state.pickLeague === 'Todas' || pick.row.fx.league === state.pickLeague);
  const free = visible.filter(pick => pick.tier === 'free');
  const plus = visible.filter(pick => pick.tier === 'plus');
  const card = ({ row }) => `<article class="pick-card">
    <div class="pick-main"><div class="pick-meta"><span>${row.fx.league}</span><span>Inicio ${stamp(row.fx.kickoff)}</span></div>
      <h2>${row.fx.home} <span>vs</span> ${row.fx.away}</h2>
      <div class="pick-tags">${badge(row.market)}${badge('Gratis · demo', 'accent')}${badge(row.fx.closed ? 'Pendiente de liquidar' : 'En sombra · no publicado', 'muted')}</div>
      <p class="pick-published">Snapshot ${stamp(row.fx.snapshot)} · Pinnacle y ${row.best.book.name} en la misma respuesta</p></div>
    <div class="pick-detail">
      <div><span class="metric-label">SELECCIÓN</span><strong>${row.selection}</strong></div>
      <div><span class="metric-label">${row.best.book.name.toUpperCase()}</span><strong>${fmtOdds(row.best.price)}</strong></div>
      <div><span class="metric-label">PROBABILIDAD REAL</span><strong>${fmtPct(row.pFair, 0)}</strong><small>sale ${probabilityLabel(row.pFair)?.frequency ?? '—'}</small></div>
      <div><span class="metric-label">PRECIO MÍNIMO</span><strong>${fmtOdds(row.minPrice)}</strong></div>
      <div><span class="metric-label">VS JUSTO · AL CIERRE</span><strong class="pos">${fmtEdge(row.edge)}</strong><small>${fmtEdge(row.expectedEdge)} esperado</small></div>
    </div>
    <div class="pick-actions"><button type="button" class="pick-open" data-row="${row.key}">Ver precios <span aria-hidden="true">↗</span></button><button type="button" class="text-link" data-match="${row.fx.id}">Ficha</button></div>
  </article>`;
  return `<div class="view-title"><div><p class="eyebrow">PRONÓSTICOS / CRITERIO EN SOMBRA</p><h1>Picks</h1><p class="lead">Un pick nace cuando una casa de la lista paga al menos un 2% por encima del precio justo de Pinnacle. Cada uno lleva su cuota mínima: por debajo de ella, ya no vale.</p></div>${badge('API pública + demo señalada', 'accent')}</div>
    ${livePicks()}
    <div class="disclosure"><span class="disclosure-icon">ⓘ</span><div><strong>Maqueta ficticia bajo esta línea</strong><span>Estas tarjetas son lo que el criterio habría elegido sobre precios de demostración. No son recomendaciones reales ni se enviará ninguna apuesta.</span></div></div>
    <div class="chip-row filter-chips" role="group" aria-label="Competición">${leagues.map(league => `<button type="button" class="chip ${state.pickLeague === league ? 'selected' : ''}" data-pick-league="${league}" aria-pressed="${state.pickLeague === league}">${league.replace(' · demo', '')}</button>`).join('')}<span class="result-count" aria-live="polite">${free.length} gratis · ${plus.length} Plus · solo demo</span></div>
    <div class="picks-list">${free.map(card).join('') || '<div class="empty-state"><span class="empty-symbol">◇</span><h3>Sin picks abiertos en esta competición</h3><p>Si ninguna casa supera el umbral, no hay pick. El sistema no rellena huecos.</p></div>'}
    ${plus.map(({ row }) => `<article class="pick-card locked"><div class="pick-main"><div class="pick-meta"><span>${row.fx.league}</span><span>Inicio ${stamp(row.fx.kickoff)}</span></div><h2>Pick Plus <span>·</span> ${row.fx.home} vs ${row.fx.away}</h2><p class="pick-published">Selección, casa y precio se entregarían solo tras autorizar la suscripción en el servidor.</p></div><button type="button" class="secondary-button" data-modal="premium">Cómo funcionaría</button></article>`).join('')}</div>
    <div class="bottom-note">El bloque real consulta únicamente /picks/free y verifica la puerta comercial. Ningún pick privado ni token de servicio llega al navegador.</div>`;
}

// Línea de alta probabilidad (diseño 2026-10-05). Solo datos reales de
// /alta-probabilidad: es una línea de acierto, no de valor, y se dice.
const ALTA_MERCADO = { h2h: 'Ganador (1X2)', double_chance: 'Doble oportunidad', totals: 'Goles', team_totals_home: 'Marca el local', team_totals_away: 'Marca el visitante', btts: 'Ambos marcan', spreads: 'Hándicap asiático', corners: 'Córners', corners_home: 'Córners del local', corners_away: 'Córners del visitante' };
function altaView() {
  const head = `<div class="view-title"><div><p class="eyebrow">PRONÓSTICOS / ALTA PROBABILIDAD</p><h1>Alta probabilidad</h1><p class="lead">Un pronóstico por partido, solo si su probabilidad real está entre el 80% y el 95%: Pinnacle sin margen o, en córners, el modelo de córners sin pasar nunca de lo que da la casa. Cada uno se sella en la cadena antes del partido.</p></div>${badge('Datos del servidor', 'accent')}</div>`;
  const source = publicData?.alta;
  if (!source) return `${head}<section class="live-panel"><p>Consultando pronósticos de alta probabilidad…</p></section>`;
  if (source.status !== 'ready') return `${head}<section class="live-panel"><p>No se pudieron consultar los pronósticos. Inténtalo de nuevo más tarde.</p><button type="button" class="text-link" data-action="refresh-public">Actualizar ↻</button></section>`;
  const { estado, motivos, proximos, historial: h } = source.data;
  const ic = Array.isArray(h.diferencia_ic95) ? h.diferencia_ic95 : null;
  const record = h.n ? `<div class="live-facts"><div><span>PROMETIDO</span><strong>${realNumber(h.acierto_prometido, 1)}%</strong><small>media de las probabilidades</small></div><div><span>REAL</span><strong>${realNumber(h.acierto_real, 1)}%</strong><small>${realNumber(h.aciertos)} de ${realNumber(h.n)} acertados</small></div><div><span>DIFERENCIA · IC95</span><strong>${ic ? `${realNumber(ic[0], 1)} a ${realNumber(ic[1], 1)}` : '—'}</strong><small>${ic ? 'puntos, real − prometido' : 'Sin intervalo todavía'}</small></div></div>` : '<p>Todavía no hay pronósticos liquidados.</p>';
  const byMarket = Object.entries(h.por_mercado ?? {});
  const marketTable = byMarket.length ? `<div class="table-wrap" tabindex="0" role="region" aria-label="Acierto por mercado"><table><thead><tr><th>Mercado</th><th>Pronósticos</th><th>Prometido</th><th>Real</th></tr></thead><tbody>${byMarket.map(([market, row]) => `<tr><td>${esc(ALTA_MERCADO[market] ?? market)}</td><td>${realNumber(row.n)}</td><td>${realNumber(row.acierto_prometido, 1)}%</td><td>${realNumber(row.acierto_real, 1)}%</td></tr>`).join('')}</tbody></table></div>` : '';
  const roi = h.rendimiento_ref?.n ? `<p class="live-reason">A la mejor cuota entre las casas de la lista (${realNumber(h.rendimiento_ref.n)} pronósticos con cuota): rendimiento ${realPercent(h.rendimiento_ref.roi, 2)}.</p>` : '';
  const note = '<p class="live-reason">Es una línea de acierto, no de valor. En el histórico (football-data, 7 ligas, 2019-2025), a la mejor cuota de bet365 y 1xBet, los favoritos con probabilidad de 80% o más dejaron un rendimiento de −2,4%. La doble oportunidad, «marca un equipo», el hándicap asiático y los córners no se pudieron medir en rendimiento: no hay cuotas históricas de esos mercados. Por eso se publican las dos cosas: lo que se acierta y lo que rinde. Un hándicap devuelto o unos córners sin estadística no cuentan como acierto ni como fallo.</p>';
  const motivo = esc((motivos ?? []).join(' · '));
  const paused = estado === 'pausada' ? `<p class="live-reason">Línea pausada: ${motivo || 'sin motivo informado'}</p>` : estado !== 'activa' ? `<p class="live-reason">${motivo || 'Línea desactivada'}</p>` : '';
  const cards = proximos.length ? `<div class="live-pick-list">${proximos.map(p => `<article class="live-pick alta-pick"><div><span>${esc(p.league_id ?? 'Liga')} · ${realDate(p.kickoff_utc)} ${esc(realTime(p.kickoff_utc))}</span><h3>${esc(p.texto ?? 'Pronóstico')}</h3><p>${esc(p.local ?? 'Local')} <small>vs</small> ${esc(p.visitante ?? 'Visitante')}</p><small class="live-prob">Probabilidad real: ${esc(probabilityLabel(p.prob)?.text ?? 'sin dato')}</small></div><div><span>Cuota justa</span><strong>${realNumber(p.fair_price, 2)}</strong><small>${p.ref_price ? `${esc(p.ref_book ?? 'Casa')} ${realNumber(p.ref_price, 2)}` : 'Sin cuota de referencia'}</small><small>Lote ${esc(p.batch_date ?? '—')} · ${esc(String(p.chain_sha256 ?? '').slice(0, 12))}</small></div></article>`).join('')}</div>` : '<p>No hay pronósticos de alta probabilidad para los próximos partidos. Si ningún resultado llega al 80%, no se fuerza uno.</p>';
  const badgeText = estado === 'activa' ? 'Activa' : estado === 'pausada' ? 'Pausada' : 'Desactivada';
  return `${head}
    <section class="live-panel" aria-label="Historial de alta probabilidad"><div class="live-head"><div><p class="eyebrow">HISTORIAL PÚBLICO · /ALTA-PROBABILIDAD</p><h2>Prometido frente a real</h2></div>${badge(badgeText, estado === 'activa' ? 'good' : 'muted')}</div>${record}${marketTable}${roi}${note}</section>
    <section class="live-panel" aria-label="Próximos pronósticos de alta probabilidad"><div class="live-head"><div><p class="eyebrow">PRÓXIMOS PARTIDOS</p><h2>Pronósticos sellados</h2></div></div>${paused}${cards}<button type="button" class="text-link" data-action="refresh-public">Actualizar ↻</button></section>`;
}

// Parley del día (2026-10-11). Solo datos reales de /parley: cada parlay se
// sella en la cadena antes de los partidos; el historial incluye los perdidos.
const PARLEY_ESTADO = { ganado: 'Ganado', perdido: 'Perdido', nulo: 'Nulo' };
const PATA_ESTADO = { win: '✓', loss: '✗', push: '↺', void: '—' };

function parleyPata(p) {
  return `<div class="live-pick"><div><strong>${esc(p.texto)}</strong><small>${esc(p.local)} – ${esc(p.visitante)} · ${realDate(p.kickoff_utc)} ${esc(realTime(p.kickoff_utc))}</small></div><div><strong>${realNumber(p.price, 2)}</strong><small>${realNumber(p.prob * 100, 0)}% · ${esc(p.book)} ${p.outcome ? PATA_ESTADO[p.outcome] ?? '' : ''}${p.marcador ? ` · ${esc(p.marcador)}` : ''}</small></div></div>`;
}

function parleyTicket(t) {
  const estado = t.outcome ? PARLEY_ESTADO[t.outcome] ?? t.outcome : 'En juego';
  return `<article class="ladder-card"><div class="live-head"><div><p class="eyebrow">ESCALÓN ${realNumber(t.escalon)} · ${realNumber(t.n_patas)} PATAS</p><h3>${esc(estado)}</h3></div><strong class="ladder-balance">${realNumber(t.cuota_total, 2)}</strong></div><p class="ladder-meta">Probabilidad ${realNumber(t.prob_total * 100, 1)}% · 1 de cada ${realNumber(1 / t.prob_total, 1)}${t.factor_pago != null ? ` · pagó ×${realNumber(t.factor_pago, 2)}` : ''}</p><div class="live-pick-list">${t.patas.map(parleyPata).join('')}</div></article>`;
}

function parleyView() {
  const head = `<div class="view-title"><div><p class="eyebrow">COMBINADAS / PARLEY</p><h1>Parley del día</h1><p class="lead">De 1 a 5 parlays al día, uno por escalón de cuota (≈2,0 · 2,5 · 3,0 · 4,0 · 5,0), con la combinación más probable de todos los mercados. Se elige por probabilidad, no por valor: el margen de la casa se paga en cada pata. Cada parlay se sella en la cadena antes del partido.</p></div>${badge('Datos del servidor', 'accent')}</div>`;
  const source = publicData?.parley;
  if (!source) return `${head}<section class="live-panel"><p>Consultando el parley del día…</p></section>`;
  if (source.status !== 'ready') return `${head}<section class="live-panel"><p>No se pudo consultar el parley. Inténtalo de nuevo más tarde.</p><button type="button" class="text-link" data-action="refresh-public">Actualizar ↻</button></section>`;
  const { activo, dias, resumen, control } = source.data;
  const [ultimo, ...anteriores] = dias;
  const hoy = ultimo ? `<p class="eyebrow">${esc(String(ultimo.dia))} · lote ${esc(String(ultimo.chain_sha256 ?? '').slice(0, 12))}</p><div class="ladder-grid">${ultimo.tickets.map(parleyTicket).join('')}</div>` : `<p>${activo ? 'Hoy no hay combinación que cumpla la regla.' : 'El parley del día todavía no está activo.'}</p>`;
  const filas = Object.entries(resumen?.por_escalon ?? {}).map(([e, b]) => `<div><span>ESCALÓN ${esc(e)}</span><strong>${realNumber(b.aciertos)} de ${realNumber(b.n)}</strong><small>prometido ${realNumber(b.prob_media, 1)}% · real ${realNumber(b.acierto_real, 1)}% · ${realNumber(b.unidades, 2)} u</small></div>`).join('');
  const stats = `<div class="live-facts">${filas || '<div><span>HISTORIAL</span><strong>—</strong><small>Sin parlays liquidados todavía</small></div>'}</div><p class="ladder-meta">${(control?.motivos ?? []).map(esc).join(' · ')}</p>`;
  const historial = anteriores.length ? anteriores.map(d => `<details class="live-panel"><summary>${esc(String(d.dia))} · ${d.tickets.map(t => `${realNumber(t.cuota_total, 2)} ${t.outcome ? PARLEY_ESTADO[t.outcome] ?? '' : '…'}`).join(' · ')}</summary><div class="ladder-grid">${d.tickets.map(parleyTicket).join('')}</div></details>`).join('') : '<p>El historial empieza con el primer día sellado.</p>';
  return `${head}<section class="live-panel">${hoy}</section><section class="live-panel"><h2>Prometido frente a real</h2>${stats}</section><section><h2>Historial</h2>${historial}</section>`;
}

// Reto escalera (2026-10-08). Solo datos reales de /escalera: cada escalón
// se sella antes del partido y el historial enseña también los retos fallidos.
// Puede haber varios retos abiertos a la vez, de 3 a 6 escalones.
const ESCALERA_ESTADO = { en_curso: 'Buscando escalón', esperando: 'Esperando resultado', completado: 'Completado', fallido: 'Fallido' };
const unidades = value => `${realNumber(value, 2)} u`;
function escaleraSerie(serie) {
  if (!serie.length) return '';
  const values = [0, ...serie.map(r => Number(r.acumulado))];
  const min = Math.min(...values, 0);
  const span = Math.max(...values, 0) - min || 1;
  const x = i => 8 + i / Math.max(values.length - 1, 1) * 284;
  const y = v => 72 - (v - min) / span * 60;
  const last = values.at(-1);
  return `<svg class="clv-chart ${last < 0 ? 'neg' : ''}" viewBox="0 0 300 80" preserveAspectRatio="none" role="img" aria-label="Ganancia acumulada: ${realNumber(last, 2)} unidades tras ${serie.length} retos"><line x1="8" x2="292" y1="${y(0).toFixed(1)}" y2="${y(0).toFixed(1)}" class="zero"/><polyline points="${values.map((v, i) => `${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(' ')}" vector-effect="non-scaling-stroke"/></svg>`;
}
function escaleraPaso(p) {
  const estado = p.outcome === 'win' ? ['won', 'Ganado'] : p.outcome === 'loss' ? ['lost', 'Perdido'] : p.outcome === 'push' ? ['void', 'Devuelto (no cuenta)'] : p.outcome === 'void' ? ['void', 'Nulo (aplazado)'] : ['pending', 'Pendiente'];
  return `<article class="live-pick ladder-pick ${estado[0]}"><div><span>Escalón ${realNumber(p.paso)} · ${esc(p.league_id ?? 'Liga')} · ${realDate(p.kickoff_utc)} ${esc(realTime(p.kickoff_utc))}</span><h3>${esc(p.texto ?? 'Pronóstico')}</h3><p>${esc(p.local ?? 'Local')} <small>vs</small> ${esc(p.visitante ?? 'Visitante')}${p.marcador ? ` · ${esc(p.marcador)}` : ''}${p.valor != null ? ` · ${realNumber(p.valor)} ${String(p.market).startsWith('corners') ? 'córners' : 'tarjetas'}` : ''}</p><small class="live-prob">Probabilidad real: ${esc(probabilityLabel(p.prob)?.text ?? 'sin dato')}</small></div><div><span>Cuota</span><strong>${realNumber(p.price, 2)}</strong><small>${esc(p.book ?? 'Casa')}</small><small class="result ${estado[0] === 'won' ? 'won' : estado[0] === 'lost' ? 'lost' : ''}">${estado[1]}</small><small>Lote ${esc(p.batch_date ?? '—')} · ${esc(String(p.chain_sha256 ?? '').slice(0, 12))}</small></div></article>`;
}
function escaleraReto(r) {
  const objetivo = r.pasos_objetivo;
  const ganados = r.ganados ?? 0;
  const pasos = r.pasos ?? [];
  const peldanos = Array.from({ length: objetivo }, (_, i) => {
    const n = i + 1;
    const cls = n <= ganados ? 'won' : n === ganados + 1 && r.estado === 'esperando' ? 'pending' : '';
    return `<li class="ladder-step ${cls}"><span>${n}</span><small>${n <= ganados ? '✓' : cls === 'pending' ? 'en juego' : ''}</small></li>`;
  }).join('');
  const ultimo = pasos.at(-1);
  const potencial = r.estado === 'esperando' && ultimo ? Number(r.en_juego) * Number(ultimo.price) : null;
  const freeroll = r.freeroll_x ? `se retira la inversión al llegar a ×${realNumber(r.freeroll_x, 1)}` : 'reto sin freeroll';
  return `<article class="ladder-card"><div class="live-head"><div><p class="eyebrow">RETO #${realNumber(r.reto_id)} · ${realNumber(objetivo)} ESCALONES</p><h3>${ESCALERA_ESTADO[r.estado] ?? r.estado}</h3></div><strong class="ladder-balance">${unidades(r.saldo)}</strong></div><ol class="ladder" aria-label="Escalones del reto ${realNumber(r.reto_id)}">${peldanos}</ol><p class="ladder-meta">${r.estado === 'esperando' ? `En juego ${unidades(r.en_juego)}${potencial ? ` · si se acierta: ${unidades(potencial)}` : ''}` : `${realNumber(ganados)} de ${realNumber(objetivo)} escalones`} · empezó con ${unidades(r.stake_inicial)} · ${Number(r.retirado) > 0 ? `retirado ${unidades(r.retirado)}: lo que queda va sin riesgo propio` : freeroll}</p>${pasos.length ? `<div class="live-pick-list">${[...pasos].reverse().map(escaleraPaso).join('')}</div>` : '<p class="ladder-meta">Esperando su primer escalón sellado.</p>'}</article>`;
}
function escaleraView() {
  const head = `<div class="view-title"><div><p class="eyebrow">RETOS / ESCALERA</p><h1>Reto escalera</h1><p class="lead">Retos de 3 a 6 escalones que empiezan con 10 unidades: cada escalón apuesta todo el saldo a un pronóstico de cuota 1,25-1,40. Ganarlos todos completa el reto; fallar uno lo cierra. Cada escalón se sella en la cadena antes del partido.</p></div>${badge('Datos del servidor', 'accent')}</div>`;
  const source = publicData?.escalera;
  if (!source) return `${head}<section class="live-panel"><p>Consultando el reto escalera…</p></section>`;
  if (source.status !== 'ready') return `${head}<section class="live-panel"><p>No se pudo consultar el reto escalera. Inténtalo de nuevo más tarde.</p><button type="button" class="text-link" data-action="refresh-public">Actualizar ↻</button></section>`;
  const { activo, reglas, actuales = [], historial, resumen, por_longitud: porLongitud = {}, serie, escalones } = source.data;
  const abiertos = actuales.length ? `<div class="ladder-grid">${actuales.map(escaleraReto).join('')}</div>` : `<p>${activo ? 'No hay retos abiertos: el próximo empieza en cuanto un partido cumpla la regla.' : 'El reto escalera todavía no está activo.'}</p>`;
  const r = resumen ?? {};
  const stats = `<div class="live-facts"><div><span>RETOS CERRADOS</span><strong>${realNumber(r.cerrados ?? 0)}</strong><small>${r.cerrados ? `${realNumber(r.completados)} completados · ${realNumber(r.tasa_completados, 1)}%` : 'Aún no se cerró ninguno'}</small></div><div><span>GANANCIA ACUMULADA</span><strong>${unidades(r.ganancia ?? 0)}</strong><small>${r.cerrados ? `sobre ${unidades(r.invertido)} invertidas · ${realPercent(r.roi, 1)}` : 'contando también los fallidos'}</small></div><div><span>ESCALONES ACERTADOS</span><strong>${escalones?.n ? `${realNumber(escalones.aciertos)} de ${realNumber(escalones.n)}` : '—'}</strong><small>${escalones?.n ? `probabilidad media prometida ${realNumber(escalones.prob_media, 1)}%` : 'sin escalones liquidados'}</small></div></div>${escaleraSerie(serie ?? [])}`;
  const longitudes = (reglas.longitudes ?? []).map(n => [n, porLongitud[String(n)] ?? {}]);
  const tablaLongitud = longitudes.length ? `<div class="table-wrap" tabindex="0" role="region" aria-label="Resultados por longitud"><table><thead><tr><th>Escalones</th><th>Retos cerrados</th><th>Completados</th><th>Ganancia</th><th>Rendimiento</th></tr></thead><tbody>${longitudes.map(([n, l]) => `<tr><td>${realNumber(n)}</td><td>${realNumber(l.cerrados ?? 0)}</td><td>${l.cerrados ? `${realNumber(l.completados)} · ${realNumber(l.tasa_completados, 1)}%` : '—'}</td><td>${l.cerrados ? unidades(l.ganancia) : '—'}</td><td>${l.cerrados ? realPercent(l.roi, 1) : '—'}</td></tr>`).join('')}</tbody></table></div>` : '';
  const tabla = historial?.length ? `<div class="table-wrap" tabindex="0" role="region" aria-label="Historial de retos"><table><thead><tr><th>Reto</th><th>Inicio</th><th>Escalones</th><th>Retirado</th><th>Estado</th><th>Ganancia</th></tr></thead><tbody>${historial.map(h => `<tr><td>#${realNumber(h.reto_id)}</td><td>${realDate(h.inicio)}</td><td>${realNumber(h.ganados)} de ${realNumber(h.pasos_objetivo)}</td><td>${unidades(h.retirado)}</td><td><span class="result ${h.estado === 'completado' ? 'won' : 'lost'}">${ESCALERA_ESTADO[h.estado] ?? h.estado}</span></td><td class="edge ${Number(h.ganancia) >= 0 ? 'pos' : 'neg'}">${Number(h.ganancia) > 0 ? '+' : ''}${unidades(h.ganancia)}</td></tr>`).join('')}</tbody></table></div>` : '<p>El historial aparecerá cuando se cierre el primer reto. Los fallidos se quedan, igual que los completados.</p>';
  const handicap = reglas.lineas_handicap?.length ? `<li><strong>Hándicap asiático protector</strong> (${reglas.lineas_handicap.map(l => `${l > 0 ? '+' : ''}${realNumber(l, l % 1 ? 1 : 0)}`).join(', ')}), con la probabilidad sacada de Pinnacle y medida en el histórico.</li>` : '';
  const regla = `<ul class="ladder-rules"><li><strong>Cuota ${realNumber(reglas.cuota_min, 2)}-${realNumber(reglas.cuota_max, 2)}</strong> en las casas de la lista, la mejor del momento.</li><li><strong>Se elige el pronóstico más probable</strong> de todos los partidos y mercados: ganador, goles, ambos marcan, hándicap asiático y córners. La probabilidad sale de Pinnacle sin margen o, en córners y tarjetas, del histórico de cada equipo, de la liga y del árbitro, y nunca por encima de la que da el mercado sin margen: si el modelo es más optimista que la casa, cuenta la de la casa. Solo entran las líneas que pasaron la prueba de calibración.</li><li><strong>Retos de 3 escalones por defecto</strong>; uno de 6 como mucho ${realNumber(reglas.max_seis_mes)} veces al mes, y de 4 o 5 cuando ya hay otro abierto. Cada reto tiene un escalón al día como máximo y dos retos nunca dependen del mismo partido.</li>${handicap}<li><strong>Freeroll a ×${realNumber(reglas.freeroll_x, 1)}</strong>: se retiran las ${realNumber(reglas.stake, 0)} unidades iniciales y se sigue con la ganancia.</li></ul><p class="live-reason">Lo que hay que saber: elegir el más probable sube el acierto de cada escalón, pero no quita el margen de la casa, y la escalera lo multiplica. En el histórico (football-data, 7 ligas, 2019-2025) esta forma de elegir dejó −11,5% por reto a 3 escalones y −26% a 6, aunque se completaran el 40% y el 15% de los retos. Por eso se enseña todo: cada escalón con su probabilidad, su cuota y su resultado, también los retos fallidos. Tarjetas: amarillas + rojas, una por tarjeta; algunas casas cuentan la roja como 2. En el histórico el modelo de tarjetas solo pasó la prueba en «menos de 6,5».</p>`;
  return `${head}
    <section class="live-panel" aria-label="Retos abiertos"><div class="live-head"><div><p class="eyebrow">RETOS ABIERTOS · ${realNumber(actuales.length)}</p><h2>En curso</h2></div>${badge(activo ? 'Activo' : 'Inactivo', activo ? 'good' : 'muted')}</div>${abiertos}<button type="button" class="text-link" data-action="refresh-public">Actualizar ↻</button></section>
    <section class="live-panel" aria-label="Seguimiento de ganancias"><div class="live-head"><div><p class="eyebrow">SEGUIMIENTO · /ESCALERA</p><h2>Historial y ganancias</h2></div></div>${stats}${tablaLongitud}${tabla}</section>
    <section class="live-panel" aria-label="La regla del reto"><div class="live-head"><div><p class="eyebrow">LA REGLA</p><h2>Cómo se elige cada escalón</h2></div></div>${regla}</section>`;
}

function matchView() {
  const fx = fixtureById.get(state.selectedMatch) || fixtures[0];
  const outcomes = ['Local', 'Empate', 'Visita'];
  const probabilityCells = values => values.map((value, index) => `<div><span>${outcomes[index]}</span><strong>${value}%</strong></div>`).join('');
  const pick = pickFor(fx);
  const tabs = `<div class="tab-bar" role="tablist" aria-label="Secciones de la ficha">${MATCH_TABS.map(([id, label]) => `<button type="button" role="tab" id="match-tab-${id}" aria-controls="match-panel" aria-selected="${state.matchTab === id}" class="${state.matchTab === id ? 'selected' : ''}" data-match-tab="${id}">${label}</button>`).join('')}</div>`;
  const panels = {
    resumen: () => `<div class="analysis-grid comparison-grid"><section class="panel"><div class="panel-heading"><div><p class="eyebrow">MODELO / 1X2</p><h2>Estimación deportiva</h2></div><span class="small-tag">Diagnóstico</span></div><div class="prob-matrix">${probabilityCells(fx.probs)}</div>${probBar(fx.probs, 'Modelo')}<p class="panel-foot">Goles esperados: ${fx.xg[0].toFixed(2)} local · ${fx.xg[1].toFixed(2)} visitante. Alineaciones: no confirmadas en esta simulación.</p></section><section class="panel"><div class="panel-heading"><div><p class="eyebrow">MERCADO / 1X2</p><h2>Pinnacle sin margen</h2></div><span class="small-tag">Demo</span></div><div class="prob-matrix">${probabilityCells(fx.marketProbs)}</div>${probBar(fx.marketProbs, 'Pinnacle sin margen')}<p class="panel-foot">Precio simulado, no procede de Pinnacle. Es la referencia con la que se miden las demás casas.</p></section></div>
      <div class="analysis-grid below"><section class="panel"><p class="eyebrow">LECTURA / CONTEXTO</p><h2>Qué dicen los números</h2><p class="body-copy">${fx.note}</p><div class="context-tags">${badge('XI pendiente', 'muted')}${badge(fx.excluded ? 'Pinnacle fuera de consenso' : 'Pinnacle en consenso', fx.excluded ? 'warn' : 'muted')}</div></section>
      <section class="panel"><p class="eyebrow">CRITERIO / SOMBRA</p><h2>${pick ? 'Candidata del partido' : 'Sin candidata'}</h2>${pick ? `<div class="detail-line"><span>Selección</span><strong>${pick.row.selection}</strong></div><div class="detail-line"><span>Mejor casa</span><strong>${pick.row.best.book.name} · ${fmtOdds(pick.row.best.price)}</strong></div><div class="detail-line"><span>Probabilidad real</span><strong>${probText(pick.row.pFair)}</strong></div><div class="detail-line"><span>Justo · mínimo</span><strong>${fmtOdds(1 / pick.row.pFair)} · ${fmtOdds(pick.row.minPrice)}</strong></div><div class="detail-line"><span>vs justo · esperado al cierre</span><strong class="pos">${fmtEdge(pick.row.edge)} · ${fmtEdge(pick.row.expectedEdge)}</strong></div><button type="button" class="secondary-button full" data-row="${pick.row.key}">Ver todas las casas</button>` : `<p class="body-copy muted">${fx.closed ? 'El mercado ya cerró.' : fx.excluded ? statusText(fx.rows[0]) : 'Ninguna casa de la lista paga un 2% sobre el justo en el 1X2. No se publica nada.'}</p><button type="button" class="secondary-button full" data-match-tab="casas">Ver precios por casa</button>`}</section></div>`,
    mercados: () => `<section class="panel flush"><div class="panel-heading padded"><div><p class="eyebrow">MERCADOS / ${fx.rows.length} SELECCIONES</p><h2>Todo lo que sale de dos lambdas</h2></div><button type="button" class="text-link" data-desk-open="${fx.id}">Abrir en la mesa ↗</button></div>${marketTable(sortedRows(fx.rows), { showMatch: false, caption: `Mercados de ${fx.home} contra ${fx.away}` })}</section>`,
    casas: () => bookMatrix(fx),
    modelo: () => modelPanel(fx),
    registro: () => `<section class="panel trace-panel"><div class="panel-heading"><div><p class="eyebrow">TRAZABILIDAD</p><h2>El orden de los hechos importa</h2></div>${badge('Cronología ficticia', 'muted')}</div>${traceSteps(fx)}</section>`,
  };
  return `<div class="view-title"><div><p class="eyebrow">FICHA DE PARTIDO / ${fx.league.toUpperCase()}</p><h1>Un encuentro, todas sus capas.</h1><p class="lead">Modelo, precio justo, casas y registro se muestran por separado. Ninguna diferencia representa una ventaja demostrada.</p></div>${badge('Datos ilustrativos', 'accent')}</div>
    <div class="match-picker"><label for="match-select">Elegir partido de ejemplo</label><select id="match-select" data-filter="match">${fixtures.map(item => `<option value="${item.id}" ${item.id === fx.id ? 'selected' : ''}>${kickoffLabel(item)} · ${item.home} vs ${item.away}</option>`).join('')}</select></div>
    <div class="fixture-hero"><div class="fixture-meta"><span>${fx.league}</span><span>${dateFmt(fx.kickoff, { weekday: 'long', day: 'numeric', month: 'long' })} · ${timeLabel(fx.kickoff)}</span></div><div class="fixture-teams"><div>${teamMark(fx.home, false, true)}<h2>${fx.home}</h2><small>Local</small></div><span class="fixture-vs">VS</span><div>${teamMark(fx.away, true, true)}<h2>${fx.away}</h2><small>Visitante</small></div></div><div class="fixture-bottom">${badge(fx.closed ? 'Mercado cerrado' : fx.excluded ? 'Excluido del criterio' : 'Programado', fx.excluded ? 'warn' : 'muted')}<span>Los datos no corresponden a un partido real.</span></div></div>
    ${tabs}<div id="match-panel" role="tabpanel" aria-labelledby="match-tab-${state.matchTab}" class="tab-panel">${panels[state.matchTab]()}</div>`;
}

function clvChart(items) {
  const chronological = [...items].sort((a, b) => a.publishedAt - b.publishedAt);
  let running = 0;
  const points = chronological.map(item => (running += clvValue(item) * 100));
  const values = [0, ...points];
  const min = Math.min(...values, 0);
  const span = Math.max(...values, 0) - min || 1;
  const x = i => 8 + i / (values.length - 1) * 284;
  const y = v => 72 - (v - min) / span * 60;
  return `<svg class="clv-chart" viewBox="0 0 300 80" preserveAspectRatio="none" role="img" aria-label="CLV acumulado de la muestra ficticia: ${points.at(-1).toFixed(1)} puntos tras ${points.length} registros"><line x1="8" x2="292" y1="${y(0).toFixed(1)}" y2="${y(0).toFixed(1)}" class="zero"/><polyline points="${values.map((v, i) => `${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(' ')}" vector-effect="non-scaling-stroke"/></svg>`;
}

function historyView() {
  const filtered = archive.filter(item => (state.recordFilter === 'Todos' || item.result === state.recordFilter) && (state.recordLeague === 'Todas' || item.league === state.recordLeague));
  const averageClv = sum(archive.map(clvValue)) / archive.length;
  const beatClose = archive.filter(item => clvValue(item) > 0).length;
  const period = `${dateFmt(archive.at(-1).date, { day: 'numeric', month: 'short' })}–${dateFmt(archive[0].date, { day: 'numeric', month: 'short' })}`;
  return `<div class="view-title"><div><p class="eyebrow">EVIDENCIA / REGISTRO REAL Y MAQUETA</p><h1>Historial verificable</h1><p class="lead">Arriba se muestra el estado real de la API; debajo, un ejemplo de cómo revisar aciertos, pérdidas y cierres. Ninguna fila de la maqueta pertenece al historial real.</p></div>${badge('API pública + demo señalada', 'accent')}</div>
    ${liveEvidence()}
    <div class="disclosure"><span class="disclosure-icon">ⓘ</span><div><strong>Maqueta ficticia bajo esta línea; no es prueba de rendimiento.</strong><span>Estas filas se pueden cambiar en el navegador y no tienen cadena de hashes. El historial real está en el panel anterior y procede del servidor.</span></div></div>
    <div class="history-context"><div><span>PERIODO ILUSTRATIVO</span><strong>${period}</strong></div><div><span>COBERTURA</span><strong>${archive.length} registros inventados · todas las ligas de muestra</strong></div><div><span>ESTADO DE VERIFICACIÓN</span><strong>Sin publicación ni hash reales</strong></div></div>
    <div class="stat-grid"><div class="stat-card"><span>CLV medio · demo</span><strong>${fmtEdge(averageClv)}</strong><small>${beatClose} de ${archive.length} batieron el cierre · no es evidencia</small>${clvChart(archive)}</div><div class="stat-card"><span>Resultados de ejemplo</span><strong>${archive.length}</strong><small>${archive.filter(item => item.result === 'Ganado').length} ganados · ${archive.filter(item => item.result === 'Perdido').length} perdidos · sin selección favorable</small></div><div class="stat-card"><span>Métricas reales</span><strong>↑</strong><small>Consulta el registro público anterior; nunca se calculan con estas filas ficticias</small></div></div>
    <section class="panel record-panel"><div class="panel-heading"><div><p class="eyebrow">ARCHIVO DE MUESTRA</p><h2>Resultados, incluido lo que falla</h2><p class="record-count" aria-live="polite">${filtered.length} de ${archive.length} registros visibles</p></div><div class="record-filters"><div class="segmented" role="group" aria-label="Filtrar por competición">${['Todas', ...LEAGUES].map(league => `<button type="button" data-record-league="${league}" class="${state.recordLeague === league ? 'selected' : ''}" aria-pressed="${state.recordLeague === league}">${league.replace(' · demo', '')}</button>`).join('')}</div><div class="segmented" role="group" aria-label="Filtrar resultados">${['Todos', 'Ganado', 'Perdido'].map(filter => `<button type="button" data-record="${filter}" class="${state.recordFilter === filter ? 'selected' : ''}" aria-pressed="${state.recordFilter === filter}">${filter}</button>`).join('')}</div></div></div>
      <div class="table-wrap" tabindex="0" role="region" aria-label="Tabla de resultados de demostración, desplazable horizontalmente"><table><caption>Datos ficticios; CLV calculado como cuota registrada dividida por cuota de cierre, menos uno.</caption><thead><tr><th scope="col">Inicio</th><th scope="col">Publicado · demo</th><th scope="col">Partido</th><th scope="col">Selección</th><th scope="col">Casa</th><th scope="col">Cuota · mín.</th><th scope="col">Cierre</th><th scope="col">Resultado</th><th scope="col">CLV · demo</th></tr></thead><tbody>${filtered.map(item => `<tr><td>${stamp(item.date)}</td><td>${stamp(item.publishedAt)}</td><td><strong>${item.match}</strong><small>${item.league}</small></td><td><strong>${item.selection}</strong><small>${item.market}</small></td><td>${item.book}</td><td>${fmtOdds(item.price)}<small>mín. ${fmtOdds(item.minPrice)}</small></td><td>${fmtOdds(item.closePrice)}</td><td><span class="result ${item.result === 'Ganado' ? 'won' : 'lost'}">${item.result}</span></td><td class="edge ${clvValue(item) >= 0 ? 'pos' : 'neg'}">${fmtEdge(clvValue(item))}</td></tr>`).join('') || '<tr><td colspan="9">Ningún registro con estos filtros.</td></tr>'}</tbody></table></div></section>
    <div class="evidence-grid"><div class="panel"><span class="evidence-icon">▥</span><h3>Calibración pública</h3><p>El panel real anterior consulta las corridas registradas por el servidor, con muestra y periodo.</p></div><div class="panel"><span class="evidence-icon">⌁</span><h3>Cadena de hashes</h3><p>Los lotes reales aparecen arriba cuando existan. Esta maqueta no genera huellas válidas.</p></div><div class="panel"><span class="evidence-icon">↗</span><h3>CLV con intervalo</h3><p>La cuota publicada se comparará con el cierre; el promedio deberá ir acompañado de tamaño de muestra e incertidumbre.</p></div></div>`;
}

function plansView() { return membershipUI.plansView(); }

function accountView() { return membershipUI.accountView(); }

// ---------------------------------------------------------------- partidos reales
// Agenda y fichas con datos del servidor (/web/partidos). Es contenido: forma,
// cara a cara, promedios y tabla. No lleva cuotas, picks ni la opinión del
// modelo, y nada de aquí sale de los datos ficticios de arriba.

const STATS_TABS = [['resumen', 'Resumen'], ['forma', 'Forma'], ['h2h', 'Cara a cara'], ['estadisticas', 'Estadísticas'], ['tabla', 'Clasificación'], ['alineaciones', 'Alineaciones']];
const STATS_DAYS = [-1, 0, 1, 2, 3];
const RES_LABEL = { G: 'Ganado', E: 'Empate', P: 'Perdido' };
const BAJA_LABEL = { 'Missing Fixture': 'Baja', Questionable: 'Duda', Injured: 'Lesión', Suspended: 'Sanción' };
const STAT_ROWS = [
  ['posesion', 'Posesión', v => `${realNumber(v)}%`],
  ['xg', 'Goles esperados (xG)', v => realNumber(v, 2)],
  ['tiros', 'Tiros', realNumber],
  ['tiros_puerta', 'Tiros a puerta', realNumber],
  ['tiros_dentro_area', 'Tiros dentro del área', realNumber],
  ['corners', 'Córners', realNumber],
  ['paradas', 'Paradas', realNumber],
  ['faltas', 'Faltas', realNumber],
  ['fueras_de_juego', 'Fueras de juego', realNumber],
  ['amarillas', 'Amarillas', realNumber],
  ['rojas', 'Rojas', realNumber],
  ['pases', 'Pases', realNumber],
  ['pct_pases', 'Precisión de pase', v => `${realNumber(v)}%`],
];
const AVG_ROWS = [
  ['goles_favor', 'Goles a favor', 2], ['goles_contra', 'Goles en contra', 2],
  ['xg_favor', 'xG a favor', 2], ['xg_contra', 'xG en contra', 2],
  ['tiros_favor', 'Tiros', 1], ['tiros_puerta_favor', 'Tiros a puerta', 1],
  ['corners_favor', 'Córners', 1],
  ['pct_ambos_marcan', 'Ambos marcan', 0, '%'], ['pct_mas_2_5', 'Más de 2,5 goles', 0, '%'],
  ['pct_porteria_cero', 'Portería a cero', 0, '%'],
];

const agendaCache = new Map();
const fichaCache = new Map();

function rerenderIfIdle() {
  if (!state.modal && !state.drawer && !state.mobileMenuOpen) render();
}

function ensureAgenda(offset) {
  if (agendaCache.has(offset)) return agendaCache.get(offset);
  const entry = { status: 'loading', data: null };
  agendaCache.set(offset, entry);
  loadAgenda(addDays(offset, 12)).then(result => {
    agendaCache.set(offset, result);
    if (['partidos', 'inicio'].includes(state.route)) rerenderIfIdle();
  });
  return entry;
}

function ensureFicha(id) {
  if (fichaCache.has(id)) return fichaCache.get(id);
  const entry = { status: 'loading', data: null };
  fichaCache.set(id, entry);
  loadFicha(id).then(result => {
    fichaCache.set(id, result);
    if (state.route === 'partidos' && state.statsMatch === id) rerenderIfIdle();
  });
  return entry;
}

// Escudo servido desde /web/escudos cuando ya se descargó; si no, la inicial.
const realMark = (name, away = false, large = false, src = null) => (src
  ? `<img class="${large ? 'large-crest' : 'crest'}" src="${esc(src)}" alt="" loading="lazy" decoding="async">`
  : `<span class="${large ? 'large-team-mark' : 'team-mark'} ${away ? 'away' : ''}" aria-hidden="true">${esc(String(name || '?').charAt(0))}</span>`);
const rachaDots = (racha, title = 'Del más reciente al más antiguo') => racha
  ? `<span class="racha" title="${title}">${[...racha].map(r => `<i class="r-${esc(r)}" aria-label="${RES_LABEL[r] || r}">${esc(r)}</i>`).join('')}</span>`
  : '<span class="racha empty">sin partidos previos</span>';
const posLabel = pos => (pos ? `${pos}º` : '');
const kickoffOf = p => new Date(p.kickoff_utc);

function estadoPartido(p) {
  if (p.estado === 'finished' && p.marcador) return { main: `${p.marcador[0]} – ${p.marcador[1]}`, tag: 'Final', kind: 'muted' };
  if (p.estado === 'live') return { main: timeLabel(kickoffOf(p)), tag: 'En juego', kind: 'good' };
  if (p.estado === 'postponed') return { main: '—', tag: 'Aplazado', kind: 'warn' };
  return { main: timeLabel(kickoffOf(p)), tag: '', kind: '' };
}

function selectedAgendaMatch(list) {
  if (list.some(p => p.match_id === state.statsMatch)) return state.statsMatch;
  const next = list.find(p => p.estado === 'scheduled' && kickoffOf(p) > now) || list[0];
  return next ? next.match_id : null;
}

function realDayLabel(offset) {
  return `${dayLabel(offset)} · ${dateFmt(addDays(offset), { day: 'numeric', month: 'short' })}`;
}

function agendaItem(p) {
  const st = estadoPartido(p);
  const team = (t, away) => `<span>${realMark(t.nombre, away, false, t.escudo)}<span class="team-name">${esc(t.nombre)}</span>${t.posicion ? `<small class="st-pos">${posLabel(t.posicion)}</small>` : ''}</span>`;
  const active = state.statsMatch === p.match_id;
  return `<button type="button" class="desk-match ${active ? 'active' : ''}" data-stats-match="${esc(p.match_id)}" aria-pressed="${active}"><span class="desk-when"><span class="desk-time">${esc(st.main)}</span>${st.tag ? `<small class="tag ${st.kind}">${st.tag}</small>` : ''}</span><span class="desk-teams">${team(p.local)}${team(p.visitante, true)}</span></button>`;
}

// ---- pestañas de la ficha

function compareRows(a, b, rows) {
  return rows.map(([key, label, digits, suffix = '']) => {
    const va = a?.[key];
    const vb = b?.[key];
    if (va == null && vb == null) return '';
    const top = Math.max(Number(va) || 0, Number(vb) || 0) || 1;
    const fmt = v => (v == null ? '—' : `${realNumber(v, digits)}${suffix}`);
    return `<div class="cmp-row"><span class="cmp-val">${fmt(va)}</span><span class="cmp-bar home"><i data-width="${((Number(va) || 0) / top * 100).toFixed(1)}"></i></span><span class="cmp-label">${label}</span><span class="cmp-bar away"><i data-width="${((Number(vb) || 0) / top * 100).toFixed(1)}"></i></span><span class="cmp-val">${fmt(vb)}</span></div>`;
  }).join('');
}

function averagesPanel(f) {
  const split = state.statsSplit === 'lado';
  const a = split ? f.local.promedios.casa : f.local.promedios.todos;
  const b = split ? f.visitante.promedios.fuera : f.visitante.promedios.todos;
  const toggle = `<div class="segmented" role="group" aria-label="Qué partidos promediar">${[['todos', 'Todos'], ['lado', 'Local en casa · visitante fuera']].map(([id, label]) => `<button type="button" data-stats-split="${id}" class="${(state.statsSplit || 'todos') === id ? 'selected' : ''}" aria-pressed="${(state.statsSplit || 'todos') === id}">${label}</button>`).join('')}</div>`;
  const body = a?.n || b?.n
    ? `<div class="cmp-head"><strong>${esc(f.local.nombre)}</strong><small>${a?.n || 0} partidos · ${b?.n || 0} partidos</small><strong>${esc(f.visitante.nombre)}</strong></div>${compareRows(a, b, AVG_ROWS)}`
    : '<p class="body-copy muted">No hay partidos de estos equipos en los últimos 9 meses en la base.</p>';
  return `<section class="panel"><div class="panel-heading"><div><p class="eyebrow">PROMEDIOS · ÚLTIMOS PARTIDOS</p><h2>Cómo llegan</h2></div>${toggle}</div>${body}<p class="panel-foot">Media por partido de los últimos ${Math.max(a?.n || 0, b?.n || 0) || 10} encuentros terminados antes de este (hasta 9 meses atrás), en cualquier competición. El xG solo cuenta los partidos que lo tienen.</p></section>`;
}

function formStrip(team, away = false) {
  const r = team.forma.resumen;
  const pos = team.clasificacion;
  return `<div class="form-strip"><div class="form-strip-team">${realMark(team.nombre, away, false, team.escudo)}<div><strong>${esc(team.nombre)}</strong><small>${pos ? `${posLabel(pos.posicion)} en ${esc(pos.liga)}${pos.grupo ? ` · ${esc(pos.grupo)}` : ''} · ${realNumber(pos.puntos)} pts` : 'Sin clasificación cargada'}</small></div></div>${rachaDots(r.racha)}<small class="form-strip-sum">${r.n ? `${r.G}G ${r.E}E ${r.P}P · ${r.gf}-${r.gc} goles` : ''}</small></div>`;
}

function h2hSummary(h, f) {
  const r = h.resumen;
  if (!r.n) return '<p class="body-copy muted">No hay cruces entre estos equipos en la base.</p>';
  const pct = v => Math.round(v / r.n * 100);
  const bar = [pct(r.victorias_local), 0, pct(r.victorias_visitante)];
  bar[1] = 100 - bar[0] - bar[2];
  return `<div class="h2h-sum"><div><strong>${r.victorias_local}</strong><small>${esc(f.local.nombre)}</small></div><div><strong>${r.empates}</strong><small>Empates</small></div><div><strong>${r.victorias_visitante}</strong><small>${esc(f.visitante.nombre)}</small></div></div>${probBar(bar, 'Cara a cara')}<p class="h2h-facts">${r.n} cruces · ${realNumber(r.goles_media, 1)} goles por partido · ambos marcan ${realNumber(r.pct_ambos_marcan)}% · más de 2,5 en ${realNumber(r.pct_mas_2_5)}%</p>`;
}

function formList(team) {
  const games = team.forma.partidos;
  if (!games.length) return '<p class="body-copy muted">Sin partidos previos en la base.</p>';
  return `<ol class="form-list">${games.map(g => `<li><span class="res r-${esc(g.res)}" aria-label="${RES_LABEL[g.res]}">${esc(g.res)}</span><div><strong class="with-crest">${g.local ? 'vs' : 'en'} ${g.rival_escudo ? realMark(g.rival, false, false, g.rival_escudo) : ''}${esc(g.rival)}</strong><small>${realDate(g.fecha)} · ${esc(g.competicion)} · ${g.local ? 'Casa' : 'Fuera'}</small></div><span class="num">${g.gf}-${g.gc}${g.xg?.[0] != null ? `<small>xG ${realNumber(g.xg[0], 1)}-${realNumber(g.xg[1], 1)}</small>` : ''}</span></li>`).join('')}</ol>`;
}

function h2hList(h, f) {
  if (!h.partidos.length) return '';
  return `<ol class="form-list">${h.partidos.map(g => {
    const [casa, fuera] = g.local ? [f.local.nombre, f.visitante.nombre] : [f.visitante.nombre, f.local.nombre];
    return `<li><span class="res r-${esc(g.res)}" aria-label="${RES_LABEL[g.res]} para ${esc(f.local.nombre)}">${esc(g.res)}</span><div><strong>${esc(casa)} ${esc(g.marcador)} ${esc(fuera)}</strong><small>${realDate(g.fecha)} · ${esc(g.competicion)}</small></div></li>`;
  }).join('')}</ol><p class="panel-foot">La letra es el resultado para ${esc(f.local.nombre)}, local en este partido.</p>`;
}

function statsPanel(f) {
  const s = f.partido.estadisticas;
  if (!s || !s.home || !Object.keys(s.home).length) {
    return `<section class="panel"><p class="eyebrow">ESTADÍSTICAS DEL PARTIDO</p><h2>${f.partido.estado === 'finished' ? 'Sin estadísticas para este partido' : 'Se publican al terminar'}</h2><p class="body-copy muted">Posesión, tiros, córners, tarjetas y xG se guardan al cerrar el partido. Mientras tanto, mira los promedios de la pestaña Resumen.</p></section>`;
  }
  const rows = STAT_ROWS.map(([key, label, fmt]) => {
    const a = s.home[key];
    const b = s.away[key];
    if (a == null && b == null) return '';
    const top = Math.max(Number(a) || 0, Number(b) || 0) || 1;
    return `<div class="cmp-row"><span class="cmp-val">${a == null ? '—' : fmt(a)}</span><span class="cmp-bar home"><i data-width="${((Number(a) || 0) / top * 100).toFixed(1)}"></i></span><span class="cmp-label">${label}</span><span class="cmp-bar away"><i data-width="${((Number(b) || 0) / top * 100).toFixed(1)}"></i></span><span class="cmp-val">${b == null ? '—' : fmt(b)}</span></div>`;
  }).join('');
  return `<section class="panel"><p class="eyebrow">ESTADÍSTICAS DEL PARTIDO</p><h2>${esc(f.local.nombre)} ${f.partido.marcador ? `${f.partido.marcador[0]}–${f.partido.marcador[1]}` : 'vs'} ${esc(f.visitante.nombre)}</h2><div class="cmp-head"><strong>${esc(f.local.nombre)}</strong><small>${f.partido.descanso ? `Descanso ${f.partido.descanso[0]}–${f.partido.descanso[1]}` : ''}</small><strong>${esc(f.visitante.nombre)}</strong></div>${rows}</section>`;
}

// El proveedor describe la zona en inglés ('Promotion - Champions League (League phase)').
const zonaTabla = text => text
  .replace(/^Promotion\s*-\s*/i, '')
  .replace(/^Relegation\s*-?\s*/i, 'Descenso · ')
  .replace(/\s*\((League phase|Group Stage|Qualification)\)/i, '')
  .replace(/Play Offs?/i, 'Promoción')
  .replace(/ · $/, '');

function tablePanel(f) {
  const rows = f.tabla;
  if (!rows) return `<section class="panel"><p class="eyebrow">CLASIFICACIÓN</p><h2>Competición de eliminatorias</h2><p class="body-copy muted">En copas se muestra el puesto de cada equipo en su liga.</p>${formStrip(f.local)}${formStrip(f.visitante, true)}</section>`;
  if (!rows.length) return '<section class="panel"><p class="eyebrow">CLASIFICACIÓN</p><h2>Tabla no disponible todavía</h2><p class="body-copy muted">La clasificación se actualiza dos veces al día.</p></section>';
  const ids = new Set([f.local.id, f.visitante.id]);
  const groups = [...new Set(rows.map(r => r.grupo))];
  return groups.map(g => `<section class="panel table-panel"><div class="panel-heading"><div><p class="eyebrow">CLASIFICACIÓN${g ? ` · ${esc(g.toUpperCase())}` : ''}</p><h2>${esc(f.partido.liga.nombre)}</h2></div>${badge(`Actualizada ${realDate(rows[0].updated_at)}`, 'muted')}</div><div class="table-wrap" tabindex="0" role="region" aria-label="Clasificación, desplazable horizontalmente"><table class="standings"><thead><tr><th scope="col">#</th><th scope="col">Equipo</th><th scope="col" class="num">PJ</th><th scope="col" class="num">G</th><th scope="col" class="num">E</th><th scope="col" class="num">P</th><th scope="col" class="num">Goles</th><th scope="col" class="num">DG</th><th scope="col" class="num">Pts</th><th scope="col">Forma</th></tr></thead><tbody>${rows.filter(r => r.grupo === g).map(r => `<tr class="${ids.has(r.team_id) ? 'is-best' : ''}"><td>${r.posicion}</td><td><strong class="with-crest">${r.escudo ? realMark(r.equipo, false, false, r.escudo) : ''}${esc(r.equipo)}</strong>${r.descripcion ? `<small>${esc(zonaTabla(r.descripcion))}</small>` : ''}</td><td class="num">${r.jugados}</td><td class="num">${r.ganados}</td><td class="num">${r.empatados}</td><td class="num">${r.perdidos}</td><td class="num">${r.goles_favor}:${r.goles_contra}</td><td class="num">${r.goles_favor - r.goles_contra > 0 ? '+' : ''}${r.goles_favor - r.goles_contra}</td><td class="num"><strong>${r.puntos}</strong></td><td>${r.forma ? rachaDots(r.forma.replace(/W/g, 'G').replace(/D/g, 'E').replace(/L/g, 'P'), 'Últimos partidos de liga') : ''}</td></tr>`).join('')}</tbody></table></div></section>`).join('');
}

function lineupsPanel(f) {
  const side = (key, team) => {
    const l = f.alineaciones[key];
    const out = f.bajas?.[key] || [];
    const xi = l ? `<p class="lineup-formation">${esc(l.formacion || 'Formación sin datos')}</p><ol class="lineup">${(l.titulares || []).map(p => `<li><span>${esc(p.number ?? '')}</span><strong>${esc(p.name ?? '')}</strong><small>${esc(p.pos ?? '')}</small></li>`).join('')}</ol>` : '<p class="body-copy muted">XI sin confirmar. Se publica entre 60 y 20 minutos antes del inicio.</p>';
    const bajas = f.bajas ? (out.length ? `<ul class="bajas">${out.map(b => `<li><strong>${esc(b.jugador)}</strong><small>${esc(BAJA_LABEL[b.tipo] || b.tipo)}${b.motivo ? ` · ${esc(b.motivo)}` : ''}</small></li>`).join('')}</ul>` : '<p class="body-copy muted">Sin bajas reportadas.</p>') : '<p class="body-copy muted">Bajas aún no comprobadas.</p>';
    return `<section class="panel"><p class="eyebrow">${esc(team.nombre.toUpperCase())}</p><h2>Alineación</h2>${xi}<h3 class="sub-h">Bajas y dudas</h3>${bajas}</section>`;
  };
  return `<div class="analysis-grid even">${side('home', f.local)}${side('away', f.visitante)}</div>`;
}

function fichaMarkup(entry) {
  if (!entry || entry.status === 'loading') return '<div class="panel loading-panel"><p class="eyebrow">FICHA</p><h2>Cargando datos del partido…</h2></div>';
  if (entry.status !== 'ready') return `<div class="empty-state"><span class="empty-symbol">◇</span><h3>No se pudo cargar la ficha</h3><p>El servidor no respondió. <button type="button" class="text-link" data-action="retry-ficha">Reintentar ↻</button></p></div>`;
  const f = entry.data;
  const p = f.partido;
  const st = estadoPartido(p);
  const ko = kickoffOf(p);
  const tab = STATS_TABS.some(([id]) => id === state.statsTab) ? state.statsTab : 'resumen';
  const sideHero = (team, away) => `<div>${realMark(team.nombre, away, true, team.escudo)}<h2>${esc(team.nombre)}</h2><small>${team.clasificacion ? `${posLabel(team.clasificacion.posicion)} · ${realNumber(team.clasificacion.puntos)} pts` : away ? 'Visitante' : 'Local'}</small>${rachaDots(team.forma.resumen.racha)}</div>`;
  const panels = {
    resumen: () => `<div class="stack">${averagesPanel(f)}<div class="analysis-grid even"><section class="panel"><p class="eyebrow">RACHA · ÚLTIMOS 5</p><h2>Momento de forma</h2>${formStrip(f.local)}${formStrip(f.visitante, true)}</section><section class="panel"><p class="eyebrow">CARA A CARA</p><h2>Historial directo</h2>${h2hSummary(f.cara_a_cara, f)}<button type="button" class="text-link" data-stats-tab="h2h">Ver los cruces ↗</button></section></div></div>`,
    forma: () => `<div class="analysis-grid even"><section class="panel"><p class="eyebrow">${esc(f.local.nombre.toUpperCase())}</p><h2>Últimos partidos</h2>${formList(f.local)}</section><section class="panel"><p class="eyebrow">${esc(f.visitante.nombre.toUpperCase())}</p><h2>Últimos partidos</h2>${formList(f.visitante)}</section></div>`,
    h2h: () => `<section class="panel"><p class="eyebrow">CARA A CARA</p><h2>${esc(f.local.nombre)} vs ${esc(f.visitante.nombre)}</h2>${h2hSummary(f.cara_a_cara, f)}${h2hList(f.cara_a_cara, f)}</section>`,
    estadisticas: () => statsPanel(f),
    tabla: () => tablePanel(f),
    alineaciones: () => lineupsPanel(f),
  };
  return `<div class="fixture-hero"><div class="fixture-meta"><span>${esc(p.liga.nombre)} · ${esc(p.liga.pais)}</span><span>${dateFmt(ko, { weekday: 'long', day: 'numeric', month: 'long' })} · ${timeLabel(ko)}</span></div>
    <div class="fixture-teams">${sideHero(f.local)}<span class="fixture-vs ${p.marcador ? 'score' : ''}">${p.marcador ? `${p.marcador[0]} – ${p.marcador[1]}` : 'VS'}</span>${sideHero(f.visitante, true)}</div>
    <div class="fixture-bottom">${badge(st.tag || 'Programado', st.kind || 'muted')}<span>Datos de partidos reales. Es información, no un pronóstico.</span></div></div>
    <div class="tab-bar" role="tablist" aria-label="Secciones de la ficha">${STATS_TABS.map(([id, label]) => `<button type="button" role="tab" id="stats-tab-${id}" aria-controls="stats-panel" aria-selected="${tab === id}" class="${tab === id ? 'selected' : ''}" data-stats-tab="${id}">${label}</button>`).join('')}</div>
    <div id="stats-panel" role="tabpanel" aria-labelledby="stats-tab-${tab}" class="tab-panel">${panels[tab]()}</div>`;
}

function statsView() {
  const agenda = ensureAgenda(state.statsDay);
  const all = agenda.status === 'ready' ? agenda.data.partidos : [];
  const leagues = [...new Map(all.map(p => [p.liga.id, p.liga.nombre])).entries()];
  if (state.statsLeague !== 'Todas' && !leagues.some(([id]) => id === state.statsLeague)) state.statsLeague = 'Todas';
  const list = all.filter(p => state.statsLeague === 'Todas' || p.liga.id === state.statsLeague);
  state.statsMatch = selectedAgendaMatch(list);
  const dayIndex = STATS_DAYS.indexOf(state.statsDay);
  const byLeague = leagues.filter(([id]) => state.statsLeague === 'Todas' || id === state.statsLeague)
    .map(([id, name]) => [name, list.filter(p => p.liga.id === id)]);
  let side;
  if (agenda.status === 'loading') side = '<p class="rail-empty">Cargando partidos…</p>';
  else if (agenda.status !== 'ready') side = '<p class="rail-empty">No se pudo cargar la agenda. <button type="button" class="text-link" data-action="retry-agenda">Reintentar ↻</button></p>';
  else if (!list.length) side = '<p class="rail-empty">No hay partidos de las ligas seguidas este día.</p>';
  else side = byLeague.map(([name, games]) => `<p class="desk-league">${esc(name)}</p>${games.map(agendaItem).join('')}`).join('');
  const main = state.statsMatch ? fichaMarkup(ensureFicha(state.statsMatch))
    : agenda.status === 'loading' ? '' : '<div class="empty-state"><span class="empty-symbol">◷</span><h3>Sin partidos este día</h3><p>Prueba con otro día en el selector de la izquierda.</p></div>';
  return `<div class="view-title compact"><div><p class="eyebrow">PARTIDOS / DATOS REALES</p><h1>Partidos y estadísticas</h1><p class="lead">Forma, cara a cara, promedios, clasificación y alineaciones de las ligas que sigue QuantFut. Información para analizar, no pronósticos.</p></div>${badge('Datos reales', 'accent')}</div>
    <div class="chip-row filter-chips scroll" role="group" aria-label="Competición"><button type="button" class="chip ${state.statsLeague === 'Todas' ? 'selected' : ''}" data-stats-league="Todas" aria-pressed="${state.statsLeague === 'Todas'}">Todas <b>${all.length}</b></button>${leagues.map(([id, name]) => `<button type="button" class="chip ${state.statsLeague === id ? 'selected' : ''}" data-stats-league="${esc(id)}" aria-pressed="${state.statsLeague === id}">${esc(name)} <b>${all.filter(p => p.liga.id === id).length}</b></button>`).join('')}</div>
    <div class="desk stats-desk">
      <aside class="desk-side" aria-label="Partidos del día">
        <div class="side-head"><span>PARTIDOS</span><b>${list.length}</b></div>
        <div class="day-stepper"><button type="button" data-stats-day="${STATS_DAYS[dayIndex - 1] ?? ''}" aria-label="Día anterior" ${dayIndex <= 0 ? 'disabled' : ''}>‹</button><strong>${realDayLabel(state.statsDay)}</strong><button type="button" data-stats-day="${STATS_DAYS[dayIndex + 1] ?? ''}" aria-label="Día siguiente" ${dayIndex >= STATS_DAYS.length - 1 ? 'disabled' : ''}>›</button></div>
        <div class="desk-match-list">${side}</div>
      </aside>
      <section class="desk-main" aria-label="Ficha del partido">${main}</section>
    </div>
    <p class="bottom-note">Horarios en tu zona horaria. Resultados, estadísticas, alineaciones y bajas: API-Football; histórico: football-data y bases públicas. La clasificación se actualiza dos veces al día.</p>`;
}

// Portada: lo real primero, con enlace a la ficha.
function homeRealStrip() {
  const agenda = ensureAgenda(0);
  if (agenda.status === 'error') return `<section class="real-strip real-unavailable"><div><p class="eyebrow">PARTIDOS REALES · API PÚBLICA</p><h2>Agenda real no disponible</h2><p>No se pudo consultar el servidor. Los partidos del tablero superior son ejemplos ficticios.</p></div><button type="button" class="secondary-button" data-route="partidos">Reintentar en Partidos ↗</button></section>`;
  const games = agenda.status === 'ready' ? agenda.data.partidos : [];
  const upcoming = [...games.filter(p => p.estado !== 'finished'), ...games.filter(p => p.estado === 'finished')].slice(0, 6);
  const card = p => {
    const st = estadoPartido(p);
    const team = (t, away) => `<div class="real-team">${realMark(t.nombre, away, false, t.escudo)}<strong>${esc(t.nombre)}</strong>${t.posicion ? `<small>${posLabel(t.posicion)}</small>` : ''}${rachaDots(t.racha)}</div>`;
    return `<button type="button" class="real-card" data-open-ficha="${esc(p.match_id)}"><span class="real-card-top"><span>${esc(p.liga.nombre)}</span><span>${st.tag ? `${st.tag} · ` : ''}${esc(st.main)}</span></span>${team(p.local)}${team(p.visitante, true)}<span class="real-card-link">Ver ficha ↗</span></button>`;
  };
  const body = agenda.status === 'loading' ? '<p class="rail-empty">Cargando partidos de hoy…</p>'
    : upcoming.length ? `<div class="real-grid">${upcoming.map(card).join('')}</div>` : '<p class="rail-empty">Hoy no juega ninguna de las ligas seguidas.</p>';
  return `<section class="real-strip"><div class="section-head"><div><p class="eyebrow">HOY EN LAS LIGAS · DATOS REALES</p><h2>${games.length ? `${games.length} partidos hoy` : 'Partidos de hoy'}</h2></div><button type="button" class="text-link" data-route="partidos">Todos los partidos y estadísticas ↗</button></div>${body}</section>`;
}

// ---------------------------------------------------------------- capas

const membershipUI = createMembershipUI({
  state, esc, badge, oddsToggle, leagues: LEAGUES, fixtures, matchCard, navigate, render,
  publicStatus: () => {
    const gate = publicData?.gate;
    const active = isPublicationActive(gate);
    return `<strong>${!gate ? 'Consultando publicación…' : gate.status !== 'ready' ? 'Estado de publicación no disponible' : active ? 'Publicación autorizada por el servidor' : 'Publicación pausada'}</strong><p>La selección de un plan no cambia el estado del servidor. Esta demo no entrega picks privados ni habilita cobros.</p>`;
  },
});

function modalMarkup() {
  if (!state.modal) return '';
  if (state.modal === 'plans') {
    const gate = publicData?.gate?.status === 'ready' ? publicData.gate.data.puerta_comercial.sombra_criterio_sharp : null;
    const reasons = gate?.motivos?.length ? gate.motivos.join(' · ') : 'Todavía no hay evidencia suficiente o la API no está disponible.';
    const steps = [
      { title: 'Identidad de ejemplo', text: 'Recorre una sesión ficticia local. No pedimos correo ni creamos una cuenta en el servidor.', action: 'Continuar con identidad ficticia' },
      { title: 'La evidencia decide', text: `Puerta de CLV: ${gate?.autorizada ? 'autorizada' : 'cerrada'}. ${reasons} Una cuenta por sí sola nunca da acceso a picks.`, action: 'Ver checkout bloqueado' },
      { title: 'Cobro y acceso bloqueados', text: 'No hay formulario de tarjeta, cargo, comprobante de compra ni contenido privado. El futuro servidor requerirá cuenta verificada, pago confirmado y puerta abierta.', action: 'Reiniciar recorrido' },
    ];
    const current = steps[state.accessStep];
    return `<div class="modal-backdrop" data-action="close-modal"><div class="modal access-modal" role="dialog" aria-modal="true" aria-labelledby="modal-title"><button type="button" class="modal-close" data-action="close-modal" aria-label="Cerrar">×</button><span class="modal-mark">◈</span><p class="eyebrow">RECORRIDO DEMO · ${state.accessStep + 1} DE 3</p><h2 id="modal-title">${current.title}</h2><p>${esc(current.text)}</p><div class="access-progress" role="img" aria-label="Paso ${state.accessStep + 1} de 3">${steps.map((_, index) => `<span class="${index <= state.accessStep ? 'done' : ''}"></span>`).join('')}</div><button type="button" class="primary-button full" data-action="access-next">${current.action}</button><p class="access-footnote">Demostración sin pagos, cuentas ni picks premium reales.</p></div></div>`;
  }
  const isPremium = state.modal === 'premium';
  return `<div class="modal-backdrop" data-action="close-modal"><div class="modal" role="dialog" aria-modal="true" aria-labelledby="modal-title"><button type="button" class="modal-close" data-action="close-modal" aria-label="Cerrar">×</button><span class="modal-mark">◈</span><p class="eyebrow">${isPremium ? 'ACCESO PREMIUM DE EJEMPLO' : 'ESTADO DEL PRODUCTO'}</p><h2 id="modal-title">${isPremium ? 'El contenido privado no viaja antes de autorizarte.' : 'Los planes de pago aún no están disponibles.'}</h2><p>${isPremium ? 'En producción, FastAPI comprobará la suscripción en el servidor y solo entregará el contenido autorizado. Este prototipo no recibe picks privados.' : 'QuantFut necesita reunir un historial real de CLV y superar su puerta comercial antes de vender picks. Puedes explorar el diseño sin realizar pagos.'}</p><button type="button" class="primary-button full" data-action="close-modal">Entendido</button></div></div>`;
}

function drawerMarkup() {
  const row = state.drawer && rowByKey.get(state.drawer);
  if (!row) return '';
  const fx = row.fx;
  const siblings = fx.rows.filter(item => item.market === row.market);
  const panels = {
    resumen: () => `<div class="drawer-metrics">
        <div><span>MODELO</span><strong>${fmtPct(row.pModel)}</strong><small>diagnóstico</small></div>
        <div><span>JUSTO PINNACLE</span><strong>${fmtOdds(1 / row.pFair)}</strong><small>prob. real ${probText(row.pFair)}</small></div>
        <div><span>VS JUSTO</span><strong class="edge ${edgeClass(row.edge)}">${fmtEdge(row.edge)}</strong><small>bruto, mejor casa</small></div>
        <div><span>ESPERADO AL CIERRE</span><strong>${fmtEdge(row.expectedEdge)}</strong><small>${row.best ? `persistencia ${Math.round(row.best.book.persistence * 100)}%` : '—'}</small></div>
        <div><span>PRECIO MÍNIMO</span><strong>${row.family === '1X2' ? fmtOdds(row.minPrice) : '—'}</strong><small>${row.family === '1X2' ? 'por debajo ya no vale' : 'fuera del criterio'}</small></div>
        <div><span>SNAPSHOT</span><strong>${timeLabel(fx.snapshot)}</strong><small>${fx.closed ? 'último antes del inicio' : `hace ${minutesAgo(fx.snapshot)} min · demo`}</small></div>
      </div>
      <div class="drawer-note ${row.status}">${statusBadge(row.status)}<p>${statusText(row)}</p></div>
      ${row.history.length ? `<div class="drawer-spark"><span>Mejor precio en las últimas horas · demo</span>${spark(row.history, 280, 56)}<small>${fmtOdds(row.history[0])} → ${fmtOdds(row.best.price)}</small></div>` : ''}
      <div class="drawer-siblings"><p class="eyebrow">MISMO MERCADO</p>${siblings.map(item => `<button type="button" class="sibling ${item === row ? 'active' : ''}" data-row="${item.key}" ${item === row ? 'aria-current="true"' : ''}><span>${item.selection}</span><span>${fmtOdds(1 / item.pFair)}</span><span class="edge ${edgeClass(item.edge)}">${fmtEdge(item.edge)}</span></button>`).join('')}</div>`,
    casas: () => booksTable(row),
    modelo: () => modelPanel(fx),
    registro: () => traceSteps(fx),
  };
  return `<div class="drawer-layer"><button type="button" class="drawer-backdrop" data-action="close-drawer" aria-label="Cerrar detalle" tabindex="-1"></button>
    <aside class="drawer" role="dialog" aria-modal="true" aria-labelledby="drawer-title">
      <header class="drawer-head"><button type="button" class="drawer-close" data-action="close-drawer" aria-label="Cerrar detalle">←</button><div><p class="eyebrow">${fx.league.toUpperCase()} · ${kickoffLabel(fx)}</p><h2 id="drawer-title">${fx.home} × ${fx.away}</h2></div></header>
      <div class="drawer-hero"><div><span>${row.market}</span><strong>${row.selection}</strong></div><div class="drawer-price">${row.best ? `<strong>${fmtOdds(row.best.price)}</strong><small>${row.best.book.name}</small>` : '<strong>—</strong><small>sin cuota</small>'}</div></div>
      <div class="tab-bar" role="tablist" aria-label="Detalle de la selección">${DRAWER_TABS.map(([id, label]) => `<button type="button" role="tab" id="drawer-tab-${id}" aria-controls="drawer-panel" aria-selected="${state.drawerTab === id}" class="${state.drawerTab === id ? 'selected' : ''}" data-drawer-tab="${id}">${label}</button>`).join('')}</div>
      <div id="drawer-panel" class="drawer-body" role="tabpanel" aria-labelledby="drawer-tab-${state.drawerTab}">${panels[state.drawerTab]()}</div>
      <footer class="drawer-foot"><button type="button" class="secondary-button" data-match="${fx.id}">Abrir ficha del partido</button><span>Datos ficticios · sin apuestas</span></footer>
    </aside></div>`;
}

function closeDrawer() {
  const key = state.drawer;
  state.drawer = null;
  render();
  app.querySelector(`.row-open[data-row="${CSS.escape(key)}"], [data-row="${CSS.escape(key)}"]`)?.focus();
}

function closeModal() {
  const trigger = state.modal;
  state.modal = null;
  render();
  if (trigger) app.querySelector(`[data-modal="${trigger}"]`)?.focus();
}

function applyCybercoreTheme(root) {
  const add = (selector, ...classes) => root.querySelectorAll(selector).forEach(element => element.classList.add(...classes));

  add('.panel, .stat-card, .match-card, .feature-card, .plan-card, .rail-panel, .real-card, .membership-plan, .membership-club, .membership-comparison, .auth-card, .account-section, .pick-package, .delivery-card, .order-summary, .checkout-details', 'cyber-card');
  add('.match-card, .feature-card, .real-card, .pick-card, .membership-plan, .pick-package, .quick-btn', 'cyber-card--interactive');
  add('.hero-preview, .forecast-summary, .membership-plan.featured, .membership-plan.selected, .pod-card', 'cyber-card', 'cyber-card--holo');
  add('.membership-plan.featured, .membership-plan.selected, .pod-card', 'cyber-card--green');

  add('.primary-button', 'cyber-btn', 'cyber-btn--green', 'cyber-btn--filled');
  add('.secondary-button, .account-button', 'cyber-btn', 'cyber-btn--ghost');
  add('.text-link', 'cyber-text-green');

  add('.badge', 'cyber-badge', 'cyber-badge--sm');
  add('.badge.accent, .badge.good', 'cyber-badge--green');
  add('.badge.warn', 'cyber-badge--yellow');
  add('.badge.muted', 'cyber-badge--chrome');

  add('input:not([type="checkbox"]):not([type="radio"]), select, textarea', 'cyber-input');
  add('.table-wrap', 'cyber-table-wrapper');
  add('table', 'cyber-table');
  add('.top-link', 'cyber-nav__link');
  add('.disclosure, .mode-note, .plain-callout, .board-disclaimer', 'cyber-alert');
  add('.hero-pattern', 'cyber-scanlines', 'cyber-scanlines--fine');
  add('.publication-strip', 'cyber-datastream');
  add('.fixture-hero, .pod-panel, .auth-card', 'cyber-neon-border', 'cyber-neon-border--cyan');

  root.querySelectorAll('.view-title h1, .membership-heading h1, .auth-story h1, .forecast-copy h1').forEach(title => {
    title.classList.add('cyber-heading');
    title.dataset.text = title.textContent.trim();
  });
}

// ---------------------------------------------------------------- render

function render() {
  const views = { inicio: homeView, partidos: statsView, mercados: deskView, picks: picksView, alta: altaView, escalera: escaleraView, parley: parleyView, partido: matchView, historial: historyView, planes: plansView, cuenta: accountView, paquetes: membershipUI.packagesView, acceso: membershipUI.authView, checkout: membershipUI.checkoutView };
  const overlay = state.mobileMenuOpen || Boolean(state.modal) || Boolean(state.drawer);
  document.title = `${routeTitle[state.route]} · QuantFut`;
  app.innerHTML = `<div class="app-shell top-layout"><header class="site-header"><div class="header-main"><button type="button" class="header-brand" data-route="inicio" aria-label="QuantFut, ir a inicio"><span class="brand-mark">Q<span>.</span></span><span class="brand-text"><strong>QuantFut</strong><small>FOOTBALL INTELLIGENCE</small></span></button>${sportNavMarkup()}<span class="header-status"><span class="side-live-dot"></span><span>Sistema en validación <small>· Transparencia por diseño</small></span></span><div class="top-actions">${oddsToggle('top-odds')}<span class="demo-flag">● DEMO + DATOS PÚBLICOS</span><button type="button" class="account-button" data-route="${state.session ? 'cuenta' : 'acceso'}">${state.session ? 'Mi cuenta' : 'Entrar'} <span aria-hidden="true">↗</span></button></div></div><nav class="top-nav" aria-label="Navegación principal">${navMarkup()}</nav></header><div class="main-shell"><main id="main-content" class="content ${state.route === 'mercados' ? 'content-wide' : ''}" tabindex="-1">${views[state.route]()}</main><footer class="footer"><span>© QuantFut Intelligence · Sports Lab</span><span>Datos reales señalados; el resto es demo. Sin apuestas ni pagos.</span></footer></div></div>${mobileNavMarkup()}${drawerMarkup()}${modalMarkup()}`;
  applyCybercoreTheme(app);
  app.querySelector('.app-shell').inert = overlay;
  app.querySelector('.mobile-bottom-nav').inert = overlay;
  app.querySelectorAll('.prob-bar[data-segments]').forEach(bar => {
    const values = bar.dataset.segments.split(',');
    bar.querySelectorAll('span').forEach((segment, index) => { segment.style.width = `${values[index]}%`; });
  });
  app.querySelectorAll('.bar[data-width], .cmp-bar i[data-width]').forEach(bar => { bar.style.width = `${bar.dataset.width}%`; });
  fitDeskSide();
  if (state.modal) app.querySelector('.modal-close')?.focus();
}

// La lista de partidos solo queda fija si cabe entera bajo la cabecera.
function fitDeskSide() {
  const side = app.querySelector('.desk-side');
  const header = app.querySelector('.site-header');
  if (!side || !header) return;
  side.classList.remove('is-tall');
  side.classList.toggle('is-tall', side.offsetHeight > window.innerHeight - header.offsetHeight - 24);
}
window.addEventListener('resize', fitDeskSide);

function rerenderKeepingFocus(selector) {
  render();
  app.querySelector(selector)?.focus();
}

function openDrawer(key, trigger) {
  state.drawer = key;
  if (!trigger?.closest('.drawer')) state.drawerTab = 'resumen';
  render();
  app.querySelector('.drawer-close')?.focus();
}

app.addEventListener('click', event => {
  const button = event.target.closest('button');
  if (!button) {
    if (event.target.classList.contains('modal-backdrop')) closeModal();
    return;
  }
  const data = button.dataset;
  if (membershipUI.handleClick(button)) return;
  if (data.action === 'refresh-public') { refreshPublicData(); return; }
  if (data.route) { if (data.homeMarketMode) { state.deskMode = data.homeMarketMode; state.deskDay = state.dayOffset; state.deskSort = { key: 'edge', dir: 'desc' }; } if (data.route === 'acceso') { state.authReturn = 'cuenta'; state.authMode = 'login'; state.authMessage = ''; } navigate(data.route); return; }
  if (data.homeStatus) { state.homeStatus = data.homeStatus; rerenderKeepingFocus(`[data-home-status="${data.homeStatus}"]`); return; }
  if (data.homeLeague) { state.homeLeague = data.homeLeague; rerenderKeepingFocus(`[data-home-league="${CSS.escape(data.homeLeague)}"]`); return; }
  if (data.action === 'clear-home') { state.homeSearch = ''; state.homeStatus = 'todos'; state.homeLeague = 'Todas'; state.homeSort = 'hora'; rerenderKeepingFocus('[data-action="clear-home"]'); return; }
  if (data.openFicha) { state.statsDay = 0; state.statsLeague = 'Todas'; state.statsMatch = data.openFicha; state.statsTab = 'resumen'; navigate('partidos'); return; }
  if (data.statsMatch) { state.statsMatch = data.statsMatch; rerenderKeepingFocus(`[data-stats-match="${CSS.escape(data.statsMatch)}"]`); return; }
  if (data.statsDay !== undefined && data.statsDay !== '') { state.statsDay = Number(data.statsDay); state.statsMatch = null; rerenderKeepingFocus('.stats-desk .day-stepper strong'); return; }
  if (data.statsLeague) { state.statsLeague = data.statsLeague; state.statsMatch = null; rerenderKeepingFocus(`[data-stats-league="${CSS.escape(data.statsLeague)}"]`); return; }
  if (data.statsTab) { state.statsTab = data.statsTab; rerenderKeepingFocus(`[data-stats-tab="${data.statsTab}"][role="tab"]`); return; }
  if (data.statsSplit) { state.statsSplit = data.statsSplit; rerenderKeepingFocus(`[data-stats-split="${data.statsSplit}"]`); return; }
  if (data.action === 'retry-agenda') { agendaCache.delete(state.statsDay); render(); return; }
  if (data.action === 'retry-ficha') { fichaCache.delete(state.statsMatch); render(); return; }
  if (data.match) { state.drawer = null; openMatch(data.match); return; }
  if (data.parlay) { toggleLeg(data.parlay); rerenderKeepingFocus(button.classList.contains('slip-remove') ? '.slip-remove, [data-desk-mode="combinadas"]' : `.slip-toggle[data-parlay="${CSS.escape(data.parlay)}"]`); return; }
  if (data.deskMode) { state.deskMode = data.deskMode; state.deskSort = { key: data.deskMode === 'probables' ? 'fair' : 'edge', dir: 'desc' }; rerenderKeepingFocus(`[data-desk-mode="${data.deskMode}"]`); return; }
  if (data.action === 'load-shadow') { shadowPicks.filter(pick => pick.row.fx.day === state.deskDay && tradable(pick.row)).forEach(pick => { if (!state.parlay.includes(pick.row.key)) toggleLeg(pick.row.key); }); rerenderKeepingFocus('[data-action="load-shadow"]'); return; }
  if (data.comboTab) { state.comboTab = data.comboTab; rerenderKeepingFocus(`[data-combo-tab="${data.comboTab}"]`); return; }
  if (data.loadCombo) { state.parlay = data.loadCombo.split('|').filter(key => rowByKey.has(key)); state.comboTab = 'manual'; rerenderKeepingFocus('[data-combo-tab="manual"]'); return; }
  if (data.action === 'clear-parlay') { state.parlay = []; rerenderKeepingFocus('[data-desk-mode="combinadas"]'); return; }
  if (data.row) { openDrawer(data.row, button); return; }
  if (data.deskOpen) { state.drawer = null; state.deskDay = fixtureById.get(data.deskOpen).day; state.deskMatch = data.deskOpen; state.deskStatus = 'todos'; navigate('mercados'); return; }
  if (data.odds) { state.oddsFormat = data.odds; savePrefs(); const scope = button.closest('.top-odds') ? '.top-odds ' : button.closest('.account-content') ? '.account-content ' : ''; rerenderKeepingFocus(`${scope}[data-odds="${data.odds}"]`); return; }
  if (data.day !== undefined) { state.dayOffset = Number(data.day); rerenderKeepingFocus(`[data-day="${state.dayOffset}"]`); return; }
  if (data.deskDay !== undefined && data.deskDay !== '') { state.deskDay = Number(data.deskDay); state.deskMatch = ''; rerenderKeepingFocus('.day-stepper strong'); return; }
  if (data.deskStatus) { state.deskStatus = data.deskStatus; state.deskMatch = ''; rerenderKeepingFocus(`[data-desk-status="${data.deskStatus}"]`); return; }
  if (data.deskMatch !== undefined) { state.deskMatch = data.deskMatch; rerenderKeepingFocus(`[data-desk-match="${data.deskMatch}"]`); return; }
  if (data.deskFamily) { state.deskFamily = data.deskFamily; rerenderKeepingFocus(`[data-desk-family="${data.deskFamily}"]`); return; }
  if (data.deskToggle) { state[data.deskToggle] = !state[data.deskToggle]; rerenderKeepingFocus(`[data-desk-toggle="${data.deskToggle}"]`); return; }
  if (data.sort) { const same = state.deskSort.key === data.sort; state.deskSort = { key: data.sort, dir: same && state.deskSort.dir === 'desc' ? 'asc' : 'desc' }; rerenderKeepingFocus(`[data-sort="${data.sort}"]`); return; }
  if (data.pickLeague) { state.pickLeague = data.pickLeague; rerenderKeepingFocus(`[data-pick-league="${data.pickLeague}"]`); return; }
  if (data.matchTab) { state.matchTab = data.matchTab; rerenderKeepingFocus(`[data-match-tab="${data.matchTab}"][role="tab"]`); return; }
  if (data.drawerTab) { state.drawerTab = data.drawerTab; rerenderKeepingFocus(`[data-drawer-tab="${data.drawerTab}"]`); return; }
  if (data.record) { state.recordFilter = data.record; rerenderKeepingFocus(`[data-record="${data.record}"]`); return; }
  if (data.recordLeague) { state.recordLeague = data.recordLeague; rerenderKeepingFocus(`[data-record-league="${data.recordLeague}"]`); return; }
  if (data.modal) { state.modal = data.modal; state.accessStep = 0; render(); return; }
  if (data.action === 'access-next') {
    if (state.accessStep === 2) state.accessStep = 0;
    else state.accessStep += 1;
    render();
    app.querySelector('.access-modal [data-action="access-next"]')?.focus();
    return;
  }
  if (data.action === 'toggle-menu') { state.mobileMenuOpen = !state.mobileMenuOpen; render(); app.querySelector(state.mobileMenuOpen ? '.mobile-drawer [data-route]' : '.mobile-more')?.focus(); return; }
  if (data.action === 'close-menu') { state.mobileMenuOpen = false; render(); app.querySelector('.mobile-more')?.focus(); return; }
  if (data.action === 'close-modal') { closeModal(); return; }
  if (data.action === 'close-drawer') { closeDrawer(); return; }
});

app.addEventListener('change', event => {
  const target = event.target;
  if (target.id === 'home-sort') { state.homeSort = target.value; rerenderKeepingFocus('#home-sort'); return; }
  if (target.dataset.filter === 'match') { state.selectedMatch = target.value; rerenderKeepingFocus('#match-select'); }
  if (target.dataset.follow) {
    const league = target.dataset.follow;
    state.followed = target.checked ? [...new Set([...state.followed, league])] : state.followed.filter(item => item !== league);
    savePrefs();
    rerenderKeepingFocus(`[data-follow="${league}"]`);
  }
});

app.addEventListener('input', event => {
  const home = event.target.dataset.input === 'home-search';
  if (!home && event.target.dataset.input !== 'desk-search') return;
  const caret = event.target.selectionStart;
  if (home) state.homeSearch = event.target.value;
  else state.deskSearch = event.target.value;
  render();
  const input = app.querySelector(home ? '#home-search' : '#desk-search');
  input.focus();
  input.setSelectionRange(caret, caret);
});

app.addEventListener('submit', event => {
  if (!event.target.dataset.membershipForm) return;
  event.preventDefault();
  membershipUI.handleSubmit(event.target);
});

window.addEventListener('hashchange', () => {
  const route = location.hash.slice(1);
  if (validRoute(route) && state.route !== route) { state.route = route; state.mobileMenuOpen = false; state.drawer = null; render(); app.querySelector('#main-content')?.focus({ preventScroll: true }); }
});

function trapFocus(event, container) {
  const controls = [...app.querySelectorAll(`${container} button:not([disabled]):not([tabindex="-1"]), ${container} [tabindex="0"]`)];
  if (!controls.length) return;
  const first = controls[0];
  const last = controls[controls.length - 1];
  if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
  else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
}

window.addEventListener('keydown', event => {
  if (state.modal) {
    if (event.key === 'Escape') closeModal();
    else if (event.key === 'Tab') trapFocus(event, '.modal');
    return;
  }
  if (state.drawer) {
    if (event.key === 'Escape') closeDrawer();
    else if (event.key === 'Tab') trapFocus(event, '.drawer');
    return;
  }
  if (state.mobileMenuOpen) {
    if (event.key === 'Escape') { state.mobileMenuOpen = false; render(); app.querySelector('.mobile-more')?.focus(); }
    else if (event.key === 'Tab') trapFocus(event, '.mobile-drawer');
  }
});

const initial = location.hash.slice(1);
if (validRoute(initial)) state.route = initial;
render();
membershipUI.restoreSession();
membershipUI.loadPlans();
async function refreshPublicData() {
  const request = ++publicRequest;
  publicData = null;
  render();
  const result = await loadPublicData();
  if (request !== publicRequest) return;
  publicData = result;
  if (!state.modal && !state.drawer && !state.mobileMenuOpen) render();
}
refreshPublicData();
