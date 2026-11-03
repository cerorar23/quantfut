import test from 'node:test';
import assert from 'node:assert/strict';
import { createHubViews } from './ergonomic-views.js';

// Partido de fútbol con un pick sellado de cuota 1,07 (alta probabilidad) y un destacado distinto en su ficha.
const date = new Date('2026-10-30T12:00:00Z');
const kickoff = '2026-10-30T23:30:00Z';
const pick = { match_id: 'm1', pick_key: 'k1', local: 'Le Havre', visitante: 'PSG', kickoff_utc: kickoff, texto: 'Marca PSG', prob: .94, ref_price: 1.02, ref_book: 'jazzsports', chain_sha256: 'abc', batch_date: '2026-10-30' };
const home = { status: 'ready', data: { agenda: [{ match_id: 'm1', kickoff_utc: kickoff, liga: { nombre: 'Ligue 1' }, local: { nombre: 'Le Havre' }, visitante: { nombre: 'PSG' } }], alta_probabilidad: { proximos: [pick], vip: [] } } };
const destacado = { seleccion: 'Más de 1,5 goles', prob: .72, cuota: 1.41, cuota_tipo: 'justa', titulo: 'Goles totales' };

function cards(entry) {
  const views = createHubViews({ state: { dayOffset: 0, sport: 'todos', homeSearch: '', homeStatus: 'todos' }, esc: x => String(x ?? ''), ensureHome: () => home,
    addDays: () => date, localDay: d => d.toISOString().slice(0, 10), dayLabel: () => 'Hoy', realDate: () => '30 oct', realTime: () => '17:30', fmtOdds: String, fmtPct: String,
    dayRail: () => '', liveEvidence: () => '', ensureMatch: () => entry });
  return views.home();
}

test('la tarjeta de fútbol enseña el destacado de la ficha, no el pick sellado', () => {
  const html = cards({ status: 'ready', data: { ficha: { mercados: { destacado } }, picks: [] } });
  assert.ok(html.includes('Más de 1,5 goles'));
  assert.ok(html.includes('Pronóstico destacado'));
  assert.ok(html.includes('Cuota del modelo'));
  assert.ok(!html.includes('Marca PSG'));
});

test('si el destacado es el pick sellado se conservan su cuota publicada y su casa', () => {
  const sealed = { ...destacado, seleccion: 'Marca PSG', prob: .94, cuota: 1.5, cuota_tipo: 'publicada', pick_key: 'k1' };
  const html = cards({ status: 'ready', data: { ficha: { mercados: { destacado: sealed } }, picks: [pick] } });
  assert.ok(html.includes('Cuota publicada'));
  assert.ok(html.includes('jazzsports'));
});

test('mientras se consulta no sale el pick sellado y si falla o no hay destacado vuelve a él', () => {
  const loading = cards({ status: 'loading', data: null });
  assert.ok(loading.includes('Consultando…'));
  assert.ok(!loading.includes('Marca PSG'));
  for (const entry of [{ status: 'error', data: null }, { status: 'ready', data: { ficha: { mercados: { destacado: null } }, picks: [] } }]) {
    const html = cards(entry);
    assert.ok(html.includes('Marca PSG'));
    assert.ok(html.includes('Cuota publicada'));
  }
});

// --- el destacado sale de TODOS los mercados del partido y la fecha dice si acertó o falló ---------------------------------

// Partido cuyo único pick es de pago (candado): no tiene mercado publicado, pero su destacado sale de todos los mercados y es gratis.
const vipPick = { match_id: 'm1', local: 'Le Havre', visitante: 'PSG', kickoff_utc: kickoff, league_id: 'fr.ligue_1', locked: true };
const sinPicks = { status: 'ready', data: { agenda: home.data.agenda, alta_probabilidad: { proximos: [], vip: [vipPick] }, escalera: null, parley: null } };

function cardsSinPicks(entry, extra = {}) {
  const views = createHubViews({ state: { dayOffset: 0, sport: 'todos', homeSearch: '', homeStatus: 'todos' }, esc: x => String(x ?? ''), ensureHome: () => sinPicks,
    addDays: () => date, localDay: d => d.toISOString().slice(0, 10), dayLabel: () => 'Hoy', realDate: () => '30 oct', realTime: () => '17:30', fmtOdds: String, fmtPct: String,
    dayRail: () => '', liveEvidence: () => '', ensureMatch: () => entry, ...extra });
  return views.home();
}

