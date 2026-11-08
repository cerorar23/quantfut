import test from 'node:test';
import assert from 'node:assert/strict';

// DOM mínimo: una jarra de cookies, localStorage y los nodos que toca meta-pixel.js.
let seq = 0;
function entorno({ gpc = false, dnt = null, cookies = {}, legacy = null, https = true } = {}) {
  const jar = new Map(Object.entries(cookies));
  const scripts = [];
  const nodes = new Map();
  const doc = {
    get cookie() { return [...jar].map(([k, v]) => `${k}=${v}`).join('; '); },
    set cookie(line) {
      const [pair, ...attrs] = String(line).split(';').map(part => part.trim());
      const [name, value] = [pair.slice(0, pair.indexOf('=')), pair.slice(pair.indexOf('=') + 1)];
      if (attrs.some(a => /^max-age=0$/i.test(a))) jar.delete(name); else jar.set(name, value);
      doc.lastCookieLine = line;
    },
    getElementById: id => nodes.get(id) || null,
    createElement: tag => {
      const el = { tag, attrs: {}, children: [], listeners: {}, innerHTML: '', id: '',
        setAttribute(k, v) { this.attrs[k] = v; },
        addEventListener(type, fn) { this.listeners[type] = fn; },
        remove() { nodes.delete(this.id); } };
      return el;
    },
    head: { append: el => scripts.push(el) },
    body: { append: el => nodes.set(el.id, el) },
  };
  const store = new Map(legacy ? [['qf_ads_consent', legacy]] : []);
  const fbqCalls = [];
  Object.assign(globalThis, {
    document: doc,
    window: globalThis,
    location: { protocol: https ? 'https:' : 'http:', hostname: 'pronosticosdeportivos.pro', search: '' },
    localStorage: { getItem: k => store.get(k) ?? null, setItem: (k, v) => store.set(k, v) },
  });
  Object.defineProperty(globalThis, 'navigator', {
    configurable: true, value: { globalPrivacyControl: gpc, doNotTrack: dnt } });
  delete globalThis.fbq; delete globalThis._fbq;
  return { jar, scripts, nodes, store, fbqCalls, doc };
}

const cargar = () => import(`./meta-pixel.js?caso=${seq += 1}`);
const pulsar = (env, choice) => env.nodes.get('qf-ads-notice').listeners.click({ target: { dataset: { ads: choice } } });
const llamadasFbq = () => (globalThis.fbq?.queue || []).map(args => [...args]);

test('opt-in sin respuesta: no carga el Pixel, muestra el aviso y no manda PageView', async () => {
  const env = entorno();
  const px = await cargar();
  assert.equal(px.init('123', null, 'opt-in'), false);
  assert.equal(env.scripts.length, 0);
  assert.equal(globalThis.fbq, undefined);
  assert.ok(env.nodes.has('qf-ads-notice'));
  assert.match(env.nodes.get('qf-ads-notice').innerHTML, /Sin tu permiso no se activa nada/);
});

test('sin régimen (API antigua) se asume el estricto', async () => {
  const env = entorno();
  const px = await cargar();
  assert.equal(px.init('123', null), false);
  assert.equal(env.scripts.length, 0);
});

test('opt-in: «Aceptar» guarda la cookie para el servidor y carga el Pixel en ese momento', async () => {
  const env = entorno();
  const px = await cargar();
  px.init('123', { account: { email: 'A@B.co', display_name: 'Ana Pérez' } }, 'opt-in');
  pulsar(env, 'si');
  assert.equal(env.jar.get('qf_ads'), 'si');
  assert.match(env.doc.lastCookieLine, /Max-Age=31536000; Path=\/; SameSite=Lax; Secure/);
  assert.equal(env.scripts.length, 1);
  assert.equal(env.scripts[0].src, 'https://connect.facebook.net/en_US/fbevents.js');
  const calls = llamadasFbq();
  assert.deepEqual(calls[0].slice(0, 2), ['init', '123']);
  assert.equal(calls[0][2].em, 'a@b.co');
  assert.deepEqual(calls[1], ['track', 'PageView']);
  assert.equal(env.nodes.has('qf-ads-notice'), false);
});

test('opt-in: «Rechazar» no carga nada, deja el «no» en la cookie y retira el aviso', async () => {
  const env = entorno();
  const px = await cargar();
  px.init('123', null, 'opt-in');
  pulsar(env, 'no');
  assert.equal(env.jar.get('qf_ads'), 'no');
  assert.equal(env.scripts.length, 0);
  assert.equal(env.nodes.has('qf-ads-notice'), false);
  assert.equal(px.consentGranted(), false);
});

test('opt-in con «si» ya guardado: carga al entrar y no vuelve a preguntar', async () => {
  const env = entorno({ cookies: { qf_ads: 'si' } });
  const px = await cargar();
  assert.equal(px.init('123', null, 'opt-in'), true);
  assert.equal(env.scripts.length, 1);
  assert.equal(env.nodes.has('qf-ads-notice'), false);
});

test('opt-out sin respuesta: mide (decisión del 15-oct) y ofrece rechazar', async () => {
  const env = entorno();
  const px = await cargar();
  assert.equal(px.init('123', null, 'opt-out'), true);
  assert.equal(env.scripts.length, 1);
  assert.match(env.nodes.get('qf-ads-notice').innerHTML, /Puedes rechazarlo cuando quieras/);
});

