// Solo endpoints públicos. Cada fuente informa su propio fallo: nunca se
// sustituye evidencia ausente por los ejemplos ficticios del prototipo.
const SOURCES = {
  gate: ['/model-card', value => value && typeof value.puerta_comercial === 'object'],
  picks: ['/picks/free?limit=20', Array.isArray],
  record: ['/track-record', value => value && Array.isArray(value.mensual) && typeof value.ultimos_30d === 'object'],
  calibration: ['/calibration', value => value && Array.isArray(value.runs)],
  chain: ['/chain?limit=20', value => value && Array.isArray(value.lotes)],
};

export async function loadPublicData(fetcher = fetch) {
  const entries = await Promise.all(Object.entries(SOURCES).map(async ([key, [path, valid]]) => {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 15000);
    try {
      const response = await fetcher(path, { cache: 'no-store', signal: controller.signal });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      if (!valid(data)) throw new Error('Formato inesperado');
      return [key, { status: 'ready', data }];
    } catch {
      return [key, { status: 'error', data: null }];
    } finally {
      clearTimeout(timeout);
    }
  }));
  return Object.fromEntries(entries);
}

// Probabilidad real de un pick = la de Pinnacle sin margen (`fair_prob`), no la
// del modelo. Se enseña en frecuencia ("1 de cada 3,4") porque con cuotas altas
// el criterio pierde a menudo aunque tenga valor, y eso hay que verlo antes.
export function probabilityLabel(p) {
  const value = Number(p);
  if (p == null || !Number.isFinite(value) || value <= 0 || value >= 1) return null;
  const fmt = (x, digits) => x.toLocaleString('es-MX', { minimumFractionDigits: digits, maximumFractionDigits: digits });
  const pct = `${fmt(value * 100, 0)}%`;
  const frequency = value >= 0.5
    ? `${fmt(Math.round(value * 10), 0)} de cada 10`
    : `1 de cada ${fmt(1 / value, 1 / value < 10 ? 1 : 0)}`;
  return { pct, frequency, text: `${pct} · sale ${frequency}` };
}

// Acierto esperado de una lista: la media de sus probabilidades reales. Sin
// probabilidad en todos los picks no se estima, para no mezclar muestras.
export function expectedHitRate(picks) {
  const probs = (picks ?? []).map(pick => Number(pick?.fair_prob));
  if (!probs.length || probs.some(p => !Number.isFinite(p) || p <= 0 || p >= 1)) return null;
  return probs.reduce((a, b) => a + b, 0) / probs.length;
}

export function isPublicationActive(gate) {
  return gate?.status === 'ready'
    && gate.data.puerta_comercial.sombra_criterio_sharp?.autorizada === true
    && gate.data.puerta_comercial.publicacion_de_picks === 'activa';
}
