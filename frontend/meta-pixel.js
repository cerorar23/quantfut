// Meta Pixel de la web. El servidor envía los mismos eventos por la Conversions API; Meta deduplica por
// event_name + eventID. Coincidencia avanzada manual: datos en claro en `fbq('init', id, {...})` (el Pixel los
// cifra), solo cuando hay sesión. No carga nada si no hay Pixel configurado o el navegador pide privacidad (GPC/DNT).
//
// Consentimiento (db/104, src/qf/comercial/meta_consent.py): el servidor dice el régimen según el país.
//   · opt-in  (EEE, Reino Unido, Suiza o país desconocido): el Pixel NO se carga hasta pulsar «Aceptar».
//   · opt-out (resto): activo salvo «Rechazar» (decisión del titular, 15-oct).
// La elección vive en la cookie propia `qf_ads` (si | no) para que el servidor también deje de enviar a Meta
// los eventos de registro y compra de quien rechazó; localStorage queda solo como respaldo de lectura.
let pixelId = null;
let ready = false;
let regime = 'opt-out';
let pendingSession = null;

const cookie = name => document.cookie.match(new RegExp(`(?:^|;\\s*)${name}=([^;]*)`))?.[1] || null;

/** fbp/fbc para el servidor (EMQ). _fbc puede no existir aún: se arma con el fbclid de la URL, como indica Meta. */
export function browserIds() {
  if (!consentGranted()) return { fbp: null, fbc: null };
  let fbc = cookie('_fbc');
  if (!fbc) {
    const clickId = new URLSearchParams(location.search).get('fbclid');
    if (clickId) fbc = `fb.1.${Date.now()}.${clickId}`;
  }
  return { fbp: cookie('_fbp'), fbc };
}

const CONSENT_KEY = 'qf_ads_consent';          // clave antigua de localStorage (se sigue leyendo)
const CONSENT_COOKIE = 'qf_ads';
const YEAR = 365 * 24 * 60 * 60;

function stored() {
  const fromCookie = cookie(CONSENT_COOKIE);
  if (fromCookie === 'si' || fromCookie === 'no') return fromCookie;
  try {
    const legacy = localStorage.getItem(CONSENT_KEY);   // elección hecha antes de existir la cookie
    return legacy === 'si' || legacy === 'no' ? legacy : null;
  } catch { return null; }
}

function remember(value) {
  const secure = location.protocol === 'https:' ? '; Secure' : '';
  document.cookie = `${CONSENT_COOKIE}=${value}; Max-Age=${YEAR}; Path=/; SameSite=Lax${secure}`;
  try { localStorage.setItem(CONSENT_KEY, value); } catch { /* sin almacenamiento */ }
}

/** Borra las cookies del Pixel de este sitio al rechazar: no deben sobrevivir a un «no». */
function clearMetaCookies() {
  for (const name of ['_fbp', '_fbc']) {
    document.cookie = `${name}=; Max-Age=0; Path=/`;
    const host = location.hostname.split('.');
    if (host.length > 1) document.cookie = `${name}=; Max-Age=0; Path=/; Domain=.${host.slice(-2).join('.')}`;
  }
}

const privacySignal = () => navigator.globalPrivacyControl === true || navigator.doNotTrack === '1';

/** ¿Se puede medir ya? Señal del navegador o «no» → nunca; en opt-in solo con «si». */
export function consentGranted() {
  if (privacySignal() || stored() === 'no') return false;
  return regime === 'opt-in' ? stored() === 'si' : true;
}

