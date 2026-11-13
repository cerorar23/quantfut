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

// Orden de los mercados de un partido ya jugado (titular, 2026-11-05; fútbol, NBA y tenis): primero los acertados, de la cuota más alta
// a la más baja; después lo que no tiene resultado (devoluciones, anulados) y al final los fallados, también de mayor a menor cuota.
// Si el partido aún no tiene ningún mercado liquidado, la lista queda como vino (por probabilidad).
export const hayLiquidado = (lista, resultado) => lista.some(x => ['win', 'loss'].includes(resultado(x)));
export function ordenLiquidado(lista, { resultado, cuota, prob }) {
  if (!hayLiquidado(lista, resultado)) return lista;
  const rango = x => ({ win: 0, loss: 2 })[resultado(x)] ?? 1;
  const precio = x => { const c = cuota(x); return Number.isFinite(c) ? c : -Infinity; };
  return [...lista].sort((a, b) => rango(a) - rango(b) || precio(b) - precio(a) || (prob(b) || 0) - (prob(a) || 0));
}

// Destacado de NBA y tenis: lo elige el SERVIDOR (probabilidad máxima segura; `destacado` del evento, ver `destacado_valor.py`). Aquí solo se localiza
// ese mercado entre los publicados; si es una revisión posterior al inicio no cuenta como pronóstico previo y no se sustituye por otro.
// Solo si el servidor no mandó el campo (fuente antigua o mercados aún sin cargar) se aplica la misma regla a lo que hay en pantalla.
export function featuredSportMarket(event) {
  const markets = event.markets.filter(m => !m.revised);
  if (event.destacado !== undefined) {
    const id = typeof event.destacado === 'string' ? event.destacado : event.destacado?.id;
    return id == null ? null : markets.find(m => m.id === id) || null;
  }
  const quoted = event.sport === 'nba' && event.v2 ? markets.filter(m => !marketQuote(m).model) : [];
  return quoted.length ? bestBySafety(quoted, m => m.probability, m => m.price) : featuredModelMarket(markets);
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

// Cuota PropLine de tenis (`/web/deportes/tenis/cuotas`): la mejor casa que cotizaba el mercado cuando se selló el pronóstico. Es una referencia,
// NO va dentro del sello. El servidor la calcula aparte y en frío tarda (hasta ~100 s tras reiniciar la API; mientras, responde `unavailable`),
// así que la web pinta el tenis primero y la pide después (ver `ensureSport`).
export async function loadTennisQuotes(fetcher=fetch) {
  const controller=new AbortController(), timer=setTimeout(()=>controller.abort(),30000);
  try {
    const response=await fetcher('/web/deportes/tenis/cuotas',{signal:controller.signal,cache:'no-store'});
    if(!response.ok)throw new Error('Fuente no disponible');
    const data=await response.json();
    if(!['ok','partial'].includes(data?.state)||!data.events||typeof data.events!=='object'||Array.isArray(data.events))return {status:'unavailable',events:{}};
    return {status:'ready',events:data.events};
  } catch {return {status:'error',events:{}};}
  finally {clearTimeout(timer);}
}

const bookLabel = key => BOOK_NAMES[key] || String(key).replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());

