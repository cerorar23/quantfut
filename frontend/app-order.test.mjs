import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

// `render()` llama a `syncPublicAuth()`; si sus `let`/`const` se declaran después del primer
// `render()` de nivel superior, el script aborta con ReferenceError y la web queda en "Consultando…".
const source = readFileSync(new URL('./app.js', import.meta.url), 'utf8');
const firstRender = source.search(/^render\(\);/m);

test('el primer render() de arranque existe', () => {
  assert.ok(firstRender > 0);
});

for (const name of ['publicData', 'publicRequest', 'publicAuthKey', 'publicFetch']) {
  test(`${name} se declara antes del primer render()`, () => {
    const at = source.search(new RegExp(`^(let|const) ${name}[ =]`, 'm'));
    assert.ok(at >= 0, `${name} no se declara`);
    assert.ok(at < firstRender, `${name} se declara después del primer render()`);
  });
}

test('el pronóstico destacado de fútbol muestra si acertó o falló, como tenis y NBA', () => {
  const card = source.slice(source.indexOf('function winForecast'), source.indexOf('const rows = ficha.mercados'));
  assert.match(card, /<p class="win-sub">\$\{marketState\(feat\.resultado\)\}<\/p>/);
});
