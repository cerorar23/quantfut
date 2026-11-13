import test from 'node:test';
import assert from 'node:assert/strict';
import { createSportWindow } from './sports-window.js';
import { createHubViews } from './ergonomic-views.js';
import { loadSportWeb, loadPartidoContrato, bloquesDesdeContrato, eventosDesdeContrato, familiasDeEvento, withDetalle, esDeporteGenerico, nbaCode, featuredModelMarket } from './sports-data.js';
import { normalizarDeportes, normalizarPantallas, pantallaResuelta, datosAviso, nombreDeporte, nombreFamilia, deportesNavegacion, fijarDeportes, fijarPaginaDeporte,
  deporteBoot, deporteDeUrl, routeFromLocation, DEPORTES_RESPALDO } from './rutas.js';

// Fase 4 · 4.4: un deporte del catálogo que la web no conoce (`golf`, de prueba) se ve con lista, detalle, familias y bloques SIN tocar `frontend/`.
const SELLO = 'b'.repeat(64);
const DIA = new Date('2026-10-30T18:00:00Z');
const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);
const at = path => ({ pathname: path, hash: '', search: '' });
const respuesta = (cuerpo, status = 200) => ({ ok: status < 400, status, json: async () => cuerpo });
const sinAviso = async fn => { const original = console.warn, avisos = []; console.warn = (...a) => avisos.push(a.join(' ')); try { return [await fn(), avisos]; } finally { console.warn = original; } };

// ── contrato de golf ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
const merc = (id, label, seleccion, prob, familia, extra = {}) => ({ id, label, selection: seleccion, probability: prob, sealed_at: '2026-10-29T20:00:00Z', eligible: true, market: id, family: familia,
  line: null, player: null, player_id: null, price: null, reference: 'Probabilidad del motor', outcome: null, push_probability: null, principal: false, ...extra });
const GANADOR = merc('winner', 'Ganador del torneo', 'Scottie Scheffler', 0.82, 'ganador', { principal: true, outcome: 'win', price: 1.31, reference: 'Pinnacle' });
const TOP5 = merc('top5', 'Top 5', 'Rory McIlroy', 0.64, 'ganador');
const RONDA = merc('r1', 'Golpes en la ronda 1', 'Menos de 68.5', 0.55, 'rondas', { line: 68.5 });
const RARO = merc('raro', 'Hoyo en uno', 'Sí', 0.04 + 0.01, 'inventada');
const EVENTO = (id, extra = {}) => ({ id, sport: 'golf', home: `Scottie Scheffler <img src=x onerror=alert(1)>`, away: 'Rory McIlroy', league: 'Masters <i>Augusta</i>', start: '2026-10-30T10:00:00Z', status: 'finished',
  seal: SELLO, sealed_at: '2026-10-29T20:00:00Z', planned_seal: null, score: '-12 / -9', surface: null, bloqueados: 0, imagenes: { home: '/web/imagenes/golf/ss.png', away: 'https://otro.example/x.png' },
  markets: [GANADOR], destacado: 'winner', team_projection: null, ...extra });
