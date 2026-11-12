import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { ROUTE_PATH, INFO_PATHS, urlFor, routeFromLocation, cleanUrl, historyEntry, deporteDeUrl, isDeportePage, deporteBoot } from './rutas.js';

const FRONTEND_DIR = path.dirname(fileURLToPath(import.meta.url));

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

function reachableStaticModules(entryFile) {
  const seenSpecs = new Set();
  const seenFiles = new Set();
  const queue = [entryFile];
  const importRe = /^\s*import\s+(?:[\s\S]*?\bfrom\s+)?['"](\.\/[^'"]+)['"]/gm;

  while (queue.length > 0) {
    const file = queue.shift();
    if (seenFiles.has(file)) continue;
    seenFiles.add(file);
    const fullPath = path.join(FRONTEND_DIR, file);
    assert.ok(fs.existsSync(fullPath), `Falta el módulo estático ${file}`);
    const code = fs.readFileSync(fullPath, 'utf-8');
    importRe.lastIndex = 0;
    for (const match of code.matchAll(importRe)) {
      const spec = match[1];
      seenSpecs.add(spec);
      const target = spec.slice(2).split('?')[0];
      queue.push(target);
    }
  }
  return seenSpecs;
}

test('index.html precarga exactamente todos los módulos ES estáticos de app.js sin versiones obsoletas', () => {
  const expected = reachableStaticModules('app.js');
  const html = fs.readFileSync(path.join(FRONTEND_DIR, 'index.html'), 'utf-8');
  const preloads = [...html.matchAll(/<link\s+rel="modulepreload"\s+href="([^"]+)"\s*\/?>/g)].map((m) => m[1]);
  assert.equal(new Set(preloads).size, preloads.length, 'Hay enlaces modulepreload duplicados en index.html');
  assert.ok(preloads.every((href) => href.startsWith('./')), 'Los modulepreload deben usar ./ para que rutas_web los reescriba');
  assert.deepEqual(new Set(preloads), expected);
});

test('las rutas localizadas /en/ y /pt/ resuelven sección y deporte sin volver al español', () => {
  assert.equal(route(at('/en/')), 'inicio');
  assert.equal(route(at('/en/matches/')), 'partidos');
  assert.equal(route(at('/pt/previsoes/')), 'picks');
  assert.equal(cleanUrl(at('/en/matches/'), 'partidos'), null);
  assert.equal(cleanUrl(at('/en/', '#historial'), 'historial'), '/en/history/');
  assert.equal(historyEntry(at('/en/'), 'planes'), '/en/plans/');
  assert.equal(historyEntry(at('/pt/'), 'planes'), '/pt/planos/');
  assert.equal(deporteDeUrl(at('/en/nba/')), 'nba');
  assert.equal(deporteDeUrl(at('/pt/futbol/')), 'futbol');
});

test('las páginas informativas y legales con URL propia abren la ruta `info` (también con y sin barra final y en otros idiomas)', () => {
  for (const path of INFO_PATHS) {
    assert.equal(route({ pathname: path, hash: '' }), 'info', path);
    assert.equal(route({ pathname: path.slice(0, -1), hash: '' }), 'info', path);
    assert.equal(cleanUrl({ pathname: path, hash: '' }, 'info'), null, path);   // no se reescribe a /#info
  }
  for (const path of ['/metodologia/', '/legal/terminos', '/legal/privacidad', '/en/legal/terms', '/pt/legal/privacidade', '/pt/jogo-responsavel/']) {
    assert.ok(INFO_PATHS.has(path.endsWith('/') ? path : `${path}/`), path);
  }
  assert.equal(route({ pathname: '/historial/', hash: '' }), 'historial');   // las secciones de siempre no cambian
});

// ---- Catálogo de deportes (Fase 2 · E): DEPORTE_PATH se construye desde los slug recibidos ----
import { fijarDeportes } from './rutas.js';
import { DEPORTES_RESPALDO } from './rutas.js';

test('con la copia incrustada las URL de deporte son las de siempre, también en /en/ y /pt/', () => {
  for (const p of ['/nba/', '/nba/equipos/boston-celtics/', '/tenis/atp-finals/a-vs-b-2026-11-09/', '/futbol/liga-mx/', '/en/nba/', '/pt/futbol/'])
    assert.ok(isDeportePage(at(p)), p);
  for (const p of ['/nba/v1/', '/nba/v2/', '/tenis/v2/', '/baloncesto/', '/historial/', '/'])
    assert.equal(isDeportePage(at(p)), false, p);
});

test('fijarDeportes: un slug distinto sustituye al anterior y una lista inválida no cambia nada', () => {
  try {
    fijarDeportes([{ id: 'nba', slug: { es: 'baloncesto', en: 'basketball', pt: 'basquete' } }, { id: 'futbol', slug: { es: 'futbol', en: 'futbol', pt: 'futbol' } }]);
    assert.equal(deporteDeUrl(at('/baloncesto/')), 'nba');
    assert.equal(deporteDeUrl(at('/baloncesto/equipos/boston-celtics/')), 'nba');   // conserva la estructura de NBA
    assert.equal(deporteDeUrl(at('/baloncesto/v2/')), null);
    assert.equal(deporteDeUrl(at('/en/basketball/')), 'nba');
    assert.equal(deporteDeUrl(at('/pt/basquete/')), 'nba');
    assert.equal(deporteDeUrl(at('/nba/')), null);                                  // el slug viejo ya no es página de deporte
    assert.equal(deporteDeUrl(at('/tenis/')), null);                                // tenis salió del catálogo
    assert.equal(route(at('/baloncesto/')), 'partidos');
    fijarDeportes(null); fijarDeportes([]); fijarDeportes('x');
    assert.equal(deporteDeUrl(at('/baloncesto/')), 'nba');
  } finally {
    fijarDeportes(DEPORTES_RESPALDO);
  }
  assert.equal(deporteDeUrl(at('/nba/')), 'nba');
});

test('un deporte nuevo del catálogo usa la estructura genérica', () => {
  try {
    fijarDeportes([{ id: 'beisbol', slug: { es: 'beisbol', en: 'baseball', pt: 'beisebol' } }]);
    assert.equal(deporteDeUrl(at('/beisbol/')), 'beisbol');
    assert.equal(deporteDeUrl(at('/beisbol/mlb/a-vs-b-2026-11-09/')), 'beisbol');
    assert.equal(deporteDeUrl(at('/en/baseball/')), 'beisbol');
    assert.deepEqual(deporteBoot({ deporte: 'beisbol' }, at('/beisbol/')), { sport: 'beisbol', patch: { sport: 'beisbol', winEvent: '', winDay: 0 } });
  } finally {
    fijarDeportes(DEPORTES_RESPALDO);
  }
});

test('fútbol se reconoce con el slug de cualquier idioma: /pt/futebol/ y /futbol/', () => {
  for (const p of ['/pt/futebol/', '/pt/futebol/liga-mx/', '/pt/futebol/liga-mx/a-vs-b-2026-11-09/', '/futbol/', '/futbol/liga-mx/a-vs-b-2026-11-09/', '/en/futbol/', '/pt/futbol/'])
    assert.equal(deporteDeUrl(at(p)), 'futbol', p);
  assert.equal(route(at('/pt/futebol/liga-mx/a-vs-b-2026-11-09/')), 'partidos');
  assert.equal(cleanUrl(at('/pt/futebol/liga-mx/'), 'partidos'), null);   // no se reescribe a /pt/partidos/
  assert.equal(deporteDeUrl(at('/pt/futebol/a/b/c/')), null);
  assert.equal(deporteDeUrl(at('/pt/futebolx/')), null);
});
