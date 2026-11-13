// Rutas de la SPA con URL propia (F1.2b de docs/plan_seo_redes_web_20261108.md).
//
// Las secciones públicas tienen una URL limpia (/historial/) que el servidor responde con su propio <head> y
// un HTML inicial. Las demás (cuenta, acceso, pago, análisis…) siguen con `#`: no son contenido indexable y
// el retorno de Whop (`/?checkout=1#checkout`) y los correos dependen de ello.
//
// ROUTE_PATH debe coincidir con SECCIONES de src/qf/api/rutas_web.py: tests/test_rutas_web.py lo comprueba.
// Catálogo de deportes de la web (Fase 2 del menú «Web y App», parte E de harness/tareas.md).
//
// El servidor (GET /cliente/v1/config, contrato 1) manda `deportes: [{id, orden, estado, nombre{}, slug{}, ...}]`.
// Esta copia incrustada es lo que hay hoy (mismos slugs que las URL reales: en /pt/ el fútbol es «futebol», src/qf/api/futbol_pt.py) y es el respaldo: mientras la configuración no llega, o si llega sin `deportes` o inválida,
// la web se comporta exactamente como antes. Nunca se devuelve una lista vacía.
export const DEPORTES_RESPALDO = [
  { id: 'futbol', orden: 1, estado: 'on', nombre: { es: 'Fútbol', en: 'Football', pt: 'Futebol' }, slug: { es: 'futbol', en: 'futbol', pt: 'futebol' } },
  { id: 'nba', orden: 2, estado: 'on', nombre: { es: 'NBA', en: 'NBA', pt: 'NBA' }, slug: { es: 'nba', en: 'nba', pt: 'nba' } },
  { id: 'tenis', orden: 3, estado: 'on', nombre: { es: 'Tenis', en: 'Tennis', pt: 'Tênis' }, slug: { es: 'tenis', en: 'tenis', pt: 'tenis' } },
];
// Hoy la web muestra los nombres en español en todos los idiomas: se conserva con la copia incrustada.
const NOMBRE_RESPALDO_ES = { futbol: 'Fútbol', nba: 'NBA', tenis: 'Tenis' };

const LANGS = ['es', 'en', 'pt'];
const ID_RE = /^[a-z][a-z0-9_]{1,23}$/;
const SLUG_RE = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;
const ESTADOS = new Set(['on', 'preview']);   // `off` no sale del servidor; cualquier otro valor se ignora

// Familias de mercados del deporte (`deportes[].familias`): `[{id, orden, nombre{}}]`. Las que no cumplen se ignoran; sin ninguna válida, no hay campo.
const FAMILIA_ID_RE = /^[a-z][a-z0-9_]{0,39}$/;
function familiasValidas(lista) {
  if (!Array.isArray(lista)) return null;
  const vistas = new Set();
  const out = [];
  for (const f of lista) {
    if (!f || typeof f !== 'object' || typeof f.id !== 'string' || !FAMILIA_ID_RE.test(f.id) || vistas.has(f.id)) continue;
    vistas.add(f.id);
    out.push({ id: f.id, orden: Number.isFinite(f.orden) ? f.orden : 9999, nombre: f.nombre && typeof f.nombre === 'object' ? f.nombre : {} });
  }
  return out.length ? out.map((f, i) => [f, i]).sort((a, b) => a[0].orden - b[0].orden || a[1] - b[1]).map(([f]) => f) : null;
}

/**
 * Valida la respuesta del servidor. Devuelve la lista de deportes (solo los válidos, ordenados por `orden`) o
 * null si la respuesta no trae `deportes`, no es una lista o no queda ninguno válido: quien llama conserva lo que tiene.
 */
