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

// ---- NBA (API v2 de lectura, /nba/v1/cartelera): calendario, marcadores finales y pronósticos sellados.
// Un partido sin pronóstico igualmente figura en la cartelera, con la hora prevista de sellado y sus estadísticas.
// Nada se calcula como pronóstico en el navegador: solo se resumen marcadores finales ya registrados.
// La API trae también la pretemporada (13-16 oct): los récords y la forma solo cuentan desde el estreno de la temporada regular.
const NBA_SEASON_START = '2026-10-20', NBA_HISTORY_DAYS = 21, NBA_AHEAD_DAYS = 4;
const NBA_EAST = new Set(['ATL', 'BKN', 'BOS', 'CHA', 'CHI', 'CLE', 'DET', 'IND', 'MIA', 'MIL', 'NYK', 'ORL', 'PHI', 'TOR', 'WAS']);
const isoDay = (base, offset) => new Date(Date.UTC(base.getFullYear(), base.getMonth(), base.getDate() + offset)).toISOString().slice(0, 10);

export function nbaGames(partidos) {
  const games = new Map();
  for (const p of Array.isArray(partidos) ? partidos : []) {
    if (!Number.isInteger(p?.id) || !p.local?.nombre || !p.visitante?.nombre || !p.local.codigo || !p.visitante.codigo || !stamp(p.inicio_utc)) continue;
    const final = p.resultado && Number.isFinite(p.resultado.local) && Number.isFinite(p.resultado.visitante) ? p.resultado : null;
    games.set(p.id, { id: p.id, fecha: p.fecha, home: p.local.nombre, homeCode: p.local.codigo, away: p.visitante.nombre, awayCode: p.visitante.codigo,
      start: p.inicio_utc, planned: stamp(p.sello_previsto) ? p.sello_previsto : null, final, pick: p.pronostico || null });
  }
  return [...games.values()].sort((a, b) => Date.parse(a.start) - Date.parse(b.start));
}

function nbaPickMarkets(g) {
  const p = g.pick;
  if (!p || !probability(p.p_local) || !stamp(p.sellado_en)) return [];
  const homePick = p.p_local >= .5;
  // Un sello posterior al inicio es una revisión: ni se presenta como pronóstico previo ni cuenta como acierto.
  const eligible = Date.parse(p.sellado_en) < Date.parse(g.start);
  const outcome = eligible && g.final ? ((g.final.local > g.final.visitante) === homePick ? 'win' : 'loss') : null;
  return [{ id: `winner-${g.id}`, label: 'Ganador del partido', market: 'winner', selection: homePick ? g.home : g.away,
    probability: homePick ? p.p_local : 1 - p.p_local, price: null, reference: 'Probabilidad estadística', estimate: null,
    sealed_at: p.sellado_en, eligible, revised: !eligible, outcome, conditional: false, player: null, player_id: null, line: null }];
}

const round = (value, digits) => Math.round(value * 10 ** digits) / 10 ** digits;
const record = rows => ({ won: rows.filter(r => r.won).length, lost: rows.filter(r => !r.won).length, rate: rows.length ? round(rows.filter(r => r.won).length / rows.length, 4) : null });
const average = (rows, key) => (rows.length ? round(rows.reduce((sum, r) => sum + r[key], 0) / rows.length, 1) : null);

// Partidos terminados de un equipo antes de `before`, del más reciente al más antiguo, vistos desde ese equipo.
function nbaRows(finished, code, before) {
  return finished.filter(g => Date.parse(g.start) < before && (g.homeCode === code || g.awayCode === code))
    .sort((a, b) => Date.parse(b.start) - Date.parse(a.start))
    .map(g => { const home = g.homeCode === code, points = home ? g.final.local : g.final.visitante, against = home ? g.final.visitante : g.final.local;
      return { date: g.fecha, opponent: home ? g.away : g.home, home, points, opponent_points: against, won: points > against }; });
}

function nbaStanding(finished, code, before) {
  const conference = NBA_EAST.has(code) ? 'este' : 'oeste';
  const table = [...new Set(finished.flatMap(g => [g.homeCode, g.awayCode]))].filter(c => NBA_EAST.has(c) === (conference === 'este')).map(c => {
    const rows = nbaRows(finished, c, before);
    return { code: c, rate: rows.length ? record(rows).rate : 0, diff: rows.length ? average(rows, 'points') - average(rows, 'opponent_points') : 0 };
  }).sort((a, b) => b.rate - a.rate || b.diff - a.diff);
  const index = table.findIndex(t => t.code === code);
  return { rank: index < 0 ? null : index + 1, of: table.length, conference };
}

