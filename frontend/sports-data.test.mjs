import test from 'node:test';
import assert from 'node:assert/strict';
import {nbaEvents,nbaV2Events,tennisEvents,loadSport,loadResults} from './sports-data.js';
import {createHubViews} from './ergonomic-views.js';
const event={event_id:'1',tipoff_utc:'2026-10-27T20:00:00Z',home_team:'A',away_team:'B',status:'evaluated',final:{home:99,away:102}};
const row={event_id:'1',player_id:'winner',market:'winner',market_label:'Ganador',probability_over:.3,probability_under:.7,sealed_at_utc:'2026-10-27T19:00:00Z',result:{status:'evaluated',actual:0}};
const nba=(rows=[row])=>({live_v13:{cohorts:[{cohort:'real',created_at_utc:'2026-10-27T19:00:00Z',events:[event],predictions:rows}]}});
test('NBA usa el lado y la probabilidad publicados, con resultado previo válido',()=>{
 const [e]=nbaEvents(nba()); assert.equal(e.markets[0].selection,'B');assert.equal(e.markets[0].probability,.7);assert.equal(e.markets[0].outcome,'win');assert.equal(e.markets[0].price,null);
});
test('una revisión posterior al inicio no se cuenta como acierto previo',()=>{
 for(const changed of [{performance_eligible:false},{sealed_at_utc:'2026-10-27T20:01:00Z'}]) {
  const [e]=nbaEvents(nba([{...row,...changed}]));assert.equal(e.markets[0].outcome,null);assert.equal(e.markets[0].revised,true);
 }
});
test('NBA descarta cuarentena y probabilidades ausentes; conserva la revisión más reciente',()=>{
 assert.equal(nbaEvents(nba([{...row,probability_over:null}])).length,0);
 const v=nba();v.live_v13.cohorts[0].events[0]={...event,status:'validation_hold'};assert.equal(nbaEvents(v).length,0);
 const updated=nba();updated.live_v13.cohorts.push({...updated.live_v13.cohorts[0],recalculated_at_utc:'2026-10-28T01:00:00Z',predictions:[{...row,probability_over:.8}]});assert.equal(nbaEvents(updated).length,1);assert.equal(nbaEvents(updated)[0].markets[0].selection,'A');
});
test('tenis exige el contrato público, sello y probabilidades válidas',()=>{
 const e={id:'1',sport:'tenis',home:'A',away:'B',start:'2026-10-27T20:00:00Z',seal:'abc',markets:[{probability:.65}]};
 assert.equal(tennisEvents({state:'ok',events:[e]}).length,1);assert.equal(tennisEvents({state:'ok',events:[{...e,seal:null}]}).length,0);assert.throws(()=>tennisEvents({events:[e]}));
});
test('las fuentes fallan por separado y nunca fabrican cuotas ni publicaciones',async()=>{
 const calls=[];const fetcher=async path=>{calls.push(path);return path.startsWith('/nba/')?{ok:true,json:async()=>({fecha:'x',partidos:[]})}:{ok:true,json:async()=>({state:'unavailable',events:[]})};};
 const now=new Date(2026,10,3,12);
 assert.equal((await loadSport('nba',fetcher,now)).status,'ready');assert.equal((await loadSport('tenis',fetcher)).status,'error');
 assert.ok(calls.includes('/nba/v1/cartelera?fecha=2026-11-03')&&calls.includes('/nba/v1/cartelera?fecha=2026-11-07')&&calls.includes('/web/deportes/tenis'));assert.ok(!calls.includes('/nba/api/data'));
 assert.equal((await loadSport('nba',async()=>({ok:false}),now)).status,'error');
});
const game=(id,fecha,home,away,iso,result,pick=null)=>({id,fecha,local:{codigo:home[0],nombre:home[1]},visitante:{codigo:away[0],nombre:away[1]},inicio_utc:iso,sello_previsto:new Date(Date.parse(iso)-36e5).toISOString(),resultado:result,pronostico:pick});
const BOS=['BOS','Boston Celtics'],NYK=['NYK','New York Knicks'],MIA=['MIA','Miami Heat'];
test('la cartelera v2 conserva los partidos sin pronóstico y calcula sus estadísticas con marcadores finales',()=>{
 const rows=[game(1,'2026-10-28',BOS,NYK,'2026-10-29T00:00:00Z',{local:110,visitante:100}),game(2,'2026-11-01',MIA,BOS,'2026-11-02T00:00:00Z',{local:90,visitante:99}),
  game(3,'2026-11-04',BOS,NYK,'2026-11-05T00:00:00Z',null),game(4,'2026-11-05',MIA,NYK,'2026-11-06T00:00:00Z',null)];
 const events=nbaV2Events(rows,new Date('2026-11-03T12:00:00Z'));
 assert.equal(events.length,4);
 const next=events.find(e=>e.id===3);
 assert.deepEqual(next.markets,[]);assert.equal(next.status,'scheduled');assert.equal(next.planned_seal,'2026-11-04T23:00:00.000Z');assert.equal(next.seal,null);
 const [bos,nyk]=next.stats.teams;
 assert.equal(bos.season.won,2);assert.equal(bos.season.lost,0);assert.equal(bos.streak,2);assert.equal(bos.rest_days,2);assert.equal(bos.back_to_back,false);
 assert.equal(nyk.season.lost,1);assert.equal(nyk.streak,-1);assert.equal(nyk.scoring.points_for,100);
 assert.equal(next.stats.h2h.matches.length,1);assert.equal(next.stats.h2h.home_wins,1);assert.equal(next.stats.h2h.average_total,210);
 // las estadísticas de un partido no usan marcadores posteriores a su inicio
 assert.equal(events.find(e=>e.id===1).stats.teams[0].season.won,0);
 assert.equal(events.find(e=>e.id===2).score,'90 – 99');
});
test('el pronóstico v2 solo cuenta como previo si se selló antes del inicio',()=>{
 const pick=sealed=>({hash:'abc',p_local:.7,sellado_en:sealed});
 const [ok]=nbaV2Events([game(1,'2026-11-01',BOS,NYK,'2026-11-02T00:00:00Z',{local:100,visitante:90},pick('2026-11-01T23:00:00Z'))]);
 assert.equal(ok.markets[0].selection,'Boston Celtics');assert.equal(ok.markets[0].outcome,'win');assert.equal(ok.seal,'abc');
 const [late]=nbaV2Events([game(1,'2026-11-01',BOS,NYK,'2026-11-02T00:00:00Z',{local:100,visitante:90},pick('2026-11-02T00:30:00Z'))]);
 assert.equal(late.markets[0].outcome,null);assert.equal(late.markets[0].revised,true);
 assert.deepEqual(nbaV2Events([game(1,'2026-11-01',BOS,NYK,'2026-11-02T00:00:00Z',null,{hash:'abc',p_local:1.4,sellado_en:'2026-11-01T23:00:00Z'})])[0].markets,[]);
});
test('el historial conserva fallos reales y no acepta resultados inventados',async()=>{
 const rows=[{local:'A',visitante:'B',kickoff_utc:event.tipoff_utc,outcome:'loss'},{local:'A',visitante:'B',kickoff_utc:event.tipoff_utc,outcome:'fake'}];
 const r=await loadResults(async()=>({ok:true,json:async()=>({items:rows})}));assert.equal(r.items.length,1);assert.equal(r.items[0].outcome,'loss');
});
test('la portada conserva el bloqueo aunque el payload traiga datos privados',()=>{
 const date=new Date('2026-10-27T12:00:00Z');
 const home={status:'ready',data:{agenda:[],alta_probabilidad:{proximos:[],vip:[{match_id:'1',local:'A',visitante:'B',kickoff_utc:event.tipoff_utc,texto:'PRIVATE_SELECTION',prob:.999,ref_price:99}]}}};
 const views=createHubViews({state:{dayOffset:0,sport:'todos',homeSearch:'',homeStatus:'todos'},esc:x=>String(x??''),ensureHome:()=>home,addDays:()=>date,localDay:d=>d.toISOString().slice(0,10),dayLabel:()=> 'Hoy',realDate:()=> '27 oct',realTime:()=> '14:00',fmtOdds:String,fmtPct:String,dayRail:()=>'',liveEvidence:()=>''});
 const html=views.home();assert.ok(html.includes('acceso Plus'));assert.ok(!html.includes('PRIVATE_SELECTION'));assert.ok(!html.includes('99%'));
});

