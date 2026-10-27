"use strict";
const $ = (id) => document.getElementById(id);
const dateOptions = { timeZone: 'America/Mexico_City', day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit', hour12: false };
const date = (value) => value ? new Intl.DateTimeFormat('es-MX', dateOptions).format(new Date(value)) : 'Sin actualización verificada';
const number = (n, places=1) => new Intl.NumberFormat('es-MX', { minimumFractionDigits: 0, maximumFractionDigits: places }).format(n);
const statusNames = { pending: 'Pendiente', awaiting_result: 'Esperando resultado', evaluated: 'Evaluado', dnp: 'No participó', validation_hold: 'Resultado en revisión', result_unavailable: 'Resultado no disponible' };
const MARKET_ORDER = ['player_points','player_rebounds','player_assists','player_points_rebounds','player_points_assists','player_rebounds_assists','player_points_rebounds_assists','player_threes','player_steals','player_blocks','player_turnovers','player_blocks_steals'];
let data = null, market = 'all', modelMarket = 'all', loading = false;
function node(tag, css, text) { const n = document.createElement(tag); if (css) n.className = css; if (text !== undefined) n.textContent = text; return n; }
function link(url, text) { const n = node('a', 'official', text); if (/^https:\/\/www\.nba\.com\/game\/[a-z]{2,3}-vs-[a-z]{2,3}-00[2456]\d{7}(\/box-score)?$/.test(url)) { n.href=url; n.target='_blank'; n.rel='noopener noreferrer'; } return n; }
function isPending(row) { return !['evaluated','dnp'].includes(row.result.status); }
function modelCard(r,event) {
      const card=node('div','player-card');card.append(node('p','player-name',r.player),node('span','market-name',r.market_label));
      if(r.market==='winner') {
        card.append(node('p','estimate',`${number(r.probability_over*100)}%`),node('p','',`Gana ${event.home_team}`),node('p','model-note',`${number(r.probability_under*100)}% gana ${event.away_team}`));
      } else {
        card.append(node('p','estimate',number(r.estimate)),node('p','model-note',`Rango central 80%: ${number(r.range_low)}–${number(r.range_high)}`));
        const over=r.probability_over>=r.probability_under;
        card.append(node('p','probability',`${number(Math.max(r.probability_over,r.probability_under)*100)}% ${over?'más':'menos'} de ${number(r.line)}`),node('p','line-reference',r.reference||'Umbral estadístico de referencia'));
      }
      const outcome=r.result;
      const actual=r.market==='winner'?(outcome.actual===1?event.home_team:event.away_team):number(outcome.actual);
      card.append(node('p','result-line',outcome.status==='evaluated'?`Resultado oficial: ${actual}`:(statusNames[outcome.status]||'Pendiente')));
      const status=r.report_status&&r.report_status!=='no_listado'?` · Reporte oficial: ${r.report_status}${r.probability_play===null||r.probability_play===undefined?'':` (juega ${number(r.probability_play*100,0)}% de las veces)`}`:'';
      card.append(node('p','model-note',r.conditional_participation?`Condicionado a participación (si no juega, no cuenta)${status}`:'Partido completo · Prórroga incluida'));
      if(r.recalculated_at_utc) card.append(node('p','model-note',r.performance_eligible===false?`Recalculado ${date(r.recalculated_at_utc)}, después del inicio: no cuenta en el marcador`:`Actualizado ${date(r.recalculated_at_utc)}, antes del inicio`));
      const details=node('details','details');details.append(node('summary','','Registro del modelo'),node('p','',`Registrado ${date(r.sealed_at_utc)}. Último partido usado: ${r.last_feature_date}. Sin cuotas como entrada.`));
      if(r.original_sealed_at_utc&&r.original_probability_over!==undefined) details.append(node('p','',`Publicación original ${date(r.original_sealed_at_utc)}: ${number(r.original_probability_over*100)}% más${r.market==='winner'?' (gana local)':''}, estimación ${number(r.original_estimate)}.`));
      card.append(details);
  return card;
}
function renderModels() {
  $('models').replaceChildren();$('comparison-rows').replaceChildren();
  if(!data?.extension){$('models-count').textContent='Nuevos modelos sin datos verificados en esta actualización';return;}
  const extension=data.extension, rows=extension.predictions.filter(r=>modelMarket==='all'||r.market===modelMarket);
  $('models-count').textContent=`${extension.totals.predictions} pronósticos nuevos · 9 mercados · ${extension.totals.evaluated} resultados · Piloto original conservado`;
  for(const event of data.events) {
    const matches=rows.filter(r=>r.event_id===event.event_id);if(!matches.length)continue;
    const game=node('article','game'),head=node('div','game-header'),names=node('div');
    names.append(node('h3','game-title',`${event.away_team} · ${event.home_team}`),node('p','game-time',`${date(event.tipoff_utc)} · Ciudad de México`));
    head.append(names,link(event.official_url,'Resultado oficial ↗'));game.append(head);
    const grid=node('div','player-grid');
    for(const r of matches) grid.append(modelCard(r,event));
    game.append(grid);$('models').append(game);
  }
  for(const [key,m] of Object.entries(extension.comparison.markets)) {
    const selected=m.selections.find(s=>s.min_probability===.7),tr=node('tr');
    const label=extension.predictions.find(r=>r.market===key)?.market_label||key;
    const percent=p=>p===null?'Sin casos':`${number(p*100)}%`;
    for(const value of [label,number(m.observations,0),`${percent(selected.accuracy)} (${selected.selected})`,percent(selected.mean_probability),percent(selected.coverage),percent(selected.baseline_accuracy_same_units),`${number(m.paired_brier_difference,4)} [${m.paired_brier_difference_95_ci.map(v=>number(v,4)).join('; ')}]`])tr.append(node('td','',value));
    $('comparison-rows').append(tr);
  }
}
const availabilityText = (a) => a.state==='reporte_aplicado'
  ? `Disponibilidad: reporte oficial de lesiones de ${date(a.report_timestamp_utc)} (recibido al menos 60 min antes del salto) · ${a.used} jugadores con efecto · puntos esperados perdidos: local ${number(a.missing_points_home)}, visitante ${number(a.missing_points_away)}`
  : 'Disponibilidad: sin reporte oficial válido 60 min antes del salto; este pronóstico no incorpora lesiones';
function renderLive() {
  const box=$('live-v13'), cohorts=data?.live_v13?.cohorts||[];
  box.replaceChildren();$('live-section').hidden=!cohorts.length;if(!cohorts.length)return;
  const events=cohorts.flatMap(c=>c.events), rows=cohorts.flatMap(c=>c.predictions);
  $('live-count').textContent=`${events.length} partidos · ${rows.length} pronósticos · ${rows.filter(r=>r.result.status==='evaluated').length} resultados oficiales · modelo ${cohorts[0].version}`;
  for(const cohort of cohorts) {
    const recalculated=cohort.recalculated_at_utc?` · recalculada ${date(cohort.recalculated_at_utc)} con ${cohort.current_season_games} partidos de esta temporada${cohort.active_strength?' y fuerza individual de las plantillas actuales':''}`:'';
    const head=node('p','model-note',`Cohorte ${cohort.cohort_date} · sellada ${date(cohort.created_at_utc)} antes de cada salto · entrenado con ${new Intl.ListFormat('es',{type:'conjunction'}).format(cohort.train_seasons)}${recalculated}`);box.append(head);
    const names={winner:'Ganador',team_points:'Puntos de equipo',game_total:'Total',player_points:'Puntos de jugador',player_rebounds:'Rebotes',player_assists:'Asistencias',player_points_rebounds:'Puntos + rebotes',player_points_assists:'Puntos + asistencias',player_rebounds_assists:'Rebotes + asistencias',player_points_rebounds_assists:'Puntos + rebotes + asistencias',player_threes:'Triples',player_steals:'Robos',player_blocks:'Tapones',player_turnovers:'Pérdidas',player_blocks_steals:'Robos + tapones'},done=Object.entries(cohort.scorecard).filter(([,v])=>v.n>0);
    if(done.length) box.append(node('p','model-note',`Marcador (Brier, menor es mejor): ${done.map(([k,v])=>`${names[k]} ${number(v.brier,3)} (${v.n})`).join(' · ')}`));
    for(const event of cohort.events) {
      const game=node('article','game'),top=node('div','game-header'),names2=node('div'),meta=node('div','game-meta');
      names2.append(node('h3','game-title',`${event.away_team} · ${event.home_team}`),node('p','game-time',`${date(event.tipoff_utc)} · Ciudad de México`));
      meta.append(node('span',`badge ${event.status==='evaluated'?'done':event.status==='validation_hold'?'warn':''}`,statusNames[event.status]||'Pendiente'),link(event.official_url,'Partido en NBA.com ↗'));
      top.append(names2,meta);game.append(top,node('p','model-note',availabilityText(event.availability)));
      if(event.final) game.append(node('p','result-line',`Marcador oficial: ${event.away_team} ${event.final.away} · ${event.home_team} ${event.final.home}`));
      const grid=node('div','player-grid');
      for(const r of cohort.predictions.filter(r=>r.event_id===event.event_id)) grid.append(modelCard(r,event));
      game.append(grid);box.append(game);
    }
  }
}
function render() {
  if (!data) return;
  renderModels();renderLive();
  $('total-predictions').textContent=data.totals.predictions; $('total-players').textContent=`${data.totals.players} jugadores`;
  $('total-events').textContent=data.totals.events; $('total-evaluated').textContent=data.totals.evaluated;
  $('result-caption').textContent=data.totals.evaluated ? `${data.totals.predictions-data.totals.evaluated-data.totals.dnp} pendientes · ${data.totals.dnp} sin participación` : 'Pendientes del resultado oficial';
  const pilot=data.health.pilot.state, healthy=['waiting','completed'].includes(pilot);
  $('live-state').textContent=pilot==='completed'?'Piloto evaluado':healthy?'Piloto en seguimiento':'Seguimiento requiere revisión';
  $('live-dot').classList.toggle('warn',!healthy);
  const next=data.events.find(e=>e.status==='pending') || data.events.find(e=>e.status!=='evaluated');
  $('next-game').textContent=next?date(next.tipoff_utc):'Resultados recibidos';
  $('updated').textContent=`Datos comprobados: ${date(data.as_of)}`;
  const query=$('search').value.trim().toLocaleLowerCase('es'), selectedEvent=$('event-filter').value, selectedStatus=$('status-filter').value;
  const rows=data.predictions.filter(r=> (market==='all'||r.market===market) && (selectedEvent==='all'||r.event_id===selectedEvent)
    && (selectedStatus==='all'||(selectedStatus==='pending'?isPending(r):r.result.status===selectedStatus))
    && (!query||`${r.player} ${data.events.find(e=>e.event_id===r.event_id)?.home_team} ${data.events.find(e=>e.event_id===r.event_id)?.away_team}`.toLocaleLowerCase('es').includes(query)));
  $('visible-count').textContent=`${rows.length} de ${data.totals.predictions} pronósticos · ${data.totals.players} jugadores en el piloto`;
  $('games').replaceChildren(); $('message').hidden=rows.length>0;
  if (!rows.length) $('message').textContent=selectedStatus==='evaluated'?'Todavía no hay resultados evaluados para esta selección. Aparecerán cuando se reciba el boxscore oficial.':'No hay pronósticos que coincidan con estos filtros.';
  for (const event of data.events) {
    const matches=rows.filter(r=>r.event_id===event.event_id); if (!matches.length) continue;
    const game=node('article','game'), header=node('div','game-header'), title=node('div');
    title.append(node('h3','game-title',`${event.away_team} · ${event.home_team}`),node('p','game-time',`${date(event.tipoff_utc)} · Ciudad de México`));
    const meta=node('div','game-meta'); meta.append(node('span',`badge ${event.status==='evaluated'?'done':['validation_hold','result_unavailable'].includes(event.status)?'warn':''}`,statusNames[event.status]||'Pendiente'),link(event.official_url,'Partido en NBA.com ↗'));
    header.append(title,meta); game.append(header); const grid=node('div','player-grid');
    for (const id of [...new Set(matches.map(r=>r.player_id))]) {
      const predictions=matches.filter(r=>r.player_id===id), first=predictions[0], card=node('div','player-card'), head=node('div','player-head'), names=node('div');
      names.append(node('p','player-name',first.player),node('p','player-sub','Partido completo · Prórroga incluida'));
      head.append(node('span','avatar',first.player.split(' ').filter(Boolean).map(w=>w[0]).slice(0,2).join('')),names); card.append(head);
      for (const r of predictions.sort((a,b)=>MARKET_ORDER.indexOf(a.market)-MARKET_ORDER.indexOf(b.market))) {
        const forecast=node('div','forecast-row'), estimate=node('div'), display=node('div','estimate',number(r.estimate));
        display.append(node('small','',`Rango ${r.range_low}–${r.range_high}`)); estimate.append(node('span','market-name',r.market_label),display);
        const probabilities=node('div'), above=r.probability_over>=r.probability_under, probability=above?r.probability_over:r.probability_under;
        probabilities.append(node('p','probability',`${number(probability*100)}% ${above?'más':'menos'} de ${number(r.line)}`),node('div','line-reference',`Línea de referencia ${number(r.line)}`));
        const result=node('div','result-line');
        if (r.result.status==='evaluated') result.append(node('span','actual',`Resultado oficial: ${r.result.actual}`),node('span','',r.result.actual>r.line?'Por encima de la línea':r.result.actual<r.line?'Por debajo de la línea':'Igual a la línea'));
        else result.append(node('span','',statusNames[r.result.status]||'Pendiente'),node('span','',r.result.status==='dnp'?'Separado de la evaluación':'Sin resultado imputado'));
        forecast.append(estimate,probabilities,result);card.append(forecast);
      }
      const details=node('details','details'); details.append(node('summary','','Registro y cuotas de referencia'));
      for (const r of predictions) {
        details.append(node('p','',`${r.market_label}: registrada ${date(r.sealed_at_utc)}. ${r.recorded_book}: más ${number(r.recorded_over_decimal,2)} / menos ${number(r.recorded_under_decimal,2)}. Cuotas recibidas ${date(r.quote_received_at_utc)}.`));
        if(r.paper_selection) details.append(node('p','',`Selección histórica en simulación: ${r.paper_side==='over'?'más':'menos'} de ${number(r.line)}. Sin apuesta real.`));
      }
      card.append(details);grid.append(card);
    }
    game.append(grid);$('games').append(game);
  }
  $('services').replaceChildren();
  const services=[['Captura deportiva',data.health.capture.state,['capturing']],['Piloto',pilot,['waiting','completed']],['Alertas operativas',data.health.alerts.state,['monitoring']]];
  for(const [name,state,ok] of services) { const good=ok.includes(state); $('services').append(node('span',`service ${good?'':'warn'}`,`${name}: ${good?'activa':state==='stale'?'sin actualización reciente':'revisar'}`)); }
}
async function load() {
  if(loading)return; loading=true;$('refresh').disabled=true;
  try {
    const response=await fetch('/nba/api/data',{cache:'no-store'}); if(!response.ok) throw new Error('unavailable');
    const next=await response.json(); if(!Array.isArray(next.predictions)||!Array.isArray(next.events))throw new Error('invalid');
    data=next; const selection=$('event-filter').value;
    $('event-filter').replaceChildren(new Option('Todos los partidos','all'),...data.events.map(e=>new Option(`${e.away_team} · ${e.home_team}`,e.event_id)));
    $('event-filter').value=data.events.some(e=>e.event_id===selection)?selection:'all';render();
  } catch {
    $('message').hidden=false;$('message').textContent='No se pudieron comprobar los datos. Intenta actualizar de nuevo.';
    $('live-state').textContent='Datos sin actualización verificada';$('live-dot').classList.add('warn');
    // A stale previous response must not keep looking like current information.
    data=null;$('games').replaceChildren();$('services').replaceChildren();$('models').replaceChildren();$('live-v13').replaceChildren();$('live-section').hidden=true;$('comparison-rows').replaceChildren();$('models-count').textContent='Nuevos modelos sin actualización verificada';
    for(const id of ['total-predictions','total-events','total-evaluated'])$(id).textContent='—';
    $('next-game').textContent='Datos no disponibles';$('total-players').textContent='— jugadores';$('result-caption').textContent='Sin resultados verificados en esta actualización';
    $('updated').textContent='Sin conexión a los datos verificados';$('visible-count').textContent='Datos temporalmente no disponibles';
  } finally { loading=false;$('refresh').disabled=false; }
}
document.querySelectorAll('[data-market]').forEach(button=>button.addEventListener('click',()=>{
  market=button.dataset.market;document.querySelectorAll('[data-market]').forEach(b=>{const chosen=b===button;b.classList.toggle('selected',chosen);b.setAttribute('aria-pressed',String(chosen));});render();
}));
$('search').addEventListener('input',render);$('event-filter').addEventListener('change',render);$('status-filter').addEventListener('change',render);$('refresh').addEventListener('click',load);
document.querySelectorAll('[data-model]').forEach(button=>button.addEventListener('click',()=>{
  modelMarket=button.dataset.model;document.querySelectorAll('[data-model]').forEach(b=>{const chosen=b===button;b.classList.toggle('selected',chosen);b.setAttribute('aria-pressed',String(chosen));});renderModels();
}));
load();setInterval(()=>{if(document.visibilityState==='visible')load();},60000);