test('opt-out: «Rechazar» revoca, borra _fbp/_fbc y track() deja de enviar', async () => {
  const env = entorno({ cookies: { _fbp: 'fb.1.1.2', _fbc: 'fb.1.1.AbC' } });
  const px = await cargar();
  px.init('123', null, 'opt-out');
  pulsar(env, 'no');
  assert.equal(env.jar.get('qf_ads'), 'no');
  assert.equal(env.jar.has('_fbp'), false);
  assert.equal(env.jar.has('_fbc'), false);
  const antes = llamadasFbq().length;
  px.track('Purchase', { value: 1 }, 'purchase:1');
  assert.equal(llamadasFbq().length, antes);
  assert.ok(llamadasFbq().some(call => call[0] === 'consent' && call[1] === 'revoke'));
});

test('un «no» guardado gana en cualquier régimen', async () => {
  for (const regimen of ['opt-in', 'opt-out']) {
    const env = entorno({ cookies: { qf_ads: 'no' } });
    const px = await cargar();
    assert.equal(px.init('123', null, regimen), false);
    assert.equal(env.scripts.length, 0);
    assert.equal(env.nodes.has('qf-ads-notice'), false);
  }
});

test('la elección anterior en localStorage se sigue respetando', async () => {
  const env = entorno({ legacy: 'no' });
  const px = await cargar();
  assert.equal(px.init('123', null, 'opt-out'), false);
  assert.equal(env.scripts.length, 0);
});

test('Global Privacy Control o Do Not Track cortan la medición aunque la cookie diga «si»', async () => {
  for (const opciones of [{ gpc: true }, { dnt: '1' }]) {
    const env = entorno({ ...opciones, cookies: { qf_ads: 'si' } });
    const px = await cargar();
    assert.equal(px.init('123', null, 'opt-out'), false);
    assert.equal(env.scripts.length, 0);
    assert.equal(px.consentGranted(), false);
  }
});

test('browserIds no entrega fbp/fbc sin consentimiento y sí con él', async () => {
  let env = entorno({ cookies: { _fbp: 'fb.1.1.2', _fbc: 'fb.1.1.AbC' } });
  let px = await cargar();
  px.init('123', null, 'opt-in');
  assert.deepEqual(px.browserIds(), { fbp: null, fbc: null });
  env = entorno({ cookies: { qf_ads: 'si', _fbp: 'fb.1.1.2', _fbc: 'fb.1.1.AbC' } });
  px = await cargar();
  px.init('123', null, 'opt-in');
  assert.deepEqual(px.browserIds(), { fbp: 'fb.1.1.2', fbc: 'fb.1.1.AbC' });
});

test('openPreferences vuelve a mostrar el aviso aunque ya se haya respondido', async () => {
  const env = entorno({ cookies: { qf_ads: 'si' } });
  const px = await cargar();
  px.init('123', null, 'opt-in');
  assert.equal(env.nodes.has('qf-ads-notice'), false);
  px.openPreferences();
  assert.ok(env.nodes.has('qf-ads-notice'));
});

test('sin Pixel configurado no se hace nada', async () => {
  const env = entorno();
  const px = await cargar();
  assert.equal(px.init(null, null, 'opt-out'), false);
  assert.equal(env.nodes.size, 0);
});

// --- «Preferencias de medición» del pie: caminos que solo existen al poder reabrir el aviso ---------------------

test('rechazar y luego aceptar desde preferencias reactiva el Pixel ya cargado, sin recargar', async () => {
  const env = entorno();
  const px = await cargar();
  px.init('123', null, 'opt-out');                      // opt-out: carga el Pixel y ofrece rechazar
  pulsar(env, 'no');
  assert.ok(llamadasFbq().some(call => call[0] === 'consent' && call[1] === 'revoke'));
  px.openPreferences();
  assert.ok(env.nodes.has('qf-ads-notice'), 'el aviso se vuelve a mostrar');
  pulsar(env, 'si');
  assert.equal(env.jar.get('qf_ads'), 'si');
  assert.ok(llamadasFbq().some(call => call[0] === 'consent' && call[1] === 'grant'), 'sin «grant» Meta seguiría revocado');
  const antes = llamadasFbq().length;
  px.track('Purchase', { value: 1 }, 'purchase:1');
  assert.equal(llamadasFbq().length, antes + 1, 'y los eventos vuelven a salir');
});

test('quien rechazó al cargar y acepta después desde preferencias activa el Pixel en ese momento', async () => {
  const env = entorno({ cookies: { qf_ads: 'no' } });
  const px = await cargar();
  assert.equal(px.init('123', null, 'opt-out'), false);
  assert.equal(env.scripts.length, 0);
  px.openPreferences();
  pulsar(env, 'si');
  assert.equal(env.jar.get('qf_ads'), 'si');
  assert.equal(env.scripts.length, 1);
  assert.deepEqual(llamadasFbq().find(call => call[0] === 'track'), ['track', 'PageView']);
});

test('con una señal de privacidad del navegador, preferencias no ofrece aceptar y no carga nada', async () => {
  const env = entorno({ gpc: true });
  const px = await cargar();
  assert.equal(px.init('123', null, 'opt-out'), false);
  px.openPreferences();
  const aviso = env.nodes.get('qf-ads-notice');
  assert.match(aviso.innerHTML, /señal de privacidad/);
  assert.ok(!aviso.innerHTML.includes('data-ads="si"'), 'no se ofrece una elección que no se respetaría');
  pulsar(env, 'cerrar');
  assert.equal(env.nodes.has('qf-ads-notice'), false);
  assert.equal(env.jar.has('qf_ads'), false, '«Entendido» no guarda ninguna elección');
  px.decide('si');                                       // aunque algo llame a decide('si') directamente
  assert.equal(env.scripts.length, 0);
  assert.equal(px.consentGranted(), false);
});