const CARTELERA = { contrato: 1, deporte: 'golf', desde: '2026-10-27', dias: 7, eventos: [EVENTO('g-1'), EVENTO('g-2', { home: 'Jon Rahm', away: 'Xander Schauffele', status: 'scheduled', start: '2026-10-30T14:00:00Z', score: null, destacado: null, markets: [] })] };
const BLOQUES = [
  { id: 'rondas', tipo: 'tabla', titulo: 'Rondas jugadas', columnas: ['Ronda', 'Golpes'], filas: [['R1', 66], ['<script>alert(1)</script>', null]] },
  { id: 'forma', tipo: 'barras', titulo: 'Forma reciente', items: [{ etiqueta: 'Top 10 en el año', valor: 0.7, nota: '12 torneos' }, { etiqueta: 'Cortes pasados', valor: 0.95 }] },
  { id: 'datos', tipo: 'pares', titulo: 'Ficha', items: [{ etiqueta: 'País', valor: 'EE. UU.' }, { etiqueta: 'Ranking', valor: 1 }, { etiqueta: 'Edad', valor: null }] },
  { id: 'nota', tipo: 'texto', titulo: 'Nota del campo', cuerpo: 'Viento fuerte en la ronda final.' },
  { id: 'futuro', tipo: 'mapa', titulo: 'Tipo que esta web no conoce', puntos: [1, 2] },
  { id: 'roto', tipo: 'barras', titulo: 'Valor fuera de rango', items: [{ etiqueta: 'x', valor: 2 }] },
];
const PARTIDO = { contrato: 1, deporte: 'golf', evento: EVENTO('g-1', { markets: [GANADOR, TOP5, RONDA, RARO] }), bloques: BLOQUES };
const MERCADOS = { contrato: 1, deporte: 'golf', evento_id: 'g-1', familias: [{ id: 'ganador', mercados: [GANADOR, TOP5] }, { id: 'rondas', mercados: [RONDA] }, { id: 'otros', mercados: [RARO] }] };
const CATALOGO = normalizarDeportes({ deportes: [
  { id: 'futbol', orden: 1, estado: 'on', nombre: { es: 'Fútbol' }, slug: { es: 'futbol' } },
  { id: 'nba', orden: 2, estado: 'on', nombre: { es: 'NBA' }, slug: { es: 'nba' } },
  { id: 'tenis', orden: 3, estado: 'on', nombre: { es: 'Tenis' }, slug: { es: 'tenis' } },
  { id: 'golf', orden: 4, estado: 'on', nombre: { es: 'Golf', en: 'Golf', pt: 'Golfe' }, slug: { es: 'golf', en: 'golf', pt: 'golfe' }, familias: [
    { id: 'ganador', orden: 1, nombre: { es: 'Ganador', en: 'Winner', pt: 'Vencedor' } }, { id: 'rondas', orden: 2, nombre: { es: 'Rondas', en: 'Rounds', pt: 'Rodadas' } }] },
] });
const GOLF = CATALOGO.find(d => d.id === 'golf');

function fetcher(rutas, log = []) {
  return async (url, opciones) => {
    log.push(String(url));
    const clave = Object.keys(rutas).find(k => String(url).startsWith(k));
    const valor = clave ? rutas[clave] : { status: 404 };
    if (typeof valor === 'function') return valor(url, opciones);
    return valor.status ? respuesta({}, valor.status) : respuesta(valor);
  };
}
const RUTAS = { '/deportes/v1/golf/cartelera': CARTELERA, '/deportes/v1/golf/partido/g-1/mercados': MERCADOS, '/deportes/v1/golf/partido/g-1?': PARTIDO };

// ── ventana ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
async function ventana({ lang = 'es', pantallas = null, estado = {}, lista = null, detalle = undefined, peticiones = [] } = {}) {
  const events = lista ?? eventosDesdeContrato(CARTELERA, 'golf');
  const entry = estado.entry ?? { status: 'ready', events };
  const det = detalle !== undefined ? detalle : await loadPartidoContrato('golf', 'g-1', lang, fetcher(RUTAS, peticiones));
  const st = { sport: 'golf', winDay: 0, winDayPinned: true, winEvent: 'golf:g-1', winLastEvent: 'golf:g-1', winEvList: [], winSportFam: '', winAll: false, winPane: 'pron', ...estado.state };
  const pedidas = { detalle: [], tenis: 0, nba: 0 };
  const w = createSportWindow({ state: st, esc, badge: (t, k) => `<i data-k="${k ?? ''}">${t}</i>`, fmtPct: p => `${(p * 100).toFixed(1)}%`, fmtOdds: o => Number(o).toFixed(2), realDate: String, realTime: String,
    dateFmt: d => (d instanceof Date ? d.toISOString() : String(d)), addDays: () => DIA, localDay: d => new Date(d).toISOString().slice(0, 10), dayLabel: () => 'Hoy',
    ensureSport: () => entry, ensureTennisStats: () => { pedidas.tenis++; return { status: 'loading' }; }, ensureNbaStats: () => { pedidas.nba++; return { status: 'loading' }; },
    ensureNbaMarkets: () => { pedidas.nba++; return { status: 'loading', markets: [], projections: [] }; }, featuredModelMarket, ensureImages: () => ({ status: 'ready', nba: {}, tenis: {} }), nbaCode,
    ensureDetalle: (sport, id) => { pedidas.detalle.push(`${sport}:${id}`); return det; },
    generico: () => ({ nombre: nombreDeporte(GOLF, lang), orden: GOLF.familias.map(f => f.id), nombreFamilia: f => nombreFamilia(GOLF, f, lang),
      pantallaDeporte: pantallaResuelta(pantallas, 'deporte', 'golf'), pantallaPartido: pantallaResuelta(pantallas, 'partido', 'golf') }),
    aviso: b => datosAviso(b, lang) });
  return { html: w.view(), pedidas, st };
}

