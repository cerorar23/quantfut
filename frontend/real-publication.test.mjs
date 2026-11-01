import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { loadForecastHome, loadForecastMatch, forecastGames, publicForecasts, modelProbabilities, localDay } from './fichas-data.js';
import { createRealViews } from './real-views.js';

const day = new Date(2026,9,27,12);
const game = {match_id:'it.serie_a:2627:sassuolo-lazio:20261027',kickoff_utc:new Date(2026,9,27,17).toISOString(),estado:'scheduled',liga:{id:'it.serie_a',nombre:'Serie A'},local:{nombre:'Sassuolo'},visitante:{nombre:'Lazio'},probabilities:{home:.3,draw:.28,away:.42}};
const pick = {match_id:game.match_id,local:'Sassuolo',visitante:'Lazio',league_id:'it.serie_a',kickoff_utc:game.kickoff_utc,prob:.74,ref_price:1.29,ref_book:'book',texto:'Sin empate',chain_sha256:'abc',pick_key:'sealed-1',batch_date:'2026-10-27',locked:false};
const home = {agenda:[game],alta_probabilidad:{estado:'activa',proximos:[pick],vip:[]}};
const esc = value=>String(value??'').replace(/[<>&"]/g,c=>({'<':'&lt;','>':'&gt;','&':'&amp;','"':'&quot;'}[c]));
const view = (entry,match={status:'ready',data:{ficha:{partido:{},local:game.local,visitante:game.visitante,mercados:{filas:[]}},picks:[]}})=>createRealViews({state:{dayOffset:0,homeSearch:'',homeLeague:'Todas',homeStatus:'todos',homeSort:'hora',realMatch:game.match_id},esc,badge:(x)=>x,ensureHome:()=>entry,ensureMatch:()=>match,addDays:()=>day,localDay,dayLabel:()=> 'Hoy',timeLabel:()=>'',realDate:()=> '27 oct',realTime:()=> '17:00',fmtOdds:x=>x==null?'—':String(x),fmtPct:x=>String(x*100)+'%',liveEvidence:()=> 'EVIDENCIA_REAL',livePicks:()=> 'PICKS_DE_VALOR',dayRail:()=>''});

test('agenda and forecasts use the existing mobile public contract and timezone',async()=>{
 let requested;
 const entry=await loadForecastHome(day,async(path,options)=>{requested={path,options};return {ok:true,json:async()=>home};});
 assert.ok(requested.path.startsWith('/mobile/v1/home?fecha=2026-10-27&tz='));
 assert.equal(entry.status,'ready');
 assert.ok(requested.options.signal);
 assert.deepEqual(forecastGames(home,day),[game]);
 assert.equal(forecastGames(home,new Date(2026,9,28)).length,0);
});
test('format errors and unavailable sources never become invented forecasts',async()=>{
 assert.equal((await loadForecastHome(day,async()=>({ok:false}))).status,'error');
 assert.equal((await loadForecastHome(day,async()=>({ok:true,json:async()=>({agenda:[]})}))).status,'error');
 const empty=await loadForecastHome(day,async()=>({ok:true,json:async()=>({agenda:[],alta_probabilidad:{proximos:[],vip:[]}})}));
 assert.equal(empty.status,'ready');
 assert.deepEqual(publicForecasts(empty.data),[]);
 assert.ok(view({status:'error'}).home().toLowerCase().includes('no se pudieron consultar'));
});
test('only server-authorized and sealed predictions are displayed',()=>{
 assert.deepEqual(publicForecasts(home),[pick]);
 for(const changed of [{locked:true},{prob:NaN},{prob:1.1},{chain_sha256:null},{pick_key:null}]) assert.equal(publicForecasts({...home,alta_probabilidad:{proximos:[{...pick,...changed}]}}).length,0);
 const html=view({status:'ready',data:home}).home();
 assert.ok(html.includes('Sassuolo'));
 assert.ok(html.includes('Sin empate'));
 assert.ok(html.includes('1.29'));
 assert.ok(!html.includes('Puerto Norte'));
});
test('model probabilities are validated rather than filled with defaults',()=>{
 assert.deepEqual(modelProbabilities(game),game.probabilities);
 for(const p of [null,{home:.5,draw:.5,away:.5},{home:.5,draw:null,away:.5},{home:NaN,draw:.5,away:.5}]) assert.equal(modelProbabilities({...game,probabilities:p}),null);
});
test('locked markets never display payload prices or selections',()=>{
 const match={status:'ready',data:{ficha:{partido:{},local:game.local,visitante:game.visitante,mercados:{filas:[{locked:true,grupo:'GOLES',seleccion:'DO_NOT_SHOW',prob:.9,cuota:9.99}]}},picks:[]}};
 const html=view({status:'ready',data:home},match).markets();
 assert.ok(html.includes('Contenido reservado'));
 assert.ok(!html.includes('DO_NOT_SHOW'));
 assert.ok(!html.includes('9.99'));
});
test('match identity is encoded and source strings are escaped',async()=>{
 let requested;
 await loadForecastMatch(game.match_id,async path=>{requested=path;return {ok:true,json:async()=>({ficha:{partido:{},local:game.local,visitante:game.visitante},picks:[]})};});
 assert.ok(requested.includes('it.serie_a%3A2627'));
 const html=view({status:'ready',data:{...home,agenda:[{...game,liga:{id:'real',nombre:'<script>bad</script>'}}]}}).home();
 assert.ok(html.includes('&lt;script&gt;'));
 assert.ok(!html.includes('<script>bad'));
});
test('production boot has no simulated catalog and maps all old data views to real sources',()=>{
 const app=readFileSync(new URL('./app.js',import.meta.url),'utf8');
 for(const name of ['Puerto Norte','Estrella Azul','function seeded','function buildFixture','qf-101','DEMO + DATOS PÚBLICOS']) assert.ok(!app.includes(name));
 for(const route of ['inicio: realViews.home','mercados: windowView','picks: realViews.picks','historial: realViews.history']) assert.ok(app.includes(route));
 assert.ok(app.includes('applyCybercoreTheme(app)'));
});