export function normalizarDeportes(respuesta) {
  const lista = respuesta?.deportes;
  if (!Array.isArray(lista)) return null;
  const vistos = new Set();
  const validos = [];
  for (const d of lista) {
    if (!d || typeof d !== 'object' || typeof d.id !== 'string' || !ID_RE.test(d.id) || vistos.has(d.id)) continue;
    if (!ESTADOS.has(d.estado)) continue;
    const slug = d.slug && typeof d.slug === 'object' ? d.slug : null;
    if (!slug || typeof slug.es !== 'string' || !SLUG_RE.test(slug.es)) continue;
    const slugs = { es: slug.es };
    for (const l of ['en', 'pt']) slugs[l] = typeof slug[l] === 'string' && SLUG_RE.test(slug[l]) ? slug[l] : slug.es;
    const nombre = d.nombre && typeof d.nombre === 'object' ? d.nombre : {};
    const orden = Number.isFinite(d.orden) ? d.orden : 9999;
    vistos.add(d.id);
    const familias = familiasValidas(d.familias);
    validos.push({ id: d.id, orden, estado: d.estado, nombre, slug: slugs, ...(familias ? { familias } : {}) });
  }
  if (!validos.length) return null;
  return validos.map((d, i) => [d, i]).sort((a, b) => a[0].orden - b[0].orden || a[1] - b[1]).map(([d]) => d);
}

/** Nombre en el idioma pedido; cae a `es`, y a la copia incrustada si el servidor no lo trae. */
export function nombreDeporte(deporte, lang = 'es') {
  const n = deporte?.nombre || {};
  const pick = v => (typeof v === 'string' && v.trim() ? v.trim() : '');
  return pick(n[lang]) || pick(n.es) || NOMBRE_RESPALDO_ES[deporte?.id] || deporte?.id || '';
}

/**
 * Deportes de la navegación: sin los `preview` (siguen alcanzables por su URL) y en el orden del servidor.
 * `catalogo` es el resultado de `normalizarDeportes` o null (respaldo). Con el respaldo, los nombres son los de hoy
 * en español en todos los idiomas; con datos del servidor, `nombre[idioma]`.
 * Si todo quedara fuera de la navegación se conserva el primer deporte del catálogo: nunca una web sin deportes.
 */
export function deportesNavegacion(catalogo, lang = 'es') {
  const base = catalogo || DEPORTES_RESPALDO;
  const delServidor = Boolean(catalogo);
  let nav = base.filter(d => d.estado !== 'preview');
  if (!nav.length) nav = [base[0]];
  return nav.map(d => ({
    id: d.id,
    label: delServidor ? nombreDeporte(d, lang) : NOMBRE_RESPALDO_ES[d.id],
    slug: d.slug.es,   // el href no lleva prefijo de idioma (como el `/${id}/` de antes): siempre el slug en español
  }));
}

/** Nombre de una familia de mercados en el idioma pedido (`deportes[].familias[].nombre`); cae a `es` y, sin nombre, al id legible. `otros` no viene del catálogo. */
export function nombreFamilia(deporte, familiaId, lang = 'es') {
  const f = deporte?.familias?.find(x => x.id === familiaId);
  const pick = v => (typeof v === 'string' && v.trim() ? v.trim() : '');
  return pick(f?.nombre?.[lang]) || pick(f?.nombre?.es) || (familiaId === 'otros' ? 'Otros' : String(familiaId).replace(/_/g, ' ').replace(/^./, c => c.toUpperCase()));
}