import { featuredModelMarket } from './sports-data.js';
import { createSportWindow } from './sports-window.js';

test('el destacado de NBA y tenis usa la cuota del modelo (1 ÷ prob.) de 1,40 en adelante, sin tope, y la mayor probabilidad', () => {
  const m = (id, probability) => ({ id, probability });
  assert.equal(featuredModelMarket([m('a', .95), m('b', .70), m('c', .60), m('d', .30)]).id, 'b');
  assert.equal(featuredModelMarket([m('lo', 1 / 1.4), m('hi', 1 / 1.8)]).id, 'lo');          // 1,40 incluido; gana la mayor probabilidad
  assert.equal(featuredModelMarket([m('x', .75), m('y', .5)]).id, 'y');                         // 1,33 queda fuera; 2,00 ya cuenta (sin tope)
  assert.equal(featuredModelMarket([m('x', .75), m('y', .9)]), null);                           // todas por debajo de 1,40
  assert.equal(featuredModelMarket([m('largo', .05)]).id, 'largo');                             // cuota 20: sin tope
  assert.equal(featuredModelMarket([{ id: 'z', probability: 'alta' }, null]), null);
  assert.equal(featuredModelMarket(undefined), null);
});

test('la ventana de tenis y NBA renderiza pronóstico y estadísticas sin cuotas inventadas', () => {
  const st = { sport: 'tenis', winDay: 0, winEvent: '', winLastEvent: null, winPane: 'pron', winSportTab: 'resumen', winSportFam: '', winAll: false, winDayPinned: false };
  const start = new Date().toISOString();
  const event = { id: 'e1', sport: 'tenis', home: 'Ana Perez', away: 'Bea <b>Luz</b>', start, league: 'WTA · Test', surface: 'Hard', status: 'scheduled', seal: 'abc123', sealed_at: start,
    markets: [{ id: 'winner', label: 'Ganador del partido', selection: 'Ana Perez', probability: .65, price: null },
      { id: 'games_total-2', label: 'Juegos totales', selection: 'Más de 20.5', probability: .52, price: null }] };
  const rate = (won, lost) => ({ won, lost, rate: won / (won + lost) });
  const player = (name, rank, matches) => ({ key: 1, name, country: 'Peru', age: 21, rank, points: 1200, movement: 'up', season: { season: 2026, titles: 1, ...rate(20, 10) },
    career: rate(60, 40), surfaces: { hard: { career: rate(30, 10), season: rate(12, 4) }, clay: { career: rate(0, 0), season: null }, grass: { career: rate(4, 6), season: null } },
    ranking_history: [{ season: 2026, rank, titles: 1, ...rate(20, 10) }],
    form: { matches, windows: { 30: { ...rate(2, 1), matches: 3 }, 90: { ...rate(4, 2), matches: 6 }, 360: { ...rate(6, 4), matches: 10 } }, streak: 3, index: 72, complete_matches: 8, over_2_5_sets: .375, tiebreaks: .25,
      stages: { inicial: { ...rate(2, 2), matches: 4 }, avanzada: { ...rate(1, 0), matches: 1 } }, qualification: { won: 0, lost: 0, rate: null, matches: 0 } } });
  const last = [{ date: '2026-10-26', won: true, opponent: 'Rival X', tournament: 'Tokyo', round: '1/16-finals', score: '6-3 6-4', qualification: false }];
  const stats = { players: [player('Ana Perez', 31, last), player('Bea Luz', 12, last)], h2h: { first_wins: 2, second_wins: 1, matches: [{ date: '2026-08-06', won: true, tournament: 'Toronto', round: '1/32-finals', score: '6-4 6-4' }] } };
  const pass = v => String(v);
  const w = createSportWindow({ state: st, esc: pass, badge: (t) => `<i>${t}</i>`, fmtPct: p => `${(p * 100).toFixed(1)}%`, fmtOdds: o => o.toFixed(2),
    realDate: pass, realTime: pass, dateFmt: pass, addDays: () => new Date(), localDay: d => new Date(d).toISOString().slice(0, 10),
    dayLabel: () => 'Hoy', ensureSport: () => ({ status: 'ready', events: [event] }), ensureTennisStats: () => ({ status: 'ready', data: stats }), featuredModelMarket });
  const html = w.view();
  assert.ok(html.includes('Cuota del modelo') && html.includes('1.54'));                        // 1 ÷ 0,65
  assert.ok(html.includes('Resumen') && html.includes('Forma') && html.includes('Resultado'));
  assert.ok(!html.includes('Cuota publicada'));
  // pestañas de estadísticas de jugadores
  assert.ok(html.includes('Superficie') && html.includes('Cara a cara') && html.includes('Modelo'));
  assert.ok(html.includes('COMPARATIVA') && html.includes('#31') && html.includes('#12'));
  const tab = id => { st.winSportTab = id; return w.view(); };
  assert.ok(tab('forma').includes('Racha actual') && tab('forma').includes('Últimos 90 días') && tab('forma').includes('Rival X'));
  assert.ok(tab('superficie').includes('PISTA DURA') && tab('superficie').includes('ESTE PARTIDO'));
  assert.ok(tab('h2h').includes('Toronto'));
  assert.ok(tab('modelo').includes('JUEGOS TOTALES') && tab('modelo').includes('REGISTRO DEL ANÁLISIS'));
});

