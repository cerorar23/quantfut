// Adaptadores de publicaciones existentes. No calcula ni completa pronósticos.
const probability = p => typeof p === 'number' && Number.isFinite(p) && p > 0 && p < 1;
const stamp = s => typeof s === 'string' && Number.isFinite(Date.parse(s));

export function nbaEvents(data) {
  if (!Array.isArray(data?.live_v13?.cohorts)) throw new TypeError('Fuente NBA no disponible');
  const events = new Map();
  const cohorts = [...data.live_v13.cohorts].sort((a,b)=>String(a.recalculated_at_utc || a.created_at_utc).localeCompare(String(b.recalculated_at_utc || b.created_at_utc)));
  for (const cohort of cohorts) {
    for (const game of cohort.events || []) {
      if (game.status === 'validation_hold' || !stamp(game.tipoff_utc) || !game.home_team || !game.away_team) continue;
      const rows = (cohort.predictions || []).filter(row=>row.event_id===game.event_id && row.result?.status!=='validation_hold' && probability(row.probability_over) && stamp(row.sealed_at_utc));
      const markets = rows.map((row,index)=>{
        const winner = row.market === 'winner';
        const selection = winner ? (row.probability_over >= .5 ? game.home_team : game.away_team)
          : `${row.market === 'game_total' ? 'Total' : row.player} · Más de ${row.line}`;
        // Un recálculo posterior al salto no se presenta como pronóstico previo ni se cuenta en resultados.
        const eligible = row.performance_eligible !== false && Date.parse(row.sealed_at_utc) < Date.parse(game.tipoff_utc);
        const result = eligible && row.result?.status === 'evaluated' && typeof row.result.actual === 'number'
          ? winner ? ((row.result.actual === 1) === (row.probability_over >= .5) ? 'win':'loss')
            : row.result.actual === row.line ? 'push' : row.result.actual > row.line ? 'win':'loss' : null;
        return {id:`${row.market}-${row.player_id}-${index}`, label:row.market_label, selection,
          probability:winner && row.probability_over<.5 ? 1-row.probability_over:row.probability_over,
          price:null, reference:row.reference || 'Probabilidad estadística', estimate:row.estimate,
          sealed_at:row.sealed_at_utc, eligible, revised:!eligible, outcome:result,
          conditional:row.conditional_participation===true, market:row.market,
          player:row.market.startsWith('player_')?row.player:null,
          player_id:row.market.startsWith('player_')?row.player_id:null,
          line:typeof row.line==='number'?row.line:null};
      });
      if (!markets.length) continue;
      events.set(game.event_id,{id:game.event_id,sport:'nba',home:game.home_team,away:game.away_team,start:game.tipoff_utc,league:'NBA',
        status:game.status==='evaluated'?'finished':game.status==='awaiting_result'?'awaiting_result':'scheduled',
        markets,sealed_at:cohort.created_at_utc,seal:cohort.cohort,actionable:false,
        score:game.final?`${game.final.home} – ${game.final.away}`:null,
        availability:game.availability||null, official_url:typeof game.official_url==='string'&&game.official_url.startsWith('https://')?game.official_url:null});
    }
  }
  return [...events.values()].sort((a,b)=>Date.parse(a.start)-Date.parse(b.start));
}

export function tennisEvents(data) {
  if (!['ok','partial'].includes(data?.state) || !Array.isArray(data.events)) throw new TypeError('Fuente tenis no disponible');
  return data.events.filter(event=>event.sport==='tenis' && event.id && event.home && event.away && stamp(event.start) && event.seal && Array.isArray(event.markets))
    .map(event=>({...event,markets:event.markets.filter(m=>probability(m.probability))})).filter(event=>event.markets.length);
}

export async function loadSport(sport, fetcher=fetch) {
  const controller=new AbortController(), timer=setTimeout(()=>controller.abort(),15000);
  try {
    const path=sport==='nba'?'/nba/api/data':'/web/deportes/tenis';
    const response=await fetcher(path,{signal:controller.signal,cache:'no-store'});
    if(!response.ok)throw new Error('Fuente no disponible');
    const data=await response.json();
    return {status:'ready',events:sport==='nba'?nbaEvents(data):tennisEvents(data)};
  } catch {return {status:'error',events:[]};}
  finally {clearTimeout(timer);}
}

// Estadísticas de jugadores de un partido de tenis (las resume el servidor a partir de API-Tennis).
const finiteNumber = v => v == null || (typeof v === 'number' && Number.isFinite(v));
export async function loadTennisStats(eventId, fetcher = fetch) {
  const controller = new AbortController(), timer = setTimeout(() => controller.abort(), 15000);
  try {
    const response = await fetcher(`/web/deportes/tenis/estadisticas/${encodeURIComponent(eventId)}`, { signal: controller.signal, cache: 'no-store' });
    if (!response.ok) throw new Error('Sin estadísticas');
    const data = await response.json();
    const valid = Array.isArray(data?.players) && data.players.length === 2
      && data.players.every(p => p && typeof p === 'object' && p.surfaces && Array.isArray(p.ranking_history) && finiteNumber(p.rank))
      && data.h2h && Array.isArray(data.h2h.matches);
    if (!valid) throw new Error('Formato inesperado');
    return { status: 'ready', data };
  } catch { return { status: 'error', data: null }; } finally { clearTimeout(timer); }
}