function nbaTeamStats(finished, name, code, game) {
  const before = Date.parse(game.start), rows = nbaRows(finished, code, before), last6 = rows.slice(0, 6);
  let streak = 0;
  for (const row of rows) { if (streak === 0 || row.won === (streak > 0)) streak += row.won ? 1 : -1; else break; }
  const rest = rows.length ? Math.round((Date.parse(game.fecha) - Date.parse(rows[0].date)) / 864e5) - 1 : null;
  return { name, conference: NBA_EAST.has(code) ? 'este' : 'oeste', season: record(rows), home: record(rows.filter(r => r.home)), away: record(rows.filter(r => !r.home)),
    scoring: { games: rows.length, points_for: average(rows, 'points'), points_against: average(rows, 'opponent_points') },
    last6: { ...record(last6), games: last6.length, points_for: average(last6, 'points'), points_against: average(last6, 'opponent_points') },
    streak, rest_days: rest, back_to_back: rest === null ? null : rest === 0,
    last_season: { won: 0, lost: 0, rate: null, games: 0, points_for: null, points_against: null },
    form: { all: last6, home: rows.filter(r => r.home).slice(0, 6), away: rows.filter(r => !r.home).slice(0, 6) },
    standing: nbaStanding(finished, code, before) };
}

function nbaGameStats(finished, game) {
  const before = Date.parse(game.start);
  const matches = finished.filter(g => Date.parse(g.start) < before && new Set([g.homeCode, g.awayCode]).has(game.homeCode) && new Set([g.homeCode, g.awayCode]).has(game.awayCode))
    .sort((a, b) => Date.parse(b.start) - Date.parse(a.start))
    .map(g => ({ date: g.fecha, home: g.home, away: g.away, home_points: g.final.local, away_points: g.final.visitante }));
  const homeWins = matches.filter(m => (m.home === game.home ? m.home_points > m.away_points : m.away_points > m.home_points)).length;
  const since = finished.length ? finished.reduce((min, g) => (g.fecha < min ? g.fecha : min), finished[0].fecha) : null;
  return { teams: [nbaTeamStats(finished, game.home, game.homeCode, game), nbaTeamStats(finished, game.away, game.awayCode, game)],
    h2h: { matches, home_wins: homeWins, away_wins: matches.length - homeWins, average_total: matches.length ? round(matches.reduce((s, m) => s + m.home_points + m.away_points, 0) / matches.length, 1) : null },
    since, games_used: finished.length };
}

export function nbaV2Events(partidos, now = new Date()) {
  const games = nbaGames(partidos), finished = games.filter(g => g.final);
  return games.map(g => ({ id: g.id, sport: 'nba', home: g.home, away: g.away, start: g.start, league: 'NBA',
    status: g.final ? 'finished' : Date.parse(g.start) + 4 * 36e5 < now.getTime() ? 'awaiting_result' : 'scheduled',
    markets: nbaPickMarkets(g), sealed_at: g.pick?.sellado_en || null, seal: g.pick?.hash || null, planned_seal: g.planned,
    actionable: false, score: g.final ? `${g.final.local} – ${g.final.visitante}` : null, availability: null, official_url: null,
    v2: true, stats: nbaGameStats(finished, g) }));
}

async function loadNba(fetcher, now) {
  const back = Math.max(3, Math.min(NBA_HISTORY_DAYS, Math.floor((Date.parse(isoDay(now, 0)) - Date.parse(NBA_SEASON_START)) / 864e5)));
  const days = Array.from({ length: back + NBA_AHEAD_DAYS + 1 }, (_, i) => isoDay(now, i - back)).filter(day => day >= NBA_SEASON_START);
  const pull = async day => {
    const controller = new AbortController(), timer = setTimeout(() => controller.abort(), 15000);
    try {
      const response = await fetcher(`/nba/v1/cartelera?fecha=${day}`, { signal: controller.signal, cache: 'no-store' });
      if (!response.ok) throw new Error('Fuente no disponible');
      const data = await response.json();
      if (!Array.isArray(data?.partidos)) throw new TypeError('Fuente NBA no disponible');
      return data.partidos;
    } finally { clearTimeout(timer); }
  };
  const results = (await Promise.allSettled(days.map(pull))).filter(r => r.status === 'fulfilled');
  return results.length ? { status: 'ready', events: nbaV2Events(results.flatMap(r => r.value), now) } : { status: 'error', events: [] };
}

export async function loadSport(sport, fetcher=fetch, now=new Date()) {
  if (sport === 'nba') return loadNba(fetcher, now);
  const controller=new AbortController(), timer=setTimeout(()=>controller.abort(),15000);
  try {
    const response=await fetcher('/web/deportes/tenis',{signal:controller.signal,cache:'no-store'});
    if(!response.ok)throw new Error('Fuente no disponible');
    const data=await response.json();
    return {status:'ready',events:tennisEvents(data)};
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