test('las estadísticas de tenis rechazan respuestas incompletas o con números no finitos', async () => {
  const { loadTennisStats } = await import('./sports-data.js');
  const ok = { players: [{ surfaces: {}, ranking_history: [], rank: 3 }, { surfaces: {}, ranking_history: [], rank: null }], h2h: { matches: [] } };
  let path;
  const good = await loadTennisStats('12/3', async p => { path = p; return { ok: true, json: async () => ok }; });
  assert.equal(good.status, 'ready'); assert.equal(path, '/web/deportes/tenis/estadisticas/12%2F3');
  assert.equal((await loadTennisStats('1', async () => ({ ok: true, json: async () => ({ players: [{}] }) }))).status, 'error');
  assert.equal((await loadTennisStats('1', async () => ({ ok: true, json: async () => ({ ...ok, players: [{ ...ok.players[0], rank: 'alto' }, ok.players[1]] }) }))).status, 'error');
  assert.equal((await loadTennisStats('1', async () => ({ ok: false, status: 404 }))).status, 'error');
  assert.equal((await loadTennisStats('1', async () => { throw new Error('red'); })).status, 'error');
});

test('nbaCode reconoce a los 30 equipos por su nombre de las cuotas y no inventa códigos', async () => {
  const { nbaCode } = await import('./sports-data.js');
  assert.equal(nbaCode('Los Angeles Lakers'), 'LAL');
  assert.equal(nbaCode('LA Clippers'), 'LAC');
  assert.equal(nbaCode('Portland Trail Blazers'), 'POR');
  assert.equal(nbaCode('Philadelphia 76ers'), 'PHI');
  assert.equal(nbaCode('Equipo Inexistente'), null);
  assert.equal(nbaCode(undefined), null);
});