test('1 · la cartelera de un deporte nuevo se pide al contrato y NUNCA a los endpoints de NBA o tenis', async () => {
  assert.ok(esDeporteGenerico('golf') && !esDeporteGenerico('nba') && !esDeporteGenerico('futbol') && !esDeporteGenerico('Golf') && !esDeporteGenerico('../x'));
  const log = [];
  const r = await loadSportWeb('golf', fetcher(RUTAS, log), new Date(2026, 9, 30, 12));
  assert.equal(r.status, 'ready');
  assert.equal(log.length, 1);
  assert.match(log[0], /^\/deportes\/v1\/golf\/cartelera\?cliente=web&contrato=1&desde=2026-10-27&dias=7&tz=-?\d+$/);
  assert.ok(!log.some(u => /web\/deportes|nba\/v1/.test(u)));
  const [g1, g2] = r.events;
  assert.equal(g1.generico, true);
  assert.equal(g1.sport, 'golf');
  assert.equal(g1.home_img, '/web/imagenes/golf/ss.png');     // solo rutas del propio servidor
  assert.equal(g1.away_img, null);
  assert.equal(g1.markets[0].family, 'ganador');
  assert.equal(g1.markets[0].book, 'Pinnacle');                  // cuota con su origen → cuota de la casa; sin origen quedaría la del modelo
  assert.equal(g2.markets.length, 0);
});

test('1b · si el contrato falla el deporte nuevo queda en `error` y no se consulta otro cargador', async () => {
  for (const rutas of [{}, { '/deportes/v1/golf/cartelera': { status: 503 } }, { '/deportes/v1/golf/cartelera': { contrato: 1, deporte: 'otro', eventos: [] } }]) {
    const log = [];
    const [r, avisos] = await sinAviso(() => loadSportWeb('golf', fetcher(rutas, log), new Date(2026, 9, 30, 12)));
    assert.deepEqual(r, { status: 'error', events: [] });
    assert.equal(log.length, 1);
    assert.equal(avisos.length, 1);
  }
});

test('2 · detalle: evento completo, bloques en el idioma de la página y familias del catálogo con `otros` al final', async () => {
  const log = [];
  const [d, avisos] = await sinAviso(() => loadPartidoContrato('golf', 'g-1', 'pt', fetcher(RUTAS, log)));
  assert.deepEqual(log.sort(), ['/deportes/v1/golf/partido/g-1/mercados?cliente=web', '/deportes/v1/golf/partido/g-1?cliente=web&lang=pt']);
  assert.equal(d.status, 'ready');
  assert.deepEqual(d.event.familias.map(f => [f.id, f.markets.map(m => m.id)]), [['ganador', ['winner', 'top5']], ['rondas', ['r1']], ['otros', ['raro']]]);
  assert.equal(d.event.familias[0].markets[0], d.event.markets[0]);       // las mismas instancias: la fila destacada se reconoce por identidad
  assert.deepEqual(d.event.bloques.map(b => b.id), ['rondas', 'forma', 'datos', 'nota']);
  assert.equal(avisos.length, 1);                                          // `roto` avisa; `futuro` (tipo desconocido) NO
  const [, otro] = await sinAviso(() => loadPartidoContrato('golf', 'g-1', 'fr', fetcher(RUTAS, [])));
  assert.equal(otro.length, 1);
  const url = []; await loadPartidoContrato('golf', 'g-1', 'fr', fetcher(RUTAS, url));
  assert.ok(url.some(u => u.endsWith('lang=es')));                         // un idioma que la web no sirve sale como es
});

test('2b · sin `/mercados` el detalle agrupa por la familia de cada mercado; sin `/partido` es un error', async () => {
  const [d] = await sinAviso(() => loadPartidoContrato('golf', 'g-1', 'es', fetcher({ ...RUTAS, '/deportes/v1/golf/partido/g-1/mercados': { status: 500 } })));
  assert.equal(d.status, 'ready');
  assert.equal(d.event.familias, null);
  assert.deepEqual(familiasDeEvento(d.event, ['ganador', 'rondas']).map(f => f.id), ['ganador', 'rondas', 'inventada']);
  assert.deepEqual(familiasDeEvento({ markets: [{ id: 'a', family: 'otros' }, { id: 'b', family: 'z' }, { id: 'c', family: 'ganador' }] }, ['ganador']).map(f => f.id), ['ganador', 'z', 'otros']);
  const [e] = await sinAviso(() => loadPartidoContrato('golf', 'g-1', 'es', fetcher({ '/deportes/v1/golf/partido/g-1?': { status: 404 } })));
  assert.deepEqual(e, { status: 'error', event: null });
  const [roto] = await sinAviso(() => loadPartidoContrato('golf', 'g-1', 'es', fetcher({ '/deportes/v1/golf/partido/g-1?': () => { throw new Error('sin red'); } })));
  assert.equal(roto.status, 'error');
  assert.equal(withDetalle({ generico: true, markets_status: undefined }, { status: 'loading' }).markets_status, 'loading');
});

