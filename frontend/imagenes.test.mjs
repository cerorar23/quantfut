import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync, existsSync, statSync} from 'node:fs';
import {loadImages} from './sports-data.js';

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

test('cada foto de tenis trae autor, licencia Creative Commons y enlace a su ficha',()=>{
 for(const [clave,e] of Object.entries(manifest.tenis)){
  assert.ok(e.a&&e.a.trim(),`${clave}: sin autor`);
  assert.match(e.l,/^(CC BY|CC0|Public domain|Dominio)/i,`${clave}: licencia ${e.l}`);
  assert.match(e.p,/^https:\/\/commons\.wikimedia\.org\//,`${clave}: sin enlace a Commons`);
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