test('la ventana de NBA pinta el logo de cada equipo si el manifiesto lo trae y las iniciales si no', async () => {
  const { nbaCode } = await import('./sports-data.js');
  const st = { sport: 'nba', winDay: 0, winEvent: '', winLastEvent: null, winPane: 'pron', winSportTab: 'resumen', winSportFam: '', winAll: false, winDayPinned: false };
  const start = new Date().toISOString();
  const event = { id: 'n1', sport: 'nba', home: 'Los Angeles Lakers', away: 'Portland Trail Blazers', start, league: 'NBA', status: 'scheduled', seal: 'abc123', sealed_at: start,
    markets: [{ id: 'winner', label: 'Ganador', selection: 'Los Angeles Lakers', probability: .65, price: null }] };
  const pass = v => String(v);
  const build = images => createSportWindow({ state: st, esc: pass, badge: t => `<i>${t}</i>`, fmtPct: p => `${(p * 100).toFixed(1)}%`, fmtOdds: o => o.toFixed(2),
    realDate: pass, realTime: pass, dateFmt: pass, addDays: () => new Date(), localDay: d => new Date(d).toISOString().slice(0, 10), dayLabel: () => 'Hoy',
    ensureSport: () => ({ status: 'ready', events: [event] }), ensureNbaStats: () => ({ status: 'loading' }), featuredModelMarket, ensureImages: () => images, nbaCode });
  const ready = build({ status: 'ready', tenis: {}, nba: { LAL: { f: 'LAL.png' }, POR: { f: 'POR.png' } } }).view();
  assert.ok(ready.includes('src="/web/imagenes/nba/LAL.png"') && ready.includes('src="/web/imagenes/nba/POR.png"'));
  assert.ok(!ready.includes('is-initial'));
  const loading = build({ status: 'loading', nba: {}, tenis: {} }).view();      // manifiesto aún sin cargar o caído: iniciales, sin imágenes rotas
  assert.ok(loading.includes('is-initial') && !loading.includes('/web/imagenes/'));
});