test('3 · bloques: cada tipo con su componente, tipos desconocidos ignorados sin ruido, mal formados con un aviso', async () => {
  const [bloques, avisos] = await sinAviso(async () => bloquesDesdeContrato([...BLOQUES, null, 'x', { tipo: 'texto' }, { id: 'nota', tipo: 'texto', titulo: 't', cuerpo: 'repetido' }, { id: 'ancho', tipo: 'tabla', titulo: 't', columnas: ['a'], filas: [[1, 2]] }]));
  assert.deepEqual(bloques.map(b => b.id), ['rondas', 'forma', 'datos', 'nota']);
  assert.equal(avisos.length, 4);                                                // roto, sin id, id repetido y fila de otro ancho; `futuro`, null y 'x' no
  assert.ok(avisos.every(a => a.length < 90));
  assert.deepEqual(bloquesDesdeContrato(undefined), []);
  const { html } = await ventana();
  const panelStats = html.split('id="win-pane-stats"')[1];
  assert.ok(panelStats.includes('<table class="cyber-table cyber-table--compact">') && panelStats.includes('<th scope="col" class="n">Golpes</th>'));    // tabla → win-table
  assert.ok(panelStats.includes('<div class="win-bar">') && panelStats.includes('12 torneos') && panelStats.includes('data-value="95.0"'));                   // barras → win-bar
  assert.ok(panelStats.includes('<div class="win-kv"><span>País</span><strong>EE. UU.</strong></div>') && panelStats.includes('<strong>—</strong>'));         // pares → win-kv
  assert.ok(panelStats.includes('<div class="cyber-alert" role="note"><p class="cyber-alert__title">Nota del campo</p><p>Viento fuerte en la ronda final.</p></div>'));  // texto → cyber-alert
  assert.ok(!panelStats.includes('Tipo que esta web no conoce') && !panelStats.includes('Valor fuera de rango'));
});

test('4 · un texto del servidor se escapa siempre (equipos, torneo, bloques)', async () => {
  const { html } = await ventana();
  assert.ok(!html.includes('<script>') && !html.includes('<img src=x') && !html.includes('<i>Augusta'));
  assert.ok(html.includes('&lt;script&gt;alert(1)&lt;/script&gt;'));
  assert.ok(html.includes('Scottie Scheffler &lt;img src=x onerror=alert(1)&gt;'));
});

test('5 · deporte nuevo completo: lista, detalle, mercados por familia (nombre del catálogo) y nada de lo de NBA o tenis', async () => {
  const peticiones = [];
  const { html, pedidas } = await ventana({ lang: 'en', peticiones });
  assert.ok(html.includes('aria-label="Golf: eventos del día"') && html.includes('<b>2</b>'));                                      // lista del día
  assert.ok(html.includes('<img class="win-crest is-logo" src="/web/imagenes/golf/ss.png"') && html.includes('class="win-crest is-initial"'));
  assert.ok(html.includes('data-win-event="golf:g-1"') && html.includes('data-win-event="golf:g-2"'));
  const pron = html.split('id="win-pane-pron"')[1].split('id="win-pane-stats"')[0];
  assert.ok(pron.includes('PRONÓSTICO DESTACADO') && pron.includes('Scottie Scheffler') && pron.includes('Cuota de la casa') && pron.includes('Pinnacle'));   // destacado de la tarjeta del servidor
  assert.ok(pron.includes('data-win-sport-fam="ganador"') && pron.includes('>Winner</button>') && pron.includes('>Rounds</button>'));  // nombres en inglés
  assert.ok(pron.indexOf('data-win-sport-fam="rondas"') < pron.indexOf('data-win-sport-fam="otros"') && pron.includes('>Otros</button>'));  // `otros` al final
  assert.ok(pron.includes('class="win-feat"') && pron.includes('Top 5'));                                                                // la fila destacada y la segunda
  assert.ok(!html.includes('Proyecciones') && !html.includes('PUNTOS ESPERADOS') && !html.includes('win-tabs-wrap') && !html.includes('SUPERFICIE'));
  assert.deepEqual([pedidas.tenis, pedidas.nba], [0, 0]);                                                                              // ni estadísticas de tenis ni de NBA
  assert.deepEqual(pedidas.detalle, ['golf:g-1']);
  assert.ok(peticiones.every(u => u.startsWith('/deportes/v1/golf/')));
  const rondas = await ventana({ lang: 'pt', estado: { state: { winSportFam: 'rondas' } } });
  assert.ok(rondas.html.includes('Menos de 68.5') && rondas.html.includes('>Vencedor</button>'));
  const otros = await ventana({ estado: { state: { winSportFam: 'otros' } } });
  assert.ok(otros.html.includes('Hoyo en uno'));
  assert.ok(html.includes('Boston') === false && html.includes('data-win-sport-tab') === false);
});

