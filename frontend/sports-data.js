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
// Un partido sin pronóstico igualmente figura en la cartelera, con la hora prevista de sellado.
// Nada se calcula en el navegador: las estadísticas de equipos las publica el servidor por partido (`loadNbaStats`) y se piden al abrirlo.
// La API trae también la pretemporada (13-16 oct): la web solo muestra desde el estreno de la temporada regular.
// Días de cartelera: los 7 que navega la ventana (-3…+3 en hora local) más uno de margen a cada lado, porque la cartelera es por fecha del Este.
const NBA_SEASON_START = '2026-10-20', NBA_BACK_DAYS = 4, NBA_AHEAD_DAYS = 4;
const isoDay = (base, offset) => new Date(Date.UTC(base.getFullYear(), base.getMonth(), base.getDate() + offset)).toISOString().slice(0, 10);

export function nbaGames(partidos) {
  const games = new Map();
  for (const p of Array.isArray(partidos) ? partidos : []) {
    if (!Number.isInteger(p?.id) || !p.local?.nombre || !p.visitante?.nombre || !stamp(p.inicio_utc)) continue;
    const final = p.resultado && Number.isFinite(p.resultado.local) && Number.isFinite(p.resultado.visitante) ? p.resultado : null;
    games.set(p.id, { id: p.id, fecha: p.fecha, home: p.local.nombre, away: p.visitante.nombre,
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

export function nbaV2Events(partidos, now = new Date()) {
  const games = nbaGames(partidos);
  return games.map(g => ({ id: g.id, sport: 'nba', home: g.home, away: g.away, start: g.start, league: 'NBA',
    status: g.final ? 'finished' : Date.parse(g.start) + 4 * 36e5 < now.getTime() ? 'awaiting_result' : 'scheduled',
    markets: nbaPickMarkets(g), sealed_at: g.pick?.sellado_en || null, seal: g.pick?.hash || null, planned_seal: g.planned,
    actionable: false, score: g.final ? `${g.final.local} – ${g.final.visitante}` : null, availability: null, official_url: null,
    team_projection: Array.isArray(g.pick?.mu) && g.pick.mu.length === 2 && g.pick.mu.every(Number.isFinite) ? g.pick.mu : null,
    v2: true }));
}

const NBA_LABELS = { winner: 'Ganador del partido', handicap: 'Hándicap', game_total: 'Total del partido', team_points: 'Puntos del equipo',
  player_points: 'Puntos del jugador', player_rebounds: 'Rebotes del jugador', player_assists: 'Asistencias del jugador', player_threes: 'Triples del jugador' };
const NBA_UNITS = { game_total: 'puntos', team_points: 'puntos', player_points: 'puntos', player_rebounds: 'rebotes', player_assists: 'asistencias', player_threes: 'triples' };
const BOOK_NAMES = { bovada: 'Bovada', pinnacle: 'Pinnacle', fanduel: 'FanDuel', draftkings: 'DraftKings', betmgm: 'BetMGM', caesars: 'Caesars', bet365: 'bet365' };

export function marketQuote(m) {
  const house = typeof m?.price === 'number' && Number.isFinite(m.price) && m.price > 1 && typeof m.book === 'string' && m.book.trim();
  return house ? { price: m.price, source: BOOK_NAMES[m.book] || m.book, model: false }
    : { price: m?.probability > 0 ? 1 / m.probability : null, source: 'Del modelo', model: true };
}

// Destacado de NBA y tenis: lo elige el SERVIDOR (valor esperado; `destacado` del evento, ver `destacado_valor.py`). Aquí solo se localiza
// ese mercado entre los publicados; si es una revisión posterior al inicio no cuenta como pronóstico previo y no se sustituye por otro.
// Solo si el servidor no mandó el campo (fuente antigua o mercados aún sin cargar) se aplica la misma regla a lo que hay en pantalla.
export function featuredSportMarket(event) {
  const markets = event.markets.filter(m => !m.revised);
  if (event.destacado !== undefined) {
    const id = typeof event.destacado === 'string' ? event.destacado : event.destacado?.id;
    return id == null ? null : markets.find(m => m.id === id) || null;
  }
  const quoted = event.sport === 'nba' && event.v2 ? markets.filter(m => !marketQuote(m).model) : [];
  return quoted.length ? bestByValue(quoted, m => m.probability, m => m.price) : featuredModelMarket(markets);
}

export async function loadNbaMarkets(event, fetcher = fetch) {
  const controller = new AbortController(), timer = setTimeout(() => controller.abort(), 15000);
  try {
    const response = await fetcher(`/nba/v1/partido/${encodeURIComponent(event.id)}/mercados`, { signal: controller.signal, cache: 'no-store' });
    if (!response.ok) throw new Error('Sin mercados');
    const data = await response.json();
    if (data?.partido_id !== event.id || !Array.isArray(data.markets) || !Array.isArray(data.projections)) throw new Error('Formato inesperado');
    const valid = m => m && NBA_LABELS[m.market] && typeof m.id === 'string' && stamp(m.sealed_at) && typeof m.seal === 'string'
      && typeof m.probability === 'number' && Number.isFinite(m.probability) && m.probability >= 0 && m.probability <= 1
      && (m.market === 'winner' ? typeof m.team === 'string' && ['local', 'visit'].includes(m.side)
        : typeof m.line === 'number' && Number.isFinite(m.line) && (m.market === 'handicap' ? ['local', 'visit'] : ['over', 'under']).includes(m.side))
      && (!m.market.startsWith('player_') || (Number.isInteger(m.player_id) && typeof m.player === 'string'));
    if (!data.markets.every(valid) || !data.projections.every(p => p && ['puntos', 'rebotes', 'asistencias', 'triples'].includes(p.market)
      && Number.isInteger(p.player_id) && typeof p.player === 'string' && stamp(p.sealed_at)
      && ['estimate', 'p10', 'p50', 'p90', 'p_juega'].every(k => typeof p[k] === 'number' && Number.isFinite(p[k])))) throw new Error('Formato inesperado');
    const scores = typeof event.score === 'string' ? event.score.split(' – ').map(Number) : [];
    const markets = data.markets.map(m => {
      const eligible = Date.parse(m.sealed_at) < Date.parse(event.start);
      const label = m.player ? `${NBA_LABELS[m.market].replace(' del jugador', '')} de ${m.player}`
        : m.market === 'team_points' ? `Puntos de ${m.team}` : NBA_LABELS[m.market];
      const selection = m.market === 'winner' ? m.team : m.market === 'handicap' ? `${m.team} ${m.line > 0 ? '+' : ''}${m.line}`
        : `${m.side === 'over' ? 'Más de' : 'Menos de'} ${m.line} ${NBA_UNITS[m.market]}`;
      let actual = null;
      if (eligible && event.status === 'finished' && scores.length === 2 && scores.every(Number.isFinite)) {
        if (m.market === 'winner' || m.market === 'handicap') actual = m.team === event.home ? scores[0] - scores[1] : scores[1] - scores[0];
        else if (m.market === 'game_total') actual = scores[0] + scores[1];
        else if (m.market === 'team_points') actual = m.team === event.home ? scores[0] : scores[1];
      }
      const value = actual == null ? null : m.market === 'handicap' ? actual + m.line : actual;
      const threshold = ['winner', 'handicap'].includes(m.market) ? 0 : m.line;
      const computed = value == null ? null : value === threshold ? 'push'
        : ((m.side === 'under' ? value < threshold : value > threshold) ? 'win' : 'loss');
      const outcome = !eligible ? null : ['win', 'loss', 'push', 'void'].includes(m.outcome) ? m.outcome : computed;
      const quote = marketQuote(m);
      return { ...m, label, selection, eligible, revised: !eligible, outcome, reference: quote.model ? 'Probabilidad estadística' : quote.source };
    });
    // `destacado` lo calcula el servidor; se conserva solo su id (null = ningún mercado cumple la regla; undefined = el servidor no lo mandó).
    const destacado = data.destacado === undefined ? undefined : typeof data.destacado?.id === 'string' ? data.destacado.id : null;
    return { status: 'ready', markets, projections: data.projections, destacado };
  } catch { return { status: 'error', markets: [], projections: [] }; }
  finally { clearTimeout(timer); }
}

export function withNbaMarkets(event, entry) {
  if (event.sport !== 'nba' || !event.v2 || !entry) return event;
  return { ...event, markets_status: entry.status, markets: entry.status === 'ready' ? entry.markets : [],
    projections: entry.status === 'ready' ? entry.projections : [],
    ...(entry.status === 'ready' && entry.destacado !== undefined ? { destacado: entry.destacado } : {}) };
}

async function loadNba(fetcher, now) {
  const days = Array.from({ length: NBA_BACK_DAYS + NBA_AHEAD_DAYS + 1 }, (_, i) => isoDay(now, i - NBA_BACK_DAYS)).filter(day => day >= NBA_SEASON_START);
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

// Estadísticas de equipos de un partido de NBA (récord, forma, cara a cara, clasificación y temporada pasada): las calcula el servidor
// con los marcadores finales de la temporada regular anteriores al día del partido (API v2, /nba/v1/partido/{id}/estadisticas).
const isForm = f => f && ['all', 'home', 'away'].every(k => Array.isArray(f[k]));
export async function loadNbaStats(eventId, fetcher = fetch) {
  const controller = new AbortController(), timer = setTimeout(() => controller.abort(), 15000);
  try {
    const response = await fetcher(`/nba/v1/partido/${encodeURIComponent(eventId)}/estadisticas`, { signal: controller.signal, cache: 'no-store' });
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

// Regla del destacado por valor esperado (titular, 5-nov-2026; la misma del servidor, `destacado_valor.py`): cuota de referencia >= 1,20 y
// probabilidad >= 55 %; gana la mayor probabilidad × cuota y, en empate, la mayor probabilidad. Sin candidatos: null.
export const FEATURED_MIN_PRICE = 1.2, FEATURED_MIN_PROB = .55;
const isNum = v => typeof v === 'number' && Number.isFinite(v);
export function bestByValue(items, probOf, priceOf) {
  let best = null, bestScore = 0, bestProb = 0;
  for (const item of Array.isArray(items) ? items : []) {
    if (!item) continue;
    const p = probOf(item), c = priceOf(item);
    if (!isNum(p) || !isNum(c) || c < FEATURED_MIN_PRICE || p < FEATURED_MIN_PROB) continue;
    const score = Math.round(p * c * 1e9) / 1e9;     // sin el redondeo, el ruido de coma flotante decidiría los empates
    if (!best || score > bestScore || (score === bestScore && p > bestProb)) { best = item; bestScore = score; bestProb = p; }
  }
  return best;
}

// Sin cuota de casa la de referencia es la del modelo (1 ÷ probabilidad): ninguna casa publica estas cuotas y no se inventa otra.
export function featuredModelMarket(markets) {
  return bestByValue(markets, m => m.probability, m => probability(m.probability) ? 1 / m.probability : NaN);
}
