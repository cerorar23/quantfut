// Vistas de #alta, #parley y #escalera pensadas para convertir sin maquillar.
// Solo datos reales de /alta-probabilidad, /parley y /escalera: la prueba es el
// historial completo (también lo perdido) y el sello en la cadena. Nada de
// «segura» o «certera»; la escasez que se enseña (gratis por lote, cierre al
// empezar el partido) ya existe en el servidor.

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
const ESCALERA_ESTADO = { en_curso: 'Buscando escalón', esperando: 'Esperando resultado', completado: 'Completado', fallido: 'Fallido' };
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
    return `<section class="cv-hero cyber-card cyber-card--holo" aria-label="Resumen de resultados">
      <div class="cv-hero-copy"><p class="eyebrow">${eyebrow}</p><h1>${title}</h1><p class="lead">${lead}</p>
        <div class="cv-chips">${chips.join('')}</div>
        <div class="cv-actions"><button type="button" class="primary-button" data-route="planes">Ver planes VIP</button><button type="button" class="text-link" data-action="cv-scroll" data-target="cv-historial">Ver cada resultado ↓</button></div></div>
      <div class="cv-hero-proof"><span class="cv-big cyber-text-glow cyber-text-glow--green">${big}</span><span class="cv-big-label">${bigLabel}</span><p class="cv-big-sub">${bigSub}</p>${extra}</div>
    </section>`;
  }

  function lockedCard({ kicker, title, sub, cuotaLabel, cuota }) {
    return `<article class="cv-lock cyber-card"><span class="cv-lock-icon">${ICON.lock}</span>
      <div class="cv-lock-body"><span class="cv-kicker">${kicker}</span><h3>${title}</h3>${sub ? `<p>${sub}</p>` : ''}<div class="cv-ghost" aria-hidden="true"><i></i><i></i></div></div>
      <div class="cv-lock-side"><span>${cuotaLabel}</span><strong>${cuota}</strong><button type="button" class="primary-button cv-unlock" data-route="planes">Desbloquear</button></div></article>`;
  }

  function sealBlock(huella) {
    const paso = (n, ic, titulo, texto) => `<li><span class="cv-step-n">${n}</span><span class="cv-step-ic">${ic}</span><div><strong>${titulo}</strong><p>${texto}</p></div></li>`;
    const log = huella
      ? `<div class="cyber-terminal cyber-terminal--sm cv-terminal"><div class="cyber-terminal__header"><span class="cyber-terminal__dot cyber-terminal__dot--red"></span><span class="cyber-terminal__dot cyber-terminal__dot--yellow"></span><span class="cyber-terminal__dot cyber-terminal__dot--green"></span><span class="cyber-terminal__title">cadena · último lote</span></div><div class="cyber-terminal__body"><div class="cyber-terminal__line cyber-terminal__line--output">predecir ✓ cuota registrada</div><div class="cyber-terminal__line cyber-terminal__line--success">sellar&nbsp; ✓ sha256:${hash(huella)}…</div><div class="cyber-terminal__line cyber-terminal__line--info">publicar ✓ antes del partido, sin ediciones</div></div></div>`
      : '';
    return `<section class="cv-section" aria-label="Cómo se sella cada pronóstico"><div class="cv-section-head"><p class="eyebrow">CÓMO SE COMPRUEBA</p><h2>Nadie puede cambiar un pronóstico después</h2></div>
      <ol class="cv-steps">${paso(1, ICON.predict, 'Se predice', 'El modelo calcula la probabilidad y se guarda la cuota del momento.')}${paso(2, ICON.seal, 'Se sella', 'El pronóstico entra en una cadena de huellas (hash). Cambiarlo rompería la cadena.')}${paso(3, ICON.publish, 'Se publica', 'Sale antes del partido. Después se liquida y el resultado se queda, sea bueno o malo.')}</ol>${log}</section>`;
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

  const legal = '<p class="cv-legal">Los pronósticos son estimaciones, no garantías: se pierde a menudo y ninguna racha asegura la siguiente. Solo para mayores de 18 años. Juega con responsabilidad y solo con dinero que puedas perder.</p>';

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
      eyebrow: 'ALTA PROBABILIDAD · SELLADO ANTES DEL PARTIDO',
      title: cal ? `Prometimos <em>${pct(cal.prom)}</em>. Acertamos <em>${pct(cal.real)}</em>.` : 'Pronósticos de alta probabilidad',
      lead: 'Un pronóstico por partido, solo cuando la probabilidad real —la de Pinnacle sin margen— es alta. Cada uno se sella en la cadena antes de que ruede el balón.',
      big: cal ? pct(cal.real) : '—',
      bigLabel: 'acierto real',
      bigSub: h.n ? `${realNumber(h.aciertos)} de ${realNumber(h.n)} pronósticos liquidados` : 'Todavía no hay pronósticos liquidados',
      chips: [badge(estado === 'activa' ? 'Línea activa' : estado === 'pausada' ? 'Línea pausada' : 'Línea desactivada', estado === 'activa' ? 'good' : 'muted'), cal ? badge(cal.texto, cal.estado === 'debajo' ? 'warn' : 'accent') : '', sinMuestra ? badge('Muestra en construcción', 'warn') : '', badge('Datos del servidor', 'accent')].filter(Boolean),
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
      ? `<div class="cv-list">${libres.join('')}${cerrados.join('')}</div>`
      : '<div class="cv-empty cyber-card"><h3>Hoy no hay pronóstico que llegue a la barra</h3><p>Si ningún resultado alcanza la probabilidad exigida, no se fuerza uno. Mira abajo cómo salieron los anteriores.</p></div>';

    const porMercado = Object.entries(h.por_mercado ?? {}).sort((a, b) => b[1].n - a[1].n);
    const filas = porMercado.length ? `<div class="cv-rows" role="list">${porMercado.map(([m, r]) => `<div class="cv-row" role="listitem"><span class="cv-row-name">${esc(nombreMercado(m))}${r.n < MUESTRA_MIN ? ' <small class="cv-flag">muestra pequeña</small>' : ''}</span>${meter(r.acierto_real, 'cyber-progress--green')}<strong>${pct(r.acierto_real)}</strong><small>${realNumber(r.aciertos ?? Math.round(r.n * r.acierto_real / 100))} de ${realNumber(r.n)} · prometido ${pct(r.acierto_prometido)}</small></div>`).join('')}</div>` : '';
    const meses = (h.por_mes ?? []).length > 1 ? `<div class="cv-months">${h.por_mes.map(m => `<div><span>${esc(m.mes)}</span><strong>${pct(m.acierto_real)}</strong><small>${realNumber(m.aciertos)} de ${realNumber(m.n)}</small></div>`).join('')}</div>` : '';
    const rend = roi ? `<div class="cv-honest cyber-alert cyber-alert--warning"><strong>Acertar no es lo mismo que ganar dinero.</strong> A la mejor cuota entre las casas de la lista (${realNumber(roi.n)} pronósticos con cuota) el rendimiento fue ${realPercent(roi.roi, 2)}. Lo publicamos porque la transparencia incluye lo incómodo.</div>` : '';
    const prueba = `<section class="cv-section" id="cv-historial" tabindex="-1" aria-label="Historial de alta probabilidad"><div class="cv-section-head"><p class="eyebrow">HISTORIAL PÚBLICO</p><h2>Prometido frente a real, mercado por mercado</h2></div>${h.n ? `<div class="cv-bigfacts"><div><span>Pronósticos</span><strong>${realNumber(h.n)}</strong></div><div><span>Acertados</span><strong>${realNumber(h.aciertos)}</strong></div><div><span>Prometido</span><strong>${pct(h.acierto_prometido)}</strong></div><div><span>Real</span><strong>${pct(h.acierto_real)}</strong></div></div>${filas}${meses}${rend}` : '<p>Todavía no hay pronósticos liquidados.</p>'}</section>`;

    return `${heroCard}
      <section class="cv-section" aria-label="Pronósticos de hoy"><div class="cv-section-head"><p class="eyebrow">PRÓXIMOS PARTIDOS</p><h2>Pronósticos sellados de hoy</h2><p class="cv-sub">${libres.length ? `${libres.length} abiertos` : 'Ninguno abierto'}${cerrados.length ? ` · ${cerrados.length} en VIP` : ''}. Al empezar el partido se cierra: no se entra a última hora.</p></div>${razon}${hoy}<button type="button" class="text-link" data-action="refresh-public">Actualizar ↻</button></section>
      ${ctaBand(vip.length, 'Ves el partido y el mercado. La selección, la probabilidad real y la cuota se abren con VIP.')}
      ${prueba}
      ${sealBlock(huella)}
      ${planCompare(['Hasta el 10 % de cada lote (redondeado hacia arriba), los de mayor probabilidad', 'El historial completo, con todos los fallos', 'La comprobación en la cadena'], ['Todos los pronósticos de cada lote', 'Probabilidad real, cuota justa y casa de referencia', 'Todo sellado antes del partido'])}
      ${faq([
        ['¿Con un 82 % de acierto se gana dinero?', `No por sí solo. El acierto mide cuántas veces sale; el rendimiento depende de la cuota. ${roi ? `A la mejor cuota de la lista el rendimiento fue ${realPercent(roi.roi, 2)}.` : 'Todavía no hay rendimiento medido.'} Es una línea de acierto, no de valor, y por eso se publican las dos cosas.`],
        ['¿Y si pierdo?', 'Pasará: un 80 % también falla 2 de cada 10. Cada fallo queda en el historial sin editar. Si quieres ver cómo suman, usa el historial de arriba.'],
        ['¿Pueden cambiar un pronóstico después?', 'No. Se sella en una cadena de huellas antes del partido; tocarlo rompería la cadena y se vería.'],
        ['¿Cuánto es suficiente muestra?', `Pedimos al menos ${MUESTRA_MIN} pronósticos por mercado para fiarnos de su cifra. Los que no llegan se marcan «muestra pequeña».`],
        ['¿Cómo se cuenta un hándicap devuelto o unos córners sin estadística?', 'No cuentan como acierto ni como fallo.'],
      ])}
      ${legal}`;
  }

  // ------------------------------------------------------------ parley
  function pata(p) {
    const res = { win: '✓', loss: '✗', push: '↺', void: '—' }[p.outcome] ?? '…';
    return `<li class="cv-leg ${p.outcome ?? 'open'}"><span class="cv-leg-res" aria-label="${esc(RESULTADO_TEXTO[p.outcome] ?? 'en juego')}">${res}</span><div><strong>${esc(p.texto)}</strong><small>${esc(p.local)} – ${esc(p.visitante)} · ${fecha(p.kickoff_utc)}${p.marcador ? ` · ${esc(p.marcador)}` : ''}</small></div><div class="cv-leg-price"><strong>${realNumber(p.price, 2)}</strong><small>${realNumber(p.prob * 100, 0)}% · ${esc(p.book)}</small></div></li>`;
  }

  function ticket(t) {
    const estado = t.outcome ? PARLEY_ESTADO[t.outcome] ?? t.outcome : 'En juego';
    const cls = t.outcome === 'ganado' ? 'win' : t.outcome === 'perdido' ? 'loss' : 'open';
    return `<article class="cv-ticket cyber-card ${t.gratis ? 'cyber-card--green' : ''} ${cls}"><div class="cv-ticket-head"><div><span class="cv-kicker">${t.gratis ? badge('Gratis', 'good') : ''} Escalón ${realNumber(t.escalon)} · ${realNumber(t.n_patas)} patas</span><h3>${esc(estado)}</h3></div><div class="cv-ticket-odds"><span>Cuota total</span><strong>${realNumber(t.cuota_total, 2)}</strong></div></div>
      <p class="cv-ticket-meta">Probabilidad conjunta ${realNumber(t.prob_total * 100, 1)}% · sale 1 de cada ${realNumber(1 / t.prob_total, 1)}${t.factor_pago != null ? ` · pagó ×${realNumber(t.factor_pago, 2)}` : ''}</p><ul class="cv-legs">${t.patas.map(pata).join('')}</ul></article>`;
  }

  function parleyView() {
    const source = getData()?.parley;
    if (!source) return status('Consultando el parley del día…', 'Un momento: cargamos los escalones y el historial.', false);
    if (source.status !== 'ready') return status('No se pudo consultar el parley', 'El servidor no respondió. Inténtalo de nuevo en unos minutos.');
    const { activo, dias = [], resumen, control, reglas } = source.data;
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
      chips: [badge(activo ? 'Parley activo' : 'Parley inactivo', activo ? 'good' : 'muted'), pequena ? badge('Muestra en construcción', 'warn') : '', badge('Datos del servidor', 'accent')].filter(Boolean),
    });

    const racha = dots(lista);
    const escalera = escalones.length ? escalones.map(e => {
      const t = delDia.get(e.escalon);
      if (t && !t.locked) return ticket(t);
      if (t?.locked) return lockedCard({ kicker: `Escalón ${realNumber(e.escalon)} · cuota ${realNumber(t.cuota_min, 1)}–${realNumber(t.cuota_max, 1)}`, title: `Parley de cuota ≈${realNumber((t.cuota_min + t.cuota_max) / 2, 1)}`, sub: 'Las patas se abren con VIP', cuotaLabel: 'Rango de cuota', cuota: `${realNumber(t.cuota_min, 1)}–${realNumber(t.cuota_max, 1)}` });
      return `<article class="cv-empty cv-empty-tier cyber-card"><span class="cv-kicker">Escalón ${realNumber(e.escalon)} · cuota ${realNumber(e.cuota_min, 1)}–${realNumber(e.cuota_max, 1)}</span><p>Hoy ninguna combinación cumple la regla en este escalón. No se fuerza.</p></article>`;
    }).join('') : (ultimo ? ultimo.tickets.map(ticket).join('') : '');
    const hoy = ultimo ? `<p class="cv-sub">${esc(String(ultimo.dia))}${huella ? ` · lote sellado <code>${hash(huella)}</code>` : ''}. Un parley se juega entero en una casa: una pata que falla lo pierde.</p><div class="cv-list">${escalera}</div>` : `<div class="cv-empty cyber-card"><h3>${activo ? 'Hoy no hay combinación que cumpla la regla' : 'El parley del día todavía no está activo'}</h3><p>No se fuerza ninguna.</p></div>`;

    const filas = Object.entries(porEscalon).sort((a, b) => Number(a[0]) - Number(b[0])).map(([e, b]) => `<div class="cv-row" role="listitem"><span class="cv-row-name">Escalón ${esc(e)}${b.n < MUESTRA_MIN ? ' <small class="cv-flag">muestra pequeña</small>' : ''}</span>${meter(b.acierto_real, 'cyber-progress--green')}<strong>${realNumber(b.aciertos)} de ${realNumber(b.n)}</strong><small>real ${pct(b.acierto_real, 0)} · prometido ${pct(b.prob_media, 0)} · <span class="${Number(b.unidades) >= 0 ? 'cv-pos' : 'cv-neg'}">${unidades(b.unidades)}</span></small></div>`).join('');
    const prueba = `<section class="cv-section" id="cv-historial" tabindex="-1" aria-label="Historial del parley"><div class="cv-section-head"><p class="eyebrow">HISTORIAL PÚBLICO</p><h2>Prometido frente a real, escalón por escalón</h2></div>${filas ? `<div class="cv-rows" role="list">${filas}</div>` : '<p>El historial empieza con el primer día sellado.</p>'}<div class="cv-honest cyber-alert cyber-alert--warning"><strong>No todo escalón gana.</strong> Hay escalones en pérdida y todos tienen pocos casos. ${(control?.motivos ?? []).length ? `El control interno lo dice con estas palabras: ${esc((control.motivos ?? []).join(' · '))}.` : ''} Se elige por probabilidad, no por valor: el margen de la casa se paga en cada pata.</div></section>`;

    const dia = d => `<details class="cv-day"><summary><strong>${esc(String(d.dia))}</strong><span>${d.tickets.filter(t => !t.locked).map(t => `<i class="cv-mini ${t.outcome === 'ganado' ? 'win' : t.outcome === 'perdido' ? 'loss' : 'open'}">${realNumber(t.cuota_total, 2)} ${t.outcome ? (t.outcome === 'ganado' ? '✓' : t.outcome === 'perdido' ? '✗' : '↺') : '…'}</i>`).join('')}</span></summary><div class="cv-list">${d.tickets.filter(t => !t.locked).map(ticket).join('')}</div></details>`;
    const historial = `<section class="cv-section" aria-label="Días anteriores"><div class="cv-section-head"><p class="eyebrow">DÍA POR DÍA</p><h2>Cada parley, también los que se perdieron</h2></div>${anteriores.length ? anteriores.map(dia).join('') : '<p>El historial empieza con el primer día sellado.</p>'}</section>`;

    return `${heroCard}${racha}
      <section class="cv-section" aria-label="Parley de hoy"><div class="cv-section-head"><p class="eyebrow">LOS 5 ESCALONES DE HOY</p><h2>Elige hasta dónde subir</h2></div>${hoy}<button type="button" class="text-link" data-action="refresh-public">Actualizar ↻</button></section>
      ${ctaBand(bloqueados, 'Ves el escalón y su rango de cuota. Las patas del parley se abren con VIP.')}
      ${prueba}
      ${historial}
      ${sealBlock(huella)}
      ${planCompare(['El escalón gratis de cada día', 'Todos los parlays ya liquidados, con sus patas', 'El historial completo y la comprobación en la cadena'], ['Los 5 escalones de cada día', 'Todas las patas con cuota, probabilidad y casa', 'Todo sellado antes del partido'])}
      ${faq([
        ['¿Por qué una combinada si cada pata tiene margen?', 'Porque el margen se paga en cada pata y se multiplica. Por eso se elige la combinación más probable y se enseña el historial entero: no se vende como valor.'],
        ['¿Y si se pierde una pata?', 'Se pierde la combinada entera. Está en el historial con la pata que falló.'],
        ['¿Qué significa «1 de cada X»?', 'Es la probabilidad conjunta en frecuencia: 1 de cada 2 es 50 %. A cuota más alta, sale menos a menudo.'],
        ['¿Hay garantía de ganancia?', 'No. Ninguna racha asegura la siguiente. Hay escalones en pérdida y muestras pequeñas, y se dice.'],
      ])}
      ${legal}`;
  }

  // ------------------------------------------------------------ escalera
  function escaleraPaso(p) {
    const est = p.outcome === 'win' ? ['win', 'Ganado'] : p.outcome === 'loss' ? ['loss', 'Perdido'] : p.outcome === 'push' ? ['push', 'Devuelto (no cuenta)'] : p.outcome === 'void' ? ['push', 'Nulo (aplazado)'] : ['open', 'Pendiente'];
    const prob = probabilityLabel(p.prob);
    return `<article class="cv-pick cyber-card ${est[0]}"><div class="cv-pick-main"><span class="cv-kicker">${p.free ? badge('Gratis', 'good') : ''} Escalón ${realNumber(p.paso)} · ${esc(p.league_id ?? 'Liga')} · ${fecha(p.kickoff_utc)}</span><h3>${esc(p.texto ?? 'Pronóstico')}</h3><p>${esc(p.local ?? 'Local')} <small>vs</small> ${esc(p.visitante ?? 'Visitante')}${p.marcador ? ` · ${esc(p.marcador)}` : ''}${p.valor != null ? ` · ${realNumber(p.valor)} ${String(p.market).startsWith('corners') ? 'córners' : 'tarjetas'}` : ''}</p><small class="cv-prob">${prob ? `Probabilidad real ${esc(prob.pct)} · sale ${esc(prob.frequency)}` : 'Sin probabilidad'}</small></div>
      <div class="cv-pick-side"><span>Cuota</span><strong>${realNumber(p.price, 2)}</strong><small>${esc(p.book ?? 'Casa')}</small><small class="cv-res ${est[0]}">${est[1]}</small><small>Sello ${hash(p.chain_sha256)}</small></div></article>`;
  }

  function reto(r) {
    const objetivo = r.pasos_objetivo;
    const ganados = r.ganados ?? 0;
    const pasos = r.pasos ?? [];
    const enJuego = r.estado === 'esperando';
    const segmentos = Array.from({ length: objetivo }, (_, i) => `<span class="cyber-progress__segment ${i < ganados ? 'cyber-progress__segment--active' : ''} ${i === ganados && enJuego ? 'cv-seg-live' : ''}"></span>`).join('');
    const ultimo = pasos.at(-1);
    const potencial = enJuego && ultimo ? Number(r.en_juego) * Number(ultimo.price) : null;
    const freeroll = r.freeroll_x ? `se retira la inversión al llegar a ×${realNumber(r.freeroll_x, 1)}` : 'reto sin freeroll';
    const cerrados = (r.vip ?? []).map(p => lockedCard({ kicker: `Escalón ${realNumber(ganados + 1)} · ${esc(p.league_id ?? 'Liga')} · ${fecha(p.kickoff_utc)}`, title: esc(nombreMercado(p.market)), sub: `${esc(p.local ?? 'Local')} <small>vs</small> ${esc(p.visitante ?? 'Visitante')}`, cuotaLabel: 'Cuota · VIP', cuota: CUOTA_OCULTA }));
    return `<article class="cv-reto cyber-card"><div class="cv-reto-head"><div><span class="cv-kicker">Reto #${realNumber(r.reto_id)} · ${realNumber(objetivo)} escalones</span><h3>${esc(ESCALERA_ESTADO[r.estado] ?? r.estado)}</h3></div><div class="cv-ticket-odds"><span>Saldo</span><strong>${unidades(r.saldo).replace('+', '')}</strong></div></div>
      <div class="cyber-progress cyber-progress--green cyber-progress--segmented cv-stair" role="img" aria-label="${realNumber(ganados)} de ${realNumber(objetivo)} escalones ganados">${segmentos}</div>
      <p class="cv-ticket-meta">${enJuego ? `En juego ${realNumber(r.en_juego, 2)} u${potencial ? ` · si se acierta: ${realNumber(potencial, 2)} u` : ''}` : `${realNumber(ganados)} de ${realNumber(objetivo)} escalones`} · empezó con ${realNumber(r.stake_inicial, 2)} u · ${Number(r.retirado) > 0 ? `retirado ${realNumber(r.retirado, 2)} u: lo que queda va sin riesgo propio` : freeroll}</p>
      <div class="cv-list">${[...pasos].reverse().map(escaleraPaso).join('')}${cerrados.join('')}</div>${!pasos.length && !cerrados.length ? '<p class="cv-ticket-meta">Esperando su primer escalón sellado.</p>' : ''}</article>`;
  }

  function curva(serie) {
    if (!serie.length) return '';
    const values = [0, ...serie.map(r => Number(r.acumulado))];
    const min = Math.min(...values, 0);
    const max = Math.max(...values, 0);
    const span = max - min || 1;
    const x = i => 8 + i / Math.max(values.length - 1, 1) * 284;
    const y = v => 72 - (v - min) / span * 60;
    const last = values.at(-1);
    const area = `8,${y(0).toFixed(1)} ${values.map((v, i) => `${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(' ')} ${x(values.length - 1).toFixed(1)},${y(0).toFixed(1)}`;
    return `<figure class="cv-curve"><figcaption><span>Ganancia acumulada</span><strong class="${last < 0 ? 'cv-neg' : 'cv-pos'}">${unidades(last)}</strong></figcaption><svg viewBox="0 0 300 80" preserveAspectRatio="none" role="img" aria-label="Ganancia acumulada: ${realNumber(last, 2)} unidades tras ${serie.length} retos"><line x1="8" x2="292" y1="${y(0).toFixed(1)}" y2="${y(0).toFixed(1)}" class="zero"/><polygon class="area" points="${area}"/><polyline points="${values.map((v, i) => `${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(' ')}" vector-effect="non-scaling-stroke"/></svg><small>La curva incluye los retos fallidos: cada bajada es un reto perdido.</small></figure>`;
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

    const heroCard = hero({
      eyebrow: 'RETOS · ESCALERA',
      title: r.cerrados ? `<em>${realNumber(r.completados)} de ${realNumber(r.cerrados)}</em> retos completados, y los fallidos también se ven` : 'Reto escalera',
      lead: `Retos de ${realNumber(Math.min(...(reglas.longitudes ?? [3])))} a ${realNumber(Math.max(...(reglas.longitudes ?? [6])))} escalones que empiezan con ${realNumber(reglas.stake, 0)} unidades: cada escalón juega todo el saldo a un pronóstico de cuota ${realNumber(reglas.cuota_min, 2)}–${realNumber(reglas.cuota_max, 2)}. Ganarlos todos completa el reto; fallar uno lo cierra.`,
      big: r.cerrados ? unidades(r.ganancia) : '—',
      bigLabel: 'ganancia acumulada',
      bigSub: r.cerrados ? `sobre ${realNumber(r.invertido, 0)} u invertidas · rendimiento ${realPercent(r.roi, 1)} · ${realNumber(r.tasa_completados, 1)}% completados` : 'Aún no se cerró ningún reto',
      chips: [badge(activo ? 'Reto activo' : 'Reto inactivo', activo ? 'good' : 'muted'), (r.cerrados ?? 0) < MUESTRA_MIN ? badge('Muestra en construcción', 'warn') : '', badge('Datos del servidor', 'accent')].filter(Boolean),
      extra: curva(serie),
    });

    const abiertos = actuales.length ? `<div class="cv-list">${actuales.map(reto).join('')}</div>` : `<div class="cv-empty cyber-card"><h3>${activo ? 'No hay retos abiertos' : 'El reto escalera todavía no está activo'}</h3><p>${activo ? 'El próximo empieza en cuanto un partido cumpla la regla.' : 'Cuando se active, aparecerá aquí.'}</p></div>`;

    const longitudes = (reglas.longitudes ?? []).map(n => [n, porLongitud[String(n)] ?? {}]);
    const filas = longitudes.map(([n, l]) => `<div class="cv-row" role="listitem"><span class="cv-row-name">${realNumber(n)} escalones${(l.cerrados ?? 0) < 5 ? ' <small class="cv-flag">muestra pequeña</small>' : ''}</span>${meter(l.cerrados ? l.tasa_completados : 0, 'cyber-progress--green')}<strong>${l.cerrados ? `${realNumber(l.completados)} de ${realNumber(l.cerrados)}` : '—'}</strong><small>${l.cerrados ? `${realNumber(l.tasa_completados, 0)}% completados · <span class="${Number(l.ganancia) >= 0 ? 'cv-pos' : 'cv-neg'}">${unidades(l.ganancia)}</span> · ${realPercent(l.roi, 1)}` : 'sin retos cerrados'}</small></div>`).join('');
    const tabla = historial.length ? `<details class="cv-day"><summary><strong>Todos los retos cerrados (${realNumber(historial.length)})</strong><span>${lista.filter(x => x !== 'open').slice(-12).map(x => `<i class="cv-mini ${x}">${x === 'win' ? '✓' : '✗'}</i>`).join('')}</span></summary><div class="table-wrap" tabindex="0" role="region" aria-label="Historial de retos"><table><thead><tr><th>Reto</th><th>Inicio</th><th>Escalones</th><th>Retirado</th><th>Estado</th><th>Ganancia</th></tr></thead><tbody>${historial.map(h => `<tr><td>#${realNumber(h.reto_id)}</td><td>${realDate(h.inicio)}</td><td>${realNumber(h.ganados)} de ${realNumber(h.pasos_objetivo)}</td><td>${unidades(h.retirado).replace('+', '')}</td><td><span class="result ${h.estado === 'completado' ? 'won' : 'lost'}">${esc(ESCALERA_ESTADO[h.estado] ?? h.estado)}</span></td><td class="edge ${Number(h.ganancia) >= 0 ? 'pos' : 'neg'}">${unidades(h.ganancia)}</td></tr>`).join('')}</tbody></table></div></details>` : '<p>El historial aparecerá cuando se cierre el primer reto. Los fallidos se quedan, igual que los completados.</p>';
    const esc2 = escalones?.n ? `<div class="cv-bigfacts"><div><span>Retos cerrados</span><strong>${realNumber(r.cerrados ?? 0)}</strong></div><div><span>Completados</span><strong>${realNumber(r.completados ?? 0)}</strong></div><div><span>Escalones acertados</span><strong>${realNumber(escalones.aciertos)} de ${realNumber(escalones.n)}</strong></div><div><span>Prometido medio</span><strong>${pct(escalones.prob_media)}</strong></div></div>` : '';
    const prueba = `<section class="cv-section" id="cv-historial" tabindex="-1" aria-label="Historial de la escalera"><div class="cv-section-head"><p class="eyebrow">HISTORIAL PÚBLICO</p><h2>Retos completados y retos fallidos</h2></div>${esc2}${filas ? `<div class="cv-rows" role="list">${filas}</div>` : ''}${tabla}<div class="cv-honest cyber-alert cyber-alert--warning"><strong>Elegir lo más probable no quita el margen de la casa.</strong> La escalera lo multiplica en cada escalón. Por eso ves cada escalón con su probabilidad, su cuota y su resultado, y los retos fallidos se quedan.</div></section>`;

    const handicap = reglas.lineas_handicap?.length ? `<li><strong>Hándicap asiático protector</strong> (${reglas.lineas_handicap.map(l => `${l > 0 ? '+' : ''}${realNumber(l, l % 1 ? 1 : 0)}`).join(', ')}), con la probabilidad sacada de Pinnacle y medida en el histórico.</li>` : '';
    const regla = `<section class="cv-section" aria-label="La regla del reto"><div class="cv-section-head"><p class="eyebrow">LA REGLA</p><h2>Cómo se elige cada escalón</h2></div><ul class="cv-rules"><li><strong>Cuota ${realNumber(reglas.cuota_min, 2)}–${realNumber(reglas.cuota_max, 2)}</strong> en las casas de la lista, la mejor del momento.</li><li><strong>Se elige el pronóstico más probable</strong> de todos los partidos y mercados: ganador, goles, ambos marcan, hándicap asiático, córners y tarjetas. La probabilidad sale de Pinnacle sin margen o, en córners y tarjetas, del histórico de cada equipo, de la liga y del árbitro, y nunca por encima de la que da el mercado sin margen. Solo entran las líneas que pasaron la prueba de calibración.</li><li><strong>Retos de 3 escalones por defecto</strong>; uno de 6 como mucho ${realNumber(reglas.max_seis_mes)} veces al mes, y de 4 o 5 cuando ya hay otro abierto. Cada reto tiene un escalón al día como máximo y dos retos nunca dependen del mismo partido.</li>${handicap}<li><strong>Freeroll a ×${realNumber(reglas.freeroll_x, 1)}</strong>: se retiran las ${realNumber(reglas.stake, 0)} unidades iniciales y se sigue con la ganancia.</li></ul><p class="cv-fine">Tarjetas: amarillas + rojas, una por tarjeta; algunas casas cuentan la roja como 2. En el histórico (football-data, 7 ligas, 2019-2025) esta forma de elegir dejó −11,5% por reto a 3 escalones y −26% a 6, aunque se completaran el 40% y el 15% de los retos. Se enseña todo para que lo veas.</p></section>`;

    return `${heroCard}${dots(lista)}
      <section class="cv-section" aria-label="Retos abiertos"><div class="cv-section-head"><p class="eyebrow">RETOS ABIERTOS · ${realNumber(actuales.length)}</p><h2>Escalones en curso</h2></div>${abiertos}<button type="button" class="text-link" data-action="refresh-public">Actualizar ↻</button></section>
      ${ctaBand(bloqueados, 'Ves el partido y el mercado de cada escalón. La selección, su probabilidad y la cuota se abren con VIP.')}
      ${prueba}
      ${sealBlock(huella)}
      ${planCompare(['Los escalones ya liquidados, con su resultado', 'Una parte de los escalones abiertos', 'El historial completo y la comprobación en la cadena'], ['Todos los escalones abiertos de cada reto', 'Probabilidad real, cuota y casa de cada escalón', 'Todo sellado antes del partido'])}
      ${regla}
      ${faq([
        ['¿Se puede perder el reto?', 'Sí. Basta un escalón fallado para cerrarlo: pierdes las unidades en juego. Está en el historial como «Fallido».'],
        ['¿Qué es el freeroll?', `Al llegar a ×${realNumber(reglas.freeroll_x, 1)} se retiran las unidades iniciales y se sigue con la ganancia: lo que queda va sin riesgo propio.`],
        ['¿Con 13 retos ya se puede concluir algo?', `Todavía no. Es una muestra pequeña (pedimos ${MUESTRA_MIN}). La cifra de arriba es real, pero puede moverse mucho.`],
        ['¿Pueden cambiar un escalón después?', 'No. Se sella en la cadena antes del partido; tocarlo rompería la cadena.'],
      ])}
      ${legal}`;
  }

  // Las barras usan `--progress-value` de CyberCore: se fija por CSSOM tras pintar
  // (la política de contenido no admite `style=""` en el HTML).
  function applyMeters(root) {
    root.querySelectorAll('[data-cv-w]').forEach(bar => {
      const value = Math.max(0, Math.min(100, Number(bar.dataset.cvW) || 0));
      bar.closest('.cyber-progress')?.style.setProperty('--progress-value', `${value}%`);
    });
  }

  return { altaView, parleyView, escaleraView, applyMeters };
}