test('5b · mientras carga el detalle se ve lo de la lista; si falla, avisa con «Reintentar»', async () => {
  const cargando = await ventana({ detalle: { status: 'loading', event: null } });
  assert.ok(cargando.html.includes('Cargando mercados del partido…') && cargando.html.includes('Consultando las estadísticas del partido…'));
  assert.ok(cargando.html.includes('PRONÓSTICO DESTACADO') && cargando.html.includes('Scottie Scheffler'));
  const error = await ventana({ detalle: { status: 'error', event: null } });
  assert.ok(error.html.includes('No se pudieron cargar los mercados.') && error.html.includes('data-action="refresh-public"'));
  const sinBloques = await ventana({ detalle: { status: 'ready', event: { ...eventosDesdeContrato(CARTELERA, 'golf')[0], familias: null, bloques: [] } } });
  assert.ok(sinBloques.html.includes('Este partido no tiene estadísticas publicadas.'));
});

test('6 · fallo del contrato o lista vacía: un empty-state con «Volver a consultar», nunca una pantalla en blanco', async () => {
  const fallo = await ventana({ estado: { entry: { status: 'error', events: [] } } });
  assert.ok(fallo.html.includes('class="empty-state"') && fallo.html.includes('Volver a consultar ↻') && fallo.html.includes('data-action="refresh-public"'));
  const vacio = await ventana({ lista: [] });
  assert.ok(vacio.html.includes('Sin eventos este día') && vacio.html.includes('class="empty-state"'));
  const cargando = await ventana({ estado: { entry: { status: 'loading', events: [] } } });
  assert.ok(cargando.html.includes('Cargando eventos…'));
  assert.equal(fallo.pedidas.detalle.length, 0);
});

// ── definición de pantallas ──────────────────────────────────────────────────────────────────────────────────────────────────────────────
const sec = (id, seccion, visible = true) => ({ id, tipo: 'seccion', seccion, visible, params: {}, build_min_app: null });
const aviso = (id, texto, tono = 'info', extra = {}) => ({ id, tipo: 'aviso', visible: true, params: { texto, tono, ...extra }, build_min_app: null });

test('7 · normalizarPantallas: ausente = null; lo desconocido se ignora; sin secciones visibles equivale a no tener definición', () => {
  assert.equal(normalizarPantallas({}), null);
  assert.equal(normalizarPantallas({ pantallas: null }), null);
  assert.equal(normalizarPantallas({ pantallas: [] }), null);
  const p = normalizarPantallas({ pantallas: {
    deporte: { '*': [sec('a', 'partidos'), sec('b', 'inventada'), { id: 'c', tipo: 'mapa', visible: true }, sec('d', 'dias', false), sec('e', 'partidos'), aviso('f', { es: 'Hola' }), aviso('g', 'sin objeto'), { tipo: 'vip', id: 'MAL ID' }],
      golf: [sec('x', 'dias', false)], 'NBA!': [sec('y', 'dias')] },
    partido: { golf: [sec('h', 'cabecera'), sec('i', 'h2h'), { id: 'v', tipo: 'vip', visible: true, params: { nuevo: 1 } }] },
    inventada: { '*': [sec('z', 'dias')] } } });
  assert.deepEqual(p.deporte['*'].map(b => b.id), ['a', 'd', 'f']);        // `b` (sección), `c` (tipo), `e` (repetida), `g` (sin texto), id mal formado: fuera
  assert.equal(p.deporte.golf, undefined);                                 // sin secciones visibles: no hay definición para golf
  assert.equal(p.deporte['NBA!'], undefined);
  assert.ok(!('inventada' in p));
  assert.deepEqual(p.partido.golf.map(b => b.id), ['h', 'i', 'v']);
});

