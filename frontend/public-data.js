// Solo endpoints públicos. Cada fuente informa su propio fallo: nunca se
// sustituye evidencia ausente por los ejemplos ficticios del prototipo.
const SOURCES = {
  gate: ['/model-card', value => value && typeof value.puerta_comercial === 'object'],
  picks: ['/picks/free?limit=20', Array.isArray],
  record: ['/track-record', value => value && Array.isArray(value.mensual) && typeof value.ultimos_30d === 'object'],
  calibration: ['/calibration', value => value && Array.isArray(value.runs)],
  chain: ['/chain?limit=20', value => value && Array.isArray(value.lotes)],
  alta: ['/alta-probabilidad', value => value && Array.isArray(value.proximos) && typeof value.historial === 'object' && typeof value.estado === 'string'],
  escalera: ['/escalera', value => value && typeof value.reglas === 'object' && Array.isArray(value.actuales) && Array.isArray(value.historial) && Array.isArray(value.serie)],
  parley: ['/parley', value => value && typeof value.reglas === 'object' && Array.isArray(value.dias) && typeof value.resumen === 'object'],
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

// Pronósticos bloqueados (decisión del titular, 2026-10-18): se ven difuminados, cuota incluida, con un botón «Acceso VIP» que
// lleva a Suscripciones (Whop). El servidor NO envía la selección, la probabilidad ni la cuota de lo bloqueado en la ruta pública
// (`mobile.metadata` y /alta-probabilidad): las franjas son bloques, no datos, así que quitar el filtro con las herramientas del
// navegador no revela nada.
export const LOCKED_PLACEHOLDER = '████████ · ██ %';
export const LOCKED_QUOTE_PLACEHOLDER = '@█.██';
export function lockedPicksHtml(vip, { esc, date, time }) {
  if (!Array.isArray(vip) || vip.length === 0) return '';
  const rows = vip.map(p => `<article class="live-pick alta-pick locked-pick"><div class="locked-main"><span>${esc(p.league_id ?? 'Liga')} · ${date(p.kickoff_utc)} ${esc(time(p.kickoff_utc))}</span><h3 class="locked-blur" aria-hidden="true">${LOCKED_PLACEHOLDER}</h3><p>${esc(p.local ?? 'Local')} <small>vs</small> ${esc(p.visitante ?? 'Visitante')}</p></div><div class="locked-quote"><strong class="locked-blur" aria-hidden="true">${LOCKED_QUOTE_PLACEHOLDER}</strong><small>cuota</small></div></article>`).join('');
  const n = vip.length;
  return `<div class="live-pick-list locked-list">${rows}</div><p class="live-reason">${n} pronóstico${n === 1 ? '' : 's'} más con VIP: la selección y la probabilidad se desbloquean con la suscripción.</p><button type="button" class="primary-button locked-vip" data-route="planes">Acceso VIP</button>`;
}

// Parley bloqueado: el servidor manda solo el escalón y el rango de cuota de las reglas (`parley_acceso`), sin patas, probabilidad ni
// cuota exacta. La franja son bloques; no se pinta nada que venga en el ticket salvo el número de escalón.
export function lockedParleyHtml(t, { number }) {
  return `<article class="ladder-card locked-ticket"><div class="live-head"><div><p class="eyebrow">ESCALÓN ${number(t.escalon)} · BLOQUEADO</p><h3 class="locked-blur" aria-hidden="true">${LOCKED_PLACEHOLDER}</h3></div><strong class="ladder-balance locked-blur" aria-hidden="true">${LOCKED_QUOTE_PLACEHOLDER}</strong></div><p class="ladder-meta locked-blur" aria-hidden="true">Probabilidad ██,█% · 1 de cada ██,█</p><div class="live-pick-list"><div class="live-pick locked-blur" aria-hidden="true">████████ ██████ · ████ ████████</div></div><button type="button" class="primary-button locked-vip" data-route="planes">Acceso VIP</button></article>`;
}
