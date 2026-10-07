import test from 'node:test';
import assert from 'node:assert/strict';
import * as cuenta from './cuenta-api.js';

const json = (status, body) => ({ status, ok: status >= 200 && status < 300, json: async () => body });
const ME = { account: { account_id: 1, email: 'ana@correo.test' }, plus: false, subscription: null };

function fakeServer(routes) {
  const calls = [];
  cuenta._setFetchForTests(async (url, options) => {
    calls.push({ url, ...options });
    const handler = routes[`${options.method} ${url}`];
    if (!handler) return json(404, { detail: { code: 'no_existe', message: 'No existe' } });
    return handler(options, calls);
  });
  return calls;
}

test('el login pide el modo web y no guarda el refresh en el navegador', async () => {
  const calls = fakeServer({
    'POST /app/v1/auth/login': () => json(200, { access_token: 'acc-1', refresh_token: null }),
    'GET /app/v1/me': () => json(200, ME),
  });
  const me = await cuenta.login('ana@correo.test', 'una-clave-larga');
  assert.equal(me.account.email, 'ana@correo.test');
  assert.equal(calls[0].headers['X-QF-Client'], 'web');
  assert.equal(calls[0].credentials, 'same-origin');
  assert.equal(calls[1].headers.Authorization, 'Bearer acc-1');
});

test('un acceso caducado se renueva una sola vez aunque fallen varias peticiones a la vez', async () => {
  let refreshes = 0;
  let valid = 'a';
  fakeServer({
    'POST /app/v1/auth/login': () => json(200, { access_token: 'a', refresh_token: null }),
    'POST /app/v1/auth/refresh': async () => {
      refreshes += 1;
      await new Promise(resolve => setTimeout(resolve, 10));
      valid = `t${refreshes}`;
      return json(200, { access_token: valid, refresh_token: null });
    },
    'GET /app/v1/me': options => options.headers.Authorization === `Bearer ${valid}`
      ? json(200, ME) : json(401, { detail: { code: 'no_autenticado', message: 'Sesión no válida' } }),
  });
  await cuenta.login('ana@correo.test', 'una-clave-larga');
  valid = 'caducado';
  const results = await Promise.all([cuenta.me(), cuenta.me(), cuenta.me()]);
  assert.deepEqual(results.map(r => r.account.account_id), [1, 1, 1]);
  assert.equal(refreshes, 1);
});

test('sin cookie válida restore devuelve null y no lanza', async () => {
  fakeServer({ 'POST /app/v1/auth/refresh': () => json(401, { detail: { code: 'refresh_invalido', message: 'Sesión no válida' } }) });
  assert.equal(await cuenta.restore({ force: true }), null);
  assert.equal(cuenta.hasAccess(), false);
});

test('sin cookie indicadora restore no llama al servidor', async () => {
  const calls = fakeServer({});
  assert.equal(await cuenta.restore(), null);
  assert.equal(calls.length, 0);
});

test('los errores del servidor llegan con su código y su mensaje', async () => {
  fakeServer({ 'POST /app/v1/auth/register': () => json(409, { detail: { code: 'email_en_uso', message: 'Ya existe una cuenta con ese correo' } }) });
  await assert.rejects(cuenta.register('ana@correo.test', 'una-clave-larga', 'Ana'),
    error => error.code === 'email_en_uso' && error.status === 409 && /Ya existe/.test(error.message));
});

test('sin red el error es legible', async () => {
  cuenta._setFetchForTests(async () => { throw new TypeError('Failed to fetch'); });
  await assert.rejects(cuenta.forgotPassword('ana@correo.test'), error => error.code === 'sin_conexion');
});

test('cerrar sesión olvida el acceso aunque el servidor falle', async () => {
  fakeServer({
    'POST /app/v1/auth/login': () => json(200, { access_token: 'acc', refresh_token: null }),
    'GET /app/v1/me': () => json(200, ME),
    'POST /app/v1/auth/logout': () => json(500, {}),
  });
  await cuenta.login('ana@correo.test', 'una-clave-larga');
  await assert.rejects(cuenta.logout());
  assert.equal(cuenta.hasAccess(), false);
});
