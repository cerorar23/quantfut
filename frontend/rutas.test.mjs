import test from 'node:test';
import assert from 'node:assert/strict';
import { ROUTE_PATH, urlFor, routeFromLocation, cleanUrl, historyEntry, deporteDeUrl, isDeportePage, deporteBoot } from './rutas.js';

// Las rutas válidas de app.js (routeTitle) y sus alias, para probar la resolución como en la SPA.
const VALID = new Set(['inicio', 'partidos', 'picks', 'alta', 'escalera', 'parley', 'partido', 'historial', 'planes',
  'cuenta', 'paquetes', 'acceso', 'checkout', 'mercados', 'analisis']);
const ALIAS = { mercados: 'partidos', partido: 'partidos' };
const valid = route => VALID.has(route);
const canonical = route => ALIAS[route] || route;
const at = (pathname, hash = '', search = '') => ({ pathname, hash, search });
const route = loc => routeFromLocation(loc, valid, canonical);

test('cada sección pública tiene una URL limpia, con barra final y única', () => {
  const paths = Object.values(ROUTE_PATH);
  assert.equal(new Set(paths).size, paths.length);
  for (const [name, path] of Object.entries(ROUTE_PATH)) {
    assert.ok(valid(name), `${name} no es una ruta de la SPA`);
    assert.match(path, /^\/([a-z0-9-]+\/)?$/);
  }
  assert.equal(ROUTE_PATH.inicio, '/');
});

test('las rutas sin URL propia siguen con hash', () => {
  for (const name of ['cuenta', 'acceso', 'checkout', 'analisis']) {
    assert.equal(ROUTE_PATH[name], undefined);
    assert.equal(urlFor(name), `/#${name}`);
  }
  assert.equal(urlFor('historial'), '/historial/');
});

test('una URL limpia entra en su sección', () => {
  assert.equal(route(at('/historial/')), 'historial');
  assert.equal(route(at('/historial')), 'historial');               // sin barra final también
  assert.equal(route(at('/pronosticos/')), 'picks');
  assert.equal(route(at('/reto-escalera/')), 'escalera');
  assert.equal(route(at('/')), 'inicio');
});

test('un enlace antiguo con hash sigue funcionando y manda sobre el camino', () => {
  assert.equal(route(at('/', '#historial')), 'historial');
  assert.equal(route(at('/', '#picks')), 'picks');
  assert.equal(route(at('/historial/', '#cuenta')), 'cuenta');       // ruta sin URL propia
  assert.equal(route(at('/', '#mercados')), 'partidos');             // alias
});

test('el retorno de Whop y las rutas de pago no se tocan', () => {
  assert.equal(route(at('/', '#checkout', '?checkout=1')), 'checkout');
  assert.equal(cleanUrl(at('/', '#checkout', '?checkout=1'), 'checkout'), null);
  assert.equal(historyEntry(at('/', '#checkout'), 'checkout'), null);
});

test('rutas desconocidas no inventan sección', () => {
  assert.equal(route(at('/otra-cosa/')), null);
  assert.equal(route(at('/', '#no-existe')), 'inicio');           // un hash inválido se ignora; manda el camino
  assert.equal(route(at('/otra-cosa/', '#no-existe')), null);
  assert.equal(route(at('/historial/x/')), null);
});

test('un hash antiguo se convierte en la URL limpia, y una limpia se deja como está', () => {
  assert.equal(cleanUrl(at('/', '#historial'), 'historial'), '/historial/');
  assert.equal(cleanUrl(at('/', '#picks'), 'picks'), '/pronosticos/');
  assert.equal(cleanUrl(at('/', '#inicio'), 'inicio'), '/');
  assert.equal(cleanUrl(at('/historial/'), 'historial'), null);
  assert.equal(cleanUrl(at('/', '#cuenta'), 'cuenta'), null);
});

test('navegar añade una entrada solo si la barra no muestra ya esa ruta', () => {
  assert.equal(historyEntry(at('/'), 'historial'), '/historial/');
  assert.equal(historyEntry(at('/historial/'), 'historial'), null);
  assert.equal(historyEntry(at('/historial/'), 'inicio'), '/');
  assert.equal(historyEntry(at('/historial/'), 'cuenta'), '/#cuenta');   // pasa a hash y sale de la sección
  assert.equal(historyEntry(at('/', '#cuenta'), 'cuenta'), null);
  assert.equal(historyEntry(at('/', '#cuenta'), 'planes'), '/planes/');
});

test('ida y vuelta: lo que navigate muestra es lo que routeFromLocation lee', () => {
  for (const name of VALID) {
    const entry = urlFor(name);
    const [pathname, hash = ''] = entry.split('#');
    const back = route(at(pathname, hash ? `#${hash}` : ''));
    assert.equal(back, canonical(name), `${name} → ${entry} → ${back}`);
  }
});

