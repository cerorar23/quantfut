import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { ordenar, wilson, rachas, beneficio, calibrar, desvio, resumir, porDeporte, porDia, createHistorialViews } from './historial-views.js';

const fila = (start, outcome, extra = {}) => ({ sport: 'futbol', home: 'A', away: 'B', start, text: 'Gana A', outcome, price: 1.5, prob: 0.7, score: '1 – 0', ...extra });
const dia = start => start.slice(0, 10);

test('ordenar descarta lo no liquidado y deja el más antiguo primero', () => {
  const rows = [fila('2026-10-27T10:00:00Z', 'win'), fila('2026-10-26T10:00:00Z', 'loss'), { ...fila('2026-10-26T12:00:00Z', 'open') }, { ...fila('no-fecha', 'win') }];
  assert.deepEqual(ordenar(rows).map(r => r.start), ['2026-10-26T10:00:00Z', '2026-10-27T10:00:00Z']);
});

test('wilson: sin datos no inventa un intervalo y con pocos datos es ancho', () => {
  assert.equal(wilson(0, 0), null);
  const chico = wilson(4, 5), grande = wilson(80, 100);
  assert.ok(chico.alto - chico.bajo > grande.alto - grande.bajo);
  assert.ok(grande.bajo < 0.8 && grande.alto > 0.8);
});

test('rachas cuenta desde el último resultado y reporta el último fallo', () => {
  const r = rachas([fila('2026-10-26T01:00:00Z', 'win'), fila('2026-10-26T02:00:00Z', 'win'), fila('2026-10-26T03:00:00Z', 'loss'), fila('2026-10-26T04:00:00Z', 'win'), fila('2026-10-26T05:00:00Z', 'win')]);
  assert.deepEqual(r, { actual: 2, mejor: 2, desdeUltimoFallo: 2 });
  assert.equal(rachas([fila('2026-10-26T01:00:00Z', 'win')]).desdeUltimoFallo, null);
});

test('beneficio: gana cuota − 1, pierde 1, y solo cuenta cuotas reales (nunca la del modelo)', () => {
  const rows = [fila('2026-10-26T01:00:00Z', 'win', { price: 1.5 }), fila('2026-10-26T02:00:00Z', 'loss', { price: 1.2 }), fila('2026-10-26T03:00:00Z', 'win', { price: null, prob: 0.5 }), fila('2026-10-26T04:00:00Z', 'win', { sport: 'nba', price: null })];
  const b = beneficio(rows);
  assert.equal(b.n, 2);
  assert.ok(Math.abs(b.unidades - (0.5 - 1)) < 1e-9);
  assert.deepEqual(b.curva.map(v => Math.round(v * 100) / 100), [0, 0.5, -0.5]);
});

test('calibrar compara la probabilidad prometida con el acierto real', () => {
  const rows = Array.from({ length: 10 }, (_, i) => fila(`2026-10-26T0${i}:00:00Z`, i < 7 ? 'win' : 'loss', { prob: 0.7 }));
  const c = calibrar(rows);
  assert.equal(c.n, 10);
  assert.ok(Math.abs(c.prometido - 0.7) < 1e-9 && Math.abs(c.real - 0.7) < 1e-9);
  assert.equal(c.estado, 'dentro');
  assert.equal(calibrar([fila('2026-10-26T01:00:00Z', 'win', { prob: null })]), null);
});

test('resumir y agrupaciones cuadran entre sí', () => {
  const rows = [fila('2026-10-26T01:00:00Z', 'win'), fila('2026-10-26T20:00:00Z', 'loss'), fila('2026-10-27T01:00:00Z', 'win', { sport: 'tenis', price: null })];
  const r = resumir(rows);
  assert.equal(r.n, 3); assert.equal(r.aciertos, 2); assert.equal(r.fallos, 1);
  assert.deepEqual(porDeporte(rows).map(d => [d.sport, d.n]), [['futbol', 2], ['tenis', 1]]);
  const dias = porDia(rows, dia);
  assert.deepEqual(dias.map(d => [d.dia, d.aciertos, d.fallos]), [['2026-10-26', 1, 1], ['2026-10-27', 1, 0]]);
});

