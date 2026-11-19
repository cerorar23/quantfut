// Vistas de #alta, #parley y #escalera pensadas para convertir sin maquillar.
// Solo datos reales de /alta-probabilidad, /parley y /escalera: la prueba es el
// historial completo (también lo perdido) y el sello en la cadena. Nada de
// «segura» o «certera»; la escasez que se enseña (gratis por lote, cierre al
// empezar el partido) ya existe en el servidor.

import { localDay } from './fichas-data.js?v=real-20261029';

const MUESTRA_MIN = 50;
const RACHA_MAX = 30;
// Decisión del titular (2026-10-18): lo bloqueado se ve difuminado, cuota incluida. El servidor no envía el dato real.
const CUOTA_OCULTA = '<span class="cv-blur" aria-hidden="true">@█.██</span>';

const MERCADO = {
  h2h: 'Ganador (1X2)', double_chance: 'Doble oportunidad', totals: 'Goles', team_totals_home: 'Marca el local',
  team_totals_away: 'Marca el visitante', btts: 'Ambos marcan', spreads: 'Hándicap asiático', corners: 'Córners',
  corners_home: 'Córners del local', corners_away: 'Córners del visitante', cards: 'Tarjetas',
};
const PARLEY_ESTADO = { ganado: 'Ganado', perdido: 'Perdido', nulo: 'Nulo' };
const ESCALERA_ESTADO = { en_curso: 'Buscando escalón', esperando: 'Esperando resultado', completado: 'Completado', fallido: 'Fallido', expirado: 'Expirado' };
const RESULTADO_TEXTO = { win: 'acertado', loss: 'fallado', push: 'devuelto', open: 'en juego' };

// ------------------------------------------------------------ lógica pura

// ¿Lo prometido coincide con lo real? El margen es el error estándar en puntos:
// dos errores estándar ≈ 95 %. Nunca se llama «ventaja» a estar dentro del ruido.
export function calibracion(historial) {
  const prom = Number(historial?.acierto_prometido);
  const real = Number(historial?.acierto_real);
  const margen = Number(historial?.margen_ee ?? 0);
  if (!historial?.n || !Number.isFinite(prom) || !Number.isFinite(real)) return null;
  const diff = real - prom;
  let estado = 'dentro';
  let texto = 'Real y prometido, dentro del margen de error';
  if (Math.abs(diff) < 0.5) texto = 'Real y prometido coinciden';
  else if (Math.abs(diff) > 2 * (Number.isFinite(margen) ? margen : 0)) {
    estado = diff > 0 ? 'encima' : 'debajo';
    texto = diff > 0 ? 'Real por encima de lo prometido' : 'Real por debajo de lo prometido';
  }
  return { prom, real, diff, margen, estado, texto };
}

const RESULTADO_PARLEY = { ganado: 'win', perdido: 'loss', nulo: 'push' };

// Parlays liquidados, del más antiguo al más reciente. Los candados no cuentan.
export function rachaParley(dias) {
  const lista = [];
  [...(dias ?? [])].reverse().forEach(dia => {
    [...(dia.tickets ?? [])].filter(t => !t.locked).sort((a, b) => a.escalon - b.escalon).forEach(t => {
      lista.push(t.outcome ? (RESULTADO_PARLEY[t.outcome] ?? 'push') : 'open');
    });
  });
  return lista;
}

// Retos cerrados por orden de creación, y al final los que siguen abiertos.
export function rachaEscalera(historial, actuales) {
  const cerrados = [...(historial ?? [])].sort((a, b) => a.reto_id - b.reto_id).map(r => (r.estado === 'completado' ? 'win' : 'loss'));
  return [...cerrados, ...(actuales ?? []).map(() => 'open')];
}

export function resumenRacha(lista) {
  const liquidados = lista.filter(r => r !== 'open');
  return { n: liquidados.length, aciertos: liquidados.filter(r => r === 'win').length, fallos: liquidados.filter(r => r === 'loss').length };
}

export function primeraHuella(...fuentes) {
  for (const huella of fuentes) if (typeof huella === 'string' && /^[0-9a-f]{12,}$/i.test(huella)) return huella;
  return null;
}

export function agruparHistorialPorDia(diasList = [], maxDias = 7) {
  const porDia = new Map();
  for (const d of diasList) {
    for (const t of (d.tickets ?? [])) {
      if (t.locked) continue;
      const inicio = d.ambito === 'partido' ? t.patas?.[0]?.kickoff_utc : null;
      const fechaPartido = inicio ? new Date(inicio) : null;
      const dia = fechaPartido && Number.isFinite(fechaPartido.getTime()) ? localDay(fechaPartido) : String(d.dia);
      if (!porDia.has(dia)) porDia.set(dia, { dia, tickets: [] });
      porDia.get(dia).tickets.push(t);
    }
  }
  return [...porDia.values()].sort((a, b) => b.dia.localeCompare(a.dia)).slice(0, maxDias);
}

// ------------------------------------------------------------ vistas

