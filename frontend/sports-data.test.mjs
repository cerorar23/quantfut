import test from 'node:test';
import assert from 'node:assert/strict';
import {nbaEvents,nbaV2Events,tennisEvents,loadSport,loadResults,loadNbaMarkets,withNbaMarkets,featuredModelMarket,featuredSportMarket,bestBySafety,marketQuote} from './sports-data.js';
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
const fullMarket = (extra = {}) => ({ id: 'points-10-20.5-over', market: 'player_points', side: 'over', line: 20.5, player: 'Jugador <b>', player_id: 10,
  team: 'Boston Celtics', probability: .78, push_probability: 0, conditional: true, sealed_at: '2026-11-04T23:00:00Z', seal: 'a'.repeat(64), estimate: 23, ...extra });
const fullEvent = { id: 99, sport: 'nba', v2: true, home: 'Boston Celtics', away: 'Milwaukee Bucks', start: '2026-11-05T00:00:00Z', status: 'scheduled', markets: [] };
test('carga todos los mercados del partido y el destacado puede ser un jugador', async () => {
 let path;
 const data={partido_id:99,markets:[fullMarket({id:'winner',market:'winner',side:'local',line:null,player:null,player_id:null,probability:.896}),fullMarket(),fullMarket({id:'points-10-25.5-under',line:25.5,side:'under',probability:.82})],projections:[]};
 const entry=await loadNbaMarkets(fullEvent,async p=>{path=p;return {ok:true,json:async()=>data};});
 assert.equal(path,'/nba/v1/partido/99/mercados');assert.equal(entry.status,'ready');assert.equal(entry.markets.length,3);
 const event=withNbaMarkets(fullEvent,entry);
 assert.equal(featuredModelMarket(event.markets).selection,'Menos de 25.5 puntos');
 assert.equal(featuredModelMarket(event.markets).label,'Puntos de Jugador <b>');
 assert.equal(event.markets[0].selection,'Boston Celtics');assert.ok(event.markets.every(m=>m.eligible&&!m.revised));
});
test('una carga fallida o en curso no evalúa solo el ganador ni afirma que no hay destacado', async()=>{
 for(const status of ['loading','error']) assert.deepEqual(withNbaMarkets({...fullEvent,markets:[fullMarket()]},{status}).markets,[]);
 for(const data of [{partido_id:100,markets:[],projections:[]},{partido_id:99,markets:[fullMarket({probability:NaN})],projections:[]},{partido_id:99,markets:[fullMarket({line:null})],projections:[]}])
   assert.equal((await loadNbaMarkets(fullEvent,async()=>({ok:true,json:async()=>data}))).status,'error');
 assert.equal((await loadNbaMarkets(fullEvent,async()=>{throw Error('red');})).status,'error');
});
test('los mercados posteriores al inicio se excluyen del destacado y los resultados de equipo se liquidan por lado',async()=>{
 const rows=[fullMarket({sealed_at:'2026-11-05T00:01:00Z'}),fullMarket({id:'total-under',market:'game_total',player:null,player_id:null,line:210,side:'under',probability:.8}),fullMarket({id:'spread-away',market:'handicap',team:'Milwaukee Bucks',line:5.5,side:'visit',player:null,player_id:null,probability:.8})];
 const entry=await loadNbaMarkets({...fullEvent,status:'finished',score:'110 – 100'},async()=>({ok:true,json:async()=>({partido_id:99,markets:rows,projections:[]})}));
 assert.equal(entry.markets[0].revised,true);assert.equal(entry.markets[0].outcome,null);
 assert.equal(entry.markets[1].outcome,'push');assert.equal(entry.markets[2].outcome,'loss');
 assert.notEqual(featuredModelMarket(entry.markets.filter(m=>!m.revised)).id,rows[0].id);
});
test('NBA elige el destacado por la cuota de la casa cuando existe y muestra su nombre',()=>{
 const markets=[fullMarket({id:'high-prob',probability:.8,price:1.44,book:'bovada'}),fullMarket({id:'too-short',probability:.9,price:1.12,book:'pinnacle'}),fullMarket({id:'model-only',probability:.78})];
 assert.equal(featuredSportMarket({...fullEvent,markets}).id,'high-prob');
 assert.deepEqual(marketQuote(markets[0]),{price:1.44,source:'Bovada',model:false});
 assert.equal(featuredSportMarket({...fullEvent,markets:[markets[1],markets[2]]}),null);
 assert.equal(featuredSportMarket({...fullEvent,markets:[markets[2]]}).id,'model-only');
 assert.equal(marketQuote({...markets[0],book:null}).model,true);
});
test('el resultado de jugador publicado se conserva y las revisiones nunca se convierten en aciertos',async()=>{
 for(const outcome of ['win','loss','push','void']) {
  const entry=await loadNbaMarkets(fullEvent,async()=>({ok:true,json:async()=>({partido_id:99,markets:[fullMarket({outcome})],projections:[]})}));
  assert.equal(entry.markets[0].outcome,outcome);
 }
 const late=await loadNbaMarkets(fullEvent,async()=>({ok:true,json:async()=>({partido_id:99,markets:[fullMarket({outcome:'win',sealed_at:'2026-11-05T01:00:00Z'})],projections:[]})}));
 assert.equal(late.markets[0].outcome,null);
});
test('la cartelera v2 conserva los partidos sin pronóstico y no calcula estadísticas en el navegador',()=>{
 const rows=[game(1,'2026-10-28',BOS,NYK,'2026-10-29T00:00:00Z',{local:110,visitante:100}),game(2,'2026-11-01',MIA,BOS,'2026-11-02T00:00:00Z',{local:90,visitante:99}),
  game(3,'2026-11-04',BOS,NYK,'2026-11-05T00:00:00Z',null),game(4,'2026-11-05',MIA,NYK,'2026-11-06T00:00:00Z',null)];
 const events=nbaV2Events(rows,new Date('2026-11-03T12:00:00Z'));
 assert.equal(events.length,4);
 const next=events.find(e=>e.id===3);
 assert.deepEqual(next.markets,[]);assert.equal(next.status,'scheduled');assert.equal(next.planned_seal,'2026-11-04T23:00:00.000Z');assert.equal(next.seal,null);
 assert.ok(events.every(e=>e.v2===true&&!('stats' in e)));
 assert.equal(events.find(e=>e.id===2).score,'90 – 99');assert.equal(events.find(e=>e.id===2).status,'finished');
});
test('las estadísticas de un partido se piden al servidor al abrirlo, no con la cartelera',async()=>{
 const calls=[];const fetcher=async path=>{calls.push(path);return {ok:true,json:async()=>({fecha:'x',partidos:[]})};};
 await loadSport('nba',fetcher,new Date(2026,10,3,12));
 assert.equal(calls.length,9);assert.ok(calls.every(c=>c.startsWith('/nba/v1/cartelera?fecha=')));
 assert.ok(!calls.some(c=>c.includes('estadisticas')));
});
test('la cartelera no pide días de pretemporada',async()=>{
 const calls=[];await loadSport('nba',async path=>{calls.push(path);return {ok:true,json:async()=>({partidos:[]})};},new Date(2026,9,21,12));
 assert.deepEqual(calls.map(c=>c.slice(-10)),['2026-10-20','2026-10-21','2026-10-22','2026-10-23','2026-10-24','2026-10-25']);
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

import { createSportWindow } from './sports-window.js';

test('el destacado sin cuota de casa usa la del modelo (1 ÷ prob.): la mayor probabilidad con cuota >= 1,20 y prob. >= 75 %', () => {
  const m = (id, probability) => ({ id, probability });
  assert.equal(featuredModelMarket([m('a', .95), m('b', .82), m('c', .78), m('d', .30)]).id, 'b');   // .95 paga 1,05; .30 no llega al 75 %
  assert.equal(featuredModelMarket([m('lo', 1 / 1.2), m('hi', .75)]).id, 'lo');                       // tope: 1,20 incluido (83,3 %); 75 % incluido
  assert.equal(featuredModelMarket([m('x', .5), m('y', .74)]), null);                                  // ninguna llega al 75 %
  assert.equal(featuredModelMarket([m('x', .85), m('y', .9)]), null);                                  // todas pagan menos de 1,20
  assert.equal(featuredModelMarket([m('largo', .05)]), null);                                          // cuota 20, pero 5 %: no es probable
  assert.equal(featuredModelMarket([{ id: 'z', probability: 'alta' }, null]), null);
  assert.equal(featuredModelMarket(undefined), null);
});

test('probabilidad máxima segura: gana la más probable aunque otra pague más; el empate lo decide la mayor cuota', () => {
  const rows = [{ id: 'segura', p: .82, c: 1.22 }, { id: 'rentable', p: .81, c: 1.6 }];
  for (const list of [rows, [...rows].reverse()]) assert.equal(bestBySafety(list, r => r.p, r => r.c).id, 'segura');
  const tie = [{ id: 'a', p: .8, c: 1.25 }, { id: 'b', p: .8, c: 1.45 }];
  for (const list of [tie, [...tie].reverse()]) assert.equal(bestBySafety(list, r => r.p, r => r.c).id, 'b');
  assert.equal(bestBySafety([{ p: .7, c: 1.8 }, { p: .9, c: 1.1 }], r => r.p, r => r.c), null);           // 70 % no basta; 1,10 < 1,20
  assert.equal(bestBySafety([{ p: .8, c: 1.1999 }, { p: .7499, c: 3 }], r => r.p, r => r.c), null);
  assert.equal(bestBySafety([{ p: .75, c: 1.2 }], r => r.p, r => r.c).p, .75);
});

test('el destacado de tenis y NBA lo manda el servidor: el cliente solo localiza ese mercado', async () => {
  const m = (id, probability, extra = {}) => ({ id, probability, ...extra });
  const markets = [m('a', .83), m('b', .78), m('c', .76)];
  const tenis = { sport: 'tenis', markets };
  assert.equal(featuredSportMarket({ ...tenis, destacado: { id: 'b' } }).id, 'b');   // el del servidor manda aunque 'a' sea más probable
  assert.equal(featuredSportMarket({ ...tenis, destacado: null }), null);                                   // el servidor dice que no hay
  assert.equal(featuredSportMarket({ ...tenis, destacado: { id: 'no-existe' } }), null);
  assert.equal(featuredSportMarket({ ...tenis, markets: [m('a', .83, { revised: true }), m('c', .76)], destacado: { id: 'a' } }), null);   // revisión: no se sustituye
  assert.equal(featuredSportMarket(tenis).id, 'a');                                                         // sin campo: misma regla en el cliente
  const data = { partido_id: 99, markets: [fullMarket({ id: 'p1', probability: .8 }), fullMarket({ id: 'p2', probability: .76 })], projections: [] };
  const load = extra => loadNbaMarkets(fullEvent, async () => ({ ok: true, json: async () => ({ ...data, ...extra }) }));
  const con = await load({ destacado: { id: 'p2' } });
  assert.equal(con.destacado, 'p2');
  assert.equal(featuredSportMarket(withNbaMarkets(fullEvent, con)).id, 'p2');
  assert.equal(featuredSportMarket(withNbaMarkets(fullEvent, await load({ destacado: null }))), null);
  const sin = await load({});
  assert.equal(sin.destacado, undefined);
  assert.equal(featuredSportMarket(withNbaMarkets(fullEvent, sin)).id, 'p1');
  assert.equal('destacado' in withNbaMarkets(fullEvent, { status: 'loading' }), false);
});

test('la ventana de tenis y NBA renderiza pronóstico y estadísticas sin cuotas inventadas', () => {
  const st = { sport: 'tenis', winDay: 0, winEvent: '', winLastEvent: null, winPane: 'pron', winSportTab: 'resumen', winSportFam: '', winAll: false, winDayPinned: false };
  const start = new Date().toISOString();
  const event = { id: 'e1', sport: 'tenis', home: 'Ana Perez', away: 'Bea <b>Luz</b>', start, league: 'WTA · Test', surface: 'Hard', status: 'scheduled', seal: 'abc123', sealed_at: start,
    markets: [{ id: 'winner', label: 'Ganador del partido', selection: 'Ana Perez', probability: .78, price: null },
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
  assert.ok(html.includes('Cuota del modelo') && html.includes('1.28'));                        // 1 ÷ 0,78
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
    tenis('2026-10-26T15:00:00Z', [m('winner', .9, 'win'), m('destacado', .78, 'loss'), m('revisado', .8, 'win', { revised: true })]),
    tenis('2026-10-25T15:00:00Z', [m('viejo', .78, 'win')]),
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

test('ordenLiquidado: acertados por cuota de mayor a menor, luego lo sin resultado y al final los fallados', async () => {
  const { ordenLiquidado, hayLiquidado } = await import('./sports-data.js');
  const o = { resultado: m => m.r, cuota: m => m.c, prob: m => m.p };
  const lista = [{ id: 'f1', r: 'loss', c: 1.9, p: .5 }, { id: 'w1', r: 'win', c: 1.2, p: .8 }, { id: 'n', r: null, c: 3, p: .3 },
    { id: 'w2', r: 'win', c: 1.8, p: .6 }, { id: 'f2', r: 'loss', c: 1.3, p: .7 }, { id: 'push', r: 'push', c: 2, p: .4 }, { id: 'w3', r: 'win', c: null, p: .9 }];
  assert.deepEqual(ordenLiquidado(lista, o).map(m => m.id), ['w2', 'w1', 'w3', 'n', 'push', 'f1', 'f2']);
  const ids = ordenLiquidado(lista, o).map(m => m.id);
  assert.deepEqual(ids.slice(0, 3), ['w2', 'w1', 'w3'], 'acertados: cuota 1,8 > 1,2 > sin cuota');
  assert.deepEqual(ids.slice(-2), ['f1', 'f2'], 'fallados al final, también de mayor a menor cuota (1,9 > 1,3)');
  assert.deepEqual(ids.slice(3, 5).sort(), ['n', 'push'], 'sin resultado entre unos y otros');
  const sinJugar = [{ id: 'a', r: null, c: 1.5, p: .6 }, { id: 'b', r: null, c: 2, p: .9 }];
  assert.equal(ordenLiquidado(sinJugar, o), sinJugar, 'sin nada liquidado se deja el orden recibido');
  assert.equal(hayLiquidado(sinJugar, o.resultado), false);
  assert.equal(hayLiquidado(lista, o.resultado), true);
  assert.equal(lista[0].id, 'f1', 'no muta la lista original');
});