const views = (state = {}) => createHistorialViews({
  esc: x => String(x ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/"/g, '&quot;'),
  state, fmtOdds: v => Number(v).toFixed(2), realTime: () => '20:00', localDay: d => d.toISOString().slice(0, 10), getEvidence: () => '<p>evidencia</p>',
});

const muestra = [
  fila('2026-10-26T18:00:00Z', 'win', { price: 1.28 }), fila('2026-10-26T19:00:00Z', 'loss', { price: 1.21, text: 'Menos de 4,5 goles' }),
  fila('2026-10-27T18:00:00Z', 'win', { sport: 'nba', price: null, prob: 0.68, text: 'Boston Celtics', score: '125 – 124' }),
  fila('2026-10-27T19:00:00Z', 'win', { sport: 'tenis', price: null, prob: 0.55, text: 'Carlos Alcaraz', score: '0 - 2' }),
];

test('la vista enseña los fallos, la cuota real y marca la del modelo con ≈', () => {
  const html = views().historyView(muestra, false);
  assert.ok(html.includes('3 de 4 pronósticos acertados'));
  assert.ok(html.includes('1 fallos, a la vista'));
  assert.ok(html.includes('Fallado') && html.includes('Menos de 4,5 goles'));
  assert.ok(html.includes('1.28') && html.includes('1.21'));
  assert.ok(html.includes('≈ 1.47') && html.includes('Modelo · sin casa'));
  assert.ok(!html.includes('Muestra en construcción'), 'muestra en construccion fue retirada de los chips');
  assert.ok(!html.includes('Metodología y registros de verificación'));
});

test('la vista no usa estilos en línea ni promesas', () => {
  const html = views().historyView(muestra, false);
  assert.ok(!/style=/.test(html));
  assert.ok(!/garantizad|certer|infalible|sin riesgo/i.test(html), 'sin lenguaje de certeza');
  assert.ok(!html.includes('Los pronósticos son estimaciones, no garantías'));
});

test('el beneficio nunca usa la cuota del modelo de NBA o tenis', () => {
  const soloModelo = muestra.filter(r => r.sport !== 'futbol');
  const html = views().historyView(soloModelo, false);
  assert.ok(!html.includes('Beneficio · 1 u por pronóstico'));
  assert.ok(!html.includes('el beneficio en fútbol con 1 u'), 'sin cuota de casa no hay frase de beneficio');
});

test('desvio: acumula (real − prometido), la franja crece con la varianza y el signo es honesto', () => {
  const rows = [fila('2026-10-26T01:00:00Z', 'win', { prob: 0.8 }), fila('2026-10-26T02:00:00Z', 'loss', { prob: 0.8 }), fila('2026-10-26T03:00:00Z', 'win', { prob: null })];
  const d = desvio(rows);
  assert.equal(d.n, 2);
  assert.deepEqual(d.curva.map(v => Math.round(v * 100) / 100), [0, 0.2, -0.6]);
  assert.ok(Math.abs(d.margen - 2 * Math.sqrt(2 * 0.8 * 0.2)) < 1e-9);
  assert.ok(d.banda[2] > d.banda[1]);
  assert.equal(d.estado, 'dentro');
  const mal = desvio(Array.from({ length: 100 }, (_, i) => fila(`2026-10-${10 + Math.floor(i / 24)}T${String(i % 24).padStart(2, '0')}:00:00Z`, i < 60 ? 'win' : 'loss', { prob: 0.8 })));
  assert.equal(mal.estado, 'debajo', 'si se acierta bastante menos de lo prometido, se dice');
  assert.equal(desvio([]).n, 0);
});

test('la gráfica grande mide aciertos frente a esperados, sin leyendas debajo ni encima', () => {
  const html = views().historyView(muestra, false);
  assert.ok(html.includes('Aciertos reales frente a esperados') && html.includes('cv-hist-band'));
  assert.ok(!html.includes('Cada pronóstico suma lo que salió'), 'sin la explicación sobre la gráfica');
  assert.ok(!html.includes('Hoy: ') && !html.includes('cv-hist-foot'), 'sin la frase «Hoy: … aciertos frente a los esperados»');
  assert.ok(!html.includes('Acertar lo prometido no es ganar dinero'));
  assert.ok(!html.includes('Beneficio · 1 u por pronóstico'), 'la tarjeta de beneficio ya no está');
});

test('«Acierto por día» y «Días en verde» miran solo los últimos 7 días', () => {
  const diaN = i => new Date(Date.UTC(2026, 9, 20 + i, 15)).toISOString();
  const rows = Array.from({ length: 10 }, (_, i) => [fila(diaN(i), 'win'), fila(diaN(i), i % 2 ? 'win' : 'loss')]).flat();
  const html = views().historyView(rows, false);
  const grafica = html.slice(html.indexOf('Acierto por día'), html.indexOf('Por deporte'));
  assert.equal((grafica.match(/<rect class="cv-hist-bar win"/g) || []).length, 7);
  assert.ok(html.includes('Días en verde · última semana'));
  assert.match(html, /▲ 4 de 7 días/, 'solo cuentan los 7 días recientes (4 con más aciertos que fallos: los impares)');
});

test('cada resultado enseña su cuota y, debajo, la casa (o que es del modelo)', () => {
  const rows = [
    fila('2026-10-27T10:00:00Z', 'win', { price: 1.53, book: 'Bovada' }),
    fila('2026-10-27T11:00:00Z', 'win', { sport: 'nba', price: 1.8, book: 'Pinnacle', text: 'Lakers' }),
    fila('2026-10-27T12:00:00Z', 'win', { sport: 'tenis', price: 1.76, ref: true, book: 'pinnacle', text: 'Alcaraz' }),
    fila('2026-10-27T13:00:00Z', 'win', { sport: 'tenis', price: null, prob: 0.5, text: 'Sin cuota' }),
  ];
  const html = views().historyView(rows, false);
  assert.match(html, /<strong class="cv-hist-odds">1\.53<\/strong><small class="cv-hist-book">Bovada<\/small>/);
  assert.match(html, /<strong class="cv-hist-odds">1\.8(0)?<\/strong><small class="cv-hist-book">Pinnacle<\/small>/);
  assert.match(html, /1\.76<\/strong><small class="cv-hist-book">Pinnacle · referencia<\/small>/);
  assert.match(html, /≈ 2\.00<\/strong><small class="cv-hist-book">Modelo · sin casa<\/small>/);
});

test('la cuota de referencia de tenis no entra en el beneficio', () => {
  const rows = [fila('2026-10-26T01:00:00Z', 'win', { price: 1.5 }), fila('2026-10-26T02:00:00Z', 'win', { sport: 'tenis', price: 2.2, ref: true, book: 'pinnacle' })];
  const b = beneficio(rows);
  assert.equal(b.n, 1);
  assert.ok(Math.abs(b.unidades - 0.5) < 1e-9);
});

test('filtros por deporte y resultado, y paginación', () => {
  const html = views({ resultSport: 'nba', resultOutcome: 'todos' }).historyView(muestra, false);
  assert.ok(html.includes('Mostrando 1 de 1 resultados'));
  const fallados = views({ resultOutcome: 'fallados' }).historyView(muestra, false);
  assert.ok(fallados.includes('Mostrando 1 de 1 resultados') && fallados.includes('Menos de 4,5 goles'));
  const muchas = Array.from({ length: 70 }, (_, i) => fila(new Date(Date.UTC(2026, 9, 1, i)).toISOString(), 'win'));
  const pagina = views({}).historyView(muchas, false);
  assert.ok(pagina.includes('Mostrando 30 de 70') && pagina.includes('data-result-more'));
  assert.ok(views({ resultLimit: 90 }).historyView(muchas, false).includes('Mostrando 70 de 70'));
});

test('sin datos: estado de carga o vacío, nunca cifras inventadas', () => {
  assert.ok(views().historyView([], true).includes('Consultando resultados'));
  const vacio = views().historyView([], false);
  assert.ok(vacio.includes('Sin resultados disponibles') && !vacio.includes('%'));
});

test('los textos de partidos se escapan', () => {
  const html = views().historyView([fila('2026-10-26T18:00:00Z', 'win', { home: '<img src=x>' })], false);
  assert.ok(!html.includes('<img src=x>') && html.includes('&lt;img'));
});

test('el HTML y los módulos están registrados con el mismo identificador de versión', () => {
  const ergo = readFileSync(new URL('./ergonomic-views.js', import.meta.url), 'utf8');
  assert.match(ergo, /historial-views\.js\?v=hist-casa-20261105/);
  const web = readFileSync(new URL('../src/qf/api/web.py', import.meta.url), 'utf8');
  assert.ok(web.includes('/historial-views.js'));
});
