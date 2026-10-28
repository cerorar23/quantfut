import { publicForecasts, forecastGames } from './fichas-data.js?v=real-20261029';
import { createHistorialViews } from './historial-views.js?v=hist-limpio-20261028b';

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
        home_img:game?.local?.escudo||null,away_img:game?.visitante?.escudo||null,
        league:game?.liga?.nombre||pick.league_id,status:game?.estado||'scheduled',seal:pick.chain_sha256,sealed_at:pick.batch_date,markets:[],locked_count:0});
      events.get(pick.match_id).markets.push({id:pick.pick_key,label:'Pronóstico publicado',selection:pick.texto,probability:pick.prob,price:pick.ref_price,
        reference:pick.ref_book,odds_at:pick.odds_as_of,seal:pick.chain_sha256});
    }
    // Los bloqueos solo usan la identidad pública del evento. Ningún valor privado se copia a la vista.
    for(const p of entry.data.alta_probabilidad?.vip||[]) {
      if(!p.match_id||!p.local||!p.visitante||!p.kickoff_utc)continue;
      if(!events.has(p.match_id))events.set(p.match_id,{id:p.match_id,sport:'futbol',home:p.local,away:p.visitante,start:p.kickoff_utc,
        home_img:agenda.find(g=>g.match_id===p.match_id)?.local?.escudo||null,away_img:agenda.find(g=>g.match_id===p.match_id)?.visitante?.escudo||null,
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
  const action=e=>e.sport==='futbol'?`data-real-match="${esc(e.id)}"`:`data-sport-event="${esc(eventKey(e))}"`;

  // ---- piezas visuales (clases de CYBERCORE + disposición .win-pk-* en window.css)
  const norm=s=>String(s||'').normalize('NFD').replace(/[̀-ͯ]/g,'').toLowerCase();
  const svg=body=>`<svg class="win-pk-icon" viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">${body}</svg>`;
  const sportIcon={
    futbol:svg('<circle cx="12" cy="12" r="9"/><path d="M12 7.5l3.8 2.8-1.5 4.4H9.7L8.2 10.3z"/><path d="M12 3v4.5M20.3 9.2l-4.5 1.1M17.3 19l-3-4.3M6.7 19l3-4.3M3.7 9.2l4.5 1.1"/>'),
    nba:svg('<circle cx="12" cy="12" r="9"/><path d="M12 3v18M3 12h18"/><path d="M5.6 5.6c3.5 3.2 3.5 9.6 0 12.8M18.4 5.6c-3.5 3.2-3.5 9.6 0 12.8"/>'),
    tenis:svg('<circle cx="12" cy="12" r="9"/><path d="M5.2 5.5c4.2 2.2 4.2 10.8 0 13M18.8 5.5c-4.2 2.2-4.2 10.8 0 13"/>'),
    todos:svg('<rect x="4" y="4" width="7" height="7" rx="1.5"/><rect x="13" y="4" width="7" height="7" rx="1.5"/><rect x="4" y="13" width="7" height="7" rx="1.5"/><rect x="13" y="13" width="7" height="7" rx="1.5"/>')
  };
  const lockIcon=svg('<rect x="5" y="11" width="14" height="10" rx="2"/><path d="M8 11V8a4 4 0 018 0v3"/>');
  const words=name=>String(name||'?').replace(/[.()]/g,' ').split(/\s+/).filter(Boolean);
  const monogram=(name,sport)=>{
    const w=words(name);
    if(sport==='nba'){const code=ctx.nbaCode(name);if(code)return code;}
    if(sport==='tenis'||w.length>1)return ((w[0]?.[0]||'?')+(w.length>1?w[w.length-1][0]:'')).toUpperCase();
    return String(name||'?').slice(0,3).toUpperCase();
  };
  const tone=name=>{let h=0;for(const ch of String(name||''))h=(h*31+ch.charCodeAt(0))>>>0;return h%4;};
  // Solo imágenes del propio servidor (la política de contenido no admite dominios externos).
  const ownImage=src=>typeof src==='string'&&/^\/web\/[\w./-]+\.(png|jpe?g|webp|svg)$/i.test(src)?src:null;
  // Imagen de cada lado: escudo de fútbol (de la agenda), logo NBA o foto de tenis (manifiesto alojado en el servidor).
  const images=()=>ctx.ensureImages?.()||{status:'loading',nba:{},tenis:{}};
  function imageOf(event,side) {
    const name=side==='home'?event.home:event.away,own=side==='home'?event.home_img:event.away_img;
    if(own)return {src:own};
    const index=images();
    if(event.sport==='nba'){const hit=index.nba[monogram(name,'nba')];return hit?{src:`/web/imagenes/nba/${hit.f}`,logo:true}:{};}
    if(event.sport==='tenis'){const hit=index.tenis[norm(name)];return hit?{src:`/web/imagenes/tenis/${hit.f}`,photo:true,credit:`Foto: ${hit.a} · ${hit.l} (${hit.fuente || "Wikimedia Commons"})`}:{};}
    return {};
  }
  function avatar(name,sport,image={},big=false) {
    const url=ownImage(image.src);
    const kind=image.photo?'is-photo':image.logo?'is-logo':'';
    return url?`<span class="win-pk-avatar ${kind} ${big?'is-big':''}"><img src="${esc(url)}" alt="" loading="lazy" decoding="async"${image.credit?` title="${esc(image.credit)}"`:''}></span>`
      :`<span class="win-pk-avatar is-mono is-tone-${tone(name)} ${big?'is-big':''}" aria-hidden="true">${esc(monogram(name,sport))}</span>`;
  }
  const surfaceName=raw=>{const n=norm(raw);return /clay|arcilla|tierra/.test(n)?'Arcilla':/grass|hierba|cesped/.test(n)?'Hierba':/hard|dura|cemento/.test(n)?'Pista dura':String(raw||'');};
  const badgeFor=e=>{
    const t=timing(e);
    const kind=e.status==='finished'?'':t==='Próximo'?'cyber-badge--green':'cyber-badge--yellow';
    return `<span class="cyber-badge cyber-badge--sm ${kind}">${esc(t)}</span>`;
  };
  const sportLabel=e=>`${esc(names[e.sport])}`;
  const leagueLabel=e=>`${esc(e.league||'')}${e.sport==='tenis'&&e.surface?` · ${esc(surfaceName(e.surface))}`:''}`;
  const progress=value=>{const pct=Math.max(0,Math.min(100,Math.round(value*100)));return `<div class="cyber-progress cyber-progress--green cyber-progress--sm" data-value="${pct}" role="progressbar" aria-label="Probabilidad publicada ${pct}%" aria-valuenow="${pct}" aria-valuemin="0" aria-valuemax="100"><div class="cyber-progress__bar"></div></div>`;};
  const teamsRow=(e,big=false)=>`<div class="win-pk-teams"><div class="win-pk-side">${avatar(e.home,e.sport,imageOf(e,'home'),big)}<strong>${esc(e.home)}</strong></div><span class="win-pk-vs ${e.score?'is-score':''}">${e.score?esc(e.score):'VS'}</span><div class="win-pk-side is-away">${avatar(e.away,e.sport,imageOf(e,'away'),big)}<strong>${esc(e.away)}</strong></div></div>`;
  // Sin cuota publicada (NBA, tenis) no hay bloque de cuota: la probabilidad ya sale en su barra.
  const oddsBlock=m=>m.price?`<div class="win-pk-odds"><small>Cuota publicada</small><strong>${fmtOdds(m.price)}</strong><em>${esc(m.reference||'Casa registrada')}</em></div>`:'';

  function card(event) {
    const m=featured(event),locked=!m;
    const extra=event.locked_count?`<button type="button" class="text-link win-pk-more" data-route="planes">+${event.locked_count} análisis con Plus ↗</button>`:'';
    const head=`<header class="win-pk-top"><span class="win-pk-sport">${sportIcon[event.sport]}<b>${sportLabel(event)}</b></span><span class="win-pk-league">${leagueLabel(event)}</span><time class="win-pk-time" datetime="${esc(event.start)}">${realDate(event.start)} · ${realTime(event.start)}</time></header>`;
    if(locked)return `<article class="cyber-card cyber-card--yellow win-pk-card is-locked is-${event.sport}">${head}${teamsRow(event)}<div class="win-pk-pick"><div class="win-pk-sel"><small>Pronóstico</small><strong class="win-pk-masked">${lockIcon}<span>Contenido reservado</span></strong></div><div class="win-pk-odds is-prob"><small>Acceso</small><strong>Plus</strong><em>Selección y cuota privadas</em></div></div><footer class="win-pk-foot">${badgeFor(event)}<button type="button" class="cyber-btn cyber-btn--sm cyber-btn--yellow" data-route="planes">Consultar acceso Plus ↗</button></footer></article>`;
    const seal=`<details class="win-pk-seal"><summary>Registro del pronóstico</summary><p>Publicación: ${realDate(event.sealed_at)} ${realTime(event.sealed_at)}.</p><code>${esc(m.seal||event.seal||'Registro del motor')}</code>${m.odds_at?`<p>Cuota capturada: ${realDate(m.odds_at)} ${realTime(m.odds_at)}. Puede haber cambiado.</p>`:''}<p>${esc(m.reference||'Probabilidad estadística del motor')}</p></details>`;
    return `<article class="cyber-card cyber-card--interactive win-pk-card is-${event.sport}">${head}${teamsRow(event)}<div class="win-pk-pick ${m.price?'':'is-single'}"><div class="win-pk-sel"><small>Pronóstico</small><strong>${esc(m.selection)}</strong></div>${oddsBlock(m)}</div><div class="win-pk-prob"><span>Probabilidad del modelo</span><b>${fmtPct(m.probability)}</b>${progress(m.probability)}</div>${m.revised?'<p class="win-pk-note">Revisión posterior al inicio. No cuenta como pronóstico previo.</p>':''}<footer class="win-pk-foot">${badgeFor(event)}${extra}<button type="button" class="cyber-btn cyber-btn--sm cyber-btn--green win-pk-go" ${action(event)}>Ver análisis y mercados ↗</button></footer>${seal}</article>`;
  }

  function sportTabs(events) {
    const current=state.sport||'todos';
    return `<div class="cyber-tabs cyber-tabs--pills win-pk-tabs" role="group" aria-label="Filtrar pronósticos por deporte">${Object.entries(names).map(([id,label])=>{
      const count=id==='todos'?events.length:events.filter(e=>e.sport===id).length;
      return `<button type="button" data-sport="${id}" class="cyber-tab ${current===id?'cyber-tab--active':''}" aria-pressed="${current===id}">${sportIcon[id]}<span>${label}</span><b class="win-pk-count">${count}</b></button>`;
    }).join('')}</div>`;
  }

  // Cifras del encabezado: solo cuentan lo que ya publicó el servidor.
  function summary(onDay,source) {
    const published=onDay.filter(e=>e.markets.length);
    const upcoming=published.filter(e=>e.status!=='finished'&&new Date(e.start)>new Date()).length;
    const plus=onDay.reduce((n,e)=>n+(e.locked_count||0),0);
    const resolved=resultRows(source).slice(0,50),wins=resolved.filter(r=>r.outcome==='win').length;
    const tile=(label,value,hint)=>`<li class="win-pk-stat"><small>${label}</small><strong>${value}</strong><span>${hint}</span></li>`;
    return `<ul class="win-pk-stats" aria-label="Resumen del día">${tile('Publicados',source.home.status==='ready'||published.length?published.length:'—','pronósticos del día')}${tile('Próximos',source.home.status==='ready'||published.length?upcoming:'—','aún sin empezar')}${tile('Con Plus',plus,'análisis reservados')}${tile('Aciertos',resolved.length?`${wins}/${resolved.length}`:'—','últimos resueltos')}</ul>`;
  }

  // Destacado del día: la regla de la web (`partido_mercados`: mayor probabilidad con cuota de 1,40 a 1,80) aplicada solo
  // a los pronósticos ya publicados y abiertos. No genera nada: elige entre lo que envía el servidor.
  const FEATURED_RANGE=[1.4,1.8];
  const featuredPick=picks=>picks.filter(p=>p&&p.locked!==true&&p.chain_sha256&&typeof p.ref_price==='number'&&Number.isFinite(p.ref_price)
    &&p.ref_price>=FEATURED_RANGE[0]&&p.ref_price<=FEATURED_RANGE[1]).reduce((best,p)=>(!best||p.prob>best.prob?p:best),null);

  function featuredCard(onDay,source,date) {
    if(source.home.status!=='ready')return '';
    const todays=publicForecasts(source.home.data).filter(p=>localDay(new Date(p.kickoff_utc))===date);
    const pick=featuredPick(todays);
    const event=pick&&source.events.find(e=>e.sport==='futbol'&&e.id===pick.match_id);
    if(!pick||!event)return '';
    return `<aside class="cyber-card cyber-card--green win-pk-featured" aria-label="Pronóstico destacado"><p class="eyebrow">Pronóstico destacado</p><span class="win-pk-league">${leagueLabel(event)} · ${realDate(event.start)} ${realTime(event.start)}</span>${teamsRow(event,true)}<div class="win-pk-pick"><div class="win-pk-sel"><small>Selección</small><strong>${esc(pick.texto)}</strong></div>${oddsBlock({price:pick.ref_price,probability:pick.prob,reference:pick.ref_book})}</div><div class="win-pk-prob"><span>Probabilidad del modelo</span><b>${fmtPct(pick.prob)}</b>${progress(pick.prob)}</div><button type="button" class="cyber-btn cyber-btn--green win-pk-go" data-real-match="${esc(event.id)}">Ver análisis y mercados ↗</button></aside>`;
  }

  function skeleton() {
    return `<div class="win-pk-grid" aria-hidden="true">${[1,2,3].map(()=>'<div class="cyber-skeleton-card"><div class="cyber-skeleton-card__header"><div class="cyber-skeleton cyber-skeleton--avatar"></div><div class="cyber-skeleton cyber-skeleton--title"></div></div><div class="cyber-skeleton-card__body"><div class="cyber-skeleton cyber-skeleton--text"></div><div class="cyber-skeleton cyber-skeleton--text"></div></div></div>').join('')}</div>`;
  }

  function board(source) {
    const date=localDay(addDays(state.dayOffset,12));
    const onDay=source.events.filter(e=>localDay(new Date(e.start))===date);
    const status=state.homeStatus||'proximos';
    const byStatus=onDay.filter(e=>status==='todos'||(status==='cerrados'?e.status==='finished':new Date(e.start)>new Date()&&e.status!=='finished'));
    const sport=state.sport||'todos',query=norm(state.homeSearch);
    const rows=byStatus.filter(e=>(sport==='todos'||e.sport===sport)&&(!query||norm(`${e.home} ${e.away} ${e.league}`).includes(query)))
      .sort((a,b)=>new Date(a.start)-new Date(b.start));
    const shown=[['futbol',source.home],['nba',source.nba],['tenis',source.tenis]].filter(([id])=>sport==='todos'||sport===id);
    const errors=shown.filter(([,e])=>e.status==='error');
    const loading=shown.some(([,e])=>e.status==='loading');
    const latest=source.events.filter(e=>sport==='todos'||e.sport===sport).sort((a,b)=>new Date(b.start)-new Date(a.start))[0];
    const groups=sport==='todos'?['futbol','nba','tenis'].map(id=>[id,rows.filter(e=>e.sport===id)]).filter(([,list])=>list.length):[[sport,rows]];
    const list=groups.map(([id,items])=>`<section class="win-pk-group" aria-label="${esc(names[id])}">${sport==='todos'?`<h3 class="win-pk-group-title">${sportIcon[id]}<span>${esc(names[id])}</span><b class="win-pk-count">${items.length}</b></h3>`:''}<div class="win-pk-grid">${items.map(card).join('')}</div></section>`).join('');
    const body=rows.length?list:loading?skeleton():empty('Sin pronósticos para esta búsqueda','Prueba otro deporte o fecha. Los análisis aparecen cuando el motor los publica.');
    return `<section class="win-pk-board" id="pronosticos-hoy" aria-labelledby="hub-picks-title"><div class="win-pk-bar"><div class="win-pk-bar-row">${sportTabs(byStatus)}<button type="button" class="cyber-btn cyber-btn--sm cyber-btn--ghost win-pk-refresh" data-action="refresh-public">Actualizar ↻</button></div>${ctx.dayRail()}</div><div class="win-pk-heading"><h2 id="hub-picks-title">Pronósticos ${esc(dayLabel(state.dayOffset).toLowerCase())}</h2><div class="win-pk-filters"><div class="chip-row" role="group" aria-label="Estado de los partidos">${[['proximos','Próximos'],['todos','Todos'],['cerrados','Finalizados']].map(([id,label])=>`<button type="button" class="chip ${status===id?'selected':''}" data-home-status="${id}" aria-pressed="${status===id}">${label}</button>`).join('')}</div><label class="search-field"><span class="sr-only">Buscar equipo, jugador o torneo</span><input type="search" id="home-search" data-input="home-search" value="${esc(state.homeSearch||'')}" placeholder="Equipo, jugador o torneo" /></label></div></div>${errors.map(([id])=>`<p class="bottom-note" role="status">${names[id]}: no se pudieron consultar los pronósticos. <button type="button" class="text-link" data-action="refresh-public">Reintentar</button></p>`).join('')}${body}</section>`;
  }

  function picksPage(source) {
    const date=localDay(addDays(state.dayOffset,12));
    const onDay=source.events.filter(e=>localDay(new Date(e.start))===date);
    const feat=featuredCard(onDay,source,date);
    return `<div class="win-pk"><section class="win-pk-hero ${feat?'has-featured':''}" aria-labelledby="picks-title"><div class="cyber-card cyber-card--holo win-pk-hero-copy"><p class="eyebrow">Fútbol / NBA / Tenis</p><h1 id="picks-title">Pronósticos del día</h1><p class="lead">Selecciones calculadas y selladas por el motor, con su probabilidad y su registro. Elige deporte y fecha para ver lo publicado.</p>${summary(onDay,source)}<p class="win-pk-links"><button type="button" class="text-link" data-route="historial">Ver historial verificable ↗</button></p></div>${feat}</section>${board(source)}</div>`;
  }

  function allResults(source) {
    const footballRows=results().items||[];
    const items=footballRows.map(r=>({sport:'futbol',home:r.local,away:r.visitante,start:r.kickoff_utc,text:r.texto,outcome:r.outcome,price:r.ref_price,prob:r.prob,score:`${r.home_goals} – ${r.away_goals}`}));
    for(const e of source.events.filter(e=>e.sport!=='futbol')) {
      const m=featured(e);
      if(m&&['win','loss'].includes(m.outcome))items.push({sport:e.sport,home:e.home,away:e.away,start:e.start,text:m.selection,outcome:m.outcome,price:m.price,prob:m.probability,score:e.score});
    }
    return items.sort((a,b)=>new Date(b.start)-new Date(a.start));
  }
  function resultRows(source) {
    return allResults(source).filter(r=>(state.resultSport||'todos')==='todos'||r.sport===state.resultSport);
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
  function picks(){return picksPage(sources());}
  const historial=createHistorialViews({esc,state,fmtOdds,realTime,localDay:d=>localDay(d)});
  function history(){
    const source=sources();
    const loading=results().status==='loading'||source.nba.status==='loading'||source.tenis.status==='loading';
    return historial.historyView(allResults(source),loading);
  }

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