// ── Definición de pantallas (Fase 4 · 4.2/4.4): `/cliente/v1/config` puede traer `pantallas: {deporte|partido: {'*'|<deporte>: [bloque]}}`.
// Sin ella (hoy), cada pantalla conserva su orden en código. Tipo, sección o parámetro desconocidos se IGNORAN; una lista sin secciones visibles
// (después de ignorar lo desconocido) equivale a «sin definición». Los bloques `build_min_app` son cosa de la app: la web no los lee.
export const PANTALLA_SECCIONES = {
  deporte: ['dias', 'resumen', 'destacado', 'partidos'],
  partido: ['cabecera', 'pronostico', 'mercados', 'contenido', 'sello', 'estadisticas', 'h2h', 'alertas'],
};
const BLOQUE_ID_RE = /^[a-z0-9_]{1,40}$/;
const TONOS = new Set(['info', 'exito', 'aviso', 'peligro']);
const MAX_BLOQUES_PANTALLA = 20;
function bloquePantalla(pantalla, b) {
  if (!b || typeof b !== 'object' || typeof b.id !== 'string' || !BLOQUE_ID_RE.test(b.id)) return null;
  const visible = b.visible !== false;
  const params = b.params && typeof b.params === 'object' && !Array.isArray(b.params) ? b.params : {};
  if (b.tipo === 'seccion') return PANTALLA_SECCIONES[pantalla].includes(b.seccion) ? { id: b.id, tipo: 'seccion', seccion: b.seccion, visible } : null;
  if (b.tipo === 'aviso') return params.texto && typeof params.texto === 'object' ? { id: b.id, tipo: 'aviso', visible, params } : null;
  if (b.tipo === 'vip') return { id: b.id, tipo: 'vip', visible, params };
  return null;
}
/** `pantallas` de la respuesta de configuración, validadas y sin repetir secciones; null si no hay ninguna definición utilizable. */
export function normalizarPantallas(respuesta) {
  const origen = respuesta?.pantallas;
  if (!origen || typeof origen !== 'object' || Array.isArray(origen)) return null;
  const out = {};
  for (const pantalla of Object.keys(PANTALLA_SECCIONES)) {
    const porDeporte = origen[pantalla];
    if (!porDeporte || typeof porDeporte !== 'object' || Array.isArray(porDeporte)) continue;
    for (const [clave, lista] of Object.entries(porDeporte)) {
      if ((clave !== '*' && !ID_RE.test(clave)) || !Array.isArray(lista)) continue;
      const vistas = new Set();
      const bloques = lista.slice(0, MAX_BLOQUES_PANTALLA).map(b => bloquePantalla(pantalla, b))
        .filter(b => b && (b.tipo !== 'seccion' || !vistas.has(b.seccion) && vistas.add(b.seccion)));
      if (!bloques.some(b => b.tipo === 'seccion' && b.visible)) continue;
      (out[pantalla] ??= {})[clave] = bloques;
    }
  }
  return out.deporte || out.partido ? out : null;
}
/** Definición vigente de una pantalla para un deporte: la del deporte concreto gana sobre `'*'`; sin ninguna, null (orden en código). */
export const pantallaResuelta = (pantallas, pantalla, deporte) => pantallas?.[pantalla]?.[deporte] ?? pantallas?.[pantalla]?.['*'] ?? null;
/** Datos de un bloque `aviso`: texto en el idioma (cae a `es`), tono (info|exito|aviso|peligro; otro valor = info) y enlace relativo opcional. Null si no tiene texto. */
export function datosAviso(bloque, lang = 'es') {
  const t = bloque?.params?.texto;
  const pick = v => (typeof v === 'string' && v.trim() ? v.trim() : '');
  const texto = pick(t?.[lang]) || pick(t?.es);
  if (!texto) return null;
  const enlace = bloque.params.enlace;
  return { texto, tono: TONOS.has(bloque.params.tono) ? bloque.params.tono : 'info',
    enlace: typeof enlace === 'string' && /^\/[^/\s]\S*$/.test(enlace) ? enlace : null };
}

/** URL de la petición al catálogo para un idioma. */
export const urlCatalogo = lang => `/cliente/v1/config?cliente=web&contrato=1&lang=${encodeURIComponent(LANGS.includes(lang) ? lang : 'es')}`;

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

