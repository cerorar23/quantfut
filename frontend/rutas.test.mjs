import test from 'node:test';
import assert from 'node:assert/strict';
import { ROUTE_PATH, urlFor, routeFromLocation, cleanUrl, historyEntry } from './rutas.js';

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