// Pone precio y casa de referencia en los mercados de tenis que la tengan. Muta los eventos recibidos (son los de la caché de la web).
// Nunca pisa un precio que ya trajera el feed ni inventa uno: sin precio válido y casa con nombre, el mercado se queda como estaba.
export function applyTennisQuotes(events, quotes) {
  for (const event of Array.isArray(events) ? events : []) {
    const byMarket = quotes?.[event?.id];
    if (!byMarket || typeof byMarket !== 'object') continue;
    for (const m of event.markets || []) {
      const q = byMarket[m.id];
      if (!q || m.price != null || !(typeof q.price === 'number' && Number.isFinite(q.price) && q.price > 1) || typeof q.book !== 'string' || !q.book.trim()) continue;
      const book = bookLabel(q.book.trim());
      Object.assign(m, { price: q.price, book, price_book: book, quote_as_of: q.as_of || null, reference: `${book} · referencia previa al sello` });
    }
  }
  return events;
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

// Regla del destacado «probabilidad máxima segura» (titular, 5-nov-2026; la misma del servidor, `destacado_valor.py`): cuota de referencia
// >= 1,20 y probabilidad >= 75 %; gana la MAYOR PROBABILIDAD (la cuota no multiplica nada) y, en empate, la mayor cuota. Sin candidatos: null.
export const FEATURED_MIN_PRICE = 1.2, FEATURED_MIN_PROB = .75;
const isNum = v => typeof v === 'number' && Number.isFinite(v);
export function bestBySafety(items, probOf, priceOf) {
  let best = null, bestProb = 0, bestPrice = 0;
  for (const item of Array.isArray(items) ? items : []) {
    if (!item) continue;
    const p = probOf(item), c = priceOf(item);
    if (!isNum(p) || !isNum(c) || c < FEATURED_MIN_PRICE || p < FEATURED_MIN_PROB) continue;
    if (!best || p > bestProb || (p === bestProb && c > bestPrice)) { best = item; bestProb = p; bestPrice = c; }
  }
  return best;
}

// Sin cuota de casa la de referencia es la del modelo (1 ÷ probabilidad): ninguna casa publica estas cuotas y no se inventa otra.
export function featuredModelMarket(markets) {
  return bestBySafety(markets, m => m.probability, m => probability(m.probability) ? 1 / m.probability : NaN);
}

// ---- NBA y tenis de la web por el contrato común `GET /deportes/v1/{deporte}/cartelera` (Fase 3 de «Web y App»).
// Convierte `Evento`/`Mercado` del contrato al objeto que la web ya pinta (el que construyen `nbaV2Events` y `tennisEvents`), sin cambiar ninguna vista.
//
// REGLA DE IGUALDAD (titular, 12-nov-2026): la web no puede mostrar nada distinto de lo de hoy. Por eso cada deporte tiene un interruptor propio
// (`CONTRATO_WEB`) y SOLO se enciende cuando el contrato trae todo lo que la web usa de ese deporte. NBA (cartelera) está encendido desde que el contrato
// trae `team_projection`, el ganador también en revisión (`principal`) y el `destacado` con la regla de la web; tenis sigue apagado (le faltan mercados
// en la cartelera y `no_result`; lista en `harness/tareas.md`, «Web lee el contrato»). Con el interruptor apagado `loadSportWeb` es exactamente
// `loadSport`: ni una petición más. Encendido, cualquier fallo del contrato (red, estado distinto de 200/304 o respuesta ilegible) cae al cargador
// actual con un aviso. El detalle de NBA (`loadNbaMarkets`) sigue en `/nba/v1/partido/{id}/mercados`.
export const CONTRATO_WEB = { nba: true, tenis: false };

const BACK_DAYS = 3, AHEAD_DAYS = 3;     // los 7 días que navega la ventana (-3…+3 en hora local)

const day = d => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
const utcDay = iso => Date.UTC(+iso.slice(0, 4), +iso.slice(5, 7) - 1, +iso.slice(8, 10));

// Ventana de la petición: primer día visible (hora local), nº de días y desfase local con el signo del contrato (UTC+1 = 60; `getTimezoneOffset` lo da al revés).
export function ventanaContrato(sport, now = new Date()) {
  const at = offset => new Date(now.getFullYear(), now.getMonth(), now.getDate() + offset);
  let desde = day(at(-BACK_DAYS));
  if (sport === 'nba' && desde < NBA_SEASON_START) desde = NBA_SEASON_START;
  const ultimo = day(at(AHEAD_DAYS));
  const dias = Math.max(1, Math.min(7, Math.round((utcDay(ultimo) - utcDay(desde)) / 864e5) + 1));
  return { desde, dias, tz: -now.getTimezoneOffset() || 0 };
}

// Deportes con pantalla propia en la web (el fútbol tiene la suya y no usa este contrato). Todo lo demás del catálogo se pinta con la pantalla genérica.
export const DEPORTES_PROPIOS = ['futbol', 'nba', 'tenis'];
export const esDeporteGenerico = sport => typeof sport === 'string' && /^[a-z][a-z0-9_]{1,23}$/.test(sport) && !DEPORTES_PROPIOS.includes(sport);

export function mercadoDesdeContrato(m, generico = false) {
  if (!m || typeof m.id !== 'string' || typeof m.label !== 'string' || typeof m.selection !== 'string' || !probability(m.probability)
    || typeof m.eligible !== 'boolean') throw new TypeError('Mercado del contrato inválido');
  return { id: m.id, label: m.label, selection: m.selection, probability: m.probability, price: typeof m.price === 'number' ? m.price : null,
    reference: m.reference ?? null, estimate: null, sealed_at: m.sealed_at ?? null, eligible: m.eligible, revised: !m.eligible,
    outcome: m.outcome ?? null, conditional: false, market: m.market, player: m.player ?? null, player_id: m.player_id ?? null,
    line: typeof m.line === 'number' ? m.line : null, ...(typeof m.push_probability === 'number' ? { push_probability: m.push_probability } : {}),
    // En un deporte nuevo la cuota viene con su origen en `reference` (el contrato no trae `book`): sin origen no hay cuota de casa y se muestra la del modelo.
    ...(generico ? { family: typeof m.family === 'string' ? m.family : 'otros', principal: m.principal === true,
      ...(typeof m.price === 'number' && m.price > 1 && typeof m.reference === 'string' && m.reference.trim() ? { book: m.reference.trim() } : {}) } : {}) };
}

export function eventoDesdeContrato(ev, sport) {
  if (!ev || typeof ev.id !== 'string' || typeof ev.home !== 'string' || typeof ev.away !== 'string' || !stamp(ev.start)
    || !Array.isArray(ev.markets)) throw new TypeError('Evento del contrato inválido');
  if (esDeporteGenerico(sport)) return eventoGenerico(ev, sport);
  const markets = ev.markets.map(mercadoDesdeContrato);
  if (sport === 'nba') {
    const id = Number(ev.id);
    if (!Number.isInteger(id)) throw new TypeError('Identificador de NBA inválido');
    // La web solo conoce estos tres estados de NBA; un valor nuevo del contrato se trata como programado (el contrato lo exige a los clientes).
    const status = ['finished', 'awaiting_result'].includes(ev.status) ? ev.status : 'scheduled';
    const projection = Array.isArray(ev.team_projection) && ev.team_projection.length === 2 && ev.team_projection.every(Number.isFinite) ? ev.team_projection : null;
    return { id, sport: 'nba', home: ev.home, away: ev.away, start: ev.start, league: 'NBA', status, markets, sealed_at: ev.sealed_at ?? null,
      seal: ev.seal ?? null, planned_seal: ev.planned_seal ?? null, actionable: false, score: ev.score ?? null, availability: null, official_url: null,
      team_projection: projection, v2: true };
  }
  return { id: ev.id, sport: 'tenis', home: ev.home, away: ev.away, start: ev.start, league: ev.league, surface: ev.surface ?? null, status: ev.status,
    markets, sealed_at: ev.sealed_at ?? null, seal: ev.seal ?? null, score: ev.score ?? null, actionable: false, destacado: ev.destacado ?? null };
}

// Imagen del evento: solo rutas del propio servidor (`/web/…`), como `ownImage` del hub; cualquier otra cosa se descarta.
const imagenPropia = src => (typeof src === 'string' && /^\/web\/[\w./-]+\.(png|jpe?g|webp|svg)$/i.test(src) ? src : null);

// Evento de un deporte SIN pantalla propia: la misma forma que usa la ventana de deporte, más `generico: true` (los extras atados a nba/tenis no se pintan).
function eventoGenerico(ev, sport) {
  const markets = ev.markets.map(m => mercadoDesdeContrato(m, true));
  return { id: ev.id, sport, home: ev.home, away: ev.away, start: ev.start, league: ev.league, surface: ev.surface ?? null, status: ev.status, markets,
    sealed_at: ev.sealed_at ?? null, seal: ev.seal ?? null, planned_seal: ev.planned_seal ?? null, score: ev.score ?? null, actionable: false,
    destacado: ev.destacado ?? null, home_img: imagenPropia(ev.imagenes?.home), away_img: imagenPropia(ev.imagenes?.away), generico: true, bloques: [] };
}

export function eventosDesdeContrato(data, sport) {
  if (data?.contrato !== 1 || data.deporte !== sport || !Array.isArray(data.eventos)) throw new TypeError('Respuesta del contrato inválida');
  const events = data.eventos.map(ev => eventoDesdeContrato(ev, sport));
  // Mismos filtros que hoy: tenis exige sello y mercados; NBA se queda con todos los partidos (los sin pronóstico los filtra `sources()`).
  return (sport === 'tenis' ? events.filter(e => e.seal && e.markets.length) : events).sort((a, b) => Date.parse(a.start) - Date.parse(b.start));
}

// UNA petición por deporte para los 7 días de la ventana. Lanza si el contrato no responde bien: `loadSportWeb` decide el respaldo.
export async function loadSportContrato(sport, fetcher = fetch, now = new Date()) {
  const { desde, dias, tz } = ventanaContrato(sport, now);
  const controller = new AbortController(), timer = setTimeout(() => controller.abort(), 15000);
  try {
    const response = await fetcher(`/deportes/v1/${sport}/cartelera?cliente=web&contrato=1&desde=${desde}&dias=${dias}&tz=${tz}`, { signal: controller.signal });
    if (response.status !== 200 && response.status !== 304) throw new Error(`estado ${response.status}`);
    return { status: 'ready', events: eventosDesdeContrato(await response.json(), sport) };
  } finally { clearTimeout(timer); }
}

// Cargador de la web: el contrato si el deporte lo tiene encendido y, si falla, el cargador de siempre (nunca se queda sin NBA ni tenis).
export async function loadSportWeb(sport, fetcher = fetch, now = new Date(), { contrato = CONTRATO_WEB } = {}) {
  // Un deporte del catálogo sin pantalla propia no tiene cargador anterior al que volver: solo el contrato; si falla, `error` (la vista ofrece reintentar).
  if (esDeporteGenerico(sport)) {
    try { return await loadSportContrato(sport, fetcher, now); }
    catch (error) { console.warn(`Contrato /deportes/v1/${sport} no disponible (${error?.message || error}).`); return { status: 'error', events: [] }; }
  }
  if (contrato?.[sport]) {
    try { return await loadSportContrato(sport, fetcher, now); }
    catch (error) { console.warn(`Contrato /deportes/v1/${sport} no disponible (${error?.message || error}); se usa el cargador actual.`); }
  }
  return loadSport(sport, fetcher, now);
}

// ---- Deportes del catálogo SIN pantalla propia (Fase 4 · 4.4): detalle, mercados por familia y bloques de contenido.
// Todo llega por el contrato; nada de `/web/deportes/nba|tenis/…`. Un bloque con tipo desconocido se ignora sin ruido (un cliente más viejo que el
// servidor no debe romperse); uno mal formado se ignora con un `console.warn` corto. Lo que sale de aquí ya está validado: la vista lo escapa al pintar.
const ID_BLOQUE = /^[a-z0-9_]{1,40}$/;
const texto = (v, max = 600) => typeof v === 'string' && v.length > 0 && v.length <= max;
const celda = v => v === null || typeof v === 'string' || (typeof v === 'number' && Number.isFinite(v));
const BLOQUES = {
  tabla: b => Array.isArray(b.columnas) && b.columnas.length >= 1 && b.columnas.length <= 12 && b.columnas.every(c => typeof c === 'string')
    && Array.isArray(b.filas) && b.filas.length <= 100 && b.filas.every(f => Array.isArray(f) && f.length === b.columnas.length && f.every(celda))
    && { columnas: b.columnas, filas: b.filas },
  barras: b => Array.isArray(b.items) && b.items.length <= 20
    && b.items.every(i => i && typeof i.etiqueta === 'string' && typeof i.valor === 'number' && i.valor >= 0 && i.valor <= 1 && (i.nota == null || typeof i.nota === 'string'))
    && { items: b.items.map(i => ({ etiqueta: i.etiqueta, valor: i.valor, nota: i.nota ?? '' })) },
  pares: b => Array.isArray(b.items) && b.items.length <= 30 && b.items.every(i => i && typeof i.etiqueta === 'string' && celda(i.valor ?? null))
    && { items: b.items.map(i => ({ etiqueta: i.etiqueta, valor: i.valor ?? null })) },
  texto: b => texto(b.cuerpo) && { cuerpo: b.cuerpo },
};
export function bloquesDesdeContrato(lista) {
  const out = [], vistos = new Set();
  for (const b of Array.isArray(lista) ? lista : []) {
    const construir = BLOQUES[b?.tipo];
    if (!construir) continue;                                                   // tipo desconocido: se ignora sin error
    const cuerpo = typeof b.id === 'string' && ID_BLOQUE.test(b.id) && !vistos.has(b.id) && texto(b.titulo, 120) ? construir(b) : false;
    if (!cuerpo) { console.warn(`Bloque de contenido ignorado (mal formado): ${String(b?.id).slice(0, 40)}`); continue; }
    vistos.add(b.id);
    out.push({ id: b.id, tipo: b.tipo, titulo: b.titulo, ...cuerpo });
  }
  return out;
}

// Familias de mercados de un evento en el orden del catálogo (`orden`: ids de familia), con `otros` siempre al final. Usa las del endpoint de mercados
// si llegaron (`event.familias`); si no, agrupa los mercados del evento por su `family`. Una familia sin mercados no sale.
export function familiasDeEvento(event, orden = []) {
  let grupos = event.familias;
  if (!Array.isArray(grupos)) {
    const mapa = new Map();
    for (const m of event.markets || []) { const id = m.family || 'otros'; if (!mapa.has(id)) mapa.set(id, []); mapa.get(id).push(m); }
    grupos = [...mapa].map(([id, markets]) => ({ id, markets }));
  }
  const rango = id => { const i = orden.indexOf(id); return i < 0 ? orden.length : i; };
  const normales = grupos.filter(g => g.id !== 'otros').map((g, i) => [g, i]).sort((a, b) => rango(a[0].id) - rango(b[0].id) || a[1] - b[1]).map(([g]) => g);
  return [...normales, ...grupos.filter(g => g.id === 'otros')].filter(g => g.markets.length);
}

// Detalle de un partido: `/partido/{id}` (evento completo + bloques en el idioma de la página) y `/partido/{id}/mercados` (familias del catálogo).
// Si solo falla `/mercados`, el detalle sigue con las familias que traen los propios mercados; si falla `/partido/{id}`, `error`.
export async function loadPartidoContrato(sport, id, lang = 'es', fetcher = fetch) {
  const base = `/deportes/v1/${encodeURIComponent(sport)}/partido/${encodeURIComponent(id)}`;
  const pull = async url => {
    const controller = new AbortController(), timer = setTimeout(() => controller.abort(), 15000);
    try {
      const response = await fetcher(url, { signal: controller.signal });
      if (response.status !== 200 && response.status !== 304) throw new Error(`estado ${response.status}`);
      return await response.json();
    } finally { clearTimeout(timer); }
  };
  try {
    const [partido, mercados] = await Promise.allSettled([pull(`${base}?cliente=web&lang=${['es', 'en', 'pt'].includes(lang) ? lang : 'es'}`), pull(`${base}/mercados?cliente=web`)]);
    if (partido.status !== 'fulfilled') throw partido.reason;
    const data = partido.value;
    if (data?.contrato !== 1 || data.deporte !== sport) throw new TypeError('Respuesta del contrato inválida');
    const event = eventoDesdeContrato(data.evento, sport);
    let familias = null;
    const grupos = mercados.status === 'fulfilled' && mercados.value?.contrato === 1 && String(mercados.value.evento_id) === event.id ? mercados.value.familias : null;
    if (Array.isArray(grupos)) {
      const porId = new Map(event.markets.map(m => [m.id, m]));
      const colocados = new Set();
      familias = grupos.filter(g => g && typeof g.id === 'string' && Array.isArray(g.mercados)).map(g => ({ id: g.id,
        markets: g.mercados.map(m => porId.get(m?.id)).filter(m => m && !colocados.has(m.id) && colocados.add(m.id)) }));
      const sueltos = event.markets.filter(m => !colocados.has(m.id));
      if (sueltos.length) familias.push({ id: 'otros', markets: sueltos });
    }
    return { status: 'ready', event: { ...event, familias, bloques: bloquesDesdeContrato(data.bloques) } };
  } catch (error) {
    console.warn(`Detalle /deportes/v1/${sport}/partido no disponible (${error?.message || error}).`);
    return { status: 'error', event: null };
  }
}

// El evento de la lista con el detalle encima (mercados completos, familias y bloques). Mientras carga o si falla, el de la lista más `markets_status`.
export function withDetalle(event, entry) {
  if (!event?.generico || !entry) return event;
  if (entry.status !== 'ready') return { ...event, markets_status: entry.status };
  return { ...event, ...entry.event, markets_status: 'ready' };
}