test('7b · la definición del deporte concreto gana sobre «*»; sin ninguna, null', () => {
  const p = normalizarPantallas({ pantallas: { deporte: { '*': [sec('a', 'dias')], golf: [sec('b', 'partidos')] } } });
  assert.equal(pantallaResuelta(p, 'deporte', 'golf')[0].id, 'b');
  assert.equal(pantallaResuelta(p, 'deporte', 'rugby')[0].id, 'a');
  assert.equal(pantallaResuelta(p, 'partido', 'golf'), null);
  assert.equal(pantallaResuelta(null, 'deporte', 'golf'), null);
  const sola = normalizarPantallas({ pantallas: { deporte: { golf: [sec('x', 'dias', false)], '*': [sec('a', 'resumen')] } } });
  assert.equal(pantallaResuelta(sola, 'deporte', 'golf')[0].id, 'a');       // la de golf no sirve (nada visible): cae a «*»
});

test('7c · datosAviso: idioma con caída a es, tono conocido y solo enlaces relativos', () => {
  const b = aviso('a', { es: 'Hola', en: 'Hello' }, 'peligro', { enlace: '/planes/' });
  assert.deepEqual(datosAviso(b, 'en'), { texto: 'Hello', tono: 'peligro', enlace: '/planes/' });
  assert.equal(datosAviso(b, 'pt').texto, 'Hola');
  assert.equal(datosAviso(aviso('a', { es: 'x' }, 'raro', { enlace: '//malo.example' }), 'es').tono, 'info');
  assert.equal(datosAviso(aviso('a', { es: 'x' }, 'info', { enlace: '//malo.example' }), 'es').enlace, null);
  assert.equal(datosAviso(aviso('a', { es: 'x' }, 'info', { enlace: 'https://malo.example' }), 'es').enlace, null);
  assert.equal(datosAviso(aviso('a', { en: '   ' }), 'en'), null);
});

test('8 · sin definición el orden es el de hoy; con definición se reordena, se oculta y se insertan avisos y la llamada VIP', async () => {
  const sin = (await ventana()).html;
  const orden = html => ['win-strip', 'win-work'].map(c => html.indexOf(`class="${c}"`));
  assert.ok(orden(sin)[0] < orden(sin)[1] && !sin.includes('win-pk-featured') && !sin.includes('cyber-alert--') && !sin.includes('win-vipbar'));
  assert.ok(!sin.includes('style="grid-template-columns'));

  const p = normalizarPantallas({ pantallas: {
    deporte: { golf: [aviso('a1', { es: 'Aviso es', en: 'Notice en' }, 'aviso', { enlace: '/planes/' }), sec('s1', 'destacado'), sec('s2', 'partidos'), sec('s3', 'dias'), sec('s4', 'resumen', false), { id: 'v1', tipo: 'vip', visible: true, params: {} }] },
    partido: { '*': [sec('p1', 'mercados'), aviso('a2', { es: '¡Peligro!' }, 'peligro'), sec('p2', 'pronostico', false), sec('p3', 'sello'), sec('p4', 'contenido', false), sec('p5', 'h2h')] } } });
  const { html } = await ventana({ lang: 'en', pantallas: p });
  assert.ok(html.indexOf('cyber-alert--warning') < html.indexOf('win-pk-featured') && html.indexOf('win-pk-featured') < html.indexOf('class="win-work"'));
  assert.ok(html.indexOf('class="win-work"') < html.indexOf('class="win-strip"') && html.indexOf('class="win-strip"') < html.indexOf('win-vipbar'));
  assert.ok(html.includes('Notice en') && html.includes('href="/planes/"'));
  assert.ok(!html.includes('aria-label="Golf: eventos del día"'));             // «resumen» oculto
  assert.ok(html.includes('data-route="planes"') && html.includes('Acceso VIP'));
  const pron = html.split('id="win-pane-pron"')[1].split('id="win-pane-stats"')[0];
  const stats = html.split('id="win-pane-stats"')[1];
  assert.ok(pron.includes('aria-label="Mercados"') && pron.includes('¡Peligro!') && pron.includes('cyber-alert--error') && !pron.includes('PRONÓSTICO DESTACADO'));   // pronóstico oculto
  assert.ok(stats.includes('REGISTRO DEL ANÁLISIS') && !stats.includes('Rondas jugadas'));                                                                    // contenido oculto
});

