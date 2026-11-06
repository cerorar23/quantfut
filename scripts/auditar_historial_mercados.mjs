// Solo lectura de la API pública propia. No genera ni modifica pronósticos.
import fs from 'node:fs/promises';
import path from 'node:path';

const origin = 'https://pronosticosdeportivos.pro';
const root = path.resolve(process.argv[2] || '.');
const cache = path.join(root, '.local');
const out = path.join(root, 'docs');
await fs.mkdir(cache, { recursive: true });
await fs.mkdir(out, { recursive: true });
async function download(url, name) {
  const response = await fetch(new URL(url, origin), { signal: AbortSignal.timeout(40000), cache: 'no-store' });
  if (!response.ok) throw Error('No se pudo leer ' + url + ': ' + response.status);
  const body = await response.text();
  await fs.writeFile(path.join(cache, name), body);
  return body;
}
const source = await download('/sports-data.js', 'history-live-sports.js');
await Promise.all([
  ['/web/deportes/tenis', 'history-live-tennis.json'],
  ['/web/deportes/tenis/cuotas', 'history-live-tennis-quotes.json'],
  ['/mobile/v1/markets/history?limit=500', 'history-live-alta.json'],
  ['/mobile/v1/markets/destacados?desde=2026-10-26', 'history-live-football.json'],
].map(([url, name]) => download(url, name)));
const adapter = await import(`data:text/javascript;base64,${Buffer.from(source).toString('base64')}`);
const requests = [];
const fetcher = async (url, options) => {
  const response = await fetch(new URL(url, origin), options);
  requests.push({ url: new URL(url, origin).href, status: response.status });
  return response;
};
const day = process.argv[3] || '2026-11-05';
const [y, m, d] = day.split('-').map(Number);
const nba = await adapter.loadSport('nba', fetcher, new Date(y, m - 1, d, 12));
if (nba.status !== 'ready') throw Error('NBA no disponible; no se emite una auditoría vacía');
let cursor = 0;
await Promise.all(Array.from({ length: 4 }, async () => {
  while (cursor < nba.events.length) {
    const i = cursor++;
    nba.events[i] = adapter.withNbaMarkets(nba.events[i], await adapter.loadNbaMarkets(nba.events[i], fetcher));
  }
}));
const tennisBody = JSON.parse(await fs.readFile(path.join(cache, 'history-live-tennis.json'), 'utf8'));
const quotes = JSON.parse(await fs.readFile(path.join(cache, 'history-live-tennis-quotes.json'), 'utf8'));
const tennis = adapter.tennisEvents(tennisBody);
const football = [
  ...JSON.parse(await fs.readFile(path.join(cache, 'history-live-alta.json'), 'utf8')).items,
  ...JSON.parse(await fs.readFile(path.join(cache, 'history-live-football.json'), 'utf8')).items,
].filter(r => ['win', 'loss'].includes(r.outcome) &&
  new Date(r.kickoff_utc).toLocaleDateString('en-CA', { timeZone: 'America/Mexico_City' }) >= adapter.HISTORY_SINCE);

function interval(won, n) {
  if (!n) return null;
  const z = 1.959964, p = won / n, den = 1 + z * z / n;
  const center = (p + z * z / (2 * n)) / den;
  const radius = z * Math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den;
  return [center - radius, center + radius].map(v => +v.toFixed(4));
}
function record(rows) {
  const decided = rows.filter(r => ['win', 'loss'].includes(r.outcome));
  const won = decided.filter(r => r.outcome === 'win').length;
  return { n: decided.length, won, hit_rate: decided.length ? won / decided.length : null,
    wilson95: interval(won, decided.length) };
}
function sportAudit(events, sport) {
  const families = {};
  for (const e of events) {
    const featured = adapter.featuredSportMarket(e);
    for (const m of e.markets) {
      const family = m.market || m.id.split('-')[0];
      const f = families[family] ||= { model_rows: 0, published_rows: 0, published: [], web_history: [], future_candidates: [] };
      f.model_rows++;
      const published = sport === 'tenis' ? quotes.publicables?.[e.id]?.includes(m.id) : m.publicable === true;
      if (published) { f.published_rows++; f.published.push(m); }
      const since = new Date(e.start).toLocaleDateString('en-CA', { timeZone: 'America/Mexico_City' }) >= adapter.HISTORY_SINCE;
      if (since && featured?.id === m.id && !m.revised) f.web_history.push(m);
      const quote = sport === 'tenis' ? quotes.events?.[e.id]?.[m.id] : { price: m.price, book: m.book };
      if (published && !m.revised && m.outcome == null && Date.parse(e.start) > Date.now() &&
          m.probability >= .75 && quote?.price >= 1.2) {
        f.future_candidates.push({ event: e.id, market: m.id, selection: m.selection,
          probability: m.probability, price: quote.price, book: quote.book });
      }
    }
  }
  return Object.fromEntries(Object.entries(families).map(([key, f]) => [key, {
    model_rows: f.model_rows, published_rows: f.published_rows,
    published_record: record(f.published), web_record: record(f.web_history),
    future_candidates: f.future_candidates.sort((a, b) => b.probability - a.probability),
  }]));
}
const complements = Object.fromEntries(['sets_total', 'tiebreak'].map(family => {
  const rows = tennis.flatMap(e => e.markets).filter(m => m.id.split('-')[0] === family && ['win', 'loss'].includes(m.outcome));
  return [family, [.6, .75].map(threshold => {
    const chosen = rows.map(m => ({ probability: 1 - m.probability - (m.push_probability || 0),
      outcome: m.outcome === 'win' ? 'loss' : 'win' })).filter(m => m.probability >= threshold && m.probability <= .95);
    return { threshold, ...record(chosen) };
  })];
}));
const report = { generated_at: new Date().toISOString(), timezone: 'America/Mexico_City',
  since: adapter.HISTORY_SINCE, scope: 'Mismo universo que #historial: fútbol Alta + Destacados; NBA/tenis solo Destacados',
  football: { overall: record(football), markets: Object.fromEntries([...new Set(football.map(r => r.market))]
    .map(key => [key, record(football.filter(r => r.market === key))])) },
  tennis_complements_research_only: { note: 'Complementos retrospectivos, sin cuota acreditada del lado opuesto; no se suman al historial.', families: complements },
  tennis: sportAudit(tennis, 'tenis'), nba: sportAudit(nba.events, 'nba'), requests,
  limitations: ['Ventana del servidor: NBA cuatro días atrás y cuatro adelante; tenis siete días.',
    'Las publicaciones y cuotas se obtienen en momentos distintos; los resultados son una instantánea.',
    'Los intervalos Wilson son descriptivos; varias selecciones del mismo partido no son independientes.',
    'Un porcentaje alto con pocos casos no acredita una tasa futura ni rentabilidad.',
    'No se modificó ningún sello, historial, configuración o motor.'] };
await fs.writeFile(path.join(out, 'auditoria_historial_mercados_20261105.json'), JSON.stringify(report, null, 2) + '\n');
await fs.writeFile(path.join(cache, 'history-audit-nba.json'), JSON.stringify(nba));
console.log(JSON.stringify(report, null, 2));
