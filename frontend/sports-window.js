// Ventana única de NBA y tenis: pronóstico y estadísticas del mismo evento, con el diseño de la de fútbol.
// Solo presenta lo que publican los motores; no calcula probabilidades ni inventa cuotas.
// La «cuota del modelo» es 1 ÷ probabilidad y se rotula como tal: ninguna casa publica estos mercados.

export function createSportWindow(ctx) {
  const { state, esc, badge, fmtPct, fmtOdds, realDate, realTime, dateFmt, addDays, localDay, dayLabel,
    ensureSport, featuredModelMarket } = ctx;
  const ROW_LIMIT = 24;
  const SPORT_NAME = { nba: 'NBA', tenis: 'Tenis' };
  const keyOf = event => `${event.sport}:${event.id}`;
  const num = (value, digits = 1) => (Number.isFinite(value) ? Number(value).toLocaleString('es-MX', { minimumFractionDigits: digits, maximumFractionDigits: digits }) : '—');
  const marks = name => esc(String(name || '?').split(/\s+/).filter(Boolean).slice(0, 2).map(part => part[0]).join('').toUpperCase() || '?');
  const mark = name => `<span class="win-crest is-initial" aria-hidden="true">${marks(name)}</span>`;
  const statusText = event => (event.status === 'finished' ? 'Final' : event.status === 'awaiting_result' ? 'Esperando resultado' : new Date(event.start) <= new Date() ? 'En curso o por confirmar' : 'Programado');
  const statusKind = event => (event.status === 'finished' ? 'muted' : event.status === 'awaiting_result' ? 'warn' : '');

  function family(event, m) {
    if (event.sport === 'tenis') {
      if (m.id === 'winner') return 'Ganador';
      if (/^(Ganador de set|Sets totales|Hándicap de sets)/.test(m.label)) return 'Sets';
      if (/^(Juegos totales|Hándicap de juegos)/.test(m.label)) return 'Juegos';
      if (/^Tie-break/.test(m.label)) return 'Tie-break';
      return 'Otros';
    }
    if (['winner', 'game_total', 'team_points'].includes(m.market)) return 'Partido';
    return { player_points: 'Puntos', player_rebounds: 'Rebotes', player_assists: 'Asistencias', player_threes: 'Triples' }[m.market] || 'Combinados y otros';
  }
  const FAMILY_ORDER = ['Partido', 'Ganador', 'Sets', 'Juegos', 'Tie-break', 'Puntos', 'Rebotes', 'Asistencias', 'Triples', 'Combinados y otros', 'Otros'];

  function outcomeBadge(m) {
    if (m.outcome === 'win') return badge('Acertó', 'good');
    if (m.outcome === 'loss') return badge('Falló', 'warn');
    if (m.outcome === 'push') return badge('Devolución', 'muted');
    return m.revised ? badge('Revisión', 'muted') : badge('Pendiente', 'muted');
  }

  function dayEvents(events, offset = state.winDay) {
    const day = localDay(addDays(offset, 12));
    return events.filter(e => localDay(new Date(e.start)) === day).sort((a, b) => new Date(a.start) - new Date(b.start));
  }

  const bar = (label, probability, note = '') => `<div class="win-bar"><span>${esc(label)}${note ? `<small>${esc(note)}</small>` : ''}</span><div class="cyber-progress cyber-progress--green" data-value="${(probability * 100).toFixed(1)}" role="progressbar" aria-label="${esc(label)}" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${(probability * 100).toFixed(1)}"><div class="cyber-progress__bar"></div></div><b>${fmtPct(probability)}</b></div>`;
  const kv = (label, value) => `<div class="win-kv"><span>${esc(label)}</span><strong>${value}</strong></div>`;
  const lineOf = selection => { const found = /([0-9]+(?:[.,][0-9]+)?)\s*$/.exec(String(selection)); return found ? Number(found[1].replace(',', '.')) : 0; };

  // Probabilidad de cada lado a partir del mercado «ganador» (la selección publicada y su complemento).
  function duel(event) {
    const winner = event.markets.find(m => (m.id === 'winner' || m.market === 'winner') && !m.revised) || event.markets.find(m => m.id === 'winner' || m.market === 'winner');
    if (!winner) return '';
    const homeWins = String(winner.selection).includes(event.home) || String(winner.selection) === event.home;
    const home = homeWins ? winner.probability : 1 - winner.probability;
    return `<div class="win-panel-box"><p class="eyebrow">PROBABILIDAD DE GANAR</p>${bar(event.home, home)}${bar(event.away, 1 - home)}</div>`;
  }

  // ---- pronóstico (izquierda)
  function forecast(event) {
    const feat = featuredModelMarket(event.markets.filter(m => !m.revised));
    const range = '1,40 a 1,80';
    const card = feat
      ? `<p class="eyebrow">PRONÓSTICO DESTACADO</p><div class="win-pick-grid"><div><h2>${esc(feat.selection)}</h2><p class="win-sub">${esc(feat.label)} · ${esc(event.league)} · ${esc(event.home)} vs ${esc(event.away)}</p></div><div class="win-odd"><small>Cuota del modelo</small><strong>${fmtOdds(1 / feat.probability)}</strong><em>1 ÷ probabilidad</em></div></div><div class="win-prob"><b>${fmtPct(feat.probability)}</b><div class="cyber-progress cyber-progress--green" data-value="${(feat.probability * 100).toFixed(1)}" role="progressbar" aria-label="Probabilidad del pronóstico destacado" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${(feat.probability * 100).toFixed(1)}"><div class="cyber-progress__bar"></div></div></div><p class="win-sub">${outcomeBadge(feat)}</p>`
      : `<p class="eyebrow">PRONÓSTICO DESTACADO</p><h2>Sin pronóstico destacado</h2><p class="win-sub">${event.markets.length && event.markets.every(m => m.revised) ? 'Los mercados de este evento son revisiones posteriores al inicio y no cuentan como pronóstico previo.' : `Ningún mercado de este evento tiene cuota del modelo de ${range}.`}</p>`;
    const families = [...new Set(event.markets.map(m => family(event, m)))].sort((a, b) => FAMILY_ORDER.indexOf(a) - FAMILY_ORDER.indexOf(b));
    const fam = families.includes(state.winSportFam) ? state.winSportFam : families[0];
    const all = event.markets.filter(m => family(event, m) === fam).sort((a, b) => b.probability - a.probability);
    const shown = state.winAll ? all : all.slice(0, ROW_LIMIT);
    const line = m => `<tr${feat && m === feat ? ' class="win-feat"' : ''}><td>${esc(m.label)}</td><td>${esc(m.selection)}${m.estimate != null && event.sport === 'nba' ? `<small class="win-cell-note">Proyección ${num(m.estimate)}</small>` : ''}${m.conditional ? '<small class="win-cell-note">Si el jugador participa</small>' : ''}</td><td class="n">${fmtPct(m.probability)}${m.push_probability ? `<small class="win-cell-note">Devol. ${fmtPct(m.push_probability)}</small>` : ''}</td><td class="n">${fmtOdds(1 / m.probability)}</td><td>${feat && m === feat ? badge('Destacado', 'good') : outcomeBadge(m)}</td></tr>`;
    const more = all.length > ROW_LIMIT ? `<div class="win-vipbar"><p>${state.winAll ? `Se muestran los ${all.length} mercados.` : `Se muestran ${ROW_LIMIT} de ${all.length} mercados, de mayor a menor probabilidad.`}</p><button type="button" class="cyber-btn cyber-btn--sm" data-win-all="1">${state.winAll ? 'Ver menos' : 'Ver todos'}</button></div>` : '';
    return `<article class="win-pick cyber-card" aria-label="Pronóstico destacado">${card}</article>
      <section aria-label="Mercados"><div class="win-mk-head"><h3>Mercados</h3><div class="win-chips" role="group" aria-label="Familia de mercado">${families.map(f => `<button type="button" class="chip ${fam === f ? 'selected' : ''}" data-win-sport-fam="${esc(f)}" aria-pressed="${fam === f}">${esc(f)}</button>`).join('')}</div></div>
      <div class="win-table" tabindex="0" role="region" aria-label="Mercados del evento"><table class="cyber-table cyber-table--compact"><thead><tr><th scope="col">Mercado</th><th scope="col">Selección</th><th scope="col" class="n">Prob.</th><th scope="col" class="n">Cuota</th><th scope="col">Estado</th></tr></thead><tbody>${shown.map(line).join('')}</tbody></table></div>${more}</section>
      <p class="bottom-note">Probabilidades estadísticas del motor; la cuota del modelo es 1 ÷ probabilidad y no una cuota de casa. Una estimación estadística no acredita rentabilidad.</p>`;
  }

  // ---- estadísticas (derecha)
  const TABS = { tenis: [['resumen', 'Resumen'], ['juegos', 'Juegos y sets'], ['resultado', 'Resultado'], ['registro', 'Registro']],
    nba: [['resumen', 'Resumen'], ['disponibilidad', 'Disponibilidad'], ['resultado', 'Resultado'], ['registro', 'Registro']] };

  function summary(event) {
    const parts = [duel(event)];
    if (event.sport === 'tenis') {
      parts.push(`<div class="win-panel-box"><p class="eyebrow">EL ENCUENTRO</p>${kv('Torneo', esc(event.league))}${event.surface ? kv('Superficie', esc(event.surface)) : ''}${kv('Hora', `${realDate(event.start)} ${realTime(event.start)}`)}${kv('Estado', esc(statusText(event)))}</div>`);
      const sets = event.markets.filter(m => /^Sets totales/.test(m.label) && !m.revised).sort((a, b) => lineOf(a.selection) - lineOf(b.selection));
      const tie = event.markets.find(m => /^Tie-break/.test(m.label));
      parts.push(`<div class="win-panel-box"><p class="eyebrow">CÓMO SE PROYECTA</p>${sets.map(m => bar(m.selection, m.probability, 'Sets totales')).join('')}${tie ? bar(`Tie-break: ${tie.selection}`, tie.probability) : ''}</div>`);
    } else {
      const total = event.markets.find(m => m.market === 'game_total' && !m.revised);
      const teams = event.markets.filter(m => m.market === 'team_points' && !m.revised);
      parts.push(`<div class="win-panel-box"><p class="eyebrow">EL PARTIDO</p>${kv('Hora', `${realDate(event.start)} ${realTime(event.start)}`)}${kv('Estado', esc(statusText(event)))}${event.score ? kv('Marcador', esc(event.score)) : ''}${event.official_url ? kv('Ficha oficial', `<a class="text-link" href="${esc(event.official_url)}" target="_blank" rel="noopener noreferrer">NBA.com ↗</a>`) : ''}</div>`);
      parts.push(`<div class="win-panel-box"><p class="eyebrow">PROYECCIONES DEL MOTOR</p>${total ? kv('Total de puntos', `${num(total.estimate)} <small>(línea ${num(lineOf(total.selection))} · más de ${fmtPct(total.probability)})</small>`) : ''}${teams.map(m => kv(String(m.selection).split(' · ')[0], `${num(m.estimate)} <small>(línea ${num(lineOf(m.selection))} · más de ${fmtPct(m.probability)})</small>`)).join('')}${!total && !teams.length ? '<p class="win-sub">Sin proyecciones de equipo publicadas.</p>' : ''}</div>`);
    }
    return parts.join('');
  }

  function games(event) {
    const totals = event.markets.filter(m => /^Juegos totales/.test(m.label) && !m.revised).sort((a, b) => lineOf(a.selection) - lineOf(b.selection));
    const setWinners = event.markets.filter(m => /^Ganador de set/.test(m.label) && !m.revised);
    return `<div class="win-panel-box"><p class="eyebrow">JUEGOS TOTALES</p>${totals.length ? totals.map(m => bar(m.selection, m.probability)).join('') : '<p class="win-sub">Sin mercados de juegos publicados.</p>'}</div><div class="win-panel-box"><p class="eyebrow">GANADOR DE CADA SET</p>${setWinners.length ? setWinners.map(m => bar(`${m.selection}`, m.probability, m.label.replace('Ganador de set · ', ''))).join('') : '<p class="win-sub">Sin mercados de sets publicados.</p>'}</div>`;
  }

  function availability(event) {
    const a = event.availability;
    if (!a) return '<div class="win-panel-box"><p class="eyebrow">DISPONIBILIDAD</p><p class="win-sub">Este partido no trae reporte de lesiones del motor.</p></div>';
    const label = a.state === 'reporte_aplicado' ? 'Reporte oficial aplicado' : String(a.state || 'Sin dato').replace(/_/g, ' ');
    return `<div class="win-panel-box"><p class="eyebrow">REPORTE OFICIAL DE LESIONES</p>${kv('Estado', esc(label))}${kv('Jugadores listados', num(a.listed, 0))}${kv('Jugadores con historial usado', num(a.used, 0))}${a.report_timestamp_utc ? kv('Reporte de', `${realDate(a.report_timestamp_utc)} ${realTime(a.report_timestamp_utc)}`) : ''}${typeof a.report_url === 'string' && a.report_url.startsWith('https://') ? kv('Documento', `<a class="text-link" href="${esc(a.report_url)}" target="_blank" rel="noopener noreferrer">PDF oficial ↗</a>`) : ''}</div><div class="win-panel-box"><p class="eyebrow">LO QUE FALTA POR BAJAS</p>${kv(`Puntos · ${esc(event.home)}`, num(a.missing_points_home))}${kv(`Puntos · ${esc(event.away)}`, num(a.missing_points_away))}${kv(`Minutos · ${esc(event.home)}`, num(a.missing_minutes_home))}${kv(`Minutos · ${esc(event.away)}`, num(a.missing_minutes_away))}<p class="win-sub">Producción individual y minutos que se esperaba aportaran los jugadores listados como baja.</p></div>`;
  }

  function result(event) {
    const decided = event.markets.filter(m => ['win', 'loss', 'push'].includes(m.outcome));
    if (!event.score && !decided.length) return '<div class="win-panel-box"><p class="eyebrow">RESULTADO</p><p class="win-sub">Se publica al terminar el encuentro.</p></div>';
    const wins = decided.filter(m => m.outcome === 'win').length, losses = decided.filter(m => m.outcome === 'loss').length;
    return `<div class="win-panel-box"><p class="eyebrow">RESULTADO</p>${event.score ? kv('Marcador', esc(event.score)) : ''}${kv('Mercados acertados', num(wins, 0))}${kv('Mercados fallados', num(losses, 0))}</div>${decided.length ? `<div class="win-panel-box"><p class="eyebrow">MERCADOS RESUELTOS</p>${decided.slice(0, 30).map(m => kv(`${m.label} · ${m.selection}`, `${fmtPct(m.probability)} ${outcomeBadge(m)}`)).join('')}${decided.length > 30 ? `<p class="win-sub">Y ${decided.length - 30} más.</p>` : ''}</div>` : ''}`;
  }

  function registry(event) {
    return `<div class="win-panel-box"><p class="eyebrow">REGISTRO DEL ANÁLISIS</p>${kv('Publicado', `${realDate(event.sealed_at)} ${realTime(event.sealed_at)}`)}<code class="win-code">${esc(event.seal)}</code><p class="win-sub">Sello de la publicación del motor. Lo publicado antes del inicio no se edita: una revisión posterior se marca aparte y no cuenta como pronóstico previo.</p></div>`;
  }

  function stats(event) {
    const tabs = TABS[event.sport];
    const tab = tabs.some(([id]) => id === state.winSportTab) ? state.winSportTab : 'resumen';
    const body = { resumen: () => summary(event), juegos: () => games(event), disponibilidad: () => availability(event), resultado: () => result(event), registro: () => registry(event) }[tab]();
    return `<div class="win-tabs-wrap"><div class="cyber-tabs cyber-tabs--pills cyber-tabs--scrollable" role="tablist" aria-label="Secciones de estadísticas">${tabs.map(([id, label]) => `<button type="button" role="tab" id="win-stab-${id}" aria-controls="win-stats-panel" aria-selected="${tab === id}" class="cyber-tab ${tab === id ? 'cyber-tab--active' : ''}" data-win-sport-tab="${id}">${label}</button>`).join('')}</div></div><div id="win-stats-panel" role="tabpanel" aria-labelledby="win-stab-${tab}" class="win-panel">${body}</div>`;
  }

  // ---- ventana completa
  function view() {
    const sport = state.sport;
    const entry = ensureSport(sport);
    const events = entry.status === 'ready' ? entry.events : [];
    let list = dayEvents(events);
    // Sin día elegido por la persona, se abre el día más cercano que tenga eventos publicados.
    if (entry.status === 'ready' && !list.length && !state.winDayPinned) {
      const near = [-1, 1, -2, 2, -3, 3].find(offset => dayEvents(events, offset).length);
      if (near !== undefined) { state.winDay = near; list = dayEvents(events); }
    }
    if (!list.some(e => keyOf(e) === state.winEvent)) state.winEvent = keyOf(list.find(e => e.status !== 'finished') || list[0] || { sport, id: '' });
    const event = list.find(e => keyOf(e) === state.winEvent);
    state.winResetFlag = state.winLastEvent !== state.winEvent;
    if (state.winResetFlag) { state.winSportFam = ''; state.winAll = false; }
    state.winLastEvent = state.winEvent;
    state.winEvList = list.map(keyOf);
    const index = state.winEvList.indexOf(state.winEvent);
    const leagues = [...new Set(list.map(e => e.league))];
    let rail;
    if (entry.status === 'loading') rail = '<p class="rail-empty">Cargando eventos…</p>';
    else if (entry.status !== 'ready') rail = '<p class="rail-empty">No se pudo cargar la fuente. <button type="button" class="text-link" data-action="refresh-public">Reintentar ↻</button></p>';
    else if (!list.length) rail = '<p class="rail-empty">No hay eventos publicados este día.</p>';
    else rail = leagues.map(league => `<h3 class="win-league">${esc(league)}</h3>${list.filter(e => e.league === league).map(e => `<button type="button" class="win-row" data-win-event="${esc(keyOf(e))}" aria-pressed="${keyOf(e) === state.winEvent}" ${keyOf(e) === state.winEvent ? 'aria-current="true"' : ''}><span class="win-when"><b>${realTime(e.start)}</b>${e.status === 'finished' ? '<small>Final</small>' : ''}</span><span class="win-names"><span>${mark(e.home)}<span>${esc(e.home)}</span></span><span>${mark(e.away)}<span>${esc(e.away)}</span></span></span></button>`).join('')}`).join('');
    const days = [-3, -2, -1, 0, 1, 2, 3];
    const strip = `<div class="win-day"><button type="button" data-win-day="${Math.max(-3, state.winDay - 1)}" aria-label="Día anterior" ${state.winDay <= -3 ? 'disabled' : ''}>‹</button><strong>${esc(dayLabel(state.winDay))} · ${dateFmt(addDays(state.winDay), { day: 'numeric', month: 'short' })}</strong><button type="button" data-win-day="${Math.min(3, state.winDay + 1)}" aria-label="Día siguiente" ${state.winDay >= 3 ? 'disabled' : ''}>›</button></div><div class="win-chips" role="group" aria-label="${SPORT_NAME[sport]}: eventos del día"><span class="chip selected" aria-hidden="true">${SPORT_NAME[sport]} <b>${list.length}</b></span></div>`;
    const bar0 = event
      ? `<div class="win-picker"><button type="button" data-win-ev-step="-1" aria-label="Evento anterior" ${index <= 0 ? 'disabled' : ''}>‹</button><label class="win-select"><span class="sr-only">Elegir evento</span><select id="win-event-select">${list.map(e => `<option value="${esc(keyOf(e))}" ${keyOf(e) === state.winEvent ? 'selected' : ''}>${realTime(e.start)} · ${esc(e.home)} vs ${esc(e.away)}</option>`).join('')}</select></label><button type="button" data-win-ev-step="1" aria-label="Evento siguiente" ${index >= list.length - 1 ? 'disabled' : ''}>›</button></div><div class="win-team">${mark(event.home)}<div><strong>${esc(event.home)}</strong><small>${sport === 'tenis' ? esc(event.league) : 'Local'}</small></div></div><span class="win-vs ${event.score ? 'score' : ''}">${event.score ? esc(event.score) : 'VS'}</span><div class="win-team is-away">${mark(event.away)}<div><strong>${esc(event.away)}</strong><small>${sport === 'tenis' ? esc(event.surface || 'Individual') : 'Visitante'}</small></div></div><div class="win-meta"><span>${esc(event.league)} · ${dateFmt(new Date(event.start), { weekday: 'short', day: 'numeric', month: 'short' })} ${realTime(event.start)}</span>${badge(statusText(event), statusKind(event))}</div>`
      : '';
    const body = event
      ? `<div class="win-switch" role="tablist" aria-label="Vista del evento"><button type="button" role="tab" aria-selected="${state.winPane === 'pron'}" data-win-pane="pron">Pronóstico</button><button type="button" role="tab" aria-selected="${state.winPane === 'stats'}" data-win-pane="stats">Estadísticas</button></div><div class="win-split"><div class="win-pane" id="win-pane-pron" aria-label="Pronóstico">${forecast(event)}</div><div class="win-pane" id="win-pane-stats" aria-label="Estadísticas">${stats(event)}</div></div>`
      : `<div class="empty-state"><span class="empty-symbol">◷</span><h3>${entry.status === 'loading' ? 'Cargando eventos…' : 'Sin eventos este día'}</h3><p>${entry.status === 'loading' ? 'Consultando la publicación del motor.' : 'Prueba con otro día.'}</p></div>`;
    return { markup: `<div class="win" data-pane="${state.winPane}"><div class="win-strip" role="toolbar" aria-label="Fecha">${strip}</div><div class="win-work"><aside class="win-rail" aria-label="Eventos del día">${rail}</aside><section class="win-main" aria-label="Evento seleccionado"><div class="win-matchbar">${bar0}</div>${body}</section></div></div>`, days };
  }

  return { view: () => view().markup };
}
