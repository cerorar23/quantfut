// Cliente de cuentas de la web contra /app/v1 (el mismo backend que la app).
// El refresh vive en una cookie HttpOnly que este código no puede leer; el
// token de acceso, solo en memoria: nada se guarda en el almacenamiento del navegador.
// La cabecera X-QF-Client pide al servidor ese modo cookie.

const BASE = '/app/v1';
let access = null;
let refreshing = null;
let fetchImpl = (...args) => fetch(...args);

export class ApiError extends Error {
  constructor(status, code, message) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

export function _setFetchForTests(fn) { fetchImpl = fn; access = null; refreshing = null; }
export const hasAccess = () => access !== null;

async function call(path, { method = 'GET', body, auth = false } = {}) {
  const headers = { 'X-QF-Client': 'web' };
  if (body !== undefined) headers['Content-Type'] = 'application/json';
  if (auth && access) headers.Authorization = `Bearer ${access}`;
  let response;
  try {
    response = await fetchImpl(BASE + path, {
      method, headers, credentials: 'same-origin', cache: 'no-store',
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch {
    throw new ApiError(0, 'sin_conexion', 'No hay conexión con el servidor. Inténtalo de nuevo.');
  }
  if (response.status === 204) return null;
  let data = null;
  try { data = await response.json(); } catch { /* respuesta sin JSON */ }
  if (!response.ok) {
    const detail = data && typeof data.detail === 'object' ? data.detail : {};
    throw new ApiError(response.status, detail.code || 'error',
      detail.message || (response.status === 429 ? 'Demasiados intentos, espera un momento.' : 'No se pudo completar la solicitud.'));
  }
  return data;
}

// Una sola renovación en vuelo: varias peticiones que caducan a la vez esperan la misma.
function refresh() {
  refreshing ??= call('/auth/refresh', { method: 'POST' })
    .then(tokens => { access = tokens.access_token; })
    .catch(error => { access = null; throw error; })
    .finally(() => { refreshing = null; });
  return refreshing;
}

async function authed(path, options = {}) {
  if (!access) await refresh();
  try {
    return await call(path, { ...options, auth: true });
  } catch (error) {
    if (error.status !== 401) throw error;
    await refresh();
    return call(path, { ...options, auth: true });
  }
}

export const me = () => authed('/me');

// Cookie indicadora del servidor (sin secreto): evita un refresh 401 por
// cada visitante que nunca ha iniciado sesión.
const hasSessionHint = () => typeof document !== 'undefined' && /(?:^|;\s*)qf_hay_sesion=1(?:;|$)/.test(document.cookie);

/** Al cargar la página: recupera la sesión desde la cookie, si la hay. */
export async function restore({ force = false } = {}) {
  if (!force && !hasSessionHint()) return null;
  try { await refresh(); return await me(); } catch { return null; }
}

export async function login(email, password) {
  const tokens = await call('/auth/login', { method: 'POST', body: { email, password } });
  access = tokens.access_token;
  return me();
}

export async function register(email, password, displayName) {
  const tokens = await call('/auth/register', {
    method: 'POST', body: { email, password, display_name: displayName || null },
  });
  access = tokens.access_token;
  return me();
}

export async function logout() {
  try { await authed('/auth/logout', { method: 'POST' }); } finally { access = null; }
}

export const forgotPassword = email => call('/auth/password/forgot', { method: 'POST', body: { email } });
export const resendVerification = () => authed('/auth/verify/resend', { method: 'POST' });
export const plans = () => call('/plans');
