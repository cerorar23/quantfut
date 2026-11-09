import test from 'node:test';
import assert from 'node:assert/strict';
import { ROUTE_PATH, urlFor, routeFromLocation, cleanUrl, historyEntry, isNbaPage, nbaBoot } from './rutas.js';

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

test('las páginas de NBA entran en la ventana de partidos y no se reescriben a /partidos/', () => {
  for (const path of ['/nba/', '/nba', '/nba/chicago-bulls-vs-philadelphia-76ers-2026-11-08/']) {
    assert.equal(isNbaPage(at(path)), true, path);
    assert.equal(route(at(path)), 'partidos', path);
    assert.equal(cleanUrl(at(path), 'partidos'), null, path);
  }
  // los motores no son páginas
  for (const path of ['/nba/v1/cartelera', '/nba/v2/', '/nba/v2', '/nba/v1/', '/nba/a/b/', '/nbax/']) {
    assert.equal(isNbaPage(at(path)), false, path);
  }
  assert.equal(isNbaPage(at('/nba/v10-algo/')), true);
  // un enlace con hash antiguo dentro de /nba/ sigue mandando el hash
  assert.equal(route(at('/nba/', '#historial')), 'historial');
});

test('al entrar en una página de partido la app abre ese partido y su día', () => {
  const loc = at('/nba/chicago-bulls-vs-philadelphia-76ers-2026-11-08/');
  const now = new Date(2026, 10, 8, 12, 0);   // 8-nov, hora local
  const hoy = nbaBoot({ deporte: 'nba', nbaEvento: '18220', nbaInicio: new Date(2026, 10, 8, 15, 30).toISOString() }, loc, now);
  assert.deepEqual(hoy, { sport: 'nba', winEvent: 'nba:18220', winDay: 0 });
  const ayer = nbaBoot({ deporte: 'nba', nbaEvento: '18200', nbaInicio: new Date(2026, 10, 7, 20, 0).toISOString() }, loc, now);
  assert.equal(ayer.winDay, -1);
  const lejos = nbaBoot({ deporte: 'nba', nbaEvento: '1', nbaInicio: new Date(2026, 9, 1, 20, 0).toISOString() }, loc, now);
  assert.equal(lejos.winDay, -3);   // fuera de la ventana de la app: se queda en el límite
});

test('el pilar abre NBA sin partido, y lo demás no arranca nada', () => {
  assert.deepEqual(nbaBoot({ deporte: 'nba' }, at('/nba/')), { sport: 'nba', winEvent: '', winDay: 0 });
  assert.equal(nbaBoot({ deporte: 'nba', nbaEvento: 'x;alert(1)' }, at('/nba/a-vs-b-2026-11-08/')).winEvent, '');   // id no numérico: se ignora
  assert.equal(nbaBoot({}, at('/nba/')), null);                          // sin la marca del servidor
  assert.equal(nbaBoot({ deporte: 'nba', nbaEvento: '1' }, at('/historial/')), null);   // otra ruta
});
