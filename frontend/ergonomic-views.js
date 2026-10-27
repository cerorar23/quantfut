import { publicForecasts, forecastGames } from './fichas-data.js?v=real-20261027';

export function createHubViews(ctx) {
  const {state,esc,ensureHome,addDays,localDay,dayLabel,realDate,realTime,fmtOdds,fmtPct}=ctx;
  const names={todos:'Todos',futbol:'Fútbol',nba:'NBA',tenis:'Tenis'};
  const icons={futbol:'◉',nba:'◈',tenis:'◎'};
  const ensureSport=s=>ctx.ensureSport?.(s)||{status:'loading',events:[]};
  const results=()=>ctx.ensureResults?.()||{status:'loading',items:[]};
  const empty=(title,text)=>`<div class="hub-empty"><span aria-hidden="true">◎</span><h3>${esc(title)}</h3><p>${esc(text)}</p><button type="button" class="text-link" data-action="refresh-public">Volver a consultar ↻</button></div>`;
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
  const sportTabs=(events)=>`<div class="hub-sports" role="group" aria-label="Filtrar pronósticos por deporte">${Object.entries(names).map(([id,label])=>`<button type="button" data-sport="${id}" class="${(state.sport||'todos')===id?'selected':''}" aria-pressed="${(state.sport||'todos')===id}"><span aria-hidden="true">${icons[id]||'▦'}</span>${label}<small>${id==='todos'?events.length:events.filter(e=>e.sport===id).length}</small></button>`).join('')}</div>`;
  const action=e=>e.sport==='futbol'?`data-real-match="${esc(e.id)}"`:`data-sport-event="${esc(eventKey(e))}"`;

  function card(event,hero=false) {
    const m=featured(event),locked=!m;
    return `<article class="hub-pick ${hero?'hub-featured':''} ${locked?'hub-locked':''}">
      <div class="hub-pick-top"><span class="hub-sport-label ${event.sport}"><i aria-hidden="true">${icons[event.sport]}</i>${names[event.sport]}</span><span class="hub-pick-access">${locked?'◈ Plus':event.sport==='futbol'?'Abierto':'Estadístico'}</span></div>
      <p class="hub-league">${esc(event.league)} <span>· ${realDate(event.start)} · ${realTime(event.start)}</span></p>
      <div class="hub-teams"><span class="hub-team-mark" aria-hidden="true">${esc(event.home.charAt(0))}</span><h3>${esc(event.home)}<small>vs</small>${esc(event.away)}</h3><span class="hub-team-mark away" aria-hidden="true">${esc(event.away.charAt(0))}</span></div>
      ${locked?`<div class="hub-private"><span aria-hidden="true">▧</span><strong>Pronóstico con acceso Plus</strong><p>Consulta los planes para ampliar tu acceso.</p></div>`:`<div class="hub-selection"><span>${esc(m.label||'Pronóstico')}</span><strong>${esc(m.selection)}</strong></div><dl class="hub-pick-metrics"><div><dt>Probabilidad estimada</dt><dd>${fmtPct(m.probability)}</dd></div><div><dt>${m.price?'Cuota publicada':'Tipo de análisis'}</dt><dd class="${m.price?'':'hub-stat-label'}">${m.price?fmtOdds(m.price):'Estadístico'}</dd></div></dl>`}
      <div class="hub-pick-bottom"><span>${esc(timing(event))}${m?.revised?' · Revisión posterior':''}${m?.reference&&m.price?` · ${esc(m.reference)}`:''}</span><button type="button" class="${hero?'primary-button':'secondary-button'}" ${locked?'data-route="planes"':action(event)}>${locked?'Ver acceso Plus':'Ver análisis'} <span aria-hidden="true">↗</span></button></div>
      ${event.locked_count?`<button type="button" class="hub-extra-plus" data-route="planes">${event.locked_count} análisis adicional${event.locked_count===1?'':'es'} con Plus ↗</button>`:''}
      ${m?.revised?'<p class="hub-card-note">Revisión posterior al inicio. No cuenta como pronóstico previo.</p>':''}
    </article>`;
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
    return `<section class="hub-section" id="pronosticos-hoy" aria-labelledby="hub-picks-title"><div class="hub-section-head"><div><p class="eyebrow">ELIGE TU PRÓXIMO ANÁLISIS</p><h2 id="hub-picks-title">Pronósticos <em>${esc(dayLabel(state.dayOffset).toLowerCase())}</em></h2></div><button type="button" class="text-link" data-action="refresh-public">Actualizar <span aria-hidden="true">↻</span></button></div>
      ${sportTabs(byStatus)}<div class="hub-board-tools">${ctx.dayRail()}<label class="hub-search"><span aria-hidden="true">⌕</span><span class="sr-only">Buscar equipo, jugador o torneo</span><input type="search" id="home-search" data-input="home-search" value="${esc(state.homeSearch||'')}" placeholder="Equipo, jugador o torneo" /></label></div><div class="hub-state-filter" role="group" aria-label="Estado de los partidos">${[['proximos','Próximos'],['todos','Todos'],['cerrados','Finalizados']].map(([id,label])=>`<button type="button" class="chip ${status===id?'selected':''}" data-home-status="${id}" aria-pressed="${status===id}">${label}</button>`).join('')}</div>
      ${errors.map(([id])=>`<p class="hub-source-error" role="status">${names[id]}: no se pudieron consultar los pronósticos. <button type="button" class="text-link" data-action="refresh-public">Reintentar</button></p>`).join('')}
      ${rows.length?`<div class="hub-pick-grid">${rows.map(e=>card(e)).join('')}</div>`:loading?empty('Consultando los motores…','Estamos cargando las publicaciones de cada deporte.'):empty('Sin pronósticos para esta búsqueda','Prueba otro deporte o fecha. Los nuevos análisis aparecen cuando el motor los publica.')}
      ${!rows.length&&!loading&&latest?`<div class="hub-latest"><span>Última jornada publicada${sport!=='todos'?` de ${names[sport]}`:''}: ${realDate(latest.start)}.</span><button type="button" class="secondary-button" data-available-day="${localDay(new Date(latest.start))}">Consultar esa jornada ↗</button></div>`:''}
      <p class="hub-caption">Hora de tu dispositivo. Las cuotas corresponden a su captura y pueden cambiar. Una probabilidad estimada no garantiza el resultado.</p>
      <div class="hub-tools-links" aria-label="Más análisis de fútbol"><span>Más fútbol</span><button type="button" data-route="alta">Alta probabilidad ↗</button><button type="button" data-route="parley">Parley del día ↗</button><button type="button" data-route="escalera">Reto escalera ↗</button><button type="button" data-route="partidos">Agenda y estadísticas ↗</button></div></section>`;
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
    return `<section class="hub-section hub-results" id="resultados" aria-labelledby="results-title"><div class="hub-section-head"><div><p class="eyebrow">CADA RESULTADO CUENTA</p><h2 id="results-title">Resultados recientes<span class="hub-heading-dot">.</span></h2></div>${full?'':'<button type="button" class="text-link" data-route="historial">Ver historial completo ↗</button>'}</div>
      <p class="hub-section-intro">Publicaciones resueltas, con aciertos y fallos en orden de fecha. NBA y tenis corresponden al análisis estadístico de cada motor.</p>
      ${full?`<div class="hub-result-filters" role="group" aria-label="Filtrar resultados por deporte">${Object.entries(names).map(([id,label])=>`<button type="button" class="chip ${(state.resultSport||'todos')===id?'selected':''}" data-result-sport="${id}" aria-pressed="${(state.resultSport||'todos')===id}">${label}</button>`).join('')}</div>`:''}
      ${shown.length?`<div class="hub-result-list">${shown.map(r=>`<article class="hub-result-row"><span class="hub-result-status ${r.outcome}">${r.outcome==='win'?'✓ Acertado':'× Fallado'}</span><div><strong>${esc(r.text)}</strong><span>${esc(r.home)} vs ${esc(r.away)}</span></div><span class="hub-result-meta">${names[r.sport]} · ${realDate(r.start)}<small>${r.price?`Cuota ${fmtOdds(r.price)}`:esc(r.score||'Resultado registrado')}</small></span></article>`).join('')}</div>`:empty(results().status==='loading'?'Cargando resultados…':'Sin resultados disponibles','El historial se muestra cuando los resultados han sido confirmados.')}
      <p class="hub-caption">Las revisiones NBA posteriores al inicio se excluyen de esta lista. Los resultados pasados no garantizan resultados futuros.</p></section>`;
  }
  function home() {
    const source=sources(),today=localDay(addDays(0,12)),events=source.events.filter(e=>localDay(new Date(e.start))===today);
    const first=events.find(e=>e.markets.length&&new Date(e.start)>new Date())||events.find(e=>e.markets.length);
    const open=events.filter(e=>e.markets.length&&e.status!=='finished'&&new Date(e.start)>new Date()).length, locked=events.reduce((n,e)=>n+(e.locked_count||0),0);
    return `<section class="hub-hero"><div class="hub-hero-copy"><p class="eyebrow"><span class="hub-live-dot" aria-hidden="true"></span> FÚTBOL · NBA · TENIS</p><h1>Pronósticos claros.<br><em>Todo en su sitio.</em></h1><p>Encuentra los análisis del día, consulta las probabilidades y revisa los resultados. Tres deportes, una sola experiencia.</p><div class="hub-hero-actions"><button type="button" class="primary-button" data-scroll-to="pronosticos-hoy">Ver pronósticos de hoy <span aria-hidden="true">↓</span></button><button type="button" class="text-link" data-route="historial">Explorar resultados ↗</button></div><div class="hub-hero-foot"><span>✓ Publicaciones registradas</span><span>✓ Datos de los motores</span></div></div><div class="hub-hero-preview"><div class="hub-preview-label"><span>UN ANÁLISIS PARA EMPEZAR</span><span aria-hidden="true">01 / QF</span></div>${first?card(first,true):empty('Los análisis se están preparando','Consulta los pronósticos publicados más abajo.')}</div></section>
      <div class="hub-metrics" aria-label="Resumen real del día"><div><span>01 / PARA CONSULTAR</span><strong>${source.home.status==='ready'?open:'—'}<small> análisis próximos hoy</small></strong></div><div><span>02 / UN MISMO ESPACIO</span><strong>3<small> deportes para explorar</small></strong></div><div><span>03 / ACCESO PLUS</span><strong>${source.home.status==='ready'?locked:'—'}<small> pronósticos reservados</small></strong></div></div>
      ${board(source)}${recent(source)}${ctx.plansPreview?.()||''}`;
  }
  function picks(){return `<div class="hub-page-title"><p class="eyebrow">EL DÍA EN UN SOLO LUGAR</p><h1>Tus deportes. <em>Tus análisis.</em></h1><p>Filtra por deporte y fecha para encontrar lo que quieres consultar.</p></div>${board(sources())}`;}
  function history(){return `<div class="hub-page-title"><p class="eyebrow">HISTORIAL PÚBLICO</p><h1>Resultados a la vista<span class="hub-heading-dot">.</span></h1><p>Consulta las publicaciones resueltas y conserva el contexto de cada deporte.</p></div>${recent(sources(),true)}<details class="hub-technical"><summary>Ver metodología y registros de verificación</summary>${ctx.liveEvidence()}</details>`;}
  function detail(){
    const source=sources(),e=source.events.find(e=>eventKey(e)===state.sportEvent);
    if(!e)return empty('No se pudo abrir el análisis','Vuelve a Pronósticos y selecciona un evento publicado.');
    const mode=state.sportMarket||'partido';
    const visible=e.markets.filter(m=>mode==='todos'||(e.sport==='nba'?(mode==='partido'?!String(m.market).startsWith('player_'):String(m.market).startsWith('player_')):(mode==='partido'?m.id==='winner':m.id!=='winner')));
    const marketFilters=[['partido',e.sport==='nba'?'Partido':'Ganador'],['otros',e.sport==='nba'?'Jugadores':'Juegos y sets'],['todos','Todo']];
    return `<div class="hub-page-title"><button type="button" class="text-link" data-route="picks">← Volver a pronósticos</button><p class="eyebrow">${names[e.sport]} · ${esc(e.league)}</p><h1>${esc(e.home)}<br><em>${esc(e.away)}</em></h1><p>${realDate(e.start)} · ${realTime(e.start)} · ${timing(e)}${e.score?` · ${esc(e.score)}`:''}</p></div><p class="hub-analysis-note">Probabilidades estadísticas del motor. ${e.sport==='nba'?'Las líneas estadísticas no equivalen a cuotas de una casa.':'Las probabilidades de juegos o sets pueden incluir una devolución en líneas enteras.'}</p><div class="hub-state-filter" role="group" aria-label="Tipo de mercado">${marketFilters.map(([id,label])=>`<button type="button" class="chip ${mode===id?'selected':''}" data-sport-market="${id}" aria-pressed="${mode===id}">${label}</button>`).join('')}</div><div class="hub-market-grid">${visible.map(m=>`<article class="hub-market-card"><span class="hub-market-label">${esc(m.label)}</span><h2>${esc(m.selection)}</h2><strong class="hub-market-prob">${fmtPct(m.probability)}</strong><p>Probabilidad estimada${m.push_probability?` · Devolución ${fmtPct(m.push_probability)}`:''}</p>${m.conditional?'<p>Condicionado a la participación del jugador.</p>':''}${m.revised?'<p class="hub-source-error">Revisión posterior al inicio; no cuenta como pronóstico previo.</p>':''}<small>${esc(m.reference||'Publicación del motor')}</small></article>`).join('')}</div><details class="hub-technical"><summary>Registro del análisis</summary><p>Publicado: ${realDate(e.sealed_at)} ${realTime(e.sealed_at)}</p><code>${esc(e.seal)}</code></details>`;
  }
  return {home,picks,history,detail};
}