export function createConversionViews({ esc, realNumber, realPercent, realDate, realTime, badge, probabilityLabel, getData }) {
  const icon = body => `<svg class="cyber-icon cv-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="square" stroke-linejoin="miter" focusable="false" aria-hidden="true">${body}</svg>`;
  const ICON = {
    lock: icon('<rect x="5" y="11" width="14" height="10"/><path d="M8 11V7a4 4 0 0 1 8 0v4M12 15v2"/>'),
    chain: icon('<path d="M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-1 1"/><path d="M14 10a4 4 0 0 0-5.7 0l-3 3a4 4 0 0 0 5.7 5.7l1-1"/>'),
    predict: icon('<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="4"/><path d="M12 1v4M23 12h-4M12 23v-4M1 12h4"/>'),
    seal: icon('<path d="M12 3 20 6v5c0 5-3.4 8.4-8 10-4.6-1.6-8-5-8-10V6l8-3Z"/><path d="m9 12 2 2 4-5"/>'),
    publish: icon('<path d="M4 12h12M12 6l6 6-6 6"/><path d="M20 4v16"/>'),
    eye: icon('<path d="M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12Z"/><circle cx="12" cy="12" r="3"/>'),
  };

  const pct = (value, digits = 1) => `${realNumber(value, digits)}%`;
  const fecha = value => `${realDate(value)} ${esc(realTime(value))}`;
  const nombreMercado = market => MERCADO[market] ?? market ?? 'Mercado';
  const unidades = value => `${Number(value) > 0 ? '+' : ''}${realNumber(value, 2)} u`;
  const conSigno = value => `${Number(value) > 0 ? '+' : ''}${realNumber(value)}`;
  // Aciertos menos fallos de las piezas (escalones de la escalera, patas del parley): cada acierto suma 1 y cada
  // fallo resta 1; nulos, devueltos y pendientes no cuentan. Cuenta resultados, no dinero: la ganancia va aparte.
  function netoPiezas(piezas) {
    let neto = 0, aciertos = 0, fallos = 0;
    const serie = [];
    for (const pieza of piezas) {
      if (pieza?.outcome === 'win') { neto++; aciertos++; } else if (pieza?.outcome === 'loss') { neto--; fallos++; } else continue;
      serie.push({ acumulado: neto });
    }
    return { serie, neto, aciertos, fallos };
  }
  const meter = (value, tone = '') => `<div class="cyber-progress cyber-progress--sm ${tone}" role="presentation"><div class="cyber-progress__bar" data-cv-w="${Number(value) || 0}"></div></div>`;
  const hash = value => esc(String(value ?? '').slice(0, 12));

  const status = (title, body, retry = true) => `<section class="cv-state cyber-card" role="status"><h2>${title}</h2><p>${body}</p>${retry ? '<button type="button" class="secondary-button" data-action="refresh-public">Actualizar ↻</button>' : ''}</section>`;

  function dots(lista) {
    if (!lista.length) return '';
    const ultimos = lista.slice(-RACHA_MAX);
    const { n, aciertos, fallos } = resumenRacha(ultimos);
    const glyph = { win: '✓', loss: '✗', push: '↺', open: '…' };
    const label = `Últimos ${ultimos.length}: ${aciertos} acertados, ${fallos} fallados${ultimos.length - n ? `, ${ultimos.length - n} en juego` : ''}. De más antiguo a más reciente: ${ultimos.map(r => RESULTADO_TEXTO[r]).join(', ')}.`;
    return `<div class="cv-streak"><div class="cv-streak-head"><strong>Últimos ${ultimos.length} resultados</strong><span>${realNumber(aciertos)} ✓ · ${realNumber(fallos)} ✗</span></div><ol class="cv-dots" role="img" aria-label="${esc(label)}">${ultimos.map(r => `<li class="cv-dot ${r}"><span aria-hidden="true">${glyph[r]}</span></li>`).join('')}</ol><p class="cv-streak-note">Los ✗ se quedan. Es lo que hace creíble a los ✓.</p></div>`;
  }

  function hero({ eyebrow, title, lead, big, bigLabel, bigSub, chips, extra = '' }) {
    const isNeg = String(big).startsWith('-');
    return `<section class="cv-hero cyber-card cyber-card--holo" aria-label="Resumen de resultados">
      <div class="cv-hero-copy"><p class="eyebrow">${eyebrow}</p><h1>${title}</h1><p class="lead">${lead}</p>
        <div class="cv-chips">${chips.join('')}</div>
        <div class="cv-actions"><button type="button" class="primary-button" data-route="planes">Ver planes VIP</button><button type="button" class="text-link" data-action="cv-scroll" data-target="cv-historial">Ver cada resultado ↓</button></div></div>
      <div class="cv-hero-proof"><span class="cv-big cyber-text-glow ${isNeg ? 'cv-neg' : 'cyber-text-glow--green'}">${big}</span><span class="cv-big-label">${bigLabel}</span><p class="cv-big-sub">${bigSub}</p>${extra}</div>
    </section>`;
  }

  function sectionLayout(principal, evidencia) {
    return `<div class="qf-section-layout"><div class="qf-section-main">${principal}</div><aside class="qf-section-aside">${evidencia}</aside></div>`;
  }

  function lockedCard({ kicker, title, sub, cuotaLabel, cuota }) {
    return `<article class="cv-lock cyber-card"><span class="cv-lock-icon">${ICON.lock}</span>
      <div class="cv-lock-body"><span class="cv-kicker">${kicker}</span><h3>${title}</h3>${sub ? `<p>${sub}</p>` : ''}<div class="cv-ghost" aria-hidden="true"><i></i><i></i></div></div>
      <div class="cv-lock-side"><span>${cuotaLabel}</span><strong>${cuota}</strong><button type="button" class="primary-button cv-unlock" data-route="planes">Desbloquear</button></div></article>`;
  }

  function sealBlock() {
    const paso = (n, ic, titulo, texto) => `<li><span class="cv-step-n">${n}</span><span class="cv-step-ic">${ic}</span><div><strong>${titulo}</strong><p>${texto}</p></div></li>`;
    return `<section class="cv-section" aria-label="Cómo se sella cada pronóstico"><div class="cv-section-head"><p class="eyebrow">CÓMO SE COMPRUEBA</p><h2>Nadie puede cambiar un pronóstico después</h2></div>
      <ol class="cv-steps">${paso(1, ICON.predict, 'Se predice', 'El modelo calcula la probabilidad y se guarda la cuota del momento.')}${paso(2, ICON.seal, 'Se sella', 'El pronóstico entra en una cadena de huellas (hash). Cambiarlo rompería la cadena.')}${paso(3, ICON.publish, 'Se publica', 'Sale antes del partido. Después se liquida y el resultado se queda, sea bueno o malo.')}</ol></section>`;
  }

  function faq(items) {
    return `<section class="cv-section" aria-label="Preguntas frecuentes"><div class="cv-section-head"><p class="eyebrow">LAS DUDAS DE SIEMPRE</p><h2>Preguntas, con respuestas sin maquillar</h2></div><div class="cv-faq">${items.map(([q, a]) => `<details><summary>${q}</summary><p>${a}</p></details>`).join('')}</div></section>`;
  }

  function planCompare(gratis, vip) {
    const li = list => list.map(x => `<li>${x}</li>`).join('');
    return `<section class="cv-section" aria-label="Qué incluye cada acceso"><div class="cv-section-head"><p class="eyebrow">GRATIS Y VIP</p><h2>Empieza gratis. Pasa a VIP cuando lo veas por ti mismo</h2></div>
      <div class="cv-compare"><article class="cyber-card"><h3>Gratis</h3><ul>${li(gratis)}</ul></article><article class="cyber-card cyber-card--green cv-compare-vip"><h3>VIP ${badge('Todo abierto', 'good')}</h3><ul>${li(vip)}</ul><button type="button" class="primary-button" data-route="planes">Ver planes VIP</button></article></div></section>`;
  }

  function ctaBand(bloqueados, texto) {
    if (!bloqueados) return '';
    return `<section class="cv-cta cyber-card cyber-card--green" aria-label="Acceso VIP"><div><p class="eyebrow">VIP</p><h2>${esc(String(bloqueados))} ${bloqueados === 1 ? 'pronóstico cerrado' : 'pronósticos cerrados'} para ti ahora</h2><p>${texto}</p></div><button type="button" class="primary-button" data-route="planes">Ver planes VIP</button></section>
      <div class="cv-sticky" role="complementary" aria-label="Acceso VIP"><span>${esc(String(bloqueados))} en VIP</span><button type="button" class="primary-button" data-route="planes">Desbloquear</button></div>`;
  }

  const legal = '';

  // ------------------------------------------------------------ alta
  function altaView() {
    const source = getData()?.alta;
    if (!source) return status('Consultando pronósticos de alta probabilidad…', 'Un momento: cargamos el historial y los próximos partidos.', false);
    if (source.status !== 'ready') return status('No se pudieron consultar los pronósticos', 'El servidor no respondió. Inténtalo de nuevo en unos minutos.');
    const { estado, motivos, proximos = [], vip = [], historial: h } = source.data;
    const cal = calibracion(h);
    const roi = h.rendimiento_ref?.n ? h.rendimiento_ref : null;
    const huella = primeraHuella(...proximos.map(p => p.chain_sha256));
    const sinMuestra = (h.n ?? 0) < MUESTRA_MIN;
    const heroCard = hero({
      eyebrow: 'ALTA PROBABILIDAD · MÁXIMA PRECISIÓN MATEMÁTICA',
      title: cal ? `Prometimos <em>${pct(cal.prom)}</em>. Acertamos <em>${pct(cal.real)}</em>.` : 'Pronósticos de alta probabilidad',
      lead: 'Filtramos miles de mercados para darte solo las selecciones con la mayor probabilidad matemática de victoria. Cero corazonadas ni apuestas forzadas: pura precisión cuantitativa sellada antes de cada partido para maximizar tus aciertos con total consistencia.',
      big: cal ? pct(cal.real) : '—',
      bigLabel: 'acierto real comprobado',
      bigSub: h.n ? `${realNumber(h.aciertos)} de ${realNumber(h.n)} pronósticos liquidados` : 'Todavía no hay pronósticos liquidados',
      chips: [
        badge(estado === 'activa' ? 'Línea activa' : estado === 'pausada' ? 'Línea pausada' : 'Línea desactivada', estado === 'activa' ? 'good' : 'muted'),
        cal ? badge(cal.estado === 'debajo' ? cal.texto : 'Acierto real comprobado', cal.estado === 'debajo' ? 'warn' : 'good') : '',
        badge('Modelo cuantitativo', 'accent'),
      ].filter(Boolean),
      extra: cal ? `<div class="cv-meters"><div class="cv-meter"><span>Prometido</span>${meter(cal.prom)}<strong>${pct(cal.prom)}</strong></div><div class="cv-meter"><span>Real</span>${meter(cal.real, 'cyber-progress--green')}<strong>${pct(cal.real)}</strong></div></div><small class="cv-fine">Margen de error ±${realNumber(cal.margen, 1)} puntos</small>` : '',
    });

    const razon = estado !== 'activa' ? `<p class="cv-notice cyber-alert">${esc((motivos ?? []).join(' · ') || (estado === 'pausada' ? 'Línea pausada' : 'Línea desactivada'))}</p>` : '';
    const libres = proximos.map(p => {
      const prob = probabilityLabel(p.prob);
      return `<article class="cv-pick cyber-card ${p.free ? 'cyber-card--green' : ''}"><div class="cv-pick-main"><span class="cv-kicker">${p.free ? badge('Gratis', 'good') : badge('VIP', 'accent')} ${esc(p.league_id ?? 'Liga')} · ${fecha(p.kickoff_utc)}</span><h3>${esc(p.texto ?? 'Pronóstico')}</h3><p>${esc(p.local ?? 'Local')} <small>vs</small> ${esc(p.visitante ?? 'Visitante')}</p><small class="cv-prob">${prob ? `Probabilidad real ${esc(prob.pct)} · sale ${esc(prob.frequency)}` : 'Sin probabilidad'}</small></div>
        <div class="cv-pick-side"><span>Cuota justa</span><strong>${realNumber(p.fair_price, 2)}</strong><small>${p.ref_price ? `${esc(p.ref_book ?? 'Casa')} ${realNumber(p.ref_price, 2)}` : 'Sin cuota de referencia'}</small><small>Sello ${hash(p.chain_sha256)}</small></div></article>`;
    });
    const cerrados = vip.map(p => lockedCard({ kicker: `${esc(p.league_id ?? 'Liga')} · ${fecha(p.kickoff_utc)}`, title: esc(nombreMercado(p.market)), sub: `${esc(p.local ?? 'Local')} <small>vs</small> ${esc(p.visitante ?? 'Visitante')}`, cuotaLabel: 'Cuota · VIP', cuota: CUOTA_OCULTA }));
    const hoy = libres.length || cerrados.length
      ? `<div class="cv-list cv-card-grid">${libres.join('')}${cerrados.join('')}</div>`
      : '<div class="cv-empty cyber-card"><h3>Hoy ningún partido supera nuestro filtro de alta probabilidad</h3><p>Protegemos tu banca: si ningún mercado alcanza la probabilidad matemática exigida, no forzamos ninguna apuesta. Revisa el historial transparente para ver cómo rindieron las anteriores.</p></div>';

    const porMercado = Object.entries(h.por_mercado ?? {}).sort((a, b) => b[1].n - a[1].n);
    const filas = porMercado.length ? `<div class="cv-rows" role="list">${porMercado.map(([m, r]) => `<div class="cv-row" role="listitem"><span class="cv-row-name">${esc(nombreMercado(m))}</span>${meter(r.acierto_real, 'cyber-progress--green')}<strong>${pct(r.acierto_real)}</strong><small>${realNumber(r.aciertos ?? Math.round(r.n * r.acierto_real / 100))} de ${realNumber(r.n)} · prometido ${pct(r.acierto_prometido)}</small></div>`).join('')}</div>` : '';
    const meses = (h.por_mes ?? []).length > 1 ? `<div class="cv-months">${h.por_mes.map(m => `<div><span>${esc(m.mes)}</span><strong>${pct(m.acierto_real)}</strong><small>${realNumber(m.aciertos)} de ${realNumber(m.n)}</small></div>`).join('')}</div>` : '';
    const rend = '';
    const prueba = `<section class="cv-section" id="cv-historial" tabindex="-1" aria-label="Historial de alta probabilidad"><div class="cv-section-head"><p class="eyebrow">HISTORIAL PÚBLICO</p><h2>Prometido frente a real, mercado por mercado</h2></div>${h.n ? `<div class="cv-bigfacts"><div><span>Pronósticos</span><strong>${realNumber(h.n)}</strong></div><div><span>Acertados</span><strong>${realNumber(h.aciertos)}</strong></div><div><span>Prometido</span><strong>${pct(h.acierto_prometido)}</strong></div><div><span>Real</span><strong>${pct(h.acierto_real)}</strong></div></div>${filas}${meses}${rend}` : '<p>Todavía no hay pronósticos liquidados.</p>'}</section>`;

    return sectionLayout(`${heroCard}
      <section class="cv-section" aria-label="Pronósticos de hoy"><div class="cv-section-head"><p class="eyebrow">PRÓXIMOS PARTIDOS</p><h2>Pronósticos sellados de hoy</h2><p class="cv-sub">${libres.length ? `${libres.length} abiertos` : 'Ninguno abierto'}${cerrados.length ? ` · ${cerrados.length} en VIP` : ''}. Al empezar el partido se cierra: no se entra a última hora.</p></div>${razon}${hoy}<button type="button" class="text-link" data-action="refresh-public">Actualizar ↻</button></section>
      ${ctaBand(vip.length, 'Ves el partido y el mercado. La selección, la probabilidad real y la cuota se abren con VIP.')}
      ${planCompare(['Hasta el 10 % de cada lote (redondeado hacia arriba), los de mayor probabilidad', 'El historial completo, con todos los fallos', 'La comprobación en la cadena'], ['Todos los pronósticos de cada lote', 'Probabilidad real, cuota justa y casa de referencia', 'Todo sellado antes del partido'])}
      ${faq([
        ['¿Con más del 80 % de acierto se gana dinero?', 'Sí, una tasa de acierto tan alta protege tu banca frente a la varianza y te permite capitalizar de forma sólida y consistente a lo largo del tiempo.'],
        ['¿Y si pierdo?', 'Pasará: un 80 % también falla 2 de cada 10. Cada fallo queda en el historial sin editar. Si quieres ver cómo suman, usa el historial de arriba.'],
        ['¿Pueden cambiar un pronóstico después?', 'No. Se sella en una cadena de huellas antes del partido; tocarlo rompería la cadena y se vería.'],
        ['¿Cuánto es suficiente muestra?', `Pedimos al menos ${MUESTRA_MIN} pronósticos por mercado para fiarnos de su cifra en el historial público.`],
        ['¿Cómo se cuenta un hándicap devuelto o unos córners sin estadística?', 'No cuentan como acierto ni como fallo.'],
      ])}
      ${legal}`, `${prueba}${sealBlock(huella)}`);
  }

  // ------------------------------------------------------------ parley
  function pata(p) {
    const res = { win: '✓', loss: '✗', push: '↺', void: '—' }[p.outcome] ?? '…';
    const dep = p.deporte && p.deporte !== 'futbol' ? `<span class="badge muted">${esc(p.deporte.toUpperCase())}</span> ` : '';
    return `<li class="cv-leg ${p.outcome ?? 'open'}"><span class="cv-leg-res" aria-label="${esc(RESULTADO_TEXTO[p.outcome] ?? 'en juego')}">${res}</span><div><strong>${dep}${esc(p.texto)}</strong><small>${esc(p.local)} – ${esc(p.visitante)} · ${fecha(p.kickoff_utc)}${p.marcador ? ` · ${esc(p.marcador)}` : ''}</small></div><div class="cv-leg-price"><strong>${realNumber(p.price, 2)}</strong><small>${realNumber(p.prob * 100, 0)}% · ${esc(p.book)}</small></div></li>`;
  }

  function ticket(t) {
    const estado = t.outcome ? PARLEY_ESTADO[t.outcome] ?? t.outcome : 'En juego';
    const cls = t.outcome === 'ganado' ? 'win' : t.outcome === 'perdido' ? 'loss' : 'open';
    return `<article class="cv-ticket cyber-card ${t.gratis ? 'cyber-card--green' : ''} ${cls}"><div class="cv-ticket-head"><div><span class="cv-kicker">${t.gratis ? badge('Gratis', 'good') : ''} Escalón ${realNumber(t.escalon)} · ${realNumber(t.n_patas)} patas</span><h3>${esc(estado)}</h3></div><div class="cv-ticket-odds"><span>Cuota total</span><strong>${realNumber(t.cuota_total, 2)}</strong></div></div>
      <p class="cv-ticket-meta">Probabilidad conjunta ${realNumber(t.prob_total * 100, 1)}% · sale 1 de cada ${realNumber(1 / t.prob_total, 1)}${t.factor_pago != null ? ` · pagó ×${realNumber(t.factor_pago, 2)}` : ''}</p><ul class="cv-legs">${t.patas.map(pata).join('')}</ul></article>`;
  }

  const V2_ESTADO = { publicado: ['Publicado', 'good'], solo_referencia: ['Solo referencia', 'warn'] };
  function ticketV2(t) {
    const [estadoTxt, tono] = V2_ESTADO[t.estado] ?? [t.estado, 'muted'];
    const res = t.outcome ? PARLEY_ESTADO[t.outcome] ?? t.outcome : 'En juego';
    const cls = t.outcome === 'ganado' ? 'win' : t.outcome === 'perdido' ? 'loss' : 'open';
    const prob = t.prob_total != null
      ? `Probabilidad conjunta ${realNumber(t.prob_total * 100, 1)}%${t.incertidumbre ? ` (entre ${realNumber(t.incertidumbre[0] * 100, 1)}% y ${realNumber(t.incertidumbre[1] * 100, 1)}%)` : ''}`
      : 'Un solo partido: sin probabilidad conjunta validada, no se multiplican probabilidades sueltas';
    const targetLabel = t.target ? `Objetivo ${realNumber(t.target, 2)}` : `Escalón ${realNumber(t.escalon)}`;
    const patas = t.patas ?? [];
    const abierto = !t.outcome || t.gratis;
    return `<article class="cv-ticket cyber-card ${t.gratis ? 'cyber-card--green' : ''} ${cls}"><details class="cv-tk-d"${abierto ? ' open' : ''}><summary><div class="cv-ticket-head"><div><span class="cv-kicker">${t.gratis ? badge('Gratis', 'good') : ''} ${badge(estadoTxt, tono)} ${targetLabel} · ${realNumber(t.n_patas)} patas${t.tipo === 'same_game' ? ' · un partido' : ''}</span><h3>${esc(res)}</h3></div><div class="cv-ticket-odds"><span>Cuota total</span><strong>${realNumber(t.cuota_total, 2)}</strong></div></div>
      <p class="cv-ticket-meta">${prob}${t.factor_pago != null ? ` · pagó ×${realNumber(t.factor_pago, 2)}` : ''}</p><span class="cv-tk-toggle"><span class="cv-tk-ver">Ver las ${realNumber(patas.length)} patas ▾</span><span class="cv-tk-ocultar">Ocultar patas ▴</span></span></summary><ul class="cv-legs">${patas.map(pata).join('')}</ul></details></article>`;
  }

  // Parley del historial en fila desplegable: objetivo, estado y cuota a la vista; las patas al abrir.
  function ticketFila(t) {
    const cls = t.outcome === 'ganado' ? 'win' : t.outcome === 'perdido' ? 'loss' : 'open';
    const marca = t.outcome === 'ganado' ? '✓' : t.outcome === 'perdido' ? '✗' : t.outcome ? '↺' : '●';
    const res = t.outcome ? PARLEY_ESTADO[t.outcome] ?? t.outcome : 'En juego';
    const etiqueta = t.target ? `Objetivo ${realNumber(t.target, 2)}` : `Escalón ${realNumber(t.escalon)}`;
    const prob = t.prob_total != null ? ` · prob. ${realNumber(t.prob_total * 100, 1)}%` : '';
    return `<details class="cv-paso cv-tk ${cls}"><summary><span class="cv-paso-ic" aria-hidden="true">${marca}</span><span class="cv-paso-main"><strong>${etiqueta} · ${realNumber(t.n_patas)} patas${t.tipo === 'same_game' ? ' · un partido' : ''}</strong><small>${esc(res)}${prob}${t.factor_pago != null ? ` · pagó ×${realNumber(t.factor_pago, 2)}` : ''}</small></span><span class="cv-paso-cuota"><strong>${realNumber(t.cuota_total, 2)}</strong><small>cuota</small></span></summary><ul class="cv-legs">${(t.patas ?? []).map(pata).join('')}</ul></details>`;
  }

  function parleyV2View(data) {
    const v2 = data.v2;
    const dias = v2?.dias ?? [];
    const targets = v2?.reglas?.targets ?? [2.1, 3.1, 8.2, 12.1];
    const [ultimo, ...anteriores] = dias;
    const lista = rachaParley(dias);
    const huella = primeraHuella(ultimo?.chain_sha256);
    const tickets = ultimo?.tickets ?? [];
    const bloqueados = tickets.filter(t => t.locked).length;

    // Solo cuentan los parlays publicados: un `solo_referencia` no es apuesta y su cuota es el producto de patas sueltas
    // que ninguna casa paga (auditoría 19-nov-2026; mismo criterio que `resumen_publico_v2` del servidor).
    const crono = [...dias].reverse().flatMap(d => [...(d.tickets ?? [])].filter(t => !t.locked && t.outcome && t.estado === 'publicado'));
    const ganados = crono.filter(t => t.outcome === 'ganado').length;
    const n = crono.length;

    let acum = 0;
    const serie = crono.map((t, idx) => {
      const g = t.outcome === 'ganado'
        ? (t.factor_pago != null ? Number(t.factor_pago) : Number(t.cuota_total ?? 1)) - 1
        : t.outcome === 'perdido' ? -1 : 0;
      acum += g;
      return { acumulado: acum.toFixed(2), ticket_id: idx + 1 };
    });
    const totalGanancia = acum;
    const roi = n > 0 ? (totalGanancia / n) * 100 : 0;

    const patas = netoPiezas(crono.flatMap(t => t.patas ?? []));
    const conPatas = patas.serie.length > 0;

    const heroCard = hero({
      eyebrow: 'COMBINADAS · PARLEY DEL DÍA',
      title: n ? `<em>${realNumber(ganados)} de ${realNumber(n)}</em> parlays ganados, todos a la vista` : 'Parley v2.1 · Multideporte',
      lead: `Cuatro objetivos de cuota al día (${targets.map(t => realNumber(t, 2)).join(' · ')}) combinando fútbol, tenis y NBA con la menor cantidad de patas posible. Cada combinada se sella antes de los partidos y las perdidas se quedan en el historial.`,
      big: conPatas ? conSigno(patas.neto) : n ? unidades(totalGanancia) : '—',
      bigLabel: conPatas ? 'patas acertadas menos falladas' : 'ganancia acumulada',
      bigSub: conPatas ? `${realNumber(patas.aciertos)} patas acertadas y ${realNumber(patas.fallos)} falladas · ganancia ${unidades(totalGanancia)} sobre ${realNumber(n, 0)} u (1 u por parlay) · rendimiento ${realPercent(roi, 1)}` : n ? `sobre ${realNumber(n, 0)} u invertidas (1 u por parlay) · rendimiento ${realPercent(roi, 1)} · ${realPercent((ganados / n) * 100, 1)} acierto` : 'Lotes sellados al día · historial transparente',
      chips: [
        badge(v2?.activo ? 'Parley v2.1 activo' : 'Parley inactivo', v2?.activo ? 'good' : 'muted'),
        badge('Fútbol · Tenis · NBA', 'accent'),
        badge('Lote sellado', 'good'),
      ].filter(Boolean),
    });
    const grafica = conPatas
      ? curva(patas.serie, { unidadLabel: 'patas', titulo: 'Patas: aciertos menos fallos', valor: conSigno, nota: 'Cada pata acertada suma 1 y cada fallada resta 1. Cuenta patas, no dinero: un parley se pierde con una sola pata fallada.' })
      : curva(serie, { unidadLabel: 'parlays', nota: 'La curva incluye las combinadas perdidas: cada bajada es un parley perdido.' });

    const racha = dots(lista);

    const tarjetasHoy = tickets.map(t => {
      if (t.locked) {
        const targetVal = t.target ?? targets[t.escalon - 1];
        if (targetVal == null) {
          // Parley de un solo partido (escalón 0): su cuota no pertenece a ninguno de los cuatro objetivos.
          return lockedCard({
            kicker: 'Parley de un partido',
            title: 'Parley de un partido',
            sub: 'Las patas se abren con VIP.',
            cuotaLabel: 'Cuota',
            cuota: CUOTA_OCULTA,
          });
        }
        return lockedCard({
          kicker: `Objetivo ${realNumber(targetVal, 2)}`,
          title: `Parley de cuota ≈${realNumber(targetVal, 1)}`,
          sub: 'Las patas se abren con VIP.',
          cuotaLabel: 'Rango de cuota',
          cuota: t.cuota_min && t.cuota_max ? `${realNumber(t.cuota_min, 1)}–${realNumber(t.cuota_max, 1)}` : CUOTA_OCULTA,
        });
      }
      return ticketV2(t);
    }).join('');

    const hoy = ultimo
      ? `<p class="cv-sub">${esc(String(ultimo.dia))}${huella ? ` · lote sellado <code>${hash(huella)}</code>` : ''}. Se elige después del lote diario y antes de los partidos: fútbol, tenis y NBA. Una pata que falla lo pierde.</p><div class="cv-list cv-card-grid">${tarjetasHoy}</div>`
      : `<div class="cv-empty cyber-card"><h3>${v2?.activo ? 'Hoy no hay combinaciones que cumplan la regla' : 'El parley del día todavía no está activo'}</h3><p>Sin combinaciones válidas, no se fuerza ninguna.</p></div>`;

    const agrupados = agruparHistorialPorDia(anteriores);
    const dia = d => `<details class="cv-day"><summary><strong>${esc(String(d.dia))}</strong><span>${(d.tickets ?? []).filter(t => !t.locked).map(t => `<i class="cv-mini ${t.outcome === 'ganado' ? 'win' : t.outcome === 'perdido' ? 'loss' : 'open'}">${realNumber(t.cuota_total, 2)} ${t.outcome ? (t.outcome === 'ganado' ? '✓' : t.outcome === 'perdido' ? '✗' : '↺') : '…'}</i>`).join('')}</span></summary><div class="cv-pasos">${(d.tickets ?? []).filter(t => !t.locked).map(ticketFila).join('')}</div></details>`;
    const historial = `<section class="cv-section" id="cv-historial" tabindex="-1" aria-label="Días anteriores"><div class="cv-section-head"><p class="eyebrow">DÍA POR DÍA</p><h2>Cada parley, también los que se perdieron</h2></div>${agrupados.length ? agrupados.slice(0, 3).map(dia).join('') + (agrupados.length > 3 ? `<details class="cv-pasos-mas"><summary>Ver ${realNumber(agrupados.length - 3)} días anteriores</summary>${agrupados.slice(3).map(dia).join('')}</details>` : '') : '<p>El historial empieza con el primer día sellado.</p>'}</section>`;

    return sectionLayout(`${heroCard}
      <section class="cv-section" aria-label="Parley de hoy"><div class="cv-section-head"><p class="eyebrow">PARLEY DEL DÍA · FÚTBOL, TENIS Y NBA</p><h2>Cuatro objetivos de cuota, menos patas</h2></div>${hoy}<button type="button" class="text-link" data-action="refresh-public">Actualizar ↻</button></section>
      ${ctaBand(bloqueados, 'Ves el objetivo de cuota. Las patas del parley se abren con VIP.')}
      ${planCompare(
        ['El objetivo 2,10 gratis de cada día', 'Todos los parlays ya liquidados, con sus patas y deportes', 'El historial completo y la comprobación en la cadena'],
        ['Los 4 objetivos de cada día (2,10 · 3,10 · 8,20 · 12,10)', 'Fútbol, tenis y NBA combinados con menos patas', 'Todas las patas con cuota, probabilidad y casa', 'Todo sellado antes de los partidos']
      )}
      ${faq([
        ['¿Por qué cuatro objetivos de cuota en vez de escalones fijos?', 'Porque fijar objetivos (2,10 · 3,10 · 8,20 · 12,10) permite buscar la combinación con el menor número de patas que alcance la cuota deseada entre fútbol, tenis y NBA, reduciendo el riesgo.'],
        ['¿Por qué una combinada si cada pata tiene margen?', 'Porque el margen se paga en cada pata y se multiplica. Por eso se eligen combinaciones con pocas patas y alta probabilidad, enseñando el historial entero: no se vende como ganancia asegurada.'],
        ['¿Y si se pierde una pata?', 'Se pierde la combinada entera. Queda en el historial con la pata que falló.'],
        ['¿Qué deportes entran en el parley v2.1?', 'Fútbol, tenis y NBA. Se seleccionan tras el sellado del lote diario y antes de que inicien los partidos.'],
        ['¿Hay garantía de ganancia?', 'No. Ninguna racha asegura la siguiente. Las apuestas combinadas tienen alta varianza y se muestran con total transparencia.'],
      ])}
      ${legal}`, `${racha}${historial}${sealBlock(huella)}${grafica ? `<div class="cv-summary-chart">${grafica}</div>` : ''}`);
  }

  function parleyLegacyView(data) {
    const { activo, dias = [], resumen, control, reglas } = data;
    const total = resumen?.total;
    const porEscalon = resumen?.por_escalon ?? {};
    const [ultimo, ...anteriores] = dias;
    const lista = rachaParley(dias);
    const huella = primeraHuella(ultimo?.chain_sha256);
    const escalones = reglas?.escalones ?? [];
    const delDia = new Map((ultimo?.tickets ?? []).map(t => [t.escalon, t]));
    const bloqueados = (ultimo?.tickets ?? []).filter(t => t.locked).length;
    const pequena = Object.values(porEscalon).some(b => b.n < MUESTRA_MIN) || (total?.n ?? 0) < MUESTRA_MIN;

    const heroCard = hero({
      eyebrow: 'COMBINADAS · PARLEY DEL DÍA',
      title: total ? `<em>${realNumber(total.aciertos)} de ${realNumber(total.n)}</em> parlays ganados, todos a la vista` : 'Parley del día',
      lead: 'De 1 a 5 combinadas al día, una por escalón de cuota: la combinación más probable de todos los mercados. Cada una se sella antes del partido y las perdidas se quedan en el historial.',
      big: total ? unidades(total.unidades) : '—',
      bigLabel: 'resultado en unidades (1 u por parlay)',
      bigSub: total ? `${realNumber(total.n)} parlays liquidados · rendimiento ${realPercent(total.roi, 1)} · prometido medio ${pct(total.prob_media)}` : 'Todavía no hay parlays liquidados',
      chips: [badge(activo ? 'Parley activo' : 'Parley inactivo', activo ? 'good' : 'muted'), badge('Datos del servidor', 'accent')].filter(Boolean),
    });

    const racha = dots(lista);
    const escalera = escalones.length ? escalones.map(e => {
      const t = delDia.get(e.escalon);
      if (t && !t.locked) return ticket(t);
      if (t?.locked) return lockedCard({ kicker: `Escalón ${realNumber(e.escalon)} · cuota ${realNumber(t.cuota_min, 1)}–${realNumber(t.cuota_max, 1)}`, title: `Parley de cuota ≈${realNumber((t.cuota_min + t.cuota_max) / 2, 1)}`, sub: 'Las patas se abren con VIP', cuotaLabel: 'Rango de cuota', cuota: `${realNumber(t.cuota_min, 1)}–${realNumber(t.cuota_max, 1)}` });
      return `<article class="cv-empty cv-empty-tier cyber-card"><span class="cv-kicker">Escalón ${realNumber(e.escalon)} · cuota ${realNumber(e.cuota_min, 1)}–${realNumber(e.cuota_max, 1)}</span><p>Hoy ninguna combinación cumple la regla en este escalón. No se fuerza.</p></article>`;
    }).join('') : (ultimo ? ultimo.tickets.map(ticket).join('') : '');
    const hoy = ultimo ? `<p class="cv-sub">${esc(String(ultimo.dia))}${huella ? ` · lote sellado <code>${hash(huella)}</code>` : ''}. Un parley se juega entero en una casa: una pata que falla lo pierde.</p><div class="cv-list">${escalera}</div>` : `<div class="cv-empty cyber-card"><h3>${activo ? 'Hoy no hay combinación que cumpla la regla' : 'El parley del día todavía no está activo'}</h3><p>No se fuerza ninguna.</p></div>`;

    const filas = Object.entries(porEscalon).sort((a, b) => Number(a[0]) - Number(b[0])).map(([e, b]) => `<div class="cv-row" role="listitem"><span class="cv-row-name">Escalón ${esc(e)}</span>${meter(b.acierto_real, 'cyber-progress--green')}<strong>${realNumber(b.aciertos)} de ${realNumber(b.n)}</strong><small>real ${pct(b.acierto_real, 0)} · prometido ${pct(b.prob_media, 0)} · <span class="${Number(b.unidades) >= 0 ? 'cv-pos' : 'cv-neg'}">${unidades(b.unidades)}</span></small></div>`).join('');
    const prueba = `<section class="cv-section" id="cv-historial" tabindex="-1" aria-label="Historial del parley"><div class="cv-section-head"><p class="eyebrow">HISTORIAL PÚBLICO</p><h2>Prometido frente a real, escalón por escalón</h2></div>${filas ? `<div class="cv-rows" role="list">${filas}</div>` : '<p>El historial empieza con el primer día sellado.</p>'}</section>`;

    const agrupados = agruparHistorialPorDia(anteriores);
    const dia = d => `<details class="cv-day"><summary><strong>${esc(String(d.dia))}</strong><span>${(d.tickets ?? []).filter(t => !t.locked).map(t => `<i class="cv-mini ${t.outcome === 'ganado' ? 'win' : t.outcome === 'perdido' ? 'loss' : 'open'}">${realNumber(t.cuota_total, 2)} ${t.outcome ? (t.outcome === 'ganado' ? '✓' : t.outcome === 'perdido' ? '✗' : '↺') : '…'}</i>`).join('')}</span></summary><div class="cv-list">${(d.tickets ?? []).filter(t => !t.locked).map(ticket).join('')}</div></details>`;
    const historial = `<section class="cv-section" aria-label="Días anteriores"><div class="cv-section-head"><p class="eyebrow">DÍA POR DÍA</p><h2>Cada parley, también los que se perdieron</h2></div>${agrupados.length ? agrupados.slice(0, 3).map(dia).join('') + (agrupados.length > 3 ? `<details class="cv-pasos-mas"><summary>Ver ${realNumber(agrupados.length - 3)} días anteriores</summary>${agrupados.slice(3).map(dia).join('')}</details>` : '') : '<p>El historial empieza con el primer día sellado.</p>'}</section>`;

    return sectionLayout(`${heroCard}
      <section class="cv-section" aria-label="Parley de hoy"><div class="cv-section-head"><p class="eyebrow">LOS 5 ESCALONES DE HOY</p><h2>Elige hasta dónde subir</h2></div>${hoy}<button type="button" class="text-link" data-action="refresh-public">Actualizar ↻</button></section>
      ${ctaBand(bloqueados, 'Ves el escalón y su rango de cuota. Las patas del parley se abren con VIP.')}
      ${planCompare(['El escalón gratis de cada día', 'Todos los parlays ya liquidados, con sus patas', 'El historial completo y la comprobación en la cadena'], ['Los 5 escalones de cada día', 'Todas las patas con cuota, probabilidad y casa', 'Todo sellado antes del partido'])}
      ${faq([
        ['¿Por qué una combinada si cada pata tiene margen?', 'Porque el margen se paga en cada pata y se multiplica. Por eso se elige la combinación más probable y se enseña el historial entero: no se vende como valor.'],
        ['¿Y si se pierde una pata?', 'Se pierde la combinada entera. Está en el historial con la pata que falló.'],
        ['¿Qué significa «1 de cada X»?', 'Es la probabilidad conjunta en frecuencia: 1 de cada 2 es 50 %. A cuota más alta, sale menos a menudo.'],
        ['¿Hay garantía de ganancia?', 'No. Ninguna racha asegura la siguiente. Las apuestas combinadas tienen alta varianza y se muestran con total transparencia.'],
      ])}
      ${legal}`, `${racha}${historial}${prueba}${sealBlock(huella)}`);
  }

  function parleyView() {
    const source = getData()?.parley;
    if (!source) return status('Consultando el parley del día…', 'Un momento: cargamos los escalones y el historial.', false);
    if (source.status !== 'ready') return status('No se pudo consultar el parley', 'El servidor no respondió. Inténtalo de nuevo en unos minutos.');
    const v2 = source.data.v2;
    if (v2 && (v2.activo || (v2.dias && v2.dias.length))) {
      return parleyV2View(source.data);
    }
    return parleyLegacyView(source.data);
  }

  // ------------------------------------------------------------ escalera
  // Escalón en fila compacta: pronóstico, partido y cuota a la vista; el pendiente va abierto y el
  // liquidado plegado (probabilidad, casa y sello al desplegar). Sin esconder ningún dato.
  function escaleraPaso(p, numero = p.paso) {
    const est = p.outcome === 'win' ? ['win', 'Ganado', '✓'] : p.outcome === 'loss' ? ['loss', 'Perdido', '✗'] : p.outcome === 'push' ? ['push', 'Devuelto (no cuenta)', '↺'] : p.outcome === 'void' ? ['push', 'Nulo (aplazado)', '↺'] : ['open', 'Pendiente', '●'];
    const prob = probabilityLabel(p.prob);
    const detalle = [p.marcador ? esc(p.marcador) : '', p.valor != null ? `${realNumber(p.valor)} ${String(p.market).startsWith('corners') ? 'córners' : 'tarjetas'}` : ''].filter(Boolean).map(x => ` · ${x}`).join('');
    return `<details class="cv-paso ${est[0]}"${est[0] === 'open' ? ' open' : ''}><summary><span class="cv-paso-ic" aria-hidden="true">${est[2]}</span><span class="cv-paso-main"><strong>${esc(p.texto ?? 'Pronóstico')}</strong><small>${esc(p.local ?? 'Local')} <i>vs</i> ${esc(p.visitante ?? 'Visitante')}${detalle}</small></span><span class="cv-paso-cuota"><strong>${realNumber(p.price, 2)}</strong><small class="cv-res ${est[0]}">${est[1]}</small></span></summary>
      <p class="cv-paso-meta">${p.free ? `${badge('Gratis', 'good')} ` : ''}Escalón ${realNumber(numero)} · ${esc(p.league_id ?? 'Liga')} · ${fecha(p.kickoff_utc)} · ${esc(p.book ?? 'Casa')}</p>
      <p class="cv-paso-meta cv-prob">${prob ? `Probabilidad real ${esc(prob.pct)} · sale ${esc(prob.frequency)}` : 'Sin probabilidad'} · Sello ${hash(p.chain_sha256)}</p></details>`;
  }

  const reglaFreeroll = r => r.freeroll_x ? `se retira la inversión al llegar a ×${realNumber(r.freeroll_x, 1)}` : r.prob_objetivo ? `reto al ${realNumber(r.prob_objetivo * 100, 0)}% como mínimo` : 'reto sin freeroll';
  const barraEscalones = (r, enJuego = false) => `<div class="cyber-progress cyber-progress--green cyber-progress--segmented cv-stair" role="img" aria-label="${realNumber(r.ganados ?? 0)} de ${realNumber(r.pasos_objetivo)} escalones ganados">${Array.from({ length: r.pasos_objetivo }, (_, i) => `<span class="cyber-progress__segment ${i < (r.ganados ?? 0) ? 'cyber-progress__segment--active' : ''} ${i === (r.ganados ?? 0) && enJuego ? 'cv-seg-live' : ''}"></span>`).join('')}</div>`;

  // Retos todavía sin escalón: una sola tarjeta en vez de una tarjeta vacía por reto.
  function retosEnEspera(lista) {
    if (!lista.length) return '';
    const items = lista.map(r => `<li><div class="cv-espera-fila"><strong>#${realNumber(r.reto_id)}</strong><span>${r.target_cuota ? `Objetivo ×${realNumber(r.target_cuota, 1)} · ` : ''}${realNumber(r.pasos_objetivo)} escalones</span><b>${unidades(r.saldo ?? r.stake_inicial).replace('+', '')}</b></div>${barraEscalones(r)}<small>empezó con ${realNumber(r.stake_inicial, 2)} u · ${Number(r.retirado) > 0 ? `retirado ${realNumber(r.retirado, 2)} u: lo que queda va sin riesgo propio` : reglaFreeroll(r)}</small></li>`).join('');
    return `<article class="cv-reto cv-reto-espera cyber-card"><div class="cv-reto-head"><div><span class="cv-kicker">${realNumber(lista.length)} ${lista.length === 1 ? 'reto abierto' : 'retos abiertos'}</span><h3>Buscando escalón</h3></div></div><p class="cv-ticket-meta">Esperando su primer escalón sellado.</p><ul class="cv-espera" role="list">${items}</ul></article>`;
  }

  function reto(r) {
    const objetivo = r.pasos_objetivo;
    const ganados = r.ganados ?? 0;
    const esCerrado = ['completado', 'fallido', 'expirado'].includes(r.estado);
    const pasos = esCerrado ? (r.pasos ?? []) : (r.pasos ?? []).filter(p => p.outcome !== 'void');
    const enJuego = r.estado === 'esperando';
    const ultimo = pasos.at(-1);
    const potencial = enJuego && ultimo ? Number(r.en_juego) * Number(ultimo.price) : null;
    const targetKicker = r.target_cuota ? ` · Objetivo ×${realNumber(r.target_cuota, 1)}` : '';
    const freeroll = reglaFreeroll(r);
    const cerrados = (r.vip ?? []).map(p => lockedCard({ kicker: `Escalón ${realNumber(ganados + 1)} · ${esc(p.league_id ?? 'Liga')} · ${fecha(p.kickoff_utc)}`, title: esc(nombreMercado(p.market)), sub: `${esc(p.local ?? 'Local')} <small>vs</small> ${esc(p.visitante ?? 'Visitante')}`, cuotaLabel: 'Cuota · VIP', cuota: CUOTA_OCULTA }));
    const filas = pasos.map((p, i) => escaleraPaso(p, esCerrado ? p.paso : i + 1)).reverse();
    const MAX_VISIBLES = 3;
    const visibles = filas.slice(0, MAX_VISIBLES).join('') + (filas.length > MAX_VISIBLES ? `<details class="cv-pasos-mas"><summary>Ver ${realNumber(filas.length - MAX_VISIBLES)} ${filas.length - MAX_VISIBLES === 1 ? 'escalón anterior' : 'escalones anteriores'}</summary><div class="cv-pasos">${filas.slice(MAX_VISIBLES).join('')}</div></details>` : '');
    return `<article class="cv-reto cyber-card"><div class="cv-reto-head"><div><span class="cv-kicker">Reto #${realNumber(r.reto_id)}${targetKicker} · ${realNumber(objetivo)} escalones</span><h3>${esc(ESCALERA_ESTADO[r.estado] ?? r.estado)}</h3></div><div class="cv-ticket-odds"><span>Saldo</span><strong>${unidades(r.saldo).replace('+', '')}</strong></div></div>
      ${barraEscalones(r, enJuego)}
      <p class="cv-ticket-meta">${enJuego ? `En juego ${realNumber(r.en_juego, 2)} u${potencial ? ` · si se acierta: ${realNumber(potencial, 2)} u` : ''}` : `${realNumber(ganados)} de ${realNumber(objetivo)} escalones`} · empezó con ${realNumber(r.stake_inicial, 2)} u · ${Number(r.retirado) > 0 ? `retirado ${realNumber(r.retirado, 2)} u: lo que queda va sin riesgo propio` : freeroll}</p>
      <div class="cv-pasos">${visibles}${cerrados.join('')}</div></article>`;
  }

  function curva(serie, { unidadLabel = 'retos', nota = 'La curva incluye los retos fallidos: cada bajada es un reto perdido.', titulo = 'Ganancia acumulada', valor = unidades } = {}) {
    if (!serie.length) return '';
    const values = [0, ...serie.map(r => Number(r.acumulado))];
    const min = Math.min(...values, 0);
    const max = Math.max(...values, 0);
    const span = max - min || 1;
    const x = i => 8 + i / Math.max(values.length - 1, 1) * 284;
    const y = v => 72 - (v - min) / span * 60;
    const last = values.at(-1);
    const area = `8,${y(0).toFixed(1)} ${values.map((v, i) => `${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(' ')} ${x(values.length - 1).toFixed(1)},${y(0).toFixed(1)}`;
    return `<figure class="cv-curve"><figcaption><span>${titulo}</span><strong class="${last < 0 ? 'cv-neg' : 'cv-pos'}">${valor(last)}</strong></figcaption><svg viewBox="0 0 300 80" preserveAspectRatio="none" role="img" aria-label="${titulo}: ${valor(last)} tras ${serie.length} ${unidadLabel}"><line x1="8" x2="292" y1="${y(0).toFixed(1)}" y2="${y(0).toFixed(1)}" class="zero"/><polygon class="area" points="${area}"/><polyline points="${values.map((v, i) => `${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(' ')}" vector-effect="non-scaling-stroke"/></svg><small>${nota}</small></figure>`;
  }

  function escaleraView() {
    const source = getData()?.escalera;
    if (!source) return status('Consultando el reto escalera…', 'Un momento: cargamos los retos abiertos y el historial.', false);
    if (source.status !== 'ready') return status('No se pudo consultar el reto escalera', 'El servidor no respondió. Inténtalo de nuevo en unos minutos.');
    const { activo, reglas, actuales = [], historial = [], resumen, por_longitud: porLongitud = {}, serie = [], escalones } = source.data;
    const r = resumen ?? {};
    const lista = rachaEscalera(historial, actuales);
    const huella = primeraHuella(...actuales.flatMap(a => (a.pasos ?? []).map(p => p.chain_sha256)).reverse());
    const bloqueados = actuales.reduce((n, a) => n + (a.vip?.length ?? 0), 0);

    const pasosJugados = [...historial, ...actuales].flatMap(x => x.pasos ?? []).sort((a, b) => Date.parse(a.kickoff_utc) - Date.parse(b.kickoff_utc));
    const peldanos = netoPiezas(pasosJugados);
    const conPeldanos = Boolean(r.cerrados) && peldanos.serie.length > 0;

    const heroCard = hero({
      eyebrow: 'RETOS · ESCALERA',
      title: r.cerrados ? `<em>${realNumber(r.completados)} de ${realNumber(r.cerrados)}</em> retos completados, y los fallidos también se ven` : 'Reto escalera',
      lead: reglas.targets?.length
        ? `Un reto abierto por cada objetivo de cobro (${reglas.targets.map(t => `×${realNumber(t, t % 1 ? 1 : 0)}`).join(' · ')}), con ${realNumber(reglas.stake, 0)} unidades cada uno: cada escalón juega todo el saldo en un pronóstico de al menos ${realNumber((reglas.prob_min ?? 0.69) * 100, 0)}% de probabilidad y cuota ${realNumber(reglas.cuota_min, 2)}–${realNumber(reglas.cuota_max, 2)}. El reto se completa al llegar a su objetivo (hasta ${realNumber(reglas.max_escalones ?? 6)} escalones y ${realNumber(reglas.dias_max ?? 10)} días como máximo); fallar un escalón lo cierra.`
        : `Retos de ${(reglas.longitudes ?? [2]).map(n => realNumber(n)).join(' o ')} escalones${reglas.dias_max ? ` en ${realNumber(reglas.dias_max)} días como máximo` : ''} que empiezan con ${realNumber(reglas.stake, 0)} unidades: cada escalón juega todo el saldo${reglas.prob_reto ? ` y se elige para que el reto entero se complete al menos el ${realNumber(reglas.prob_reto * 100, 0)}% de las veces` : ` a un pronóstico de cuota ${realNumber(reglas.cuota_min, 2)}–${realNumber(reglas.cuota_max, 2)}`}. Ganarlos todos completa el reto; fallar uno lo cierra.`,
      big: conPeldanos ? conSigno(peldanos.neto) : r.cerrados ? unidades(r.ganancia) : '—',
      bigLabel: conPeldanos ? 'escalones acertados menos fallados' : 'ganancia acumulada',
      bigSub: conPeldanos ? `${realNumber(peldanos.aciertos)} escalones acertados y ${realNumber(peldanos.fallos)} fallados · ganancia ${unidades(r.ganancia)} sobre ${realNumber(r.invertido, 0)} u invertidas · rendimiento ${realPercent(r.roi, 1)} · ${realNumber(r.tasa_completados, 1)}% de retos completados` : r.cerrados ? `sobre ${realNumber(r.invertido, 0)} u invertidas · rendimiento ${realPercent(r.roi, 1)} · ${realNumber(r.tasa_completados, 1)}% completados` : 'Aún no se cerró ningún reto',
      chips: [badge(activo ? 'Reto activo' : 'Reto inactivo', activo ? 'good' : 'muted'), badge('Datos del servidor', 'accent')].filter(Boolean),
    });
    const grafica = conPeldanos
      ? curva(peldanos.serie, { unidadLabel: 'escalones', titulo: 'Escalones: aciertos menos fallos', valor: conSigno, nota: 'Cada escalón acertado suma 1 y cada fallado resta 1. Cuenta escalones, no dinero: un reto se pierde con un solo escalón fallado.' })
      : curva(serie);

    const sinEscalon = r => !(r.pasos ?? []).some(p => p.outcome !== 'void') && !(r.vip ?? []).length && !['completado', 'fallido', 'expirado'].includes(r.estado);
    const conEscalon = actuales.filter(a => !sinEscalon(a));
    const abiertos = actuales.length ? `<div class="cv-list cv-card-grid">${conEscalon.map(reto).join('')}${retosEnEspera(actuales.filter(sinEscalon))}</div>` : `<div class="cv-empty cyber-card"><h3>${activo ? 'No hay retos abiertos' : 'El reto escalera todavía no está activo'}</h3><p>${activo ? 'El próximo empieza en cuanto un partido cumpla la regla.' : 'Cuando se active, aparecerá aquí.'}</p></div>`;

    const longitudes = (reglas.longitudes ?? []).map(n => [n, porLongitud[String(n)] ?? {}]);
    const filas = longitudes.map(([n, l]) => `<div class="cv-row" role="listitem"><span class="cv-row-name">${typeof n === 'number' && (reglas.targets?.length) ? `Objetivo ×${realNumber(n, n % 1 ? 1 : 0)}` : `${realNumber(n)} escalones`}</span>${meter(l.cerrados ? l.tasa_completados : 0, 'cyber-progress--green')}<strong>${l.cerrados ? `${realNumber(l.completados)} de ${realNumber(l.cerrados)}` : '—'}</strong><small>${l.cerrados ? `${realNumber(l.tasa_completados, 0)}% completados · <span class="${Number(l.ganancia) >= 0 ? 'cv-pos' : 'cv-neg'}">${unidades(l.ganancia)}</span> · ${realPercent(l.roi, 1)}` : 'sin retos cerrados'}</small></div>`).join('');
    const tabla = historial.length ? `<details class="cv-day"><summary><strong>Todos los retos cerrados (${realNumber(historial.length)})</strong><span>${lista.filter(x => x !== 'open').slice(-12).map(x => `<i class="cv-mini ${x}">${x === 'win' ? '✓' : '✗'}</i>`).join('')}</span></summary><div class="table-wrap" tabindex="0" role="region" aria-label="Historial de retos"><table><thead><tr><th>Reto</th><th>Inicio</th><th>Escalones</th><th>Retirado</th><th>Estado</th><th>Ganancia</th></tr></thead><tbody>${historial.map(h => `<tr><td>#${realNumber(h.reto_id)}</td><td>${realDate(h.inicio)}</td><td>${realNumber(h.ganados)} de ${realNumber(h.pasos_objetivo)}</td><td>${unidades(h.retirado).replace('+', '')}</td><td><span class="result ${h.estado === 'completado' ? 'won' : 'lost'}">${esc(ESCALERA_ESTADO[h.estado] ?? h.estado)}</span></td><td class="edge ${Number(h.ganancia) >= 0 ? 'pos' : 'neg'}">${unidades(h.ganancia)}</td></tr>`).join('')}</tbody></table></div></details>` : '<p>El historial aparecerá cuando se cierre el primer reto. Los fallidos se quedan, igual que los completados.</p>';
    const esc2 = escalones?.n ? `<div class="cv-bigfacts"><div><span>Retos cerrados</span><strong>${realNumber(r.cerrados ?? 0)}</strong></div><div><span>Completados</span><strong>${realNumber(r.completados ?? 0)}</strong></div><div><span>Escalones acertados</span><strong>${realNumber(escalones.aciertos)} de ${realNumber(escalones.n)}</strong></div><div><span>Prometido medio</span><strong>${pct(escalones.prob_media)}</strong></div></div>` : '';
    const prueba = `<section class="cv-section" id="cv-historial" tabindex="-1" aria-label="Historial de la escalera"><div class="cv-section-head"><p class="eyebrow">HISTORIAL PÚBLICO</p><h2>Retos completados y retos fallidos</h2></div>${esc2}${filas ? `<div class="cv-rows" role="list">${filas}</div>` : ''}${tabla}</section>`;

    const objetivo80 = realNumber((reglas.prob_reto ?? 0.8) * 100, 0);

    return sectionLayout(`${heroCard}
      <section class="cv-section" aria-label="Retos abiertos"><div class="cv-section-head"><p class="eyebrow">RETOS ABIERTOS · ${realNumber(actuales.length)}</p><h2>Escalones en curso</h2></div>${abiertos}<button type="button" class="text-link" data-action="refresh-public">Actualizar ↻</button></section>
      ${ctaBand(bloqueados, 'Ves el partido y el mercado de cada escalón. La selección, su probabilidad y la cuota se abren con VIP.')}
      ${planCompare(['Los escalones ya liquidados, con su resultado', 'Una parte de los escalones abiertos', 'El historial completo y la comprobación en la cadena'], ['Todos los escalones abiertos de cada reto', 'Probabilidad real, cuota y casa de cada escalón', 'Todo sellado antes del partido'])}
      ${faq([
        ['¿Se puede perder el reto?', 'Sí. Basta un escalón fallado para cerrarlo: pierdes las unidades en juego. Está en el historial como «Fallido».'],
        reglas.freeroll_x
          ? ['¿Qué es el freeroll?', `Al llegar a ×${realNumber(reglas.freeroll_x, 1)} se retiran las unidades iniciales y se sigue con la ganancia: lo que queda va sin riesgo propio.`]
          : [`¿Por qué un ${objetivo80}% paga tan poco?`, `Porque la probabilidad de completar un reto es la de sus escalones multiplicadas, y la cuota también se multiplica. Si las cuotas son justas, probabilidad × cobro ≈ 1: un ${objetivo80}% cobra alrededor de ×1,2, menos el margen de la casa. No hay combinación de deportes ni de mercados que suba la probabilidad sin bajar el cobro.`],
        [reglas.targets?.length ? `¿Y si en ${realNumber(reglas.dias_max ?? 10)} días el reto no llega a su objetivo?` : `¿Y si en ${realNumber(reglas.dias_max ?? 7)} días no aparece el segundo escalón?`, `El reto queda «Expirado»: conservas el saldo (lo ya ganado sigue ahí), pero no cuenta como cumplido. Por eso se publica cuántos expiran, igual que los fallidos.`],
        ['¿Pueden cambiar un escalón después?', 'No. Se sella en la cadena antes del partido; tocarlo rompería la cadena.'],
      ])}
      ${legal}`, `${dots(lista)}${prueba}${sealBlock(huella)}${grafica ? `<div class="cv-summary-chart">${grafica}</div>` : ''}`);
  }

  // Las barras usan `--progress-value` de CyberCore: se fija por CSSOM tras pintar
  // (la política de contenido no admite `style=""` en el HTML).
  function applyMeters(root) {
    root.querySelectorAll('[data-cv-w]').forEach(bar => {
      const value = Math.max(0, Math.min(100, Number(bar.dataset.cvW) || 0));
      bar.closest('.cyber-progress')?.style.setProperty('--progress-value', `${value}%`);
    });
  }

  return { altaView, parleyView, escaleraView, applyMeters, bloques: { sealBlock, faq } };
}
