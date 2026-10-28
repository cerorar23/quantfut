import test from 'node:test';
import assert from 'node:assert/strict';
import { calibracion, rachaParley, rachaEscalera, resumenRacha, primeraHuella, createConversionViews } from './conversion-views.js';

test('calibracion no vende ventaja dentro del ruido', () => {
  assert.equal(calibracion({ n: 385, acierto_prometido: 82.3, acierto_real: 82.3, margen_ee: 1.9 }).estado, 'dentro');
  assert.match(calibracion({ n: 385, acierto_prometido: 82.3, acierto_real: 82.3, margen_ee: 1.9 }).texto, /coinciden/);
  assert.equal(calibracion({ n: 100, acierto_prometido: 80, acierto_real: 71, margen_ee: 2 }).estado, 'debajo');
  assert.equal(calibracion({ n: 100, acierto_prometido: 80, acierto_real: 90, margen_ee: 2 }).estado, 'encima');
  assert.equal(calibracion({ n: 100, acierto_prometido: 80, acierto_real: 81.5, margen_ee: 2 }).estado, 'dentro');
  assert.equal(calibracion({ n: 0 }), null);
  assert.equal(calibracion(null), null);
});

test('rachaParley va de antiguo a reciente y salta los candados', () => {
  const dias = [
    { dia: '2026-10-27', tickets: [{ escalon: 1, outcome: 'ganado' }, { escalon: 2, locked: true }] },
    { dia: '2026-10-26', tickets: [{ escalon: 2, outcome: 'perdido' }, { escalon: 1, outcome: 'nulo' }, { escalon: 3, outcome: null }] },
  ];
  assert.deepEqual(rachaParley(dias), ['push', 'loss', 'open', 'win']);
  assert.deepEqual(rachaParley(undefined), []);
});

test('rachaEscalera ordena por reto y deja los abiertos al final', () => {
  const lista = rachaEscalera([{ reto_id: 3, estado: 'fallido' }, { reto_id: 1, estado: 'completado' }], [{ reto_id: 4 }]);
  assert.deepEqual(lista, ['win', 'loss', 'open']);
  assert.deepEqual(resumenRacha(lista), { n: 2, aciertos: 1, fallos: 1 });
});

test('primeraHuella solo acepta hashes hexadecimales', () => {
  assert.equal(primeraHuella(undefined, 'xyz', 'fa382d6b342e0d59'), 'fa382d6b342e0d59');
  assert.equal(primeraHuella(null), null);
});

const helpers = data => ({
  esc: text => String(text).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]),
  realNumber: (v, d = 0) => (v == null || !Number.isFinite(Number(v)) ? '—' : Number(v).toLocaleString('es-MX', { minimumFractionDigits: d, maximumFractionDigits: d })),
  realPercent: (v, d = 1) => `${Number(v) > 0 ? '+' : ''}${Number(v).toFixed(d)}%`,
  realDate: () => '27 oct 2026',
  realTime: () => '19:45',
  badge: (text, kind = '') => `<span class="badge ${kind}">${text}</span>`,
  probabilityLabel: p => (p ? { pct: `${Math.round(p * 100)}%`, frequency: '8 de cada 10', text: '' } : null),
  getData: () => data,
});

const alta = {
  status: 'ready',
  data: {
    estado: 'activa', motivos: [],
    proximos: [{ free: true, texto: 'Menos de 5,5 tarjetas', local: 'A', visitante: 'B', kickoff_utc: '2026-10-27T19:45:00Z', prob: 0.8, fair_price: 1.25, chain_sha256: 'fa382d6b342e0d591938c57713610d0d788f6b8173488ccc0a0fa4a16222a929' }],
    vip: [{ market: 'corners', local: 'C', visitante: 'D', kickoff_utc: '2026-10-27T20:00:00Z', cuota: 1.33, locked: true }],
    historial: { n: 385, aciertos: 317, acierto_prometido: 82.3, acierto_real: 82.3, margen_ee: 1.9, por_mes: [], por_mercado: { corners: { n: 71, aciertos: 59, acierto_prometido: 83.3, acierto_real: 83.1 } }, rendimiento_ref: { n: 275, roi: -3.07 } },
  },
};

