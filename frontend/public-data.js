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

export function isPublicationActive(gate) {
  return gate?.status === 'ready'
    && gate.data.puerta_comercial.sombra_criterio_sharp?.autorizada === true
    && gate.data.puerta_comercial.publicacion_de_picks === 'activa';
}
