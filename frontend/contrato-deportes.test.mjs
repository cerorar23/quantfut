import test from 'node:test';
import assert from 'node:assert/strict';
import { nbaV2Events, tennisEvents, loadSport, CONTRATO_WEB, ventanaContrato, eventoDesdeContrato, eventosDesdeContrato, loadSportContrato, loadSportWeb } from './sports-data.js';

const SELLO = 'a'.repeat(64);
const NOW = new Date(2026, 10, 5, 12);               // 5-nov-2026 12:00, hora local del que corre la prueba

// ── fixtures: los mismos partidos en la forma de /nba/v1/cartelera (cargador actual) y en la del contrato ────────────────
const game = (id, fecha, inicio, resultado, pick) => ({ id, fecha, local: { codigo: 'BOS', nombre: 'Boston Celtics' }, visitante: { codigo: 'NYK', nombre: 'New York Knicks' },
  inicio_utc: inicio, sello_previsto: new Date(Date.parse(inicio) - 36e5).toISOString(), resultado, pronostico: pick });
const pick = (p, sellado, mu = null) => ({ hash: SELLO, p_local: p, sellado_en: sellado, ...(mu ? { mu } : {}) });
const PARTIDOS = [
  game(1, '2026-11-02', '2026-11-03T00:00:00Z', { local: 110, visitante: 100 }, pick(0.7, '2026-11-02T22:00:00Z')),        // acertado
  game(2, '2026-11-03', '2026-11-04T00:00:00Z', { local: 90, visitante: 99 }, pick(0.4, '2026-11-03T22:00:00Z')),         // visitante, acertado
  game(3, '2026-11-04', '2026-11-05T00:00:00Z', null, null),                                                              // sin pronóstico, aún sin resultado
  game(4, '2026-11-04', '2026-11-05T01:00:00Z', null, pick(0.62, '2026-11-04T22:00:00Z')),                                 // con pronóstico, sin resultado (4 h pasadas)
];
const mercadoGanador = (id, seleccion, prob, outcome, sellado) => ({ id: `winner-${id}`, label: 'Ganador del partido', selection: seleccion, probability: prob, sealed_at: sellado,
  eligible: true, market: 'winner', family: 'winner', line: null, player: null, player_id: null, price: null, reference: 'Probabilidad estadística', outcome, push_probability: null });
const eventoNba = (id, inicio, estado, score, mercados, extra = {}) => ({ id: String(id), sport: 'nba', home: 'Boston Celtics', away: 'New York Knicks', league: 'NBA', start: inicio,
  status: estado, seal: SELLO, sealed_at: mercados[0]?.sealed_at ?? null, planned_seal: new Date(Date.parse(inicio) - 36e5).toISOString().replace('.000Z', 'Z'),
  score, surface: null, bloqueados: 0, imagenes: null, markets: mercados, destacado: mercados[0]?.id ?? null, ...extra });
const CONTRATO_NBA = { contrato: 1, deporte: 'nba', desde: '2026-11-02', dias: 7, eventos: [
  eventoNba(1, '2026-11-03T00:00:00Z', 'finished', '110 – 100', [mercadoGanador(1, 'Boston Celtics', 0.7, 'win', '2026-11-02T22:00:00Z')]),
  eventoNba(2, '2026-11-04T00:00:00Z', 'finished', '90 – 99', [mercadoGanador(2, 'New York Knicks', 0.6, 'win', '2026-11-03T22:00:00Z')]),
  { ...eventoNba(3, '2026-11-05T00:00:00Z', 'awaiting_result', null, []), seal: null, sealed_at: null },
  eventoNba(4, '2026-11-05T01:00:00Z', 'awaiting_result', null, [mercadoGanador(4, 'Boston Celtics', 0.62, null, '2026-11-04T22:00:00Z')]),
] };

const mercadoTenis = (id, label, seleccion, prob, outcome = null) => ({ id, label, selection: seleccion, probability: prob, sealed_at: '2026-11-05T06:00:00Z', eligible: true,
  market: id.replace(/-\d+$/, ''), family: id.replace(/-\d+$/, ''), line: null, player: null, player_id: null, price: null, reference: 'Probabilidad del motor', outcome, push_probability: null });
