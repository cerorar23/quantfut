import assert from 'node:assert/strict';
import test from 'node:test';
import { expectedHitRate, isPublicationActive, loadPublicData, probabilityLabel } from './public-data.js';

const responses = {
  '/model-card': { puerta_comercial: { autorizada: false,
    sombra_criterio_sharp: { autorizada: false }, publicacion_de_picks: 'pausada' } },
  '/picks/free?limit=20': [],
  '/track-record': { mensual: [], ultimos_30d: { n: 0 } },
  '/calibration': { runs: [] },
  '/chain?limit=20': { lotes: [] },
  '/alta-probabilidad': { estado: 'desactivada', motivos: ['Línea desactivada'], proximos: [], historial: { n: 0 } },
  '/escalera': { activo: false, reglas: { cuota_min: 1.25, cuota_max: 1.4, longitudes: [3, 4, 5, 6] }, actuales: [], historial: [], serie: [], resumen: { cerrados: 0 } },
  '/parley': { activo: false, reglas: { escalones: [] }, control: { pausados: [], motivos: [] }, resumen: { total: { n: 0 }, por_escalon: {} }, dias: [] },
};

test('consulta solo rutas públicas y conserva los estados vacíos', async () => {
  const called = [];
  const data = await loadPublicData(async (path, options) => {
    called.push(path);
    assert.equal(options.cache, 'no-store');
    return { ok: true, json: async () => responses[path] };
  });
  assert.deepEqual(called.sort(), Object.keys(responses).sort());
  assert.ok(called.every(path => !path.startsWith('/v1/')));
  assert.equal(data.picks.status, 'ready');
  assert.deepEqual(data.picks.data, []);
  assert.equal(data.record.data.ultimos_30d.n, 0);
  assert.equal(isPublicationActive(data.gate), false);
});

test('una fuente fallida no se interpreta como una lista vacía', async () => {
  const data = await loadPublicData(async path => path === '/chain?limit=20'
    ? { ok: false, status: 503 }
    : { ok: true, json: async () => responses[path] });
  assert.deepEqual(data.chain, { status: 'error', data: null });
  assert.equal(data.record.status, 'ready');
});

test('la puerta exige autorización y publicación activas a la vez', () => {
  const gate = { status: 'ready', data: { puerta_comercial: { autorizada: false,
    sombra_criterio_sharp: { autorizada: true }, publicacion_de_picks: 'pausada' } } };
  assert.equal(isPublicationActive(gate), false);
  gate.data.puerta_comercial.publicacion_de_picks = 'activa';
  assert.equal(isPublicationActive(gate), true);
  gate.data.puerta_comercial.sombra_criterio_sharp.autorizada = false;
  assert.equal(isPublicationActive(gate), false);
  gate.status = 'error';
  assert.equal(isPublicationActive(gate), false);
});

test('la probabilidad real se muestra en porcentaje y en frecuencia', () => {
  assert.deepEqual(probabilityLabel(0.2941), { pct: '29%', frequency: '1 de cada 3.4', text: '29% · sale 1 de cada 3.4' });
  assert.equal(probabilityLabel(0.71).frequency, '7 de cada 10');
  assert.equal(probabilityLabel(0.08).frequency, '1 de cada 13');
  for (const bad of [null, undefined, 0, 1, -0.2, 'x', NaN]) assert.equal(probabilityLabel(bad), null);
});

test('el acierto esperado no se estima si falta alguna probabilidad', () => {
  assert.equal(expectedHitRate([{ fair_prob: 0.2 }, { fair_prob: 0.4 }]).toFixed(2), '0.30');
  assert.equal(expectedHitRate([{ fair_prob: 0.2 }, { fair_prob: null }]), null);
  assert.equal(expectedHitRate([]), null);
});

test('la línea de alta probabilidad se carga de su ruta pública', async () => {
  const data = await loadPublicData(async path => ({ ok: true, json: async () => responses[path] }));
  assert.equal(data.alta.status, 'ready');
  assert.equal(data.alta.data.estado, 'desactivada');
  const roto = await loadPublicData(async path => ({ ok: true, json: async () => (path === '/alta-probabilidad' ? { proximos: 'x' } : responses[path]) }));
  assert.equal(roto.alta.status, 'error');
});

test('el reto escalera se carga de su ruta pública y un formato roto no se enseña', async () => {
  const data = await loadPublicData(async path => ({ ok: true, json: async () => responses[path] }));
  assert.equal(data.escalera.status, 'ready');
  assert.deepEqual(data.escalera.data.reglas.longitudes, [3, 4, 5, 6]);
  const roto = await loadPublicData(async path => ({ ok: true, json: async () => (path === '/escalera' ? { reglas: {}, historial: 'x' } : responses[path]) }));
  assert.equal(roto.escalera.status, 'error');
});

test('el parley se carga de su ruta pública y un formato roto no se enseña', async () => {
  const data = await loadPublicData(async path => ({ ok: true, json: async () => responses[path] }));
  assert.equal(data.parley.status, 'ready');
  assert.deepEqual(data.parley.data.dias, []);
  const roto = await loadPublicData(async path => ({ ok: true, json: async () => (path === '/parley' ? { dias: 'x' } : responses[path]) }));
  assert.equal(roto.parley.status, 'error');
});

import { LOCKED_PLACEHOLDER, lockedPicksHtml } from './public-data.js';

const fmt = { esc: s => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;'), date: () => '19 oct', time: () => '15:00', number: (v, d) => Number(v).toFixed(d) };

test('los pronósticos bloqueados se muestran difuminados con botón a Suscripciones', () => {
  const html = lockedPicksHtml([
    { league_id: 'gb.premier_league', kickoff_utc: '2026-10-19T15:00:00Z', local: 'Tottenham', visitante: 'Coventry', market: 'totals', cuota: 1.35 },
    { league_id: 'es.laliga', kickoff_utc: '2026-10-19T17:00:00Z', local: 'Getafe', visitante: 'Rayo', cuota: null },
  ], fmt);
  assert.equal((html.match(/class="live-pick alta-pick locked-pick"/g) ?? []).length, 2);
  assert.equal((html.match(/locked-blur/g) ?? []).length, 2);
  assert.ok(html.includes(LOCKED_PLACEHOLDER));
  assert.ok(html.includes('data-route="planes"') && html.includes('Acceso VIP'));
  assert.ok(html.includes('1.35'));                       // la cuota publicada se ve
  assert.equal((html.match(/<small>cuota<\/small>/g) ?? []).length, 1);   // sin cuota no se inventa
  assert.ok(html.includes('2 pronósticos más con VIP'));
});

test('lo bloqueado nunca pinta selección ni probabilidad, aunque el servidor mande campos de más', () => {
  const html = lockedPicksHtml([{ local: 'A', visitante: 'B', texto: 'Más de 2,5 goles', prob: 0.87, selection: 'over', line: 2.5 }], fmt);
  assert.ok(!html.includes('Más de 2,5') && !html.includes('0.87') && !html.includes('over'));
});

test('sin bloqueados no se pinta nada y el HTML se escapa', () => {
  assert.equal(lockedPicksHtml([], fmt), '');
  assert.equal(lockedPicksHtml(undefined, fmt), '');
  assert.ok(!lockedPicksHtml([{ local: '<img src=x>', visitante: 'B' }], fmt).includes('<img'));
});