import { loadFootballFeatured, HISTORY_SINCE } from './sports-data.js';

test('el historial arranca el 26 de octubre y pide al servidor el destacado de fútbol desde esa fecha', async () => {
  assert.equal(HISTORY_SINCE, '2026-10-26');
  let url = '';
  const rows = [{ local: 'A', visitante: 'B', kickoff_utc: event.tipoff_utc, outcome: 'win' }, { local: 'A', visitante: 'B', kickoff_utc: event.tipoff_utc, outcome: null }];
  const r = await loadFootballFeatured(async u => { url = u; return { ok: true, json: async () => ({ items: rows }) }; });
  assert.equal(url, '/mobile/v1/markets/destacados?desde=2026-10-26');
  assert.equal(r.status, 'ready'); assert.equal(r.items.length, 1);
  assert.equal((await loadFootballFeatured(async () => ({ ok: false }))).status, 'error');
});

test('el historial solo junta destacados (fútbol, NBA y tenis) y Alta probabilidad desde el 26 de octubre', () => {
  const m = (id, probability, outcome, extra = {}) => ({ id, selection: id, probability, outcome, price: null, ...extra });
  const tenis = (start, markets) => ({ sport: 'tenis', id: start, home: 'T1', away: 'T2', start, score: '2 - 0', markets });
  const events = [
    tenis('2026-10-26T15:00:00Z', [m('winner', .9, 'win'), m('destacado', .7, 'loss'), m('revisado', .72, 'win', { revised: true })]),
    tenis('2026-10-25T15:00:00Z', [m('viejo', .7, 'win')]),
    tenis('2026-10-27T15:00:00Z', [m('sin-rango', .95, 'win')]),
  ];
  const results = { status: 'ready',
    items: [{ local: 'A', visitante: 'B', kickoff_utc: '2026-10-26T18:00:00Z', outcome: 'win', texto: 'alta', prob: .8, ref_price: 1.25, home_goals: 1, away_goals: 0 },
            { local: 'A', visitante: 'B', kickoff_utc: '2026-10-25T18:00:00Z', outcome: 'win', texto: 'vieja', prob: .8, ref_price: 1.25, home_goals: 1, away_goals: 0 }],
    featured: [{ local: 'C', visitante: 'D', kickoff_utc: '2026-10-27T18:00:00Z', outcome: 'loss', texto: 'dest', prob: .65, ref_price: null, home_goals: 0, away_goals: 1 }] };
  const views = createHubViews({ state: { dayOffset: 0, sport: 'todos', resultSport: 'todos' }, esc: x => String(x ?? ''), ensureHome: () => ({ status: 'ready', data: { agenda: [] } }), ensureSport: s => (s === 'tenis' ? { status: 'ready', events } : { status: 'ready', events: [] }), ensureResults: () => results,
    addDays: () => new Date('2026-10-27T12:00:00Z'), localDay: d => d.toISOString().slice(0, 10), dayLabel: () => 'Hoy', realDate: () => '27 oct', realTime: () => '14:00', fmtOdds: String, fmtPct: String, dayRail: () => '', liveEvidence: () => '' });
  const html = views.history();
  assert.match(html, /1 de 3 pronósticos acertados/);
  for (const fuera of ['vieja', 'viejo', 'winner', 'revisado', 'sin-rango']) assert.ok(!html.includes(fuera), fuera);
  for (const dentro of ['alta', 'dest', 'T1 vs T2', 'C vs D']) assert.ok(html.includes(dentro), dentro);
});
