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
