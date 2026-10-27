import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createHash} from 'node:crypto';

// Decisión explícita del titular: reorganizar sin cambiar el CSS anterior.
const original={
 'styles.css':'9cebbf1d0f3ee89f32538869c3f5b26a5d4cac94331ab2f6f2c43000bd1cb9c2',
 'future.css':'eff42cf86b57fde81de78a928a7f1f783d743dba83fbdb1af740fbe1042eaf56',
 'membership.css':'57201c52ee5ff92061d9fdd9f9fc1aba8a88e4e78cd7b416bd2e1d8249e73cce',
 'vendor/cybercore/cybercore.min.css':'8c4bc2fc1eb7e80c565e992a3815056787bcf74b5f56f8d7c97b6927f7e74c5c'
};
test('las cuatro hojas CSS son exactamente las anteriores al rediseño',()=>{
 for(const [file,digest] of Object.entries(original)) {
  const css=readFileSync(new URL(file,import.meta.url),'utf8').replace(/\r\n/g,'\n');
  assert.equal(createHash('sha256').update(css).digest('hex'),digest,file);
 }
});
test('el HTML solo carga las hojas originales más la disposición de la ventana única y no introduce estilos inline',()=>{
 const html=readFileSync(new URL('./index.html',import.meta.url),'utf8');
 const sheets=[...html.matchAll(/<link[^>]+rel="stylesheet"[^>]+href="([^"]+)"/g)].map(m=>m[1].replace(/^\.\//,'').split('?')[0]);
 assert.deepEqual(sheets.sort(),[...Object.keys(original),'window.css'].sort());
 assert.ok(!html.includes('<style'));
 const views=readFileSync(new URL('./ergonomic-views.js',import.meta.url),'utf8');
 assert.ok(!views.includes('style='));assert.ok(!views.includes('<style'));
});
test('las tarjetas y los botones del hub usan los componentes visuales anteriores',()=>{
 const views=readFileSync(new URL('./ergonomic-views.js',import.meta.url),'utf8');
 for(const cls of ['live-pick','live-pick-list','live-panel','forecast-hero','forecast-summary','primary-button','text-link','chip'])assert.ok(views.includes(cls));
 for(const cls of ['hub-pick','hub-hero','hub-market-card'])assert.ok(!views.includes(`class="${cls}`));
});

// window.css es solo disposición (cuadrículas, alturas, desplazamiento): ni colores ni fuentes propios,
// y todos sus selectores cuelgan de .win / .is-win, así que no pueden alterar CYBERCORE ni otras vistas.
test('window.css no define colores propios y solo actúa dentro de la ventana única',()=>{
 const css=readFileSync(new URL('./window.css',import.meta.url),'utf8').replace(/\/\*[\s\S]*?\*\//g,'');
 assert.ok(!/#[0-9a-fA-F]{3,8}\b/.test(css),'colores hexadecimales');
 assert.ok(!/\b(rgb|rgba|hsl|hsla)\(/.test(css),'colores rgb/hsl');
 assert.ok(!/font-family\s*:/.test(css),'familias tipográficas propias');
 const selectors=[...css.matchAll(/([^{}]+)\{/g)].map(m=>m[1].trim()).filter(text=>text&&!text.startsWith('@'));
 assert.ok(selectors.length>20);
 for(const group of selectors)for(const selector of group.split(',').map(x=>x.trim())){
  assert.ok(/\.(win|is-win)\b/.test(selector),`${selector} no cuelga de .win`);
 }
});
