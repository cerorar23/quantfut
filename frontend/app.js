import { loadPublicData, isPublicationActive, probabilityLabel, expectedHitRate, lockedPicksHtml, lockedParleyHtml, sessionFetch } from './public-data.js?v=54fa60ae0082';
import { loadAgenda, loadFicha, loadForecastHome, loadForecastMatch, localDay, featuredMarket } from './fichas-data.js?v=real-20261029';
import { createMembershipUI } from './membership.js?v=planes-20261027';
import { createRealViews } from './real-views.js?v=planes-20261027';
import { loadSport, loadResults, loadImages, loadTennisStats, loadNbaStats, featuredModelMarket } from './sports-data.js?v=imagenes-20261029';
import { createSportWindow } from './sports-window.js?v=planes-20261027';
import { authHeaders } from './cuenta-api.js?v=b298f1c04385';
import { createConversionViews } from './conversion-views.js?v=conv-20261027';

// Fuentes reales: no se incluyen equipos, cuotas ni resultados simulados.
const now = new Date();
const today = new Date(now); today.setHours(0, 0, 0, 0);
const addDays = (offset, hour = 20) => { const date = new Date(); date.setDate(date.getDate() + offset); date.setHours(hour,0,0,0); return date; };
const LEAGUES = [], fixtures = [], archive = [], allRows = [], shadowPicks = [];
const rowByKey = new Map(), fixtureById = new Map();
const sum = values => values.reduce((total,value)=>total+value,0);
const round2 = value => Math.round(value*100)/100;
const SOFT_MIN_EDGE = .02, MAX_SHARP_DEVIATION = .03;
const pickFor = () => null;

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
  { route: 'picks', label: 'Pronósticos', short: 'Picks', icon: NAV_ICONS.pick, group: 'EXPLORAR' },
  { route: 'historial', label: 'Historial', short: 'Historial', icon: NAV_ICONS.history, group: 'EVIDENCIA' },
  { route: 'alta', label: 'Alta probabilidad', short: 'Alta prob.', icon: NAV_ICONS.target, group: 'HERRAMIENTAS' },
  { route: 'parley', label: 'Parley del día', short: 'Parley', icon: NAV_ICONS.combine, group: 'HERRAMIENTAS' },
  { route: 'escalera', label: 'Reto escalera', short: 'Escalera', icon: NAV_ICONS.rise, group: 'HERRAMIENTAS' },
  { route: 'paquetes', label: 'Paquetes de picks', short: 'Paquetes', icon: NAV_ICONS.package, group: 'ACCESO' },
  { route: 'planes', label: 'Suscripciones', short: 'Planes', icon: NAV_ICONS.shield, group: 'ACCESO' },
  { route: 'cuenta', label: 'Mi cuenta', short: 'Mi cuenta', icon: NAV_ICONS.user, group: 'ACCESO' },
];
const MOBILE_PRIMARY = ['inicio', 'historial', 'planes', 'cuenta'];
const routeTitle = { inicio: 'Portada', partidos: 'Partidos y estadísticas', mercados: 'Mesa de mercados', picks: 'Picks', alta: 'Alta probabilidad', escalera: 'Reto escalera', parley: 'Parley del día', partido: 'Análisis del partido', historial: 'Historial', planes: 'Suscripciones', cuenta: 'Mi cuenta', paquetes: 'Paquetes de picks', acceso: 'Acceso', checkout: 'Revisar pedido' };
const validRoute = route => Object.hasOwn(routeTitle, route);
const ROUTE_ALIAS = { mercados: 'partidos', partido: 'partidos' };
const canonicalRoute = route => ROUTE_ALIAS[route] || route;
routeTitle.analisis = 'Análisis deportivo';
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
  selectedMatch: '',
  realMatch: '',
  statsDay: 0,
  statsLeague: 'Todas',
  statsMatch: null,
  statsTab: 'resumen',
  statsSplit: 'todos',
  winPane: 'pron',
  winDay: 0,
  winEvent: '',
  winLastEvent: null,
  winEvList: [],
  winSportTab: 'resumen',
  winSportFam: '',
  winFormScope: 'all',
  winAll: false,
  winResetFlag: false,
  winDayPinned: false,
  winFam: 'Todos',
  winLast: null,
  winList: [],
  matchTab: 'resumen',
  dayOffset: 0,
  sport: 'todos',
  resultSport: 'todos',
  sportEvent: '',
  sportMarket: 'partido',
  homeSearch: '',
  homeStatus: 'proximos',
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
// Se declaran aquí, antes del primer `render()`, que ya llama a `syncPublicAuth`: más abajo caen en la zona muerta temporal y el script aborta.
// Un suscriptor VIP ve todos los pronósticos también en la web (ver `sessionFetch`).
const publicFetch = sessionFetch((...args) => fetch(...args), authHeaders, ['/alta-probabilidad', '/escalera', '/parley', '/mobile/v1/home', '/mobile/v1/matches/']);
// Al iniciar o cerrar sesión, o al activarse la suscripción, se recargan los datos con la sesión nueva.
let publicAuthKey = 'visitante';
const realHomeCache = new Map(), realMatchCache = new Map();
const sportsCache = new Map();
let resultsCache = null;
let imagesCache = null;
let realGeneration = 0;
function ensureSport(sport) {
  if(sportsCache.has(sport))return sportsCache.get(sport);
  const entry={status:'loading',events:[]},generation=realGeneration;
  sportsCache.set(sport,entry);
  loadSport(sport).then(result=>{if(generation!==realGeneration)return;sportsCache.set(sport,result);rerenderIfIdle();});
  return entry;
}
const tennisStatsCache = new Map();
function ensureTennisStats(id) {
  if (tennisStatsCache.has(id)) return tennisStatsCache.get(id);
  const entry = { status: 'loading', data: null }, generation = realGeneration;
  tennisStatsCache.set(id, entry);
  loadTennisStats(id).then(result => { if (generation !== realGeneration) return; tennisStatsCache.set(id, result); rerenderIfIdle(); });
  return entry;
}
const nbaStatsCache = new Map();
function ensureNbaStats(id) {
  if (nbaStatsCache.has(id)) return nbaStatsCache.get(id);
  const entry = { status: 'loading', data: null }, generation = realGeneration;
  nbaStatsCache.set(id, entry);
  loadNbaStats(id).then(result => { if (generation !== realGeneration) return; nbaStatsCache.set(id, result); rerenderIfIdle(); });
  return entry;
}
function ensureResults() {
  if(resultsCache)return resultsCache;
  resultsCache={status:'loading',items:[]}; const generation=realGeneration;
  loadResults().then(result=>{if(generation!==realGeneration)return;resultsCache=result;rerenderIfIdle();});
  return resultsCache;
}
function ensureImages() {
  if(imagesCache)return imagesCache;
  imagesCache={status:'loading',nba:{},tenis:{}};
  loadImages().then(result=>{imagesCache=result;rerenderIfIdle();});
  return imagesCache;
}
function ensureRealHome(offset) {
  const key = localDay(addDays(offset,12));
  if (realHomeCache.has(key)) return realHomeCache.get(key);
  const entry = {status:'loading',data:null}, generation=realGeneration;
  realHomeCache.set(key,entry);
  loadForecastHome(addDays(offset,12),publicFetch).then(result=>{
    if(generation!==realGeneration)return;
    realHomeCache.set(key,result);
    if(result.status==='ready')LEAGUES.splice(0,LEAGUES.length,...new Set(result.data.agenda.map(g=>g.liga.nombre)));
    rerenderIfIdle();
  });
  return entry;
}
function ensureRealMatch(id) {
  if(realMatchCache.has(id))return realMatchCache.get(id);
  const entry={status:'loading',data:null},generation=realGeneration;
  realMatchCache.set(id,entry);
  loadForecastMatch(id,publicFetch).then(result=>{
    if(generation!==realGeneration)return;
    realMatchCache.set(id,result); if(state.realMatch===id)rerenderIfIdle();
  });
  return entry;
}


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
  route = canonicalRoute(route);
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
  state.realMatch = id;
  state.selectedMatch = id;
  state.matchTab = tab;
  navigate('partido');
}

