import test from 'node:test';
import assert from 'node:assert/strict';
import { calibracion, rachaParley, rachaEscalera, resumenRacha, primeraHuella, agruparHistorialPorDia, createConversionViews } from './conversion-views.js';

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

test('alta enseña lo gratis, el candado y la verificación matemática', () => {
  const view = createConversionViews(helpers({ alta })).altaView();
  assert.match(view, /82\.3%/);
  assert.match(view, /317 de 385/);
  assert.match(view, /Gratis/);
  assert.match(view, /cv-lock/);
  assert.match(view, /cv-blur/);
  assert.doesNotMatch(view, /1\.33/, 'la cuota bloqueada no se pinta aunque llegue en los datos');
  assert.doesNotMatch(view, /Acertar no es lo mismo que ganar dinero/);
  assert.doesNotMatch(view, /cyber-alert--warning/);
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
  assert.doesNotMatch(p, /Muestra en construcción/);
  assert.match(p, /cv-lock/);
  assert.match(p, /Perdido/);
  const e = views.escaleraView();
  assert.match(e, /6 de 13/);
  assert.match(e, /Fallido/);
  assert.match(e, /cyber-progress--segmented/);
  assert.doesNotMatch(e + p, /style="/);
});

test('escalera al 80 % en 7 días: umbral, plazo, expirados y sin freeroll', () => {
  const escalera = {
    status: 'ready',
    data: {
      activo: true,
      reglas: { cuota_min: 1.03, cuota_max: 1.4, stake: '10.00', freeroll_x: null, longitudes: [2], prob_reto: 0.8, prob_max: 0.95, umbrales: { 2: 0.8944 }, por_dia: 2, dias_max: 7, lineas_handicap: [1.5] },
      actuales: [{ reto_id: 30, estado: 'en_curso', ganados: 1, pasos_objetivo: 2, saldo: '10.60', en_juego: null, stake_inicial: '10.00', retirado: '0.00', freeroll_x: null, prob_objetivo: 0.8, pasos: [], vip: [] }],
      historial: [{ reto_id: 29, estado: 'expirado', ganados: 1, pasos_objetivo: 2, retirado: '0.00', ganancia: '0.60', inicio: '2026-10-20T09:00:00Z' }],
      resumen: { cerrados: 1, completados: 0, expirados: 1 },
      por_longitud: {},
      serie: [],
    },
  };
  const e = createConversionViews(helpers({ escalera })).escaleraView();
  assert.match(e, /al menos el 80% de las veces/);
  assert.match(e, /Retos de 2 escalones en 7 días como máximo/);
  assert.match(e, /Expirado/);
  assert.match(e, /en 7 días no aparece el segundo escalón/);
  assert.match(e, /reto al 80% como mínimo/);
  assert.match(e, /Por qué un 80% paga tan poco/);
  assert.doesNotMatch(e, /Freeroll a|freeroll\?/);
  assert.doesNotMatch(e, /Cómo se elige cada escalón/);
});

test('parley v2.1 sustituye a v1 como vista principal con cuatro objetivos y multideporte', () => {
  const parley = {
    status: 'ready',
    data: {
      activo: true,
      dias: [],
      v2: {
        activo: true,
        estrategia: 'objetivos_cuota',
        version: '2.1',
        reglas: { targets: [2.1, 3.1, 8.2, 12.1], deportes: ['futbol', 'tenis', 'nba'] },
        dias: [
          {
            dia: '2026-11-07',
            chain_sha256: 'f847dbf4c1763e9fb1db739740164894e909ac07b7843349bceaad2f0c71d97d',
            tickets: [
              {
                escalon: 1,
                target: 2.1,
                tipo: 'multievento',
                estado: 'publicado',
                n_patas: 2,
                cuota_total: 2.06,
                prob_total: 0.48,
                locked: false,
                gratis: true,
                patas: [
                  { deporte: 'futbol', texto: 'Rosario Central', local: 'Rosario Central', visitante: 'Estudiantes', kickoff_utc: '2026-11-07T20:30:00Z', price: 1.2, prob: 0.84, book: 'strendus', outcome: null },
                  { deporte: 'nba', texto: 'Over 220.5', local: 'Lakers', visitante: 'Warriors', kickoff_utc: '2026-11-08T01:00:00Z', price: 1.72, prob: 0.58, book: 'bovada', outcome: null },
                ],
              },
              { escalon: 2, locked: true, cuota_min: 3.03, cuota_max: 3.16 },
              { escalon: 3, locked: true, cuota_min: 8.0, cuota_max: 8.4 },
              { escalon: 4, locked: true, cuota_min: 11.8, cuota_max: 12.4 },
            ],
          },
        ],
      },
    },
  };
  const view = createConversionViews(helpers({ parley })).parleyView();
  assert.match(view, /PARLEY DEL DÍA · FÚTBOL, TENIS Y NBA/);
  assert.match(view, /Cuatro objetivos de cuota, menos patas/);
  assert.match(view, /Objetivo 2\.10/);
  assert.match(view, /Objetivo 3\.10/);
  assert.match(view, /Objetivo 8\.20/);
  assert.match(view, /Objetivo 12\.10/);
  assert.match(view, /Rosario Central/);
  assert.match(view, /NBA/);
  assert.match(view, /f847dbf4c176/);
  assert.match(view, /cv-lock/);
  assert.doesNotMatch(view, /LOS 5 ESCALONES DE HOY/);
  assert.doesNotMatch(view, /Muestra en construcción/);
  assert.doesNotMatch(view, /cadena · último lote/);
  assert.doesNotMatch(view, /cv-terminal/);
  assert.doesNotMatch(view, /Los pronósticos son estimaciones/);
});

test('escalera 6 targets (2.0 a 20.0): objetivos de cobro, freeroll y hasta 6 escalones', () => {
  const escalera = {
    status: 'ready',
    data: {
      activo: true,
      reglas: {
        cuota_min: 1.25, cuota_max: 2.10, stake: '10.00', freeroll_x: 2.5,
        targets: [2.0, 2.8, 4.5, 7.5, 12.0, 20.0], max_escalones: 6,
        prob_reto: 0.4761, prob_min: 0.69, prob_max: 0.95, por_dia: 1, dias_max: 10,
        lineas_handicap: [-1.0, -0.5, 0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0],
      },
      actuales: [
        { reto_id: 101, estado: 'en_curso', ganados: 2, pasos_objetivo: 6, target_cuota: 2.0, saldo: '20.10', en_juego: null, stake_inicial: '10.00', retirado: '0.00', freeroll_x: 2.5, pasos: [], vip: [] },
        { reto_id: 102, estado: 'en_curso', ganados: 1, pasos_objetivo: 6, target_cuota: 20.0, saldo: '15.00', en_juego: null, stake_inicial: '10.00', retirado: '0.00', freeroll_x: 2.5, pasos: [], vip: [] },
      ],
      historial: [
        { reto_id: 100, estado: 'completado', ganados: 3, pasos_objetivo: 6, target_cuota: 4.5, retirado: '10.00', ganancia: '45.00', inicio: '2026-11-01T10:00:00Z' },
      ],
      resumen: { cerrados: 1, completados: 1, expirados: 0, ganancia: '45.00', invertido: '10.00', roi: 450.0, tasa_completados: 100 },
      serie: [{ acumulado: '45.00', reto_id: 100 }],
    },
  };
  const view = createConversionViews(helpers({ escalera })).escaleraView();
  assert.match(view, /Objetivo ×2\.0/);
  assert.match(view, /Objetivo ×20\.0/);
  assert.match(view, /Qué es el freeroll\?/);
  assert.match(view, /Completado/);
  assert.doesNotMatch(view, /Cómo se elige cada escalón/);
  assert.doesNotMatch(view, /LA REGLA/);
  assert.doesNotMatch(view, /no es una garantía/);
  assert.doesNotMatch(view, /muestra pequeña/);
  assert.doesNotMatch(view, /Muestra en construcción/);
  assert.doesNotMatch(view, /Los pronósticos son estimaciones/);
  assert.doesNotMatch(view, /cv-legal/);
});

test('agruparHistorialPorDia junta varios parlays del mismo dia en una sola fila y limita a 10', () => {
  const dias = [
    { dia: '2026-11-07', tickets: [{ id: 1, cuota_total: 1.87, outcome: 'perdido' }] },
    { dia: '2026-11-07', tickets: [{ id: 2, cuota_total: 1.94, outcome: 'perdido' }] },
    { dia: '2026-11-07', tickets: [{ id: 3, cuota_total: 1.73, outcome: 'ganado' }] },
    { dia: '2026-11-06', tickets: [{ id: 4, cuota_total: 2.10, outcome: 'ganado' }, { id: 5, cuota_total: 3.10, outcome: 'perdido' }] },
  ];
  const agrupado = agruparHistorialPorDia(dias, 10);
  assert.equal(agrupado.length, 2);
  assert.equal(agrupado[0].dia, '2026-11-07');
  assert.equal(agrupado[0].tickets.length, 3);
  assert.equal(agrupado[1].dia, '2026-11-06');
  assert.equal(agrupado[1].tickets.length, 2);

  // Probar tope de 10
  const muchos = Array.from({ length: 15 }, (_, i) => ({
    dia: `2026-11-${String(i + 1).padStart(2, '0')}`,
    tickets: [{ id: i + 1, cuota_total: 2.0, outcome: 'ganado' }],
  }));
  const limitado = agruparHistorialPorDia(muchos, 10);
  const totalTickets = limitado.reduce((acc, d) => acc + d.tickets.length, 0);
  assert.equal(totalTickets, 10);
});

test('parley v2.1 agrupa tickets del mismo dia en una sola fila en el historial', () => {
  const parley = {
    status: 'ready',
    data: {
      activo: true,
      dias: [],
      v2: {
        activo: true,
        estrategia: 'objetivos_cuota',
        version: '2.1',
        reglas: { targets: [2.1, 3.1, 8.2, 12.1], deportes: ['futbol', 'tenis', 'nba'] },
        dias: [
          {
            dia: '2026-11-07',
            tickets: [{ escalon: 1, target: 2.1, cuota_total: 2.06, locked: false, gratis: true, patas: [] }],
          },
          {
            dia: '2026-11-07',
            tickets: [{ escalon: 1, target: 2.1, cuota_total: 1.87, outcome: 'perdido', locked: false, patas: [] }],
          },
          {
            dia: '2026-11-07',
            tickets: [{ escalon: 1, target: 2.1, cuota_total: 1.94, outcome: 'perdido', locked: false, patas: [] }],
          },
          {
            dia: '2026-11-07',
            tickets: [{ escalon: 1, target: 2.1, cuota_total: 1.73, outcome: 'ganado', locked: false, patas: [] }],
          },
        ],
      },
    },
  };
  const view = createConversionViews(helpers({ parley })).parleyView();
  // En el historial solo debe existir un único <details class="cv-day"> para el día 2026-11-07
  const matches = view.match(/<details class="cv-day">/g) ?? [];
  assert.equal(matches.length, 1, 'los 3 parlays del día deben quedar en una única fila');
  assert.match(view, /1\.87 ✗/);
  assert.match(view, /1\.94 ✗/);
  assert.match(view, /1\.73 ✓/);
});