const FEED_TENIS = { state: 'ok', events: [
  { id: 't-1', sport: 'tenis', home: 'Ana Pérez', away: 'Bea Luz', start: '2026-11-05T10:00:00Z', league: 'WTA · Basilea', surface: 'Pista dura', sealed_at: '2026-11-05T06:00:00Z', seal: SELLO, status: 'finished',
    score: '6-4 6-3', actionable: false, destacado: { id: 'winner' }, markets: [
      { id: 'winner', label: 'Ganador del partido', selection: 'Ana Pérez', probability: 0.61, price: null, reference: 'Probabilidad del motor', outcome: 'win', push_probability: null },
      { id: 'games_total-1', label: 'Juegos totales', selection: 'Más de 18.5', probability: 0.55, price: null, reference: 'Probabilidad del motor', outcome: 'loss', push_probability: 0 }] },
  { id: 't-2', sport: 'tenis', home: 'Cy Ríos', away: 'Dan Sol', start: '2026-11-06T10:00:00Z', league: 'ATP · Basilea', surface: 'Pista dura', sealed_at: '2026-11-05T06:00:00Z', seal: SELLO, status: 'scheduled',
    score: null, actionable: false, destacado: null, markets: [
      { id: 'winner', label: 'Ganador del partido', selection: 'Dan Sol', probability: 0.58, price: null, reference: 'Probabilidad del motor', outcome: null, push_probability: null }] },
] };
const eventoTenis = (e, soloDestacado = false) => ({ id: e.id, sport: 'tenis', home: e.home, away: e.away, league: e.league, start: e.start, status: e.status, seal: e.seal, sealed_at: e.sealed_at,
  planned_seal: null, score: e.score, surface: e.surface, bloqueados: 0, imagenes: null, destacado: e.destacado?.id ?? null,
  markets: e.markets.filter(m => !soloDestacado || m.id === e.destacado?.id).map(m => ({ ...mercadoTenis(m.id, m.label, m.selection, m.probability, m.outcome), push_probability: m.push_probability })) });
const CONTRATO_TENIS = { contrato: 1, deporte: 'tenis', desde: '2026-11-02', dias: 7, eventos: FEED_TENIS.events.map(e => eventoTenis(e)) };

const respuesta = (cuerpo, status = 200) => ({ ok: status >= 200 && status < 300, status, json: async () => cuerpo });
const resumen = events => events.map(e => ({ id: String(e.id), home: e.home, away: e.away, start: Date.parse(e.start), status: e.status, score: e.score,
  markets: e.markets.map(m => [m.id, m.probability, m.outcome]) }));
const sinAviso = async fn => { const original = console.warn, avisos = []; console.warn = (...a) => avisos.push(a.join(' ')); try { return [await fn(), avisos]; } finally { console.warn = original; } };

// ── ventana ───────────────────────────────────────────────────────────────────────────────────────────────────────────
test('la ventana cubre los 7 días de la web en hora local y manda el desfase con el signo del contrato', () => {
  const v = ventanaContrato('nba', NOW);
  assert.deepEqual([v.desde, v.dias], ['2026-11-02', 7]);
  assert.equal(v.tz, NOW.getTimezoneOffset() === 0 ? 0 : -NOW.getTimezoneOffset());     // UTC+1 = 60 (getTimezoneOffset da -60)
  assert.deepEqual(ventanaContrato('tenis', NOW), v);
});
test('NBA no pide días anteriores al estreno de la temporada y acorta los días', () => {
  const v = ventanaContrato('nba', new Date(2026, 9, 21, 12));
  assert.deepEqual([v.desde, v.dias], ['2026-10-20', 5]);                                  // 20…24 oct (21 + 3)
  assert.equal(ventanaContrato('tenis', new Date(2026, 9, 21, 12)).desde, '2026-10-18');   // tenis no tiene fecha de inicio
});

