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

// La web usa la misma asignación real gratis/VIP que la app. El servidor
// omite los datos bloqueados antes de enviarlos; el navegador no los inventa.
export function loadForecastHome(date, fetcher = fetch) {
  const params = new URLSearchParams({ fecha: localDay(date), tz: String(tzMinutes(date)) });
  return getJson(`/mobile/v1/home?${params}`,
    value => value && Array.isArray(value.agenda)
      && value.agenda.every(g => typeof g.match_id === 'string' && g.kickoff_utc && g.liga?.nombre && g.local?.nombre && g.visitante?.nombre)
      && value.alta_probabilidad
      && Array.isArray(value.alta_probabilidad.proximos) && Array.isArray(value.alta_probabilidad.vip), fetcher);
}

export function loadForecastMatch(matchId, fetcher = fetch) {
  return getJson(`/mobile/v1/matches/${encodeURIComponent(matchId)}`,
    value => value && value.ficha && value.ficha.partido && value.ficha.local && value.ficha.visitante && Array.isArray(value.picks), fetcher);
}

export function forecastGames(home, date) {
  const day = localDay(date);
  return (home?.agenda || []).filter(game => game.kickoff_utc
    && localDay(new Date(game.kickoff_utc)) === day);
}

export function publicForecasts(home) {
  return (home?.alta_probabilidad?.proximos || []).filter(p => p.locked !== true
    && typeof p.prob === 'number' && Number.isFinite(p.prob) && p.prob > 0 && p.prob < 1
    && p.chain_sha256 && p.pick_key);
}

export function modelProbabilities(game) {
  const p = game?.probabilities;
  if (!p || ['home','draw','away'].some(k => typeof p[k] !== 'number' || !Number.isFinite(p[k]) || p[k] < 0 || p[k] > 1)
      || Math.abs(p.home + p.draw + p.away - 1) > .005) return null;
  return p;
}

// Pronóstico destacado: entre los publicados y abiertos con cuota de 1,40 a 1,80,
// el de mayor probabilidad. No genera nada: solo elige entre lo que envía el servidor.
export const FEATURED_ODDS = Object.freeze({ min: 1.4, max: 1.8 });

export function featuredPick(picks) {
  const open = (Array.isArray(picks) ? picks : []).filter(p => p && p.locked !== true && p.chain_sha256
    && typeof p.prob === 'number' && Number.isFinite(p.prob) && p.prob > 0 && p.prob < 1
    && typeof p.ref_price === 'number' && Number.isFinite(p.ref_price)
    && p.ref_price >= FEATURED_ODDS.min && p.ref_price <= FEATURED_ODDS.max);
  return open.reduce((best, p) => (!best || p.prob > best.prob ? p : best), null);
}
