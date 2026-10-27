import test from 'node:test';
import assert from 'node:assert/strict';
import {nbaEvents,tennisEvents,loadSport,loadResults} from './sports-data.js';
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
 const calls=[];const fetcher=async path=>{calls.push(path);return{ok:true,json:async()=>path.includes('/nba/')?nba():{state:'unavailable',events:[]}};};
 assert.equal((await loadSport('nba',fetcher)).status,'ready');assert.equal((await loadSport('tenis',fetcher)).status,'error');assert.deepEqual(calls,['/nba/api/data','/web/deportes/tenis']);assert.equal((await loadSport('nba',async()=>({ok:false}))).events.length,0);
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

test('el destacado de NBA y tenis usa la cuota del modelo (1 ÷ prob.) de 1,40 a 1,80 y la mayor probabilidad', () => {
  const m = (id, probability) => ({ id, probability });
  assert.equal(featuredModelMarket([m('a', .95), m('b', .70), m('c', .60), m('d', .30)]).id, 'b');
  assert.equal(featuredModelMarket([m('lo', 1 / 1.4), m('hi', 1 / 1.8)]).id, 'lo');          // extremos incluidos
  assert.equal(featuredModelMarket([m('x', .75), m('y', .5)]), null);                           // 1,33 y 2,00 quedan fuera
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