// ── conversión ────────────────────────────────────────────────────────────────────────────────────────────────────────
test('un evento de NBA del contrato se convierte al objeto que la web ya pinta', () => {
  const e = eventoDesdeContrato(CONTRATO_NBA.eventos[0], 'nba');
  assert.equal(e.id, 1);                                                   // la web compara `partido_id` con un número
  assert.deepEqual([e.sport, e.league, e.v2, e.actionable, e.availability, e.official_url, e.team_projection], ['nba', 'NBA', true, false, null, null, null]);
  assert.deepEqual([e.status, e.score, e.seal, e.sealed_at], ['finished', '110 – 100', SELLO, '2026-11-02T22:00:00Z']);
  assert.deepEqual(e.markets[0], { id: 'winner-1', label: 'Ganador del partido', selection: 'Boston Celtics', probability: 0.7, price: null, reference: 'Probabilidad estadística',
    estimate: null, sealed_at: '2026-11-02T22:00:00Z', eligible: true, revised: false, outcome: 'win', conditional: false, market: 'winner', player: null, player_id: null, line: null });
  const revisado = eventoDesdeContrato(eventoNba(5, '2026-11-05T00:00:00Z', 'scheduled', null, [{ ...mercadoGanador(5, 'Boston Celtics', 0.6, null, '2026-11-05T01:00:00Z'), eligible: false }]), 'nba');
  assert.equal(revisado.markets[0].revised, true);                         // revised = !eligible
  assert.equal(eventoDesdeContrato({ ...CONTRATO_NBA.eventos[0], status: 'live' }, 'nba').status, 'scheduled');   // estado desconocido de NBA = programado
  assert.deepEqual(eventoDesdeContrato({ ...CONTRATO_NBA.eventos[0], team_projection: [110.5, 104.2] }, 'nba').team_projection, [110.5, 104.2]);
});
test('un evento de tenis del contrato conserva lo que la web usa y el destacado como id', () => {
  const e = eventoDesdeContrato(CONTRATO_TENIS.eventos[0], 'tenis');
  assert.deepEqual([e.id, e.sport, e.league, e.surface, e.status, e.score, e.seal, e.destacado], ['t-1', 'tenis', 'WTA · Basilea', 'Pista dura', 'finished', '6-4 6-3', SELLO, 'winner']);
  assert.deepEqual([e.markets[1].id, e.markets[1].outcome, e.markets[1].push_probability, e.markets[1].revised], ['games_total-1', 'loss', 0, false]);
});
test('una respuesta que no cumple el contrato se rechaza entera', () => {
  for (const mala of [null, { ...CONTRATO_NBA, contrato: 2 }, { ...CONTRATO_NBA, deporte: 'tenis' }, { ...CONTRATO_NBA, eventos: null },
    { ...CONTRATO_NBA, eventos: [{ ...CONTRATO_NBA.eventos[0], id: 'abc' }] }, { ...CONTRATO_NBA, eventos: [{ ...CONTRATO_NBA.eventos[0], start: 'ayer' }] },
    { ...CONTRATO_NBA, eventos: [{ ...CONTRATO_NBA.eventos[0], markets: [{ ...CONTRATO_NBA.eventos[0].markets[0], probability: 1 }] }] }]) assert.throws(() => eventosDesdeContrato(mala, 'nba'));
});

// ── paridad con el cargador actual ───────────────────────────────────────────────────────────────────────────────────
test('paridad NBA: el contrato y nbaV2Events dan los mismos eventos', () => {
  const ahora = new Date('2026-11-05T06:00:00Z');
  assert.deepEqual(resumen(eventosDesdeContrato(CONTRATO_NBA, 'nba')), resumen(nbaV2Events(PARTIDOS, ahora)));
  const [c, w] = [eventosDesdeContrato(CONTRATO_NBA, 'nba'), nbaV2Events(PARTIDOS, ahora)];
  c.forEach((e, i) => assert.deepEqual([e.seal, e.sealed_at, Date.parse(e.planned_seal)], [w[i].seal, w[i].sealed_at, Date.parse(w[i].planned_seal)]));
});
test('paridad tenis: el contrato con todos los mercados y tennisEvents dan los mismos eventos', () => {
  assert.deepEqual(resumen(eventosDesdeContrato(CONTRATO_TENIS, 'tenis')), resumen(tennisEvents(FEED_TENIS)));
});

// ── brechas conocidas: lo que el contrato 1 NO trae y por lo que los interruptores siguen apagados ─────────────────────
test('brechas: la cartelera del contrato no trae todo lo que la web usa hoy', () => {
  assert.deepEqual(CONTRATO_WEB, { nba: false, tenis: false });
  // Tenis: en la cartelera cada evento solo lleva el destacado; la web pinta totales, sets y tie-break de TODOS los mercados.
  const soloDestacado = { ...CONTRATO_TENIS, eventos: FEED_TENIS.events.map(e => eventoTenis(e, true)) };
  const hoy = tennisEvents(FEED_TENIS), contrato = eventosDesdeContrato(soloDestacado, 'tenis');
  assert.equal(hoy[0].markets.length, 2);
  assert.equal(contrato.find(e => e.id === 't-1').markets.length, 1);
  assert.deepEqual(hoy.map(e => e.id), ['t-1', 't-2']);
  assert.deepEqual(contrato.map(e => e.id), ['t-1']);                      // sin destacado no hay ningún mercado y el partido desaparece de la cartelera
  // NBA: un pronóstico revisado (sello posterior al inicio) no es destacado y la cartelera lo recorta: la web hoy lo conserva como mercado revisado.
  const tarde = game(9, '2026-11-04', '2026-11-05T00:00:00Z', null, pick(0.6, '2026-11-05T00:30:00Z', [112, 105]));
  const [hoyNba] = nbaV2Events([tarde], new Date('2026-11-05T01:00:00Z'));
  const [contratoNba] = eventosDesdeContrato({ ...CONTRATO_NBA, eventos: [eventoNba(9, '2026-11-05T00:00:00Z', 'scheduled', null, [], { sealed_at: '2026-11-05T00:30:00Z' })] }, 'nba');
  assert.equal(hoyNba.markets.length, 1);
  assert.equal(contratoNba.markets.length, 0);
  assert.deepEqual(hoyNba.team_projection, [112, 105]);                    // y `team_projection` («Puntos esperados») no existe en el contrato
  assert.equal(contratoNba.team_projection, null);
});

