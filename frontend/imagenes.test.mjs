import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync, existsSync, statSync} from 'node:fs';
import {loadImages, nbaCode, featuredModelMarket} from './sports-data.js';
import {createSportWindow} from './sports-window.js';
import {imageMarkup, playerPhoto, installImageFallback} from './sport-images.js';

const base=new URL('./imagenes/',import.meta.url);
const manifest=JSON.parse(readFileSync(new URL('manifiesto.json',base),'utf8'));

test('el manifiesto apunta a archivos reales, ligeros y con formato de imagen',()=>{
 assert.equal(Object.keys(manifest.nba).length,30);
 assert.ok(Object.keys(manifest.tenis).length>100);
 for(const carpeta of ['nba','tenis'])for(const [clave,e] of Object.entries(manifest[carpeta])){
  const ruta=new URL(`${carpeta}/${e.f}`,base);
  assert.ok(existsSync(ruta),`${carpeta}/${e.f}`);
  assert.ok(statSync(ruta).size<=300000,`${clave} pesa demasiado`);
  const bytes=readFileSync(ruta);
  assert.ok(bytes.subarray(0,4).equals(Buffer.from([0x89,0x50,0x4e,0x47]))||(bytes[0]===0xff&&bytes[1]===0xd8),`${clave} no es PNG/JPEG`);
  assert.match(e.f,/^[a-z0-9][a-z0-9-]*\.(png|jpg)$/i);
 }
});