// Estadísticas de equipos de un partido de NBA (forma, cara a cara y clasificación; el servidor resume marcadores finales).
const isForm = f => f && ['all', 'home', 'away'].every(k => Array.isArray(f[k]));
export async function loadNbaStats(eventId, fetcher = fetch) {
  const controller = new AbortController(), timer = setTimeout(() => controller.abort(), 15000);
  try {
    const response = await fetcher(`/web/deportes/nba/estadisticas/${encodeURIComponent(eventId)}`, { signal: controller.signal, cache: 'no-store' });
    if (!response.ok) throw new Error('Sin estadísticas');
    const data = await response.json();
    const valid = Array.isArray(data?.teams) && data.teams.length === 2
      && data.teams.every(t => t && typeof t.name === 'string' && t.season && t.last6 && t.scoring && t.standing && isForm(t.form))
      && data.h2h && Array.isArray(data.h2h.matches);
    if (!valid) throw new Error('Formato inesperado');
    return { status: 'ready', data };
  } catch { return { status: 'error', data: null }; } finally { clearTimeout(timer); }
}

export async function loadResults(fetcher=fetch) {
  const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),15000);
  try {
    const response=await fetcher('/mobile/v1/markets/history?limit=500',{signal:controller.signal,cache:'no-store'});
    if(!response.ok)throw new Error();
    const data=await response.json();if(!Array.isArray(data.items))throw new Error();
    return {status:'ready',items:data.items.filter(r=>['win','loss'].includes(r.outcome)&&r.local&&r.visitante&&stamp(r.kickoff_utc))};
  } catch {return {status:'error',items:[]};}
  finally {clearTimeout(timer);}
}

// El historial de la web empieza el 26 de octubre (día local): de ahí hacia atrás no se muestra nada.
export const HISTORY_SINCE='2026-10-26';

// Destacado de fútbol de cada partido terminado (lo calcula el servidor: recorre cada partido).
export async function loadFootballFeatured(fetcher=fetch) {
  const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),30000);
  try {
    const response=await fetcher(`/mobile/v1/markets/destacados?desde=${HISTORY_SINCE}`,{signal:controller.signal,cache:'no-store'});
    if(!response.ok)throw new Error();
    const data=await response.json();if(!Array.isArray(data.items))throw new Error();
    return {status:'ready',items:data.items.filter(r=>['win','loss'].includes(r.outcome)&&r.local&&r.visitante&&stamp(r.kickoff_utc))};
  } catch {return {status:'error',items:[]};}
  finally {clearTimeout(timer);}
}

// Código de tres letras del manifiesto de logos a partir del nombre que publican las cuotas («Los Angeles Lakers» → LAL).
const NBA_CODES=[['hawks','ATL'],['celtics','BOS'],['nets','BKN'],['hornets','CHA'],['bulls','CHI'],['cavaliers','CLE'],['mavericks','DAL'],['nuggets','DEN'],['pistons','DET'],['warriors','GSW'],['rockets','HOU'],['pacers','IND'],['clippers','LAC'],['lakers','LAL'],['grizzlies','MEM'],['heat','MIA'],['bucks','MIL'],['timberwolves','MIN'],['pelicans','NOP'],['knicks','NYK'],['thunder','OKC'],['magic','ORL'],['76ers','PHI'],['suns','PHX'],['blazers','POR'],['kings','SAC'],['spurs','SAS'],['raptors','TOR'],['jazz','UTA'],['wizards','WAS']];
export function nbaCode(name) {
  const n=String(name||'').normalize('NFD').replace(/[̀-ͯ]/g,'').toLowerCase();
  const hit=NBA_CODES.find(([k])=>n.includes(k));
  return hit?hit[1]:null;
}

// Logos NBA y fotos de tenis alojados en el servidor (scripts/imagenes). Si el manifiesto falla, las tarjetas usan iniciales.
export async function loadImages(fetcher=fetch) {
  const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),15000);
  try {
    const response=await fetcher('/web/imagenes/manifiesto.json',{signal:controller.signal,cache:'no-store'});
    if(!response.ok)throw new Error();
    const data=await response.json();
    const dictionary=value=>value!==null&&typeof value==='object'&&!Array.isArray(value);
    if(!data||!dictionary(data.nba)||!dictionary(data.tenis))throw new Error();
    return {status:'ready',nba:data.nba,tenis:data.tenis};
  } catch {return {status:'error',nba:{},tenis:{}};}
  finally {clearTimeout(timer);}
}

// Destacado de NBA y tenis: de los mercados publicados, el de mayor probabilidad con «cuota del modelo»
// (1 ÷ probabilidad) de 1,40 en adelante, sin tope (titular, 2-nov-2026). Ninguna casa publica estas cuotas; no se inventa ninguna.
export function featuredModelMarket(markets, range = [1.4, Infinity]) {
  return (Array.isArray(markets) ? markets : []).reduce((best, m) => {
    if (!m || !probability(m.probability)) return best;
    const odds = 1 / m.probability;
    return odds >= range[0] && odds <= range[1] && (!best || m.probability > best.probability) ? m : best;
  }, null);
}
