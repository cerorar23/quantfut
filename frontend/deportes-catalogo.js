// Catálogo de deportes de la web (Fase 2 del menú «Web y App», parte E de harness/tareas.md).
//
// El servidor (GET /cliente/v1/config, contrato 1) manda `deportes: [{id, orden, estado, nombre{}, slug{}, ...}]`.
// Esta copia incrustada es lo que hay hoy (mismos slugs que las URL de src/qf/api/rutas_web.py: en /en/ y /pt/ el
// slug es el mismo) y es el respaldo: mientras la configuración no llega, o si llega sin `deportes` o inválida,
// la web se comporta exactamente como antes. Nunca se devuelve una lista vacía.
export const DEPORTES_RESPALDO = [
  { id: 'futbol', orden: 1, estado: 'on', nombre: { es: 'Fútbol', en: 'Football', pt: 'Futebol' }, slug: { es: 'futbol', en: 'futbol', pt: 'futbol' } },
  { id: 'nba', orden: 2, estado: 'on', nombre: { es: 'NBA', en: 'NBA', pt: 'NBA' }, slug: { es: 'nba', en: 'nba', pt: 'nba' } },
  { id: 'tenis', orden: 3, estado: 'on', nombre: { es: 'Tenis', en: 'Tennis', pt: 'Tênis' }, slug: { es: 'tenis', en: 'tenis', pt: 'tenis' } },
];
// Hoy la web muestra los nombres en español en todos los idiomas: se conserva con la copia incrustada.
const NOMBRE_RESPALDO_ES = { futbol: 'Fútbol', nba: 'NBA', tenis: 'Tenis' };

const LANGS = ['es', 'en', 'pt'];
const ID_RE = /^[a-z][a-z0-9_]{1,23}$/;
const SLUG_RE = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;
const ESTADOS = new Set(['on', 'preview']);   // `off` no sale del servidor; cualquier otro valor se ignora

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
    validos.push({ id: d.id, orden, estado: d.estado, nombre, slug: slugs });
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
    slug: d.slug[LANGS.includes(lang) ? lang : 'es'] || d.slug.es,
  }));
}

/** URL de la petición al catálogo para un idioma. */
export const urlCatalogo = lang => `/cliente/v1/config?cliente=web&contrato=1&lang=${encodeURIComponent(LANGS.includes(lang) ? lang : 'es')}`;