test('las páginas de deporte entran en la ventana de partidos y no se reescriben a /partidos/', () => {
  const buenas = {
    nba: ['/nba/', '/nba', '/nba/chicago-bulls-vs-philadelphia-76ers-2026-11-08/', '/nba/v10-algo/', '/nba/equipos/boston-celtics/'],
    tenis: ['/tenis/', '/tenis', '/tenis/atp-finals/', '/tenis/atp-finals/sinner-vs-alcaraz-2026-11-12/'],
    futbol: ['/futbol/', '/futbol/liga-mx/', '/futbol/liga-mx/club-queretaro-vs-puebla-2026-11-09/'],
  };
  for (const [sport, paths] of Object.entries(buenas)) {
    for (const path of paths) {
      assert.equal(deporteDeUrl(at(path)), sport, path);
      assert.equal(isDeportePage(at(path)), true, path);
      assert.equal(route(at(path)), 'partidos', path);
      assert.equal(cleanUrl(at(path), 'partidos'), null, path);
    }
  }
  // los motores no son páginas
  for (const path of ['/nba/v1/cartelera', '/nba/v2/', '/nba/v2', '/nba/v1/', '/nba/a/b/', '/nbax/', '/tenis/v2/cartelera',
    '/tenis/v2/', '/tenis/v2', '/futbol/a/b/c/', '/futbolx/', '/historial/', '/nba/equipos/', '/nba/equipos/a/b/']) {
    assert.equal(isDeportePage(at(path)), false, path);
  }
  // un enlace con hash antiguo dentro de /nba/ sigue mandando el hash
  assert.equal(route(at('/nba/', '#historial')), 'historial');
});

const hoyLocal = new Date(2026, 10, 8, 12, 0);   // 8-nov, hora local
const iso = (d, h = 20) => new Date(2026, 10, d, h, 0).toISOString();

test('NBA y tenis: al entrar en un partido la app abre ese evento y su día', () => {
  const nba = at('/nba/chicago-bulls-vs-philadelphia-76ers-2026-11-08/');
  const hoy = deporteBoot({ deporte: 'nba', evento: '18220', inicio: iso(8, 15) }, nba, hoyLocal);
  assert.deepEqual(hoy, { sport: 'nba', patch: { sport: 'nba', winEvent: 'nba:18220', winDay: 0, winDayPinned: true, winSportTab: 'resumen', winPane: 'pron' } });
  assert.equal(deporteBoot({ deporte: 'nba', evento: '18200', inicio: iso(7) }, nba, hoyLocal).patch.winDay, -1);
  assert.equal(deporteBoot({ deporte: 'nba', evento: '1', inicio: new Date(2026, 9, 1, 20).toISOString() }, nba, hoyLocal).patch.winDay, -3);
  const tenis = deporteBoot({ deporte: 'tenis', evento: '12176073', inicio: iso(9) }, at('/tenis/atp-finals/a-vs-b-2026-11-09/'), hoyLocal);
  assert.equal(tenis.patch.winEvent, 'tenis:12176073');
  assert.equal(tenis.patch.winDay, 1);
});

test('compatibilidad: el HTML de F2.1 ya desplegado usaba nbaEvento y nbaInicio', () => {
  const r = deporteBoot({ deporte: 'nba', nbaEvento: '18220', nbaInicio: iso(8, 15) }, at('/nba/x-vs-y-2026-11-08/'), hoyLocal);
  assert.equal(r.patch.winEvent, 'nba:18220');
});

test('fútbol: al entrar en un partido la app fija statsMatch y statsDay dentro de la ventana -1..3', () => {
  const loc = at('/futbol/liga-mx/club-queretaro-vs-puebla-2026-11-09/');
  const id = 'mx.liga_mx:2627:queretaro-puebla:20261109';
  assert.deepEqual(deporteBoot({ deporte: 'futbol', evento: id, inicio: iso(9) }, loc, hoyLocal),
    { sport: 'futbol', patch: { sport: 'futbol', statsMatch: id, statsDay: 1, statsLeague: 'Todas', statsTab: 'resumen', winPane: 'pron' } });
  assert.equal(deporteBoot({ deporte: 'futbol', evento: id, inicio: iso(5) }, loc, hoyLocal).patch.statsDay, -1);
  assert.equal(deporteBoot({ deporte: 'futbol', evento: id, inicio: iso(20) }, loc, hoyLocal).patch.statsDay, 3);
});

test('el pilar abre el deporte sin partido, y lo demás no arranca nada', () => {
  assert.deepEqual(deporteBoot({ deporte: 'nba' }, at('/nba/')), { sport: 'nba', patch: { sport: 'nba', winEvent: '', winDay: 0 } });
  assert.deepEqual(deporteBoot({ deporte: 'futbol' }, at('/futbol/')), { sport: 'futbol', patch: { sport: 'futbol' } });
  assert.equal(deporteBoot({ deporte: 'tenis', evento: 'x;alert(1)' }, at('/tenis/t/a-vs-b-2026-11-08/')).patch.winEvent, '');   // id no numérico
  assert.deepEqual(deporteBoot({ deporte: 'futbol', evento: '<img src=x>' }, at('/futbol/l/a-vs-b-2026-11-08/')).patch, { sport: 'futbol' });
  assert.equal(deporteBoot({}, at('/nba/')), null);                                   // sin la marca del servidor
  assert.equal(deporteBoot({ deporte: 'nba', evento: '1' }, at('/historial/')), null); // otra ruta
  assert.equal(deporteBoot({ deporte: 'tenis', evento: '1' }, at('/nba/')), null);     // la marca no coincide con la URL
});