/** Aviso con «Rechazar» y «Aceptar» igual de visibles. En opt-in nada se mide hasta responder. */
export function showNotice(force = false) {
  if (document.getElementById('qf-ads-notice')) return;
  if (!force && (stored() || privacySignal())) return;
  const bar = document.createElement('div');
  bar.id = 'qf-ads-notice';
  bar.setAttribute('role', 'region');
  bar.setAttribute('aria-label', 'Medición publicitaria');
  const text = regime === 'opt-in'
    ? 'Con tu permiso usamos cookies y el Pixel de Meta para medir nuestros anuncios. Sin tu permiso no se activa nada.'
    : 'Usamos cookies y el Pixel de Meta para medir nuestros anuncios. Puedes rechazarlo cuando quieras.';
  bar.innerHTML = `<p>${text} <a href="/legal/privacidad" target="_blank" rel="noopener">Privacidad</a></p>`
    + '<div><button type="button" data-ads="no">Rechazar</button><button type="button" data-ads="si">Aceptar</button></div>';
  bar.addEventListener('click', event => {
    const choice = event.target?.dataset?.ads;
    if (choice !== 'si' && choice !== 'no') return;
    decide(choice);
    bar.remove();
  });
  document.body.append(bar);
}

/** Registra la elección y la aplica al instante: «no» apaga y limpia; «si» carga el Pixel si aún no estaba. */
export function decide(choice) {
  remember(choice);
  if (choice === 'no') {
    try { window.fbq?.('consent', 'revoke'); } catch { /* sin Pixel */ }
    clearMetaCookies();
    return;
  }
  if (!ready && pixelId) start(pixelId, pendingSession);
}

/** Para un enlace «Preferencias de medición» del pie: vuelve a mostrar el aviso. */
export const openPreferences = () => showNotice(true);

function loadSdk() {
  if (window.fbq) return;
  const f = window; const n = f.fbq = function () { n.callMethod ? n.callMethod.apply(n, arguments) : n.queue.push(arguments); };
  if (!f._fbq) f._fbq = n;
  n.push = n; n.loaded = true; n.version = '2.0'; n.queue = [];
  const script = document.createElement('script');
  script.async = true;
  script.src = 'https://connect.facebook.net/en_US/fbevents.js';
  document.head.append(script);
}

const clean = text => String(text || '').normalize('NFC').toLowerCase().replace(/[^\p{L}\p{N}\s]/gu, '').trim();

/** Datos para la coincidencia avanzada a partir de la sesión de la cuenta (em, fn, ln, external_id). */
export function matchingData(session) {
  if (!session?.account) return {};
  const { email, display_name: name } = session.account;
  const [first, ...rest] = clean(name).split(/\s+/).filter(Boolean);
  const data = { em: String(email || '').trim().toLowerCase() };
  if (first) data.fn = first;
  if (rest.length) data.ln = rest.join(' ');
  if (session.meta_external_id) data.external_id = session.meta_external_id;
  return Object.fromEntries(Object.entries(data).filter(([, value]) => value));
}

function start(id, session) {
  try {
    loadSdk();
    window.fbq('init', id, matchingData(session));
    if (!ready) window.fbq('track', 'PageView');
    ready = true;
  } catch { return false; }
  return true;
}

/** `consentRegime` lo manda el servidor en /app/v1/whop/config. Sin dato se asume el régimen estricto. */
export function init(id, session, consentRegime = 'opt-in') {
  if (!id) return false;
  pixelId = id; pendingSession = session; regime = consentRegime === 'opt-out' ? 'opt-out' : 'opt-in';
  if (privacySignal() || stored() === 'no') return false;
  if (!consentGranted()) { showNotice(); return false; }     // opt-in sin respuesta: aviso y nada más
  if (!start(id, session)) return false;
  showNotice();                                                // opt-out: se mide y se ofrece rechazar
  return true;
}

/** Vuelve a inicializar con los datos de la cuenta al iniciar sesión (Meta lo admite). */
export function identify(session) {
  pendingSession = session;
  if (pixelId && ready && consentGranted()) { try { window.fbq('init', pixelId, matchingData(session)); } catch { /* sin Pixel */ } }
}

export function track(event, params = {}, eventID) {
  if (!ready || !consentGranted()) return;
  try { window.fbq('track', event, params, eventID ? { eventID } : undefined); } catch { /* el Pixel nunca rompe la página */ }
}
