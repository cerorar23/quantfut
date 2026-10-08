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