const sportActive = id => state.sport === id || (id === 'futbol' && state.sport === 'todos' && state.route === 'partidos');

function sportNavMarkup() {
  return `<nav class="sport-nav" aria-label="Deporte">${[['futbol','Fútbol'],['nba','NBA'],['tenis','Tenis']].map(([id,label])=>`<a href="#picks" data-sport="${id}" class="${sportActive(id)?'active':''}" ${sportActive(id)?'aria-current="page"':''}>${label}</a>`).join('')}</nav>`;
}

function navMarkup() {
  const groups = [...new Set(nav.map(item => item.group))];
  return groups.map(group => `<div class="top-nav-group" role="group" aria-label="${group.charAt(0)}${group.slice(1).toLowerCase()}"><span class="top-nav-label" aria-hidden="true">${group}</span>${nav.filter(item => item.group === group && ['inicio','picks','historial','alta','parley','escalera','planes'].includes(item.route)).map(item => {
    const active = state.route === item.route;
    return `<button type="button" class="top-link ${active ? 'active' : ''}" data-route="${item.route}" ${active ? 'aria-current="page"' : ''}><span class="nav-icon" aria-hidden="true">${item.icon}</span><span>${item.label}</span></button>`;
  }).join('')}</div>`).join('');
}

function mobileNavMarkup() {
  const primary = nav.filter(item => MOBILE_PRIMARY.includes(item.route));
  const extra = nav.filter(item => !MOBILE_PRIMARY.includes(item.route));
  const link = item => `<button type="button" class="mobile-nav-link ${state.route === item.route ? 'active' : ''}" data-route="${item.route}" ${state.route === item.route ? 'aria-current="page"' : ''}><span aria-hidden="true">${item.icon}</span><small>${item.short}</small></button>`;
  const drawer = state.mobileMenuOpen ? `<div class="mobile-menu-layer"><button type="button" class="mobile-menu-backdrop" data-action="close-menu" aria-label="Cerrar menú adicional"></button><div id="mobile-extra-menu" class="mobile-drawer" role="dialog" aria-modal="true" aria-label="Más secciones"><div class="mobile-drawer-head"><div><p class="eyebrow">QUANTFUT / EXPLORAR</p><h2>Más secciones</h2></div><button type="button" class="mobile-drawer-close" data-action="close-menu" aria-label="Cerrar menú">×</button></div>${extra.map(item => `<button type="button" class="mobile-drawer-link" data-route="${item.route}" ${state.route === item.route ? 'aria-current="page"' : ''}><span aria-hidden="true">${item.icon}</span><span>${item.label}</span><span aria-hidden="true">↗</span></button>`).join('')}<p>Las cuentas y los pronósticos se consultan en el servidor.</p></div></div>` : '';
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

// #alta, #parley y #escalera: vistas de conversión en conversion-views.js
// (solo datos reales de /alta-probabilidad, /parley y /escalera).
const conversionViews = createConversionViews({ esc, realNumber, realPercent, realDate, realTime, badge, probabilityLabel, getData: () => publicData });
const { altaView, parleyView, escaleraView } = conversionViews;

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

function fichaPanels(f) {
  return {
    resumen: () => `<div class="stack">${averagesPanel(f)}<div class="analysis-grid even"><section class="panel"><p class="eyebrow">RACHA · ÚLTIMOS 5</p><h2>Momento de forma</h2>${formStrip(f.local)}${formStrip(f.visitante, true)}</section><section class="panel"><p class="eyebrow">CARA A CARA</p><h2>Historial directo</h2>${h2hSummary(f.cara_a_cara, f)}<button type="button" class="text-link" data-stats-tab="h2h">Ver los cruces ↗</button></section></div></div>`,
    forma: () => `<div class="analysis-grid even"><section class="panel"><p class="eyebrow">${esc(f.local.nombre.toUpperCase())}</p><h2>Últimos partidos</h2>${formList(f.local)}</section><section class="panel"><p class="eyebrow">${esc(f.visitante.nombre.toUpperCase())}</p><h2>Últimos partidos</h2>${formList(f.visitante)}</section></div>`,
    h2h: () => `<section class="panel"><p class="eyebrow">CARA A CARA</p><h2>${esc(f.local.nombre)} vs ${esc(f.visitante.nombre)}</h2>${h2hSummary(f.cara_a_cara, f)}${h2hList(f.cara_a_cara, f)}</section>`,
    estadisticas: () => statsPanel(f),
    tabla: () => tablePanel(f),
    alineaciones: () => lineupsPanel(f),
  };
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
  const panels = fichaPanels(f);
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

// ---- ventana única: pronóstico + estadísticas del mismo partido

const WIN_TABS = [['resumen', 'Resumen'], ['forma', 'Forma'], ['h2h', 'Cara a cara'], ['estadisticas', 'Estadísticas'], ['tabla', 'Tabla'], ['alineaciones', 'Alineaciones']];
let winResetScroll = false;

const winCrest = team => (team.escudo
  ? `<img class="win-crest" src="${esc(team.escudo)}" alt="" loading="lazy" decoding="async">`
  : `<span class="win-crest is-initial" aria-hidden="true">${esc(String(team.nombre || '?').charAt(0))}</span>`);

function winRow(p) {
  const st = estadoPartido(p);
  const active = state.statsMatch === p.match_id;
  return `<button type="button" class="win-row" data-stats-match="${esc(p.match_id)}" aria-pressed="${active}" ${active ? 'aria-current="true"' : ''}><span class="win-when"><b>${esc(st.main)}</b>${st.tag ? `<small>${st.tag}</small>` : ''}</span><span class="win-names"><span>${winCrest(p.local)}<span>${esc(p.local.nombre)}</span></span><span>${winCrest(p.visitante)}<span>${esc(p.visitante.nombre)}</span></span></span></button>`;
}

function winTeam(team, detail, away) {
  const pts = detail?.clasificacion ? ` · ${realNumber(detail.clasificacion.puntos)} pts` : '';
  return `<div class="win-team ${away ? 'is-away' : ''}">${winCrest(team)}<div><strong>${esc(team.nombre)}</strong><small>${team.posicion ? posLabel(team.posicion) : away ? 'Visitante' : 'Local'}${pts}</small>${rachaDots(team.racha)}</div></div>`;
}

function winForecast(game, entry) {
  if (entry.status === 'loading') return '<div class="panel loading-panel"><p class="eyebrow">PRONÓSTICO</p><h2>Consultando pronósticos…</h2></div>';
  if (entry.status !== 'ready') return '<div class="empty-state"><h3>No se pudo consultar el pronóstico</h3><p>El servidor no respondió. <button type="button" class="text-link" data-action="retry-real">Reintentar ↻</button></p></div>';
  const { ficha, picks } = entry.data;
  const feat = featuredMarket(ficha.mercados);
  const sealed = feat?.pick_key ? picks.find(p => p.pick_key === feat.pick_key && p.chain_sha256) : null;
  const range = (ficha.mercados?.rango || [1.4, 1.8]).map(x => Number(x).toFixed(2).replace('.', ',')).join(' a ');
  const card = feat
    ? `<p class="eyebrow">PRONÓSTICO DESTACADO${sealed ? ` · LOTE ${esc(sealed.batch_date)}` : ''}</p><div class="win-pick-grid"><div><h2>${esc(feat.seleccion)}</h2><p class="win-sub">${esc(feat.titulo || feat.grupo)} · ${esc(game.liga.nombre)} · ${esc(game.local.nombre)} vs ${esc(game.visitante.nombre)}</p></div><div class="win-odd"><small>${feat.cuota_tipo === 'publicada' ? 'Cuota publicada' : 'Cuota del modelo'}</small><strong>${fmtOdds(feat.cuota)}</strong><em>${feat.cuota_tipo === 'publicada' ? esc(sealed?.ref_book || 'Casa registrada') : '1 ÷ probabilidad'}</em></div></div><div class="win-prob"><b>${fmtPct(feat.prob)}</b><div class="cyber-progress cyber-progress--green" data-value="${(feat.prob * 100).toFixed(1)}" role="progressbar" aria-label="Probabilidad del pronóstico destacado" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${(feat.prob * 100).toFixed(1)}"><div class="cyber-progress__bar"></div></div></div>${sealed ? `<details class="win-reg"><summary>Registro del pronóstico</summary><p>Casa: ${esc(sealed.ref_book || 'No disponible')} · Cuota capturada ${realDate(sealed.odds_as_of)} ${realTime(sealed.odds_as_of)}.</p><code>${esc(sealed.chain_sha256)}</code><p>La cuota corresponde a la captura registrada y puede haber cambiado.</p></details>` : ''}`
    : `<p class="eyebrow">PRONÓSTICO DESTACADO</p><h2>Sin pronóstico destacado</h2><p class="win-sub">Ningún mercado de este partido tiene cuota de ${range}.</p>`;
  const rows = ficha.mercados?.filas || [];
  const groups = [...new Set(rows.map(r => r.grupo))];
  const fam = groups.includes(state.winFam) ? state.winFam : 'Todos';
  const shown = rows.filter(r => fam === 'Todos' || r.grupo === fam).sort((a, b) => Number(a.locked === true) - Number(b.locked === true));
  const locked = rows.filter(r => r.locked === true).length;
  const line = r => (r.locked
    ? `<tr class="win-lock"><td>${esc(r.grupo)}</td><td>Contenido reservado</td><td class="n" aria-hidden="true">••</td><td class="n" aria-hidden="true">••</td><td>${badge('VIP', 'warn')}</td></tr>`
    : `<tr${r.destacado ? ' class="win-feat"' : ''}><td>${esc(r.titulo || r.grupo)}</td><td>${esc(r.seleccion)}</td><td class="n">${typeof r.prob === 'number' ? fmtPct(r.prob) : '—'}</td><td class="n">${typeof r.cuota === 'number' ? fmtOdds(r.cuota) : '—'}</td><td>${r.destacado ? badge('Destacado', 'good') : r.cuota_tipo === 'publicada' ? badge('Cuota registrada', 'good') : badge('Cuota del modelo', 'muted')}</td></tr>`);
  const market = rows.length
    ? `<section aria-label="Mercados"><div class="win-mk-head"><h3>Mercados</h3><div class="win-chips" role="group" aria-label="Familia de mercado">${['Todos', ...groups].map(g => `<button type="button" class="chip ${fam === g ? 'selected' : ''}" data-win-fam="${esc(g)}" aria-pressed="${fam === g}">${esc(g)}</button>`).join('')}</div></div><div class="win-table" tabindex="0" role="region" aria-label="Mercados del partido"><table class="cyber-table cyber-table--compact"><thead><tr><th scope="col">Mercado</th><th scope="col">Selección</th><th scope="col" class="n">Prob.</th><th scope="col" class="n">Cuota</th><th scope="col">Acceso</th></tr></thead><tbody>${shown.map(line).join('')}</tbody></table></div>${locked ? `<div class="win-vipbar"><p><strong>${locked} mercados con plan VIP</strong>Para ver todos los mercados necesitas un plan VIP contratado.</p><button type="button" class="cyber-btn cyber-btn--green cyber-btn--sm" data-route="planes">Acceso VIP ↗</button></div>` : ''}</section>`
    : '<p class="win-sub">No hay mercados disponibles para este encuentro.</p>';
  return `<article class="win-pick cyber-card" aria-label="Pronóstico destacado">${card}</article>${market}<p class="bottom-note">El servidor decide qué mercados se abren según tu acceso; los bloqueados no llevan selección ni cuota. Una estimación estadística no acredita rentabilidad.</p>`;
}

function winStats(entry) {
  if (!entry || entry.status === 'loading') return '<div class="panel loading-panel"><p class="eyebrow">ESTADÍSTICAS</p><h2>Cargando datos del partido…</h2></div>';
  if (entry.status !== 'ready') return '<div class="empty-state"><h3>No se pudo cargar la ficha</h3><p>El servidor no respondió. <button type="button" class="text-link" data-action="retry-ficha">Reintentar ↻</button></p></div>';
  const tab = WIN_TABS.some(([id]) => id === state.statsTab) ? state.statsTab : 'resumen';
  return `<div class="win-tabs-wrap"><div class="cyber-tabs cyber-tabs--pills cyber-tabs--scrollable" role="tablist" aria-label="Secciones de estadísticas">${WIN_TABS.map(([id, label]) => `<button type="button" role="tab" id="win-tab-${id}" aria-controls="win-stats-panel" aria-selected="${tab === id}" class="cyber-tab ${tab === id ? 'cyber-tab--active' : ''}" data-stats-tab="${id}">${label}</button>`).join('')}</div></div><div id="win-stats-panel" role="tabpanel" aria-labelledby="win-tab-${tab}" class="win-panel">${fichaPanels(entry.data)[tab]()}</div>`;
}

function windowView() {
  if (state.sport === 'nba' || state.sport === 'tenis') { const markup = sportWindow.view(); winResetScroll = state.winResetFlag; return markup; }
  const agenda = ensureAgenda(state.statsDay);
  const all = agenda.status === 'ready' ? agenda.data.partidos : [];
  const leagues = [...new Map(all.map(p => [p.liga.id, p.liga.nombre])).entries()];
  if (state.statsLeague !== 'Todas' && !leagues.some(([id]) => id === state.statsLeague)) state.statsLeague = 'Todas';
  const list = all.filter(p => state.statsLeague === 'Todas' || p.liga.id === state.statsLeague);
  state.statsMatch = selectedAgendaMatch(list);
  winResetScroll = state.winLast !== state.statsMatch;
  if (winResetScroll) state.winFam = 'Todos';
  state.winLast = state.statsMatch;
  state.realMatch = state.statsMatch || '';
  state.winList = list.map(p => p.match_id);
  const game = list.find(p => p.match_id === state.statsMatch);
  const dayIndex = STATS_DAYS.indexOf(state.statsDay);
  const index = state.winList.indexOf(state.statsMatch);
  const byLeague = leagues.filter(([id]) => state.statsLeague === 'Todas' || id === state.statsLeague).map(([id, name]) => [name, list.filter(p => p.liga.id === id)]);
  let rail;
  if (agenda.status === 'loading') rail = '<p class="rail-empty">Cargando partidos…</p>';
  else if (agenda.status !== 'ready') rail = '<p class="rail-empty">No se pudo cargar la agenda. <button type="button" class="text-link" data-action="retry-agenda">Reintentar ↻</button></p>';
  else if (!list.length) rail = '<p class="rail-empty">No hay partidos de las ligas seguidas este día.</p>';
  else rail = byLeague.map(([name, games]) => `<h3 class="win-league">${esc(name)}</h3>${games.map(winRow).join('')}`).join('');
  const ficha = game ? ensureFicha(game.match_id) : null;
  const detail = ficha?.status === 'ready' ? ficha.data : null;
  const st = game ? estadoPartido(game) : null;
  const bar = game
    ? `<div class="win-picker"><button type="button" data-win-step="-1" aria-label="Partido anterior" ${index <= 0 ? 'disabled' : ''}>‹</button><label class="win-select"><span class="sr-only">Elegir partido</span><select id="win-select">${list.map(p => `<option value="${esc(p.match_id)}" ${p.match_id === state.statsMatch ? 'selected' : ''}>${esc(estadoPartido(p).main)} · ${esc(p.local.nombre)} vs ${esc(p.visitante.nombre)}</option>`).join('')}</select></label><button type="button" data-win-step="1" aria-label="Partido siguiente" ${index >= list.length - 1 ? 'disabled' : ''}>›</button></div>${winTeam(game.local, detail?.local)}<span class="win-vs ${game.marcador ? 'score' : ''}">${game.marcador ? `${game.marcador[0]} – ${game.marcador[1]}` : 'VS'}</span>${winTeam(game.visitante, detail?.visitante, true)}<div class="win-meta"><span>${esc(game.liga.nombre)} · ${dateFmt(kickoffOf(game), { weekday: 'short', day: 'numeric', month: 'short' })} ${timeLabel(kickoffOf(game))}</span>${badge(st.tag || 'Programado', st.kind || 'muted')}</div>`
    : '';
  const body = game
    ? `<div class="win-switch" role="tablist" aria-label="Vista del partido"><button type="button" role="tab" aria-selected="${state.winPane === 'pron'}" data-win-pane="pron">Pronóstico</button><button type="button" role="tab" aria-selected="${state.winPane === 'stats'}" data-win-pane="stats">Estadísticas</button></div><div class="win-split"><div class="win-pane" id="win-pane-pron" aria-label="Pronóstico">${winForecast(game, ensureRealMatch(game.match_id))}</div><div class="win-pane" id="win-pane-stats" aria-label="Estadísticas">${winStats(ficha)}</div></div>`
    : `<div class="empty-state"><span class="empty-symbol">◷</span><h3>${agenda.status === 'loading' ? 'Cargando partidos…' : 'Sin partidos este día'}</h3><p>${agenda.status === 'loading' ? 'Consultando la agenda del servidor.' : 'Prueba con otro día o con otra competición.'}</p></div>`;
  return `<div class="win" data-pane="${state.winPane}"><div class="win-strip" role="toolbar" aria-label="Fecha y competición"><div class="win-day"><button type="button" data-stats-day="${STATS_DAYS[dayIndex - 1] ?? ''}" aria-label="Día anterior" ${dayIndex <= 0 ? 'disabled' : ''}>‹</button><strong>${realDayLabel(state.statsDay)}</strong><button type="button" data-stats-day="${STATS_DAYS[dayIndex + 1] ?? ''}" aria-label="Día siguiente" ${dayIndex >= STATS_DAYS.length - 1 ? 'disabled' : ''}>›</button></div><div class="win-chips" role="group" aria-label="Competición"><button type="button" class="chip ${state.statsLeague === 'Todas' ? 'selected' : ''}" data-stats-league="Todas" aria-pressed="${state.statsLeague === 'Todas'}">Todas <b>${all.length}</b></button>${leagues.map(([id, name]) => `<button type="button" class="chip ${state.statsLeague === id ? 'selected' : ''}" data-stats-league="${esc(id)}" aria-pressed="${state.statsLeague === id}">${esc(name)} <b>${all.filter(p => p.liga.id === id).length}</b></button>`).join('')}</div></div><div class="win-work"><aside class="win-rail" aria-label="Partidos del día">${rail}</aside><section class="win-main" aria-label="Partido seleccionado"><div class="win-matchbar">${bar}</div>${body}</section></div></div>`;
}

// Portada: lo real primero, con enlace a la ficha.
const membershipUI = createMembershipUI({
  state, esc, badge, oddsToggle, leagues: LEAGUES, fixtures, matchCard, navigate, render,
  publicStatus: () => {
    const source = ensureRealHome(0);
    return `<strong>${source.status==='ready'?'Contenido y acceso verificados por el servidor':source.status==='error'?'No se pudo consultar el contenido':'Consultando el contenido disponible…'}</strong><p>La suscripción amplía tu acceso a los pronósticos de fútbol disponibles. NBA y tenis ofrecen análisis estadísticos públicos.</p>`;
  },
});

const realViews = createRealViews({ state, esc, badge, ensureHome:ensureRealHome, ensureMatch:ensureRealMatch,
  addDays, localDay, dayLabel, timeLabel, realDate, realTime, fmtOdds, fmtPct, liveEvidence, livePicks, dayRail,
  ensureSport, ensureResults, ensureImages, plansPreview:()=>membershipUI.plansPreview() });

const sportWindow = createSportWindow({ state, esc, badge, fmtPct, fmtOdds, realDate, realTime, dateFmt, addDays, localDay, dayLabel, ensureSport, ensureTennisStats, ensureNbaStats, featuredModelMarket });

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
  if(state.mobileMenuOpen && window.matchMedia('(min-width:761px)').matches)state.mobileMenuOpen=false;
  const views = { inicio: realViews.home, partidos: windowView, mercados: windowView, picks: realViews.picks, analisis: realViews.detail, alta: altaView, escalera: escaleraView, parley: parleyView, partido: windowView, historial: realViews.history, planes: plansView, cuenta: accountView, paquetes: membershipUI.packagesView, acceso: membershipUI.authView, checkout: membershipUI.checkoutView };
  const overlay = state.mobileMenuOpen || Boolean(state.modal) || Boolean(state.drawer);
  const winScroll = [...app.querySelectorAll('.win-pane')].map(pane => pane.scrollTop);
  document.title = `${routeTitle[state.route]} · QuantFut`;
  app.innerHTML = `<div class="app-shell top-layout ${state.route === 'partidos' ? 'is-win' : ''} ${state.route === 'picks' ? 'is-win-picks' : ''}"><header class="site-header"><div class="header-main"><button type="button" class="header-brand" data-route="inicio" aria-label="QuantFut, ir a inicio"><span class="brand-mark">Q<span>.</span></span><span class="brand-text"><strong>QuantFut</strong><small>SPORTS INTELLIGENCE</small></span></button>${sportNavMarkup()}<span class="header-status"><span class="side-live-dot"></span><span>Pronósticos reales <small>· Registros verificables</small></span></span><div class="top-actions">${oddsToggle('top-odds')}<span class="demo-flag">● DATOS REALES</span><button type="button" class="account-button" data-route="${state.session ? 'cuenta' : 'acceso'}">${state.session ? 'Mi cuenta' : 'Entrar'} <span aria-hidden="true">↗</span></button></div></div><nav class="top-nav" aria-label="Navegación principal">${navMarkup()}</nav></header><div class="main-shell"><main id="main-content" class="content ${state.route === 'mercados' ? 'content-wide' : ''}" tabindex="-1">${views[state.route]()}</main><footer class="footer"><span>© QuantFut Intelligence · Sports Lab</span><span>Pronósticos y cuotas registrados por el servidor. Sin resultados garantizados.</span><span>Escudos de fútbol de API-Football, logos NBA de TheSportsDB y fotos de tenis de Wikimedia Commons con licencia Creative Commons. <a class="text-link" href="/web/imagenes/creditos" target="_blank" rel="noopener">Créditos de imágenes ↗</a></span></footer></div></div>${mobileNavMarkup()}${drawerMarkup()}${modalMarkup()}`;
  applyCybercoreTheme(app);
  conversionViews.applyMeters(app);
  membershipUI.afterRender();
  app.querySelector('.app-shell').inert = overlay;
  syncPublicAuth();
  app.querySelector('.mobile-bottom-nav').inert = overlay;
  app.querySelectorAll('.prob-bar[data-segments]').forEach(bar => {
    const values = bar.dataset.segments.split(',');
    bar.querySelectorAll('span').forEach((segment, index) => { segment.style.width = `${values[index]}%`; });
  });
  app.querySelectorAll('.cyber-progress[data-value]').forEach(bar => bar.style.setProperty('--progress-value', `${bar.dataset.value}%`));
  const winPanes = app.querySelectorAll('.win-pane');
  if (!winResetScroll && winPanes.length === winScroll.length) winPanes.forEach((pane, i) => { pane.scrollTop = winScroll[i]; });
  app.querySelectorAll('.bar[data-width], .cmp-bar i[data-width]').forEach(bar => { bar.style.width = `${bar.dataset.width}%`; });
  fitDeskSide();
  if (state.modal) app.querySelector('.modal-close')?.focus();
}

// --win-head (alto de la cabecera de siempre) se vuelve a medir cuando carga el CSS o las fuentes, no solo al pintar:
// lo usan la ventana única y la barra fija de Pronósticos.
let headerWatcher = null;
function watchHeaderHeight(header) {
  const set = () => app.style.setProperty('--win-head', `${header.offsetHeight}px`);
  set();
  headerWatcher?.disconnect();
  if (typeof ResizeObserver === 'undefined') return;
  headerWatcher = new ResizeObserver(set);
  headerWatcher.observe(header);
}

// La lista de partidos solo queda fija si cabe entera bajo la cabecera.
function fitDeskSide() {
  const head = app.querySelector('.site-header');
  if (head) app.style.setProperty('--win-head', `${head.offsetHeight}px`);
  const side = app.querySelector('.desk-side');
  const header = app.querySelector('.site-header');
  if (header) watchHeaderHeight(header);
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
  const button = event.target.closest('button, a[data-sport]');
  if(button?.matches('a[data-sport]'))event.preventDefault();
  if (!button) {
    if (event.target.classList.contains('modal-backdrop')) closeModal();
    return;
  }
  const data = button.dataset;
  if (membershipUI.handleClick(button)) return;
  if (data.scrollTo) { app.querySelector(`#${CSS.escape(data.scrollTo)}`)?.scrollIntoView({behavior:window.matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth',block:'start'}); return; }
  if (data.sport) { const fromHeader=Boolean(button.closest('.sport-nav'));state.sport=data.sport; state.homeSearch=''; if(fromHeader&&state.route==='partidos'){state.winDay=0;state.winDayPinned=false;state.winEvent='';state.winLastEvent=null;state.winPane='pron';render();app.querySelector(`.sport-nav [data-sport="${data.sport}"]`)?.focus();return;} if(!['inicio','picks'].includes(state.route))navigate('picks');else rerenderKeepingFocus(`[data-sport="${data.sport}"]`);if(fromHeader)app.querySelector('#pronosticos-hoy')?.scrollIntoView({block:'start',behavior:'instant'}); return; }
  if (data.resultSport) {state.resultSport=data.resultSport;rerenderKeepingFocus(`[data-result-sport="${data.resultSport}"]`);return;}
  if (data.sportEvent) {const [sport]=data.sportEvent.split(':');const found=ensureSport(sport).events?.find(e=>`${e.sport}:${e.id}`===data.sportEvent);const day=found?new Date(found.start):new Date();day.setHours(0,0,0,0);const current=new Date();current.setHours(0,0,0,0);state.sport=sport;state.winEvent=data.sportEvent;state.winDay=Math.max(-3,Math.min(3,Math.round((day-current)/86400000)));state.winDayPinned=true;state.winSportTab='resumen';state.winPane='pron';navigate('partidos');return;}
  if (data.sportMarket) {state.sportMarket=data.sportMarket;rerenderKeepingFocus(`[data-sport-market="${data.sportMarket}"]`);return;}
  if (data.availableDay) {const target=new Date(`${data.availableDay}T12:00:00`);const current=new Date();current.setHours(12,0,0,0);state.dayOffset=Math.round((target-current)/86400000);state.homeStatus='todos';render();return;}
  if (data.realMatch) {
    const game=[...realHomeCache.values()].flatMap(e=>e.data?.agenda||[]).find(g=>g.match_id===data.realMatch);
    if(game){ const date=new Date(game.kickoff_utc); date.setHours(0,0,0,0); const current=new Date(); current.setHours(0,0,0,0); state.dayOffset=Math.round((date-current)/86400000); }
    state.statsDay = STATS_DAYS.includes(state.dayOffset) ? state.dayOffset : 0; state.statsLeague = 'Todas'; state.statsMatch = data.realMatch; state.statsTab = 'resumen'; state.winPane = 'pron'; state.sport = 'futbol'; navigate('partidos'); return;
  }
  if (data.action === 'refresh-public') { refreshPublicData(); return; }
  if (data.action === 'cv-scroll') { const target = app.querySelector(`#${CSS.escape(data.target)}`); target?.scrollIntoView({ behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth', block: 'start' }); target?.focus({ preventScroll: true }); return; }
  if (data.route) { if (data.homeMarketMode) { state.deskMode = data.homeMarketMode; state.deskDay = state.dayOffset; state.deskSort = { key: 'edge', dir: 'desc' }; } if (data.route === 'acceso') { state.authReturn = 'cuenta'; state.authMode = 'login'; state.authMessage = ''; } navigate(data.route); return; }
  if (data.homeStatus) { state.homeStatus = data.homeStatus; rerenderKeepingFocus(`[data-home-status="${data.homeStatus}"]`); return; }
  if (data.homeLeague) { state.homeLeague = data.homeLeague; rerenderKeepingFocus(`[data-home-league="${CSS.escape(data.homeLeague)}"]`); return; }
  if (data.action === 'clear-home') { state.homeSearch = ''; state.homeStatus = 'todos'; state.homeLeague = 'Todas'; state.homeSort = 'hora'; rerenderKeepingFocus('[data-action="clear-home"]'); return; }
  if (data.openFicha) {
    const game = ensureRealHome(0).data?.agenda.find(g=>g.match_id===data.openFicha);
    const date = game ? new Date(game.kickoff_utc) : new Date(); date.setHours(0,0,0,0);
    const current = new Date(); current.setHours(0,0,0,0);
    state.statsDay = Math.round((date-current)/86400000); state.statsLeague = 'Todas'; state.statsMatch = data.openFicha; state.statsTab = 'resumen'; navigate('partidos'); return;
  }
  if (data.winEvent) { state.winEvent = data.winEvent; rerenderKeepingFocus(`[data-win-event="${CSS.escape(data.winEvent)}"]`); return; }
  if (data.winEvStep) { const next = state.winEvList[state.winEvList.indexOf(state.winEvent) + Number(data.winEvStep)]; if (next) { state.winEvent = next; rerenderKeepingFocus(`[data-win-ev-step="${data.winEvStep}"]`); } return; }
  if (data.winDay !== undefined && data.winDay !== '') { state.winDay = Number(data.winDay); state.winDayPinned = true; state.winEvent = ''; rerenderKeepingFocus('.win-day strong'); return; }
  if (data.winSportTab) { state.winSportTab = data.winSportTab; rerenderKeepingFocus(`[data-win-sport-tab="${data.winSportTab}"]`); return; }
  if (data.winFormScope) { state.winFormScope = data.winFormScope; rerenderKeepingFocus(`[data-win-form-scope="${data.winFormScope}"]`); return; }
  if (data.winSportFam) { state.winSportFam = data.winSportFam; state.winAll = false; rerenderKeepingFocus(`[data-win-sport-fam="${CSS.escape(data.winSportFam)}"]`); return; }
  if (data.winAll) { state.winAll = !state.winAll; rerenderKeepingFocus('[data-win-all]'); return; }
  if (data.winPane) { state.winPane = data.winPane; rerenderKeepingFocus(`[data-win-pane="${data.winPane}"]`); return; }
  if (data.winFam) { state.winFam = data.winFam; rerenderKeepingFocus(`[data-win-fam="${CSS.escape(data.winFam)}"]`); return; }
  if (data.winStep) { const next = state.winList[state.winList.indexOf(state.statsMatch) + Number(data.winStep)]; if (next) { state.statsMatch = next; rerenderKeepingFocus(`[data-win-step="${data.winStep}"]`); } return; }
  if (data.action === 'retry-real') { realMatchCache.delete(state.statsMatch); render(); return; }
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
  if (target.id === 'win-event-select') { state.winEvent = target.value; rerenderKeepingFocus('#win-event-select'); return; }
  if (target.id === 'win-select') { state.statsMatch = target.value; rerenderKeepingFocus('#win-select'); return; }
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
  const route = canonicalRoute(location.hash.slice(1));
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

const initial = canonicalRoute(location.hash.slice(1));
if (validRoute(initial)) state.route = initial;
window.addEventListener('resize',()=>{if(state.mobileMenuOpen && window.matchMedia('(min-width:761px)').matches){state.mobileMenuOpen=false;render();}});
membershipUI.handleReturn();
render();
membershipUI.restoreSession();
membershipUI.loadPlans();
membershipUI.loadPaymentConfig();
function syncPublicAuth() {
  const s = state.session;
  const key = s ? `${s.account?.account_id ?? s.account?.email ?? 'cuenta'}:${s.plus ? 'vip' : 'gratis'}` : 'visitante';
  if (key === publicAuthKey) return;
  publicAuthKey = key;
  refreshPublicData();
}
async function refreshPublicData() {
  const request = ++publicRequest;
  publicData = null;
  if(request>1){ realGeneration++; realHomeCache.clear(); realMatchCache.clear(); sportsCache.clear(); tennisStatsCache.clear(); nbaStatsCache.clear(); resultsCache=null; }
  render();
  const result = await loadPublicData(publicFetch);
  if (request !== publicRequest) return;
  publicData = result;
  if (!state.modal && !state.drawer && !state.mobileMenuOpen) render();
}
refreshPublicData();

// Actualiza las publicaciones reales cuando la web está visible, sin alterar motores.
setInterval(()=>{
  if(document.visibilityState==='visible' && !state.modal && !state.drawer && !state.authBusy
      && !['acceso','checkout','cuenta'].includes(state.route)
      && !document.activeElement?.matches('input,textarea,select,[contenteditable="true"]'))refreshPublicData();
},90000);
