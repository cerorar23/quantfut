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
const LOCALIZED_ROUTE_PATH = {
  en: {
    inicio: '/en/', partidos: '/en/matches/', picks: '/en/predictions/', historial: '/en/history/',
    alta: '/en/high-probability-picks/', parley: '/en/parlay-of-the-day/', escalera: '/en/ladder-challenge/',
    paquetes: '/en/packages/', planes: '/en/plans/',
  },
  pt: {
    inicio: '/pt/', partidos: '/pt/partidos/', picks: '/pt/previsoes/', historial: '/pt/historico/',
    alta: '/pt/alta-probabilidade/', parley: '/pt/multipla-do-dia/', escalera: '/pt/desafio-escada/',
    paquetes: '/pt/pacotes/', planes: '/pt/planos/',
  },
};
const PATH_ROUTE = Object.fromEntries(Object.entries(ROUTE_PATH).map(([route, path]) => [path, route]));
const LOCALIZED_PATH_ROUTE = Object.fromEntries(
  Object.values(LOCALIZED_ROUTE_PATH).flatMap(map => Object.entries(map).map(([route, path]) => [path, route])),
);
const withSlash = path => (path.endsWith('/') ? path : `${path}/`);

/** Idioma derivado del prefijo de URL ('en' | 'pt' | 'es'). */
export function urlLang(loc) {
  const path = withSlash(loc?.pathname || '/');
  if (path.startsWith('/en/')) return 'en';
  if (path.startsWith('/pt/')) return 'pt';
  return 'es';
}

// Páginas de deporte con URL propia: /nba/<partido>/, /tenis/<torneo>/<partido>/ y /futbol/<competición>/<partido>/ (más sus
// pilares /nba/, /tenis/, /futbol/ y prefijos /en/, /pt/). El servidor las responde con el mismo shell de la SPA y deja en <html> qué abrir.
// `/nba/v1`, `/nba/v2` y `/tenis/v2` son los motores, no páginas.
const SEG = '[a-z0-9]+(?:-[a-z0-9]+)*';
const DEPORTE_PATH = {
  nba: new RegExp(`^/nba/(?:equipos/${SEG}/|(?!v[12]/|equipos/)${SEG}/)?$`),
  tenis: new RegExp(`^/tenis/(?:(?!v2/)${SEG}/(?:${SEG}/)?)?$`),
  futbol: new RegExp(`^/futbol/(?:${SEG}/(?:${SEG}/)?)?$`),
};
/** Deporte de una página con URL propia ('nba' | 'tenis' | 'futbol') o null. */
export function deporteDeUrl(loc) {
  const path = withSlash(loc.pathname || '/').replace(/^\/(?:en|pt)(?=\/)/, '');
  return Object.keys(DEPORTE_PATH).find(sport => DEPORTE_PATH[sport].test(path)) ?? null;
}
export const isDeportePage = loc => deporteDeUrl(loc) !== null;

/** URL que se muestra al entrar en una ruta: la limpia si la tiene, y si no `/#ruta`. */
export const urlFor = (route, lang = 'es') =>
  (LOCALIZED_ROUTE_PATH[lang]?.[route] ?? ROUTE_PATH[route] ?? `/#${route}`);

/**
 * Ruta que pide una ubicación, o null si no pide ninguna conocida. Manda el hash —las rutas sin URL
 * propia y los enlaces antiguos `/#historial`— y después el camino.
 */
export function routeFromLocation(loc, valid, canonical = route => route) {
  const hashed = canonical(String(loc.hash || '').slice(1));
  if (valid(hashed)) return hashed;
  if (isDeportePage(loc)) return 'partidos';
  const path = withSlash(loc.pathname || '/');
  return PATH_ROUTE[path] ?? LOCALIZED_PATH_ROUTE[path] ?? null;
}

/** URL limpia a la que hay que llevar una ubicación con hash antiguo (`/#historial` → `/historial/`), o null. */
export function cleanUrl(loc, route) {
  if (isDeportePage(loc) && !loc.hash) return null;   // /nba/…, /tenis/…, /futbol/… ya son URL limpias: no se reescriben a /partidos/
  if (!ROUTE_PATH[route]) return null;
  const path = urlFor(route, urlLang(loc));
  return (withSlash(loc.pathname || '/') !== path || loc.hash) ? path : null;
}

/** Entrada que `navigate()` añade al historial, o null si la barra ya muestra esa ruta. */
export function historyEntry(loc, route, lang = urlLang(loc)) {
  const target = urlFor(route, lang);
  const current = `${withSlash(loc.pathname || '/')}${loc.hash || ''}`;
  return current === target ? null : target;
}

const STATS_DAYS = [-1, 0, 1, 2, 3];   // misma ventana que el fútbol en app.js
const dayOffset = (startIso, now, min, max) => {
  const start = new Date(startIso || NaN);
  if (Number.isNaN(start.getTime())) return 0;
  const day = new Date(start); day.setHours(0, 0, 0, 0);
  const today = new Date(now); today.setHours(0, 0, 0, 0);
  return Math.max(min, Math.min(max, Math.round((day - today) / 86400000)));
};

/**
 * Qué abrir al entrar por una página de deporte. `data` es `document.documentElement.dataset`: el servidor deja
 * `deporte`, y en la página de un partido `evento` (y `inicio`, ISO) — antes de F3 solo NBA, con `nbaEvento`/`nbaInicio`.
 * Devuelve `{ sport, patch }`: `patch` son los campos de `state` que hay que fijar, o null si no hay nada que abrir.
 *  - NBA y tenis eligen el evento de la ventana de deportes (`winEvent = '<deporte>:<id>'`, día entre -3 y 3).
 *  - Fútbol elige `statsMatch` (el match_id) y `statsDay` (entre -1 y 3, como `STATS_DAYS` de app.js).
 */
export function deporteBoot(data, loc, now = new Date()) {
  const sport = deporteDeUrl(loc);
  if (!sport || data?.deporte !== sport) return null;
  const id = String(data.evento ?? data.nbaEvento ?? '');
  const inicio = data.inicio ?? data.nbaInicio;
  if (sport === 'futbol') {
    if (!/^[A-Za-z0-9._:-]{3,120}$/.test(id)) return { sport, patch: { sport } };
    const day = dayOffset(inicio, now, STATS_DAYS[0], STATS_DAYS[STATS_DAYS.length - 1]);
    return { sport, patch: { sport, statsMatch: id, statsDay: day, statsLeague: 'Todas', statsTab: 'resumen', winPane: 'pron' } };
  }
  if (!/^[0-9]+$/.test(id)) return { sport, patch: { sport, winEvent: '', winDay: 0 } };
  return { sport, patch: { sport, winEvent: `${sport}:${id}`, winDay: dayOffset(inicio, now, -3, 3), winDayPinned: true,
    winSportTab: 'resumen', winPane: 'pron' } };
}