test('8b · partidos oculto: sin lista lateral y a todo el ancho; cabecera oculta: queda solo el selector', async () => {
  const p = normalizarPantallas({ pantallas: { deporte: { '*': [sec('a', 'dias')] }, partido: { '*': [sec('b', 'cabecera', false), sec('c', 'mercados')] } } });
  const { html } = await ventana({ pantallas: p });
  assert.ok(!html.includes('class="win-rail"') && html.includes('<div class="win-work" style="grid-template-columns:minmax(0,1fr)">'));
  assert.ok(html.includes('class="win-picker"') && !html.includes('class="win-team"'));
  assert.ok(html.includes('aria-label="Mercados"'));
});

test('8c · el aviso con texto en pt cae a es si no hay traducción y un aviso sin texto no se pinta', async () => {
  const p = normalizarPantallas({ pantallas: { deporte: { '*': [aviso('a', { es: 'Solo español' }), sec('b', 'partidos')] } } });
  assert.ok((await ventana({ lang: 'pt', pantallas: p })).html.includes('Solo español'));
  const q = normalizarPantallas({ pantallas: { deporte: { '*': [aviso('a', { en: 'x' }), sec('b', 'partidos')] } } });
  assert.ok(!(await ventana({ lang: 'pt', pantallas: q })).html.includes('<div class="cyber-alert" role="status">'));
});

// ── entrada ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
test('9 · abrir /golf/ arranca en la pantalla genérica aunque el catálogo aún no haya llegado', () => {
  fijarDeportes(DEPORTES_RESPALDO);
  fijarPaginaDeporte({}, at('/golf/'));
  assert.equal(deporteDeUrl(at('/golf/')), null);                                    // sin la marca del servidor, la web no inventa deportes
  fijarPaginaDeporte({ deporte: 'golf' }, at('/golf/'));
  assert.equal(deporteDeUrl(at('/golf/')), 'golf');
  assert.equal(routeFromLocation(at('/golf/'), () => false), 'partidos');
  assert.equal(deporteDeUrl(at('/pronosticos/')), null);                             // otra URL de un solo segmento no se confunde con golf
  assert.equal(routeFromLocation(at('/pronosticos/'), () => false), 'picks');
  assert.deepEqual(deporteBoot({ deporte: 'golf' }, at('/golf/')), { sport: 'golf', patch: { sport: 'golf', winEvent: '', winDay: 0 } });
  const hoy = new Date(2026, 9, 30, 12);
  const dentro = deporteBoot({ deporte: 'golf', evento: 'g-1', inicio: new Date(2026, 9, 29, 10).toISOString() }, at('/golf/'), hoy);
  assert.deepEqual(dentro.patch, { sport: 'golf', winEvent: 'golf:g-1', winDay: -1, winDayPinned: true, winSportTab: 'resumen', winPane: 'pron' });
  assert.equal(deporteBoot({ deporte: 'golf', evento: '<x>' }, at('/golf/')).patch.winEvent, '');
  assert.equal(deporteBoot({ deporte: 'golf' }, at('/nba/')), null);
  assert.equal(deporteBoot({ deporte: 'golf' }, at('/historial/')), null);
  assert.equal(deporteBoot({ deporte: 'nba', evento: 'abc' }, at('/nba/')).patch.winEvent, '');      // NBA y tenis siguen pidiendo ids numéricos
  fijarPaginaDeporte({}, at('/'));
});

test('9b · con el catálogo, un deporte nuevo se reconoce en es, en y pt (también por /en/ y /pt/)', () => {
  fijarDeportes(CATALOGO);
  for (const ruta of ['/golf/', '/en/golf/', '/pt/golfe/', '/golfe/torneo/', '/pt/golf/torneo/partido/']) assert.equal(deporteDeUrl(at(ruta)), 'golf', ruta);
  assert.equal(deporteDeUrl(at('/rugby/')), null);
  assert.deepEqual(deporteBoot({ deporte: 'golf', evento: 'g-9' }, at('/pt/golfe/')).patch.winEvent, 'golf:g-9');
  fijarDeportes(DEPORTES_RESPALDO);
});

