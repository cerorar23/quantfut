// Agenda y fichas de partido REALES (endpoints públicos /web/partidos). Nada
// de esto se mezcla con los datos ficticios de la mesa: si la API falla, la
// vista lo dice en vez de rellenar con ejemplos.
const TIMEOUT_MS = 15000;

async function getJson(path, valid, fetcher) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), TIMEOUT_MS);
  try {
    const response = await fetcher(path, { signal: controller.signal });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json();
    if (!valid(data)) throw new Error('Formato inesperado');
    return { status: 'ready', data };
  } catch {
    return { status: 'error', data: null };
  } finally {
    clearTimeout(timeout);
  }
}

// Día local del visitante como YYYY-MM-DD.
export function localDay(date) {
  const pad = value => String(value).padStart(2, '0');
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}

// getTimezoneOffset() va al revés (UTC-6 devuelve 360): la API espera -360.
export const tzMinutes = date => -date.getTimezoneOffset();

export function loadAgenda(date, fetcher = fetch) {
  const params = new URLSearchParams({ fecha: localDay(date), tz: String(tzMinutes(date)) });
  return getJson(`/web/partidos?${params}`, value => value && Array.isArray(value.partidos), fetcher);
}

export function loadFicha(matchId, fetcher = fetch) {
  return getJson(`/web/partidos/${encodeURIComponent(matchId)}`,
    value => value && value.partido && value.local && value.visitante && value.cara_a_cara, fetcher);
}