test('cada foto de tenis trae autor y fuente; las del proveedor no se atribuyen una licencia CC',()=>{
 for(const [clave,e] of Object.entries(manifest.tenis)){
  assert.ok(e.a&&e.a.trim(),`${clave}: sin autor`);
  if(e.fuente==='API-Tennis'){
   assert.equal(e.l,'Imagen del proveedor');
   assert.match(e.p,/^https:\/\/api\.api-tennis\.com\/logo-tennis\/\d+_[a-z0-9-]+\.jpg$/);
  }else{
   assert.match(e.l,/^(CC BY|CC0|Public domain|Dominio)/i,`${clave}: licencia ${e.l}`);
   assert.match(e.p,/^https:\/\/commons\.wikimedia\.org\//,`${clave}: sin enlace a Commons`);
  }
  assert.equal(clave,clave.toLowerCase());
 }
});

test('la página de créditos nombra a cada autor y las dos fuentes',()=>{
 const html=readFileSync(new URL('creditos.html',base),'utf8');
 assert.ok(html.includes('Wikimedia Commons')&&html.includes('TheSportsDB'));
 assert.ok(!html.includes('<script'));
 for(const e of Object.values(manifest.tenis))assert.ok(html.includes(e.n.replace(/&/g,'&amp;')),`falta ${e.n}`);
});

test('loadImages devuelve el manifiesto y, si falla, un estado de error sin romper la vista',async()=>{
 const ok=await loadImages(async()=>({ok:true,json:async()=>manifest}));
 assert.equal(ok.status,'ready');assert.equal(Object.keys(ok.nba).length,30);
 const caido=await loadImages(async()=>{throw new Error('red');});
 assert.deepEqual(caido,{status:'error',nba:{},tenis:{}});
 const raro=await loadImages(async()=>({ok:true,json:async()=>({nba:1})}));
 assert.equal(raro.status,'error');
});

test('las vistas solo piden imágenes al propio servidor',()=>{
 const views=readFileSync(new URL('./ergonomic-views.js',import.meta.url),'utf8');
 assert.ok(!/https?:\/\/[^'"`\s]*\.(png|jpe?g|webp|svg)/i.test(views));
 assert.ok(views.includes('/web/imagenes/'));
});

test('un manifiesto nulo o con listas se convierte en error recuperable',async()=>{
 for(const invalid of [{nba:null,tenis:{}},{nba:{},tenis:null},{nba:[],tenis:{}},{nba:{},tenis:[]}]){
  assert.equal((await loadImages(async()=>({ok:true,json:async()=>invalid}))).status,'error');
 }
});

function sportView(sport,home,away,index=manifest){
 const start='2026-10-28T16:00:00Z';
 const esc=value=>String(value).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'})[c]);
 const event={id:'image-test',sport,home,away,start,league:sport,status:'scheduled',seal:'test',sealed_at:start,
  markets:[{id:'winner',market:'winner',label:'Ganador',selection:home,probability:.7}]};
 return createSportWindow({
  state:{sport,winDay:0,winPane:'pron',winSportTab:'resumen',winAll:false},esc,
  badge:esc,fmtPct:p=>String(p*100),fmtOdds:String,realDate:String,realTime:String,dateFmt:String,
  addDays:()=>new Date(start),localDay:d=>new Date(d).toISOString().slice(0,10),dayLabel:()=> 'Hoy',
  ensureSport:()=>({status:'ready',events:[event]}),ensureImages:()=>index,nbaCode,featuredModelMarket,
  ensureTennisStats:()=>({status:'loading'}),ensureNbaStats:()=>({status:'loading'})
 }).view();
}

test('tenis muestra fotos y sus créditos en la lista y el encabezado, también con acentos',()=>{
 const html=sportView('tenis','Jakub Menšík','Adrian Mannarino');
 for(const name of ['jakub mensik','adrian mannarino']){
  const photo=manifest.tenis[name];
  assert.equal(html.split(`src="/web/imagenes/tenis/${photo.f}"`).length-1,2);
  assert.ok(html.includes(photo.l));
 }
 assert.match(html,/win-crest is-photo/);
});

test('NBA mantiene los logos en la lista y en el encabezado',()=>{
 const html=sportView('nba','Boston Celtics','Brooklyn Nets');
 for(const code of ['BOS','BKN'])assert.equal(html.split(`src="/web/imagenes/nba/${manifest.nba[code].f}"`).length-1,2);
});

test('sin foto o con un nombre de archivo inválido usa iniciales y no solicita rutas arbitrarias',()=>{
 const html=sportView('tenis','Jugador desconocido','Otro jugador',{nba:{},tenis:{'otro jugador':{f:'../privado.png'}}});
 assert.ok(!html.includes('<img'));
 assert.match(html,/win-crest is-initial/);
});

test('las fotos individuales solo aceptan un deporte conocido y un id numérico de jugador',()=>{
 assert.equal(playerPhoto('nba',2544),'/web/imagenes/jugadores/nba/2544.png');
 assert.equal(playerPhoto('futbol','874'),'/web/imagenes/jugadores/futbol/874.png');
 for(const [sport,id] of [['nba',1610612738],['nba','../2544'],['nba',0],['tenis',42]])assert.equal(playerPhoto(sport,id),null);
 const esc=s=>s.replaceAll('"','&quot;');
 assert.ok(!imageMarkup('https://evil.example/photo.png','Jugador',esc).includes('<img'));
 assert.ok(!imageMarkup('/web/../privado.png','Jugador',esc).includes('<img'));
 assert.match(imageMarkup(playerPhoto('nba',2544),'Jugador "X"',esc),/data-image-name="Jugador &quot;X&quot;"/);
});

test('una descarga fallida se sustituye por una marca accesible sin repetir peticiones',()=>{
 let handler, replacement;
 installImageFallback({addEventListener:(type,fn,capture)=>{assert.equal(type,'error');assert.equal(capture,true);handler=fn;}});
 const span={setAttribute:(key,value)=>{span[key]=value;}};
 handler({target:{tagName:'IMG',matches:()=>true,dataset:{imageName:'Jayson Tatum'},className:'player-photo',ownerDocument:{createElement:()=>span},replaceWith:value=>{replacement=value;}}});
 assert.equal(replacement.textContent,'JT');
 assert.equal(replacement['aria-label'],'Imagen no disponible: Jayson Tatum');
 assert.ok(!replacement.src);
});