test('alta enseña lo gratis, el candado y el rendimiento negativo sin maquillar', () => {
  const view = createConversionViews(helpers({ alta })).altaView();
  assert.match(view, /82\.3%/);
  assert.match(view, /317 de 385/);
  assert.match(view, /Gratis/);
  assert.match(view, /cv-lock/);
  assert.match(view, /cv-blur/);
  assert.doesNotMatch(view, /1\.33/, 'la cuota bloqueada no se pinta aunque llegue en los datos');
  assert.match(view, /−3\.07%|-3\.07%/);
  assert.match(view, /data-route="planes"/);
  assert.doesNotMatch(view, /\b(segura|seguro|certera|certero)\b|garantizad[oa]s? de ganar/i);
  assert.doesNotMatch(view, /style="/);
});

test('las vistas pintan un estado de error sin datos inventados', () => {
  const views = createConversionViews(helpers({ alta: { status: 'error', data: null }, parley: { status: 'error', data: null }, escalera: { status: 'error', data: null } }));
  for (const view of [views.altaView(), views.parleyView(), views.escaleraView()]) {
    assert.match(view, /No se pud/);
    assert.doesNotMatch(view, /cv-hero/);
  }
  assert.match(createConversionViews(helpers({})).parleyView(), /Consultando/);
});

test('parley y escalera cuentan fallos y retos perdidos', () => {
  const parley = {
    status: 'ready',
    data: {
      activo: true,
      reglas: { escalones: [{ escalon: 1, cuota_min: 1.9, cuota_max: 2.2 }, { escalon: 2, cuota_min: 2.2, cuota_max: 2.7 }] },
      control: { motivos: ['escalón 1: muestra insuficiente (12 < 50)'] },
      resumen: { total: { n: 48, aciertos: 24, unidades: 12.13, roi: 25.3, prob_media: 39.5 }, por_escalon: { 1: { n: 12, aciertos: 9, acierto_real: 75, prob_media: 54.3, roi: 46.2, unidades: 5.54 } } },
      dias: [
        { dia: '2026-10-27', chain_sha256: 'fa382d6b342e0d591938c57713610d0d788f6b8173488ccc0a0fa4a16222a929', tickets: [{ escalon: 1, gratis: true, outcome: 'ganado', cuota_total: 1.9, prob_total: 0.5, n_patas: 1, factor_pago: 1.9, patas: [{ texto: 'X', local: 'A', visitante: 'B', kickoff_utc: '2026-10-27T19:45:00Z', price: 1.9, prob: 0.5, book: 'bovada', outcome: 'win' }] }, { escalon: 2, locked: true, cuota_min: 2.2, cuota_max: 2.7 }] },
        { dia: '2026-10-26', tickets: [{ escalon: 1, outcome: 'perdido', cuota_total: 2, prob_total: 0.5, n_patas: 1, patas: [] }] },
      ],
    },
  };
  const escalera = {
    status: 'ready',
    data: {
      activo: true,
      reglas: { cuota_min: 1.25, cuota_max: 1.4, stake: '10.00', freeroll_x: 2.5, longitudes: [3, 4], max_seis_mes: 3, lineas_handicap: [] },
      actuales: [{ reto_id: 16, estado: 'en_curso', ganados: 1, pasos_objetivo: 4, saldo: '12.70', en_juego: null, stake_inicial: '10.00', retirado: '0.00', freeroll_x: 2.5, pasos: [], vip: [] }],
      historial: [{ reto_id: 14, estado: 'fallido', ganados: 2, pasos_objetivo: 4, retirado: '0.00', ganancia: '-10.00', inicio: '2026-10-20T09:00:00Z' }],
      resumen: { cerrados: 13, completados: 6, ganancia: '33.49', invertido: '130.00', roi: 25.8, tasa_completados: 46.2 },
      por_longitud: { 3: { cerrados: 4, completados: 2, ganancia: '0.13', roi: 0.3, tasa_completados: 50 } },
      serie: [{ acumulado: '10.00', reto_id: 1 }, { acumulado: '0.00', reto_id: 2 }],
      escalones: { n: 42, aciertos: 35, prob_media: 77.5 },
    },
  };
  const views = createConversionViews(helpers({ parley, escalera }));
  const p = views.parleyView();
  assert.match(p, /24 de 48/);
  assert.match(p, /Muestra en construcción/);
  assert.match(p, /cv-lock/);
  assert.match(p, /Perdido/);
  const e = views.escaleraView();
  assert.match(e, /6 de 13/);
  assert.match(e, /Fallido/);
  assert.match(e, /cyber-progress--segmented/);
  assert.doesNotMatch(e + p, /style="/);
});

// conversion.css es aditiva (las cuatro hojas originales no cambian, ver original-css.test.mjs): todos sus
// selectores cuelgan de .cv-, así que no puede alterar otras vistas ni CYBERCORE.
test('conversion.css solo actúa sobre sus propias clases .cv-', async () => {
  const { readFileSync } = await import('node:fs');
  const css = readFileSync(new URL('./conversion.css', import.meta.url), 'utf8').replace(/\/\*[\s\S]*?\*\//g, '');
  assert.ok(!/@import|url\(/.test(css), 'sin recursos externos');
  const selectors = [...css.matchAll(/([^{}]+)\{/g)].map(m => m[1].trim()).filter(t => t && !t.startsWith('@') && !/^(from|to|\d+%)/.test(t));
  const fuera = selectors.flatMap(group => group.split(',')).map(t => t.trim()).filter(t => !t.startsWith('.cv-'));
  assert.deepEqual(fuera, []);
});