test('un partido con pick solo de pago enseña igual el destacado de la ficha (todos los mercados son opción)', () => {
  const html = cardsSinPicks({ status: 'ready', data: { ficha: { mercados: { destacado } }, picks: [] } });
  assert.ok(html.includes('Más de 1,5 goles'), 'sin destacado en la tarjeta');
  assert.ok(html.includes('Pronóstico destacado'));
  assert.ok(!html.includes('Contenido reservado'));
});

test('con pick solo de pago: mientras se consulta dice Consultando… y si no hay destacado queda reservado como antes', () => {
  assert.ok(cardsSinPicks({ status: 'loading', data: null }).includes('Consultando…'));
  assert.ok(!cardsSinPicks({ status: 'loading', data: null }).includes('Contenido reservado'));
  for (const entry of [{ status: 'error', data: null }, { status: 'ready', data: { ficha: { mercados: { destacado: null } }, picks: [] } }]) {
    assert.ok(cardsSinPicks(entry).includes('Contenido reservado'));
  }
});

test('la fecha de la tarjeta lleva Acertó, Falló o Devolución cuando el partido ya terminó, y nada si no', () => {
  const con = resultado => cardsSinPicks({ status: 'ready', data: { ficha: { mercados: { destacado: { ...destacado, resultado } } }, picks: [] } });
  for (const [r, texto, clase] of [['win', 'Acertó', 'good'], ['loss', 'Falló', 'warn'], ['push', 'Devolución', 'muted']]) {
    const html = con(r);
    const cabecera = html.slice(html.indexOf('win-pk-when'), html.indexOf('</header>'));
    assert.ok(cabecera.includes('30 oct · 17:30'), 'la fecha sigue en la cabecera');
    assert.ok(cabecera.includes(`<span class="badge ${clase}">${texto}</span>`), `${texto} junto a la fecha`);
  }
  const pendiente = con(undefined);
  assert.ok(!/Acertó|Falló|Devolución/.test(pendiente));
});

test('el pick sellado de un partido ya liquidado también marca el estado en la fecha', () => {
  const sellado = { status: 'ready', data: { ficha: { mercados: { destacado: null } }, picks: [] } };
  const html = cards(sellado);   // cae al pick sellado (sin `outcome`): sin insignia, sin romper la cabecera
  assert.ok(html.includes('win-pk-when') && !/Acertó|Falló/.test(html));
});

// --- partidos de fútbol ya terminados: salen como tarjeta con su destacado resuelto ------------------------------------------

const terminado = { match_id: 'm9', league_id: 'fr.ligue_1', kickoff_utc: '2026-10-30T19:00:00Z', local: 'Lorient', visitante: 'Brest', texto: 'Más de 1,5 goles',
  prob: .72, ref_price: null, outcome: 'win', home_goals: 2, away_goals: 1, market: 'totals', selection: 'over', line: 1.5 };
const sinNada = { status: 'ready', data: { agenda: home.data.agenda, alta_probabilidad: { proximos: [], vip: [] }, escalera: null, parley: null } };

function tarjetasTerminadas(featured, estado = 'cerrados', pedidos = [], vista = 'home') {
  const views = createHubViews({ state: { dayOffset: 0, sport: 'todos', homeSearch: '', homeStatus: estado }, esc: x => String(x ?? ''), ensureHome: () => sinNada,
    addDays: () => date, localDay: d => d.toISOString().slice(0, 10), dayLabel: () => 'Hoy', realDate: () => '30 oct', realTime: () => '13:00', fmtOdds: String, fmtPct: String,
    dayRail: () => '', liveEvidence: () => '', ensureResults: () => ({ status: 'ready', items: [], featured }),
    ensureMatch: id => { pedidos.push(id); return { status: 'loading', data: null }; } });
  return views[vista]();
}

test('un partido de fútbol terminado sale como tarjeta con su destacado, el marcador y Acertó en la fecha', () => {
  const pedidos = [];
  const html = tarjetasTerminadas([terminado], 'cerrados', pedidos);
  assert.ok(html.includes('Lorient') && html.includes('Brest'));
  assert.ok(html.includes('2 – 1'), 'marcador');
  assert.ok(html.includes('Más de 1,5 goles') && html.includes('Pronóstico destacado'));
  assert.ok(html.includes('Cuota del modelo') && html.includes('1.39'), 'sin cuota publicada: 1 ÷ probabilidad');
  assert.ok(html.includes('<span class="badge good">Acertó</span>'), 'Acertó junto a la fecha');
  assert.deepEqual(pedidos, [], 'ya trae su destacado: no pide la ficha');
});