// ── peticiones y respaldo ────────────────────────────────────────────────────────────────────────────────────────────
test('la cartelera de NBA del contrato es UNA petición para la ventana de 7 días (antes, 9)', async () => {
  const llamadas = [];
  const { status, events } = await loadSportContrato('nba', async url => { llamadas.push(url); return respuesta(CONTRATO_NBA); }, NOW);
  const v = ventanaContrato('nba', NOW);
  assert.deepEqual(llamadas, [`/deportes/v1/nba/cartelera?cliente=web&contrato=1&desde=2026-11-02&dias=7&tz=${v.tz}`]);
  assert.equal(status, 'ready'); assert.equal(events.length, 4);
  const antes = []; await loadSport('nba', async url => { antes.push(url); return respuesta({ partidos: [] }); }, NOW);
  assert.equal(antes.length, 9);
});
test('con el interruptor apagado la web usa el cargador actual sin tocar el contrato', async () => {
  const llamadas = [];
  const [r, avisos] = await sinAviso(() => loadSportWeb('nba', async url => { llamadas.push(url); return respuesta({ partidos: [] }); }, NOW));
  assert.equal(r.status, 'ready'); assert.equal(llamadas.length, 9);
  assert.ok(llamadas.every(u => u.startsWith('/nba/v1/cartelera?fecha=')) && !avisos.length);
  const [t] = await sinAviso(() => loadSportWeb('tenis', async url => { llamadas.push(url); return respuesta(FEED_TENIS); }, NOW));
  assert.equal(t.events.length, 2); assert.equal(llamadas.at(-1), '/web/deportes/tenis');
});
test('con el interruptor encendido el contrato manda y no se pide nada más', async () => {
  const llamadas = [];
  const [r, avisos] = await sinAviso(() => loadSportWeb('nba', async url => { llamadas.push(url); return respuesta(CONTRATO_NBA); }, NOW, { contrato: { nba: true } }));
  assert.equal(r.events.length, 4); assert.equal(llamadas.length, 1); assert.deepEqual(avisos, []);
});
test('si el contrato falla (503, 304 sin cuerpo, red, JSON roto o forma inválida) la web usa el cargador actual y avisa', async () => {
  const actual = url => url.startsWith('/deportes/') ? null : url.startsWith('/nba/') ? respuesta({ partidos: PARTIDOS }) : respuesta(FEED_TENIS);
  const fallos = {
    '503': () => respuesta({ detail: 'Fuente no disponible' }, 503),
    '304 sin cuerpo': () => ({ ok: false, status: 304, json: async () => { throw new SyntaxError('sin cuerpo'); } }),
    'red caída': () => { throw new TypeError('Failed to fetch'); },
    'JSON roto': () => ({ ok: true, status: 200, json: async () => { throw new SyntaxError('Unexpected token <'); } }),
    'forma inválida': () => respuesta({ contrato: 1, deporte: 'nba', eventos: 'no' }),
    'otro contrato': () => respuesta({ ...CONTRATO_NBA, contrato: 2 }),
  };
  for (const [nombre, fallo] of Object.entries(fallos)) {
    for (const sport of ['nba', 'tenis']) {
      const llamadas = [];
      const fetcher = async url => { llamadas.push(url); if (url.startsWith('/deportes/')) return fallo(); return actual(url); };
      const [r, avisos] = await sinAviso(() => loadSportWeb(sport, fetcher, NOW, { contrato: { nba: true, tenis: true } }));
      assert.equal(r.status, 'ready', `${sport}: ${nombre}`);
      assert.ok(r.events.length > 0, `${sport}: ${nombre}`);
      assert.equal(avisos.length, 1, `${sport}: ${nombre}`);
      assert.match(avisos[0], new RegExp(`/deportes/v1/${sport}`));
      assert.ok(llamadas[0].startsWith('/deportes/v1/') && llamadas.length > 1, `${sport}: ${nombre}`);
    }
  }
  // Si además falla el cargador actual, el resultado es el error de siempre (no una excepción).
  const [r] = await sinAviso(() => loadSportWeb('tenis', async () => respuesta({}, 503), NOW, { contrato: { tenis: true } }));
  assert.deepEqual(r, { status: 'error', events: [] });
});