// ── hub ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
function hub(sport = 'todos', { lista = [], estado = 'ready' } = {}) {
  const nav = deportesNavegacion(CATALOGO, 'es');
  const pedidos = [];
  const views = createHubViews({ state: { dayOffset: 0, sport, homeSearch: '', homeStatus: 'todos', resultSport: 'todos' }, esc, ensureHome: () => ({ status: 'ready', data: { agenda: [], alta_probabilidad: { proximos: [], vip: [] } } }),
    ensureSport: id => { pedidos.push(id); return id === 'golf' ? { status: estado, events: lista } : { status: 'ready', events: [] }; }, ensureResults: () => ({ status: 'ready', items: [], featured: [] }),
    ensureMatch: () => ({ status: 'error', data: null }), ensureImages: () => ({ status: 'ready', nba: {}, tenis: {} }), nbaCode, dayRail: () => '', plansPreview: () => '', sportList: () => nav,
    addDays: () => DIA, localDay: d => new Date(d).toISOString().slice(0, 10), dayLabel: () => 'Hoy', realDate: String, realTime: String, fmtOdds: o => Number(o).toFixed(2), fmtPct: p => `${(p * 100).toFixed(1)}%` });
  return { views, pedidos };
}

test('10 · el selector, las pestañas del hub y «Todos» incluyen el deporte nuevo con el nombre del catálogo', () => {
  const eventos = eventosDesdeContrato(CARTELERA, 'golf');
  const { views, pedidos } = hub('todos', { lista: eventos });
  const html = views.picks();
  assert.ok(html.includes('data-sport="golf"') && html.includes('<span>Golf</span><b class="win-pk-count">1</b>'));          // pestaña con su cuenta (el evento sin mercados no entra)
  assert.ok(html.includes('aria-label="Golf"') && html.includes('data-sport-event="golf:g-1"') && html.includes('Scottie Scheffler'));      // «Todos» agrupa golf
  assert.ok(!html.includes('<img src=x') && html.includes('&lt;img src=x onerror=alert(1)&gt;'));
  assert.ok(html.includes('src="/web/imagenes/golf/ss.png"'));
  assert.ok(pedidos.includes('golf'));
  const solo = hub('golf', { lista: eventos }).views.picks();
  assert.ok(solo.includes('data-sport-event="golf:g-1"') && solo.includes('cyber-tab--active'));
  const vacia = hub('golf', { lista: [] }).views.picks();
  assert.ok(vacia.includes('Sin pronósticos para esta búsqueda') && vacia.includes('Volver a consultar ↻'));
  const error = hub('golf', { estado: 'error' }).views.picks();
  assert.ok(error.includes('no se pudieron consultar los pronósticos') && error.includes('Reintentar'));
  assert.ok(!hub('todos', { lista: eventos }).views.history().includes('Scottie'));                                                   // el historial sigue siendo de fútbol, NBA y tenis
});

test('10b · en el hub un evento sin mercados no sale (ni con el candado de Plus); la ventana sí lo lista', () => {
  const eventos = eventosDesdeContrato(CARTELERA, 'golf');
  const html = hub('golf', { lista: eventos }).views.picks();
  assert.ok(html.includes('golf:g-1') && !html.includes('golf:g-2') && !html.includes('Contenido reservado'));
});

test('11 · con solo los tres deportes de siempre en la navegación el hub no pide nada más (mismas peticiones que antes)', () => {
  const pedidos = new Set();
  const sinGolf = createHubViews({ state: { dayOffset: 0, sport: 'todos', homeSearch: '', homeStatus: 'todos', resultSport: 'todos' }, esc, ensureHome: () => ({ status: 'ready', data: { agenda: [], alta_probabilidad: { proximos: [], vip: [] } } }),
    ensureSport: id => { pedidos.add(id); return { status: 'ready', events: [] }; }, ensureResults: () => ({ status: 'ready', items: [], featured: [] }),
    ensureMatch: () => ({ status: 'error', data: null }), ensureImages: () => ({ status: 'ready', nba: {}, tenis: {} }), nbaCode, dayRail: () => '', plansPreview: () => '',
    addDays: () => DIA, localDay: d => new Date(d).toISOString().slice(0, 10), dayLabel: () => 'Hoy', realDate: String, realTime: String, fmtOdds: String, fmtPct: String });
  sinGolf.picks(); sinGolf.home();
  assert.deepEqual([...pedidos].sort(), ['nba', 'tenis']);
  const conGolf = hub('todos');
  conGolf.views.picks();
  assert.deepEqual([...new Set(conGolf.pedidos)].sort(), ['golf', 'nba', 'tenis']);
});
