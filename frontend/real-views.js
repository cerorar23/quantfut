// Presentación del contrato real de la app con las clases del diseño existente.
// No genera probabilidades, cuotas, selecciones ni resultados.
import { forecastGames, publicForecasts, modelProbabilities } from './fichas-data.js?v=real-20261029';
import { createHubViews } from './ergonomic-views.js?v=acomodo-20261029';

export function createRealViews(ctx) {
  const { state, esc, badge, ensureHome, ensureMatch, addDays, localDay, dayLabel,
    timeLabel, realDate, realTime, fmtOdds, fmtPct, liveEvidence, livePicks } = ctx;
  const sameDay = (stamp, date) => stamp && localDay(new Date(stamp)) === localDay(date);
  const message = (title, text) => `<div class="empty-state"><h3>${esc(title)}</h3><p>${esc(text)}</p><button type="button" class="text-link" data-action="refresh-public">Actualizar ↻</button></div>`;
  const unavailable = entry => entry.status === 'loading'
    ? message('Consultando pronósticos reales…', 'La agenda y los pronósticos se leen del servidor.')
    : message('No se pudieron consultar los pronósticos', 'Inténtalo de nuevo. No se sustituyen los datos ausentes por ejemplos.');
  const tag = game => badge(game.estado === 'finished' ? 'Finalizado' : game.estado === 'cancelled' ? 'Cancelado' : game.estado === 'postponed' ? 'Aplazado' : 'Programado', 'muted');
  const mark = team => `<span class="team-mark" aria-hidden="true">${esc(String(team || '?').charAt(0))}</span>`;

  function pickCard(pick) {
    return `<article class="live-pick"><div><span>${esc(pick.league_id)} · ${realDate(pick.kickoff_utc)} ${realTime(pick.kickoff_utc)}</span><h3>${esc(pick.local)} <small>vs</small> ${esc(pick.visitante)}</h3><p><strong>${esc(pick.texto)}</strong></p><small>Probabilidad publicada: ${fmtPct(pick.prob)} · Lote ${esc(pick.batch_date)}</small><p><button type="button" class="text-link" data-real-match="${esc(pick.match_id)}">Ver análisis y mercados ↗</button></p><details><summary>Registro del pronóstico</summary><p>Casa: ${esc(pick.ref_book || 'No disponible')} · Cuota capturada ${realDate(pick.odds_as_of)} ${realTime(pick.odds_as_of)}.</p><code>${esc(pick.chain_sha256)}</code><p>La cuota corresponde a la captura registrada y puede haber cambiado.</p></details></div><div><span>Cuota publicada</span><strong>${fmtOdds(pick.ref_price)}</strong><small>${esc(pick.ref_book || 'Sin casa publicada')}</small></div></article>`;
  }

  function published(entry, date = null) {
    if (entry.status !== 'ready') return unavailable(entry);
    const all = publicForecasts(entry.data);
    const rows = date ? all.filter(p => sameDay(p.kickoff_utc, date)) : all;
    const locked = (entry.data.alta_probabilidad.vip || []).filter(p => !date || sameDay(p.kickoff_utc, date));
    return `<section class="live-panel" aria-label="Pronósticos reales publicados"><div class="live-head"><div><p class="eyebrow">MOTOR ACTIVO / PUBLICACIONES REALES</p><h2>Pronósticos publicados</h2></div>${badge(`${rows.length} disponibles`, 'good')}</div>${rows.length ? `<div class="live-pick-list">${rows.map(pickCard).join('')}</div>` : '<p>No hay pronósticos abiertos que cumplan las reglas de acceso para esta fecha. La agenda permanece disponible y no se rellena con selecciones inventadas.</p>'}${locked.length ? `<div class="disclosure"><div><strong>${locked.length} pronósticos requieren acceso autorizado</strong><span>El servidor conserva las selecciones y cuotas privadas. <button type="button" class="text-link" data-route="planes">Consultar planes ↗</button></span></div></div>` : ''}<p class="live-reason">Pronósticos registrados y sellados por QuantFut. Las probabilidades no garantizan el resultado ni la rentabilidad.</p></section>`;
  }

  function home() {
    const date = addDays(state.dayOffset, 12);
    const entry = ensureHome(state.dayOffset);
    const games = entry.status === 'ready' ? forecastGames(entry.data, date) : [];
    const picks = entry.status === 'ready' ? publicForecasts(entry.data) : [];
    const leagues = [...new Set(games.map(g => g.liga.nombre))];
    const query = String(state.homeSearch || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
    const matching = games.filter(g => (state.homeLeague === 'Todas' || g.liga.nombre === state.homeLeague)
      && (state.homeStatus === 'todos' || (state.homeStatus === 'proximos' ? g.estado !== 'finished' : g.estado === 'finished'))
      && (!query || `${g.local.nombre} ${g.visitante.nombre} ${g.liga.nombre}`.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().includes(query)));
    const pickFor = id => picks.find(p => p.match_id === id);
    matching.sort((a,b) => state.homeSort === 'precio'
      ? (pickFor(b.match_id)?.ref_price || 0) - (pickFor(a.match_id)?.ref_price || 0)
      : new Date(a.kickoff_utc) - new Date(b.kickoff_utc));
    const row = game => {
      const p = modelProbabilities(game), pick = pickFor(game.match_id);
      return `<article class="schedule-row"><div class="schedule-time"><strong>${realTime(game.kickoff_utc)}</strong><small>${game.estado === 'finished' ? 'Finalizado' : 'Programado'}</small></div><button type="button" class="schedule-teams" data-real-match="${esc(game.match_id)}"><span>${mark(game.local.nombre)}<strong>${esc(game.local.nombre)}</strong></span><span>${mark(game.visitante.nombre)}<strong>${esc(game.visitante.nombre)}</strong></span></button><div class="schedule-prob">${p ? `<span>1 <b>${fmtPct(p.home)}</b></span><span>X <b>${fmtPct(p.draw)}</b></span><span>2 <b>${fmtPct(p.away)}</b></span><small>Probabilidad del modelo</small>` : `<small>${game.pronostico_desde && new Date(game.pronostico_desde) > new Date() ? `Cálculo previsto: ${realDate(game.pronostico_desde)} ${realTime(game.pronostico_desde)}` : 'Sin probabilidad publicada'}</small>`}</div><div class="schedule-price"><strong>${pick ? fmtOdds(pick.ref_price) : '—'}</strong><small>${pick ? esc(pick.ref_book || 'Cuota publicada') : 'Sin cuota pública'}</small></div><div class="schedule-selection"><strong>${pick ? esc(pick.texto) : game.marcador ? esc(game.marcador.join(' – ')) : 'Consultar mercados'}</strong><small>${pick ? `Sellado: ${esc(pick.batch_date)}` : 'Datos del servidor'}</small></div><div class="schedule-state">${pick ? badge('Publicado', 'good') : tag(game)}</div><button type="button" class="schedule-arrow" data-real-match="${esc(game.match_id)}" aria-label="Ver análisis de ${esc(game.local.nombre)} contra ${esc(game.visitante.nombre)}">↗</button></article>`;
    };
    return `<section class="forecast-hero" aria-labelledby="forecast-title"><div class="forecast-copy"><p class="eyebrow">FÚTBOL / ANÁLISIS Y PRECIO JUSTO</p><h1 id="forecast-title">Lee el partido.<br><em>Entiende la cuota.</em></h1><p>El contexto del encuentro, la probabilidad del modelo y los pronósticos publicados. Datos reales del motor, antes de decidir.</p><div class="hero-actions"><button type="button" class="primary-button" data-route="picks">Ver pronósticos reales <span aria-hidden="true">↗</span></button><button type="button" class="text-link" data-route="historial">Ver historial verificable ↗</button></div></div><aside class="forecast-summary" aria-label="Resumen de la agenda real"><span class="summary-icon" aria-hidden="true">Q.</span><div><span class="eyebrow">AGENDA REAL / ${dayLabel(state.dayOffset).toUpperCase()}</span><strong>${entry.status === 'ready' ? games.length : '—'}<small> partidos</small></strong><p>Motor con ejecución diaria. Los pronósticos se muestran cuando están calculados y autorizados.</p></div><div class="summary-bottom"><span>${games.filter(g=>modelProbabilities(g)).length} con probabilidades</span><span>Fuente: QuantFut</span></div></aside></section><div class="publication-strip"><span class="publication-dot ${entry.status === 'ready' ? 'active' : ''}" aria-hidden="true"></span><strong>${entry.status === 'ready' ? 'Datos reales del motor' : 'Consultando el servidor'}</strong><span>Sin partidos, cuotas ni resultados simulados.</span><button type="button" class="text-link" data-action="refresh-public">Actualizar ↻</button></div><div class="forecast-shortcuts"><button type="button" data-route="picks">Pronósticos publicados ↗</button><button type="button" data-route="mercados">Mercados del partido ↗</button><button type="button" data-route="parley">Parley del día ↗</button><button type="button" data-route="partidos">Estadísticas ↗</button></div>${published(entry,date)}<section class="forecast-board"><div class="board-top"><div><p class="eyebrow">AGENDA / DATOS REALES</p><h2>Partidos y pronósticos</h2></div><label class="search-field"><span class="sr-only">Buscar equipo o liga</span><input id="home-search" data-input="home-search" type="search" value="${esc(state.homeSearch)}" placeholder="Buscar equipo o liga" /></label></div>${ctx.dayRail()}<div class="board-toolbar"><div class="chip-row">${[['todos','Todos'],['proximos','Próximos'],['cerrados','Finalizados']].map(([id,label])=>`<button type="button" class="chip ${state.homeStatus === id ? 'selected' : ''}" data-home-status="${id}" aria-pressed="${state.homeStatus === id}">${label}</button>`).join('')}</div><label>Ordenar <select id="home-sort"><option value="hora" ${state.homeSort === 'hora' ? 'selected' : ''}>Hora del partido</option><option value="precio" ${state.homeSort === 'precio' ? 'selected' : ''}>Cuota publicada</option></select></label></div><div class="board-layout"><aside class="league-rail"><p class="eyebrow">COMPETICIONES</p>${['Todas',...leagues].map(l=>`<button type="button" data-home-league="${esc(l)}" class="${state.homeLeague === l ? 'active' : ''}" aria-pressed="${state.homeLeague === l}"><span>${esc(l)}</span><b>${l === 'Todas' ? games.length : games.filter(g=>g.liga.nombre===l).length}</b></button>`).join('')}</aside><div class="board-matches"><div class="schedule-columns" aria-hidden="true"><span>HORA</span><span>PARTIDO</span><span>MODELO · 1X2</span><span>CUOTA PUBLICADA</span><span>PRONÓSTICO / RESULTADO</span><span>ESTADO</span><span></span></div>${entry.status !== 'ready' ? unavailable(entry) : matching.length ? leagues.filter(l=>matching.some(g=>g.liga.nombre===l)).map(l=>`<section class="schedule-group"><h3>${esc(l)}</h3>${matching.filter(g=>g.liga.nombre===l).map(row).join('')}</section>`).join('') : message('Sin partidos para estos filtros','Cambia la fecha o la competición.')}<div class="board-foot"><span>${matching.length} de ${games.length} partidos reales</span><button type="button" class="text-link" data-action="clear-home">Limpiar filtros ↻</button></div></div></div><p class="board-disclaimer">Las cuotas conservan la casa y la hora de captura. Los partidos futuros pueden no tener pronóstico hasta la corrida de su día. No se calcula una ventaja de mercado a partir de probabilidades ausentes.</p></section>`;
  }

  function markets() {
    const home = ensureHome(state.dayOffset);
    if (home.status !== 'ready') return unavailable(home);
    const games = forecastGames(home.data,addDays(state.dayOffset,12));
    let selected = games.find(g=>g.match_id === state.realMatch) || games[0];
    if (!selected) return message('Sin partidos disponibles','La agenda real no contiene partidos para consultar.');
    state.realMatch = selected.match_id;
    const entry = ensureMatch(selected.match_id);
    const body = entry.status !== 'ready' ? unavailable(entry) : (() => {
      const data = entry.data, f = data.ficha, rows = f.mercados?.filas || [];
      return `<div class="view-title compact"><div><p class="eyebrow">ANÁLISIS / MERCADOS REALES</p><h1>${esc(f.local.nombre)} vs ${esc(f.visitante.nombre)}</h1><p>${realDate(selected.kickoff_utc)} ${realTime(selected.kickoff_utc)} · ${esc(selected.liga.nombre)}</p></div>${badge('Datos del servidor','accent')}</div>${data.picks.length ? `<div class="live-pick-list">${data.picks.filter(p=>p.locked!==true && p.chain_sha256).map(pickCard).join('')}</div>` : ''}${rows.length ? `<div class="table-wrap" tabindex="0" role="region" aria-label="Mercados públicos del partido"><table><thead><tr><th>Mercado</th><th>Selección</th><th>Probabilidad</th><th>Cuota publicada</th><th>Acceso</th></tr></thead><tbody>${rows.map(r=>r.locked ? `<tr><td>${esc(r.grupo)}</td><td colspan="3">Contenido reservado por el servidor</td><td><button type="button" class="text-link" data-route="planes">Consultar acceso ↗</button></td></tr>` : `<tr><td>${esc(r.titulo || r.grupo)}</td><td>${esc(r.seleccion)}</td><td>${typeof r.prob==='number' ? fmtPct(r.prob) : '—'}</td><td>${typeof r.cuota==='number' ? fmtOdds(r.cuota) : '—'}</td><td>${r.cuota_tipo === 'publicada' ? 'Cuota registrada' : 'Referencia estadística'}</td></tr>`).join('')}</tbody></table></div>` : '<p>No hay mercados públicos disponibles para este encuentro.</p>'}<p class="bottom-note">El servidor decide qué está disponible según la sesión. Los campos bloqueados no contienen selecciones ni cuotas privadas. Una estimación estadística no acredita rentabilidad.</p><button type="button" class="secondary-button" data-open-ficha="${esc(selected.match_id)}">Ver estadísticas del partido ↗</button>`;
    })();
    return `${ctx.dayRail()}<div class="desk stats-desk"><aside class="desk-side"><div class="side-head">PARTIDOS REALES</div><div class="desk-match-list">${games.map(g=>`<button type="button" class="desk-match ${g.match_id===state.realMatch?'active':''}" data-real-match="${esc(g.match_id)}"><span class="desk-when">${realDate(g.kickoff_utc)} ${realTime(g.kickoff_utc)}</span><span class="desk-teams"><strong>${esc(g.local.nombre)}</strong><strong>${esc(g.visitante.nombre)}</strong></span></button>`).join('')}</div></aside><section class="desk-main">${body}</section></div>`;
  }

  function picks() {
    const entry = ensureHome(0);
    return `<div class="view-title"><div><p class="eyebrow">PUBLICACIONES / DATOS REALES</p><h1>Pronósticos</h1><p class="lead">Selecciones calculadas y selladas por el motor, con cuota y fuente registradas.</p></div>${badge(entry.status === 'ready' ? 'Datos reales' : 'Consultando',entry.status === 'ready' ? 'good' : 'muted')}</div>${published(entry)}<details class="publication-details"><summary>Estado separado de los picks de valor</summary>${livePicks()}</details>`;
  }

  function history() {
    return `<div class="view-title"><div><p class="eyebrow">EVIDENCIA / REGISTRO REAL</p><h1>Historial verificable</h1><p class="lead">Resultados, calibración y sellos publicados por el servidor, sin filas simuladas.</p></div></div>${liveEvidence()}`;
  }
  const hub=createHubViews(ctx);
  return { home:hub.home, markets, picks:hub.picks, history:hub.history, detail:hub.detail };
}