// Páginas informativas, legales y de herramientas (src/qf/api/paginas.py, legal.py, calibracion.py, cuota_justa.py, verificacion.py): el servidor las responde dentro del mismo shell que
// fútbol, NBA y tenis y deja su texto en [data-info-contenido]; la ruta `info` de la app lo conserva en su <main>.
export const INFO_PATHS = new Set([
  '/metodologia/', '/juego-responsable/', '/sobre-nosotros/', '/legal/terminos/', '/legal/privacidad/',
  '/en/methodology/', '/en/responsible-gambling/', '/en/about/', '/en/legal/terms/', '/en/legal/privacy/',
  '/pt/metodologia/', '/pt/jogo-responsavel/', '/pt/sobre-nos/', '/pt/legal/termos/', '/pt/legal/privacidade/',
  '/legal/eliminar-cuenta/', '/en/legal/delete-account/', '/pt/legal/excluir-conta/',
  '/calibracion/', '/calculadora-cuota-justa/', '/verificacion/',
  '/en/calibration/', '/en/fair-odds-calculator/', '/en/verification/',
  '/pt/calibracao/', '/pt/calculadora-odd-justa/', '/pt/verificacao/',
]);

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
// Los slugs llegan de la configuración (abajo); la copia incrustada es el respaldo. Tras quitar el prefijo /en o /pt se
// acepta el slug de CUALQUIER idioma del deporte (p. ej. /pt/futebol/ y /futbol/). La estructura del camino depende del
// deporte: nba, tenis y fútbol tienen la suya; uno nuevo usa la genérica.
const ESTRUCTURA = {
  nba: slugs => new RegExp(`^/${slugs}/(?:equipos/${SEG}/|(?!v[12]/|equipos/)${SEG}/)?$`),
  tenis: slugs => new RegExp(`^/${slugs}/(?:(?!v2/)${SEG}/(?:${SEG}/)?)?$`),
  futbol: slugs => new RegExp(`^/${slugs}/(?:${SEG}/(?:${SEG}/)?)?$`),
};
const genericaPath = slugs => new RegExp(`^/${slugs}/(?:${SEG}/(?:${SEG}/)?)?$`);
function construirDeportePath(deportes) {
  const mapa = {};
  for (const d of deportes) {
    const slugs = [...new Set(['es', 'en', 'pt'].map(l => d.slug?.[l]).filter(Boolean))];
    mapa[d.id] = (ESTRUCTURA[d.id] || genericaPath)(`(?:${slugs.join('|')})`);
  }
  return mapa;
}
let DEPORTE_PATH = construirDeportePath(DEPORTES_RESPALDO);
/** Fija los deportes de la configuración; sin lista válida conserva los que hay (nunca se queda sin deportes). */
export function fijarDeportes(catalogo) {
  if (Array.isArray(catalogo) && catalogo.length) DEPORTE_PATH = construirDeportePath(catalogo);
}
// La página `/{slug}/` de un deporte del catálogo sin página propia (src/qf/api/deporte_generico.py) llega con `<html data-deporte=…>` ANTES de que el catálogo
// se descargue: sin esto su URL no se reconocería hasta entonces. Solo vale para esa misma ruta (`ruta`), no para otra de un solo segmento.
let PAGINA_DEPORTE = null;
/** Registra el deporte que el servidor puso en esta página (`dataset.deporte`) si su URL es `/{slug}/`. Llamar antes de calcular la ruta inicial. */
export function fijarPaginaDeporte(data, loc) {
  const id = data?.deporte, ruta = withSlash(loc?.pathname || '/');
  PAGINA_DEPORTE = typeof id === 'string' && ID_RE.test(id) && new RegExp(`^/${SEG}/$`).test(ruta) ? { id, ruta } : null;
}
/** Deporte de una página con URL propia (su `id` en el catálogo: 'nba' | 'tenis' | 'futbol'…) o null. */
export function deporteDeUrl(loc) {
  const path = withSlash(loc.pathname || '/').replace(/^\/(?:en|pt)(?=\/)/, '');
  return Object.keys(DEPORTE_PATH).find(sport => DEPORTE_PATH[sport].test(path)) ?? (PAGINA_DEPORTE?.ruta === path ? PAGINA_DEPORTE.id : null);
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
  if (INFO_PATHS.has(path)) return 'info';
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
  // nba y tenis tienen ids numéricos; un deporte nuevo del catálogo, cualquier id seguro del contrato.
  if (!(ESTRUCTURA[sport] ? /^[0-9]+$/ : /^[A-Za-z0-9._:-]{1,120}$/).test(id)) return { sport, patch: { sport, winEvent: '', winDay: 0 } };
  return { sport, patch: { sport, winEvent: `${sport}:${id}`, winDay: dayOffset(inicio, now, -3, 3), winDayPinned: true,
    winSportTab: 'resumen', winPane: 'pron' } };
}
