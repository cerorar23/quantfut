import { publicForecasts, forecastGames } from './fichas-data.js?v=real-20261028';

export function createHubViews(ctx) {
  const {state,esc,ensureHome,addDays,localDay,dayLabel,realDate,realTime,fmtOdds,fmtPct}=ctx;
  const names={todos:'Todos',futbol:'Fútbol',nba:'NBA',tenis:'Tenis'};
  const icons={futbol:'◉',nba:'◈',tenis:'◎'};
  const ensureSport=s=>ctx.ensureSport?.(s)||{status:'loading',events:[]};
  const results=()=>ctx.ensureResults?.()||{status:'loading',items:[]};
  const empty=(title,text)=>`<div class="empty-state"><span aria-hidden="true">◎</span><h3>${esc(title)}</h3><p>${esc(text)}</p><button type="button" class="text-link" data-action="refresh-public">Volver a consultar ↻</button></div>`;
  function football(entry) {
    if(entry.status!=='ready')return [];
    const events=new Map();
    const agenda=entry.data.agenda||[];
    for(const pick of publicForecasts(entry.data)) {
      const game=agenda.find(g=>g.match_id===pick.match_id);
      if(!events.has(pick.match_id)) events.set(pick.match_id,{id:pick.match_id,sport:'futbol',home:pick.local,away:pick.visitante,start:pick.kickoff_utc,
        league:game?.liga?.nombre||pick.league_id,status:game?.estado||'scheduled',seal:pick.chain_sha256,sealed_at:pick.batch_date,markets:[],locked_count:0});
      events.get(pick.match_id).markets.push({id:pick.pick_key,label:'Pronóstico publicado',selection:pick.texto,probability:pick.prob,price:pick.ref_price,
        reference:pick.ref_book,odds_at:pick.odds_as_of,seal:pick.chain_sha256});
    }
    // Los bloqueos solo usan la identidad pública del evento. Ningún valor privado se copia a la vista.
    for(const p of entry.data.alta_probabilidad?.vip||[]) {
      if(!p.match_id||!p.local||!p.visitante||!p.kickoff_utc)continue;
      if(!events.has(p.match_id))events.set(p.match_id,{id:p.match_id,sport:'futbol',home:p.local,away:p.visitante,start:p.kickoff_utc,
        league:agenda.find(g=>g.match_id===p.match_id)?.liga?.nombre||p.league_id,status:'scheduled',markets:[],locked_count:0});
      events.get(p.match_id).locked_count++;
    }
    return [...events.values()];
  }
  function sources(offset=state.dayOffset) {
    const home=ensureHome(offset), nba=ensureSport('nba'),tenis=ensureSport('tenis');
    return {home,nba,tenis,events:[...football(home),...(nba.events||[]),...(tenis.events||[])]};
  }
  const eventKey=e=>`${e.sport}:${e.id}`;
  const featured=e=>e.markets.find(m=>m.id==='winner'||m.market==='winner')||e.markets[0];
  const timing=e=>e.status==='finished'?'Finalizado':e.status==='awaiting_result'?'Esperando resultado':new Date(e.start)<=new Date()?'Hora prevista superada':'Próximo';
  const sportTabs=events=>`<div class="chip-row" role="group" aria-label="Filtrar pronósticos por deporte">${Object.entries(names).map(([id,label])=>`<button type="button" data-sport="${id}" class="chip ${(state.sport||'todos')===id?'selected':''}" aria-pressed="${(state.sport||'todos')===id}">${label} · ${id==='todos'?events.length:events.filter(e=>e.sport===id).length}</button>`).join('')}</div>`;
  const action=e=>e.sport==='futbol'?`data-real-match="${esc(e.id)}"`:`data-sport-event="${esc(eventKey(e))}"`;

  function card(event) {
    const m=featured(event),locked=!m;
    return `<article class="live-pick ${locked?'locked-pick':''}"><div><span>${names[event.sport]} · ${esc(event.league)} · ${realDate(event.start)} ${realTime(event.start)}</span><h3>${esc(event.home)} <small>vs</small> ${esc(event.away)}</h3><p><strong>${locked?'Pronóstico con acceso Plus':esc(m.selection)}</strong></p><small>${locked?'La selección está reservada.':`Probabilidad publicada: ${fmtPct(m.probability)}`} · ${esc(timing(event))}</small><p><button type="button" class="text-link" ${locked?'data-route="planes"':action(event)}>${locked?'Consultar acceso Plus':'Ver análisis y mercados'} ↗</button></p>${event.locked_count?`<p><button type="button" class="text-link" data-route="planes">${event.locked_count} análisis adicional${event.locked_count===1?'':'es'} con Plus ↗</button></p>`:''}${m?.revised?'<p class="bottom-note">Revisión posterior al inicio. No cuenta como pronóstico previo.</p>':''}${!locked?`<details><summary>Registro del pronóstico</summary><p>Publicación: ${realDate(event.sealed_at)} ${realTime(event.sealed_at)}.</p><code>${esc(m.seal||event.seal||'Registro del motor')}</code>${m.odds_at?`<p>Cuota capturada: ${realDate(m.odds_at)} ${realTime(m.odds_at)}. Puede haber cambiado.</p>`:''}<p>${esc(m.reference||'Probabilidad estadística del motor')}</p></details>`:''}</div><div><span>${locked?'Acceso':m.price?'Cuota publicada':'Probabilidad estimada'}</span><strong>${locked?'Plus':m.price?fmtOdds(m.price):fmtPct(m.probability)}</strong><small>${locked?'Contenido reservado':m.price?esc(m.reference||'Cuota registrada'):'Análisis estadístico'}</small></div></article>`;
  }

  function board(source) {
    const date=localDay(addDays(state.dayOffset,12));
    const onDay=source.events.filter(e=>localDay(new Date(e.start))===date);
    const status=state.homeStatus||'proximos';
    const byStatus=onDay.filter(e=>status==='todos'||(status==='cerrados'?e.status==='finished':new Date(e.start)>new Date()&&e.status!=='finished'));
    const sport=state.sport||'todos',query=String(state.homeSearch||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();
    const rows=byStatus.filter(e=>(sport==='todos'||e.sport===sport)&&(!query||`${e.home} ${e.away} ${e.league}`.normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase().includes(query)))
      .sort((a,b)=>new Date(a.start)-new Date(b.start));
    const errors=[['futbol',source.home],['nba',source.nba],['tenis',source.tenis]].filter(([id,e])=>(sport==='todos'||sport===id)&&e.status==='error');
    const loading=[['futbol',source.home],['nba',source.nba],['tenis',source.tenis]].some(([id,e])=>(sport==='todos'||sport===id)&&e.status==='loading');
    const latest=source.events.filter(e=>sport==='todos'||e.sport===sport).sort((a,b)=>new Date(b.start)-new Date(a.start))[0];
    return `<section class="live-panel" id="pronosticos-hoy" aria-labelledby="hub-picks-title"><div class="live-head"><div><p class="eyebrow">PRONÓSTICOS / DATOS REALES</p><h2 id="hub-picks-title">Pronósticos ${esc(dayLabel(state.dayOffset).toLowerCase())}</h2></div><button type="button" class="text-link" data-action="refresh-public">Actualizar ↻</button></div>${sportTabs(byStatus)}${ctx.dayRail()}<div class="board-toolbar"><div class="chip-row" role="group" aria-label="Estado de los partidos">${[['proximos','Próximos'],['todos','Todos'],['cerrados','Finalizados']].map(([id,label])=>`<button type="button" class="chip ${status===id?'selected':''}" data-home-status="${id}" aria-pressed="${status===id}">${label}</button>`).join('')}</div><label class="search-field"><span class="sr-only">Buscar equipo, jugador o torneo</span><input type="search" id="home-search" data-input="home-search" value="${esc(state.homeSearch||'')}" placeholder="Equipo, jugador o torneo" /></label></div>${errors.map(([id])=>`<p class="bottom-note" role="status">${names[id]}: no se pudieron consultar los pronósticos. <button type="button" class="text-link" data-action="refresh-public">Reintentar</button></p>`).join('')}${rows.length?`<div class="live-pick-list">${rows.map(e=>card(e)).join('')}</div>`:loading?empty('Consultando los motores…','Estamos cargando las publicaciones de cada deporte.'):empty('Sin pronósticos para esta búsqueda','Prueba otro deporte o fecha. Los análisis aparecen cuando el motor los publica.')}${!rows.length&&!loading&&latest?`<p class="bottom-note">Última jornada publicada${sport!=='todos'?` de ${names[sport]}`:''}: ${realDate(latest.start)}. <button type="button" class="text-link" data-available-day="${localDay(new Date(latest.start))}">Consultar esa jornada ↗</button></p>`:''}<p class="live-reason">Hora de tu dispositivo. Las cuotas corresponden a la captura registrada y pueden cambiar. Una probabilidad no garantiza el resultado.</p><details class="publication-details"><summary>Más herramientas de fútbol</summary><div class="forecast-shortcuts"><button type="button" data-route="alta">Alta probabilidad ↗</button><button type="button" data-route="parley">Parley del día ↗</button><button type="button" data-route="escalera">Reto escalera ↗</button><button type="button" data-route="partidos">Agenda y estadísticas ↗</button></div></details></section>`;
  }

  function resultRows(source) {
    const footballRows=results().items||[];
    const items=footballRows.map(r=>({sport:'futbol',home:r.local,away:r.visitante,start:r.kickoff_utc,text:r.texto,outcome:r.outcome,price:r.ref_price,score:`${r.home_goals} – ${r.away_goals}`}));
    for(const e of source.events.filter(e=>e.sport!=='futbol')) {
      const m=featured(e);
      if(m&&['win','loss'].includes(m.outcome))items.push({sport:e.sport,home:e.home,away:e.away,start:e.start,text:m.selection,outcome:m.outcome,price:m.price,score:e.score});
    }
    return items.sort((a,b)=>new Date(b.start)-new Date(a.start)).filter(r=>(state.resultSport||'todos')==='todos'||r.sport===state.resultSport);
  }
  function recent(source,full=false) {
    const items=resultRows(source), shown=items.slice(0,full?50:5);
    return `<section class="live-panel" id="resultados" aria-labelledby="results-title"><div class="live-head"><div><p class="eyebrow">HISTORIAL / DATOS REALES</p><h2 id="results-title">Resultados recientes</h2></div>${full?'':'<button type="button" class="text-link" data-route="historial">Ver historial completo ↗</button>'}</div><p class="body-copy">Publicaciones resueltas, con aciertos y fallos por fecha. NBA y tenis corresponden al análisis estadístico de sus motores.</p>${full?`<div class="chip-row" role="group" aria-label="Filtrar resultados por deporte">${Object.entries(names).map(([id,label])=>`<button type="button" class="chip ${(state.resultSport||'todos')===id?'selected':''}" data-result-sport="${id}" aria-pressed="${(state.resultSport||'todos')===id}">${label}</button>`).join('')}</div>`:''}${shown.length?`<div class="table-wrap" tabindex="0" role="region" aria-label="Resultados reales por fecha"><table><thead><tr><th>Estado</th><th>Deporte</th><th>Partido</th><th>Pronóstico</th><th>Cuota / resultado</th><th>Fecha</th></tr></thead><tbody>${shown.map(r=>`<tr><td><span class="badge ${r.outcome==='win'?'good':'neg'}">${r.outcome==='win'?'Acertado':'Fallado'}</span></td><td>${names[r.sport]}</td><td>${esc(r.home)} vs ${esc(r.away)}</td><td>${esc(r.text)}</td><td>${r.price?fmtOdds(r.price):esc(r.score||'Registrado')}</td><td>${realDate(r.start)}</td></tr>`).join('')}</tbody></table></div>`:empty(results().status==='loading'?'Cargando resultados…':'Sin resultados disponibles','El historial aparece cuando los resultados están confirmados.')}<p class="live-reason">Las revisiones NBA posteriores al inicio no cuentan como pronósticos previos. Los resultados pasados no garantizan resultados futuros.</p></section>`;
  }

  function home() {
    const source=sources(),today=localDay(addDays(0,12)),events=source.events.filter(e=>localDay(new Date(e.start))===today);
    const upcoming=events.filter(e=>e.markets.length&&e.status!=='finished'&&new Date(e.start)>new Date()).length;
    return `<section class="forecast-hero" aria-labelledby="forecast-title"><div class="forecast-copy"><p class="eyebrow">FÚTBOL / NBA / TENIS</p><h1 id="forecast-title">Lee el partido.<br><em>Entiende la cuota.</em></h1><p>El contexto del encuentro, las probabilidades y los pronósticos publicados. Los tres deportes en un mismo lugar, con datos reales de los motores.</p><div class="hero-actions"><button type="button" class="primary-button" data-scroll-to="pronosticos-hoy">Ver pronósticos reales <span aria-hidden="true">↗</span></button><button type="button" class="text-link" data-route="historial">Ver historial verificable ↗</button></div></div><aside class="forecast-summary" aria-label="Resumen de publicaciones reales"><span class="summary-icon" aria-hidden="true">Q.</span><div><span class="eyebrow">PUBLICACIONES REALES / HOY</span><strong>${source.home.status==='ready'?upcoming:'—'}<small> análisis próximos</small></strong><p>Fútbol, NBA y tenis. Los análisis aparecen cuando están calculados y publicados.</p></div><div class="summary-bottom"><span>Tres deportes</span><span>Fuente: QuantFut</span></div></aside></section><div class="publication-strip"><span class="publication-dot ${source.home.status==='ready'?'active':''}" aria-hidden="true"></span><strong>Datos reales de los motores</strong><span>Pronósticos y resultados registrados.</span><button type="button" class="text-link" data-action="refresh-public">Actualizar ↻</button></div><div class="forecast-shortcuts"><button type="button" data-route="picks">Pronósticos publicados ↗</button><button type="button" data-route="historial">Resultados reales ↗</button><button type="button" data-route="partidos">Agenda y estadísticas ↗</button><button type="button" data-route="planes">Planes y acceso ↗</button></div>${board(source)}${recent(source)}${ctx.plansPreview?.()||''}`;
  }
  function picks(){return `<div class="view-title"><div><p class="eyebrow">FÚTBOL / NBA / TENIS</p><h1>Pronósticos</h1><p class="lead">Selecciona un deporte y una fecha para consultar las publicaciones reales.</p></div></div>${board(sources())}`;}
  function history(){return `<div class="view-title"><div><p class="eyebrow">EVIDENCIA / REGISTRO REAL</p><h1>Historial verificable</h1><p class="lead">Resultados publicados por el servidor, con aciertos y fallos a la vista.</p></div></div>${recent(sources(),true)}<details class="publication-details"><summary>Metodología y registros de verificación</summary>${ctx.liveEvidence()}</details>`;}

  function detail(){
    const source=sources(),e=source.events.find(e=>eventKey(e)===state.sportEvent);
    if(!e)return empty('No se pudo abrir el análisis','Vuelve a Pronósticos y selecciona un evento publicado.');
    const mode=state.sportMarket||'partido';
    const visible=e.markets.filter(m=>mode==='todos'||(e.sport==='nba'?(mode==='partido'?!String(m.market).startsWith('player_'):String(m.market).startsWith('player_')):(mode==='partido'?m.id==='winner':m.id!=='winner')));
    const marketFilters=[['partido',e.sport==='nba'?'Partido':'Ganador'],['otros',e.sport==='nba'?'Jugadores':'Juegos y sets'],['todos','Todo']];
    return `<div class="view-title"><div><button type="button" class="text-link" data-route="picks">← Volver a pronósticos</button><p class="eyebrow">${names[e.sport]} / ${esc(e.league)}</p><h1>${esc(e.home)} vs ${esc(e.away)}</h1><p>${realDate(e.start)} ${realTime(e.start)} · ${esc(timing(e))}${e.score?` · ${esc(e.score)}`:''}</p></div></div><p class="bottom-note">Probabilidades estadísticas del motor. Las líneas estadísticas no equivalen a cuotas publicadas de una casa.</p><div class="chip-row" role="group" aria-label="Tipo de mercado">${marketFilters.map(([id,label])=>`<button type="button" class="chip ${mode===id?'selected':''}" data-sport-market="${id}" aria-pressed="${mode===id}">${label}</button>`).join('')}</div><section class="live-panel"><div class="table-wrap" tabindex="0" role="region" aria-label="Análisis real del partido"><table><thead><tr><th>Mercado</th><th>Selección</th><th>Probabilidad</th><th>Referencia</th><th>Registro</th></tr></thead><tbody>${visible.map(m=>`<tr><td>${esc(m.label)}</td><td>${esc(m.selection)}</td><td>${fmtPct(m.probability)}${m.push_probability?`<small>Devolución ${fmtPct(m.push_probability)}</small>`:''}</td><td>${esc(m.reference||'Probabilidad estadística')}${m.conditional?'<small>Condicionado a la participación del jugador</small>':''}</td><td>${m.revised?'Revisión posterior al inicio; no cuenta como pronóstico previo':'Publicado por el motor'}</td></tr>`).join('')}</tbody></table></div><details><summary>Registro del análisis</summary><p>Publicado: ${realDate(e.sealed_at)} ${realTime(e.sealed_at)}</p><code>${esc(e.seal)}</code></details></section>`;
  }

  return {home,picks,history,detail};
}