test('el destacado fallado marca Falló y el filtro Próximos no enseña los terminados', () => {
  const fallado = { ...terminado, outcome: 'loss' };
  assert.ok(tarjetasTerminadas([fallado]).includes('<span class="badge warn">Falló</span>'));
  const tarjetas = html => (html.match(/win-pk-card /g) || []).length;
  assert.equal(tarjetas(tarjetasTerminadas([terminado], 'proximos')), 0);   // el panel de resultados sigue nombrando el partido; la tarjeta no
  assert.equal(tarjetas(tarjetasTerminadas([terminado], 'todos')), 1);
});

test('los terminados no inflan «Publicados» y las filas sin resultado o sin equipos se ignoran', () => {
  const html = tarjetasTerminadas([terminado, { ...terminado, match_id: 'x', outcome: 'push' }, { ...terminado, match_id: 'y', local: '' }], 'cerrados');
  assert.equal((html.match(/win-pk-card /g) || []).length, 1);                 // solo el 'win'; 'push' y sin equipo se ignoran
  assert.ok(/Publicados<\/small><strong>0</.test(tarjetasTerminadas([terminado], 'cerrados', [], 'picks')), 'Publicados sigue en 0');
});

test('la liga de un partido terminado sale con su nombre (de la agenda del día) y no con su id', () => {
  const otra = { status: 'ready', data: { ...sinNada.data, agenda: [{ match_id: 'fr.ligue_1:2627:x-y:20261030', kickoff_utc: kickoff, liga: { id: 1, nombre: 'Ligue 1' },
    local: { nombre: 'X' }, visitante: { nombre: 'Y' } }] } };
  const views = createHubViews({ state: { dayOffset: 0, sport: 'todos', homeSearch: '', homeStatus: 'cerrados' }, esc: x => String(x ?? ''), ensureHome: () => otra,
    addDays: () => date, localDay: d => d.toISOString().slice(0, 10), dayLabel: () => 'Hoy', realDate: () => '30 oct', realTime: () => '13:00', fmtOdds: String, fmtPct: String,
    dayRail: () => '', liveEvidence: () => '', ensureResults: () => ({ status: 'ready', items: [], featured: [terminado] }), ensureMatch: () => ({ status: 'loading' }) });
  const html = views.home();
  assert.ok(html.includes('Ligue 1') && !html.includes('fr.ligue_1'));
});

test('el partido terminado usa el escudo que manda el servidor y, si no hay, las iniciales', () => {
  const conEscudo = { ...terminado, local_escudo: '/web/escudos/7.png', visitante_escudo: null };
  const html = tarjetasTerminadas([conEscudo]);
  assert.ok(html.includes('<img src="/web/escudos/7.png"'), 'escudo del local');
  assert.ok(html.includes('is-mono'), 'el visitante sin escudo queda con iniciales');
  assert.ok(!tarjetasTerminadas([terminado]).includes('<img src="/web/escudos/'), 'sin escudo en el servidor no se inventa ninguno');
});

// --- la cuota del destacado es la de una casa y la tarjeta dice cuál -------------------------------------------------------

test('el destacado con cuota de casa enseña «Cuota de la casa» y su nombre, no «del modelo»', () => {
  const html = cards({ status: 'ready', data: { ficha: { mercados: { destacado: { ...destacado, cuota: 1.46, cuota_tipo: 'casa', casa: 'William Hill' } } }, picks: [] } });
  assert.ok(html.includes('Cuota de la casa'));
  assert.ok(html.includes('William Hill'));
  assert.ok(html.includes('1.46'));
  assert.ok(!html.includes('Cuota del modelo') && !html.includes('1 ÷ probabilidad'));
});

test('el destacado publicado sin pick a mano toma la casa que manda el servidor', () => {
  const html = cards({ status: 'ready', data: { ficha: { mercados: { destacado: { ...destacado, cuota: 1.5, cuota_tipo: 'publicada', casa: 'Betano' } } }, picks: [] } });
  assert.ok(html.includes('Cuota publicada') && html.includes('Betano'));
});

test('el partido terminado enseña la casa de su cuota; sin casa guarda el precio del modelo', () => {
  const conCasa = tarjetasTerminadas([{ ...terminado, ref_price: 1.47, ref_book: 'bet365' }]);
  assert.ok(conCasa.includes('bet365') && conCasa.includes('1.47') && conCasa.includes('Cuota publicada'));
  const sinCasa = tarjetasTerminadas([terminado]);
  assert.ok(sinCasa.includes('Cuota del modelo') && sinCasa.includes('1 ÷ probabilidad'));
});
