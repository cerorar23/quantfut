// Rutas de la SPA con URL propia (F1.2b de docs/plan_seo_redes_web_20261108.md).
//
// Las secciones públicas tienen una URL limpia (/historial/) que el servidor responde con su propio <head> y
// un HTML inicial. Las demás (cuenta, acceso, pago, análisis…) siguen con `#`: no son contenido indexable y
// el retorno de Whop (`/?checkout=1#checkout`) y los correos dependen de ello.
//
// ROUTE_PATH debe coincidir con SECCIONES de src/qf/api/rutas_web.py: tests/test_rutas_web.py lo comprueba.
export const ROUTE_PATH = {
  inicio: '/', partidos: '/partidos/', picks: '/pronosticos/', historial: '/historial/',
  alta: '/pronosticos-alta-probabilidad/', parley: '/parley-del-dia/', escalera: '/reto-escalera/',
  paquetes: '/paquetes/', planes: '/planes/',
};
const PATH_ROUTE = Object.fromEntries(Object.entries(ROUTE_PATH).map(([route, path]) => [path, route]));
const withSlash = path => (path.endsWith('/') ? path : `${path}/`);

// Páginas de NBA con URL propia (/nba/ y /nba/<local>-vs-<visitante>-<AAAA-MM-DD>/): el servidor las responde con el
// mismo shell de la SPA y deja en <html> qué abrir. `/nba/v1` y `/nba/v2` son los motores, no páginas.
const NBA_PATH = /^\/nba\/(?:(?!v[12]\/)[a-z0-9]+(?:-[a-z0-9]+)*\/)?$/;
export const isNbaPage = loc => NBA_PATH.test(withSlash(loc.pathname || '/'));

/** URL que se muestra al entrar en una ruta: la limpia si la tiene, y si no `/#ruta`. */
export const urlFor = route => ROUTE_PATH[route] ?? `/#${route}`;

/**
 * Ruta que pide una ubicación, o null si no pide ninguna conocida. Manda el hash —las rutas sin URL
 * propia y los enlaces antiguos `/#historial`— y después el camino.
 */
export function routeFromLocation(loc, valid, canonical = route => route) {
  const hashed = canonical(String(loc.hash || '').slice(1));
  if (valid(hashed)) return hashed;
  if (isNbaPage(loc)) return 'partidos';
  return PATH_ROUTE[withSlash(loc.pathname || '/')] ?? null;
}

/** URL limpia a la que hay que llevar una ubicación con hash antiguo (`/#historial` → `/historial/`), o null. */
export function cleanUrl(loc, route) {
  if (isNbaPage(loc) && !loc.hash) return null;   // /nba/… ya es una URL limpia: no se reescribe a /partidos/
  const path = ROUTE_PATH[route];
  if (!path) return null;
  return (withSlash(loc.pathname || '/') !== path || loc.hash) ? path : null;
}

/** Entrada que `navigate()` añade al historial, o null si la barra ya muestra esa ruta. */
export function historyEntry(loc, route) {
  const target = urlFor(route);
  const current = `${withSlash(loc.pathname || '/')}${loc.hash || ''}`;
  return current === target ? null : target;
}

/**
 * Qué abrir al entrar por una página de NBA: el deporte y, si es la página de un partido, ese partido y el día
 * (desplazamiento respecto a hoy, entre -3 y 3, como el resto de la ventana). `data` es `document.documentElement.dataset`.
 */
export function nbaBoot(data, loc, now = new Date()) {
  if (!isNbaPage(loc) || data?.deporte !== 'nba') return null;
  const id = String(data.nbaEvento || '');
  if (!/^[0-9]+$/.test(id)) return { sport: 'nba', winEvent: '', winDay: 0 };
  const start = new Date(data.nbaInicio || NaN);
  let winDay = 0;
  if (!Number.isNaN(start.getTime())) {
    const day = new Date(start); day.setHours(0, 0, 0, 0);
    const today = new Date(now); today.setHours(0, 0, 0, 0);
    winDay = Math.max(-3, Math.min(3, Math.round((day - today) / 86400000)));
  }
  return { sport: 'nba', winEvent: `nba:${id}`, winDay };
}
