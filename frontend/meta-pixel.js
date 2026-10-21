// Meta Pixel de la web. El servidor envía los mismos eventos por la Conversions API; Meta deduplica por
// event_name + eventID. Coincidencia avanzada manual: datos en claro en `fbq('init', id, {...})` (el Pixel los
// cifra), solo cuando hay sesión. No carga nada si no hay Pixel configurado o el navegador pide privacidad (GPC/DNT).
let pixelId = null;
let ready = false;

const cookie = name => document.cookie.match(new RegExp(`(?:^|;\\s*)${name}=([^;]*)`))?.[1] || null;

/** fbp/fbc para el servidor (EMQ). _fbc puede no existir aún: se arma con el fbclid de la URL, como indica Meta. */
export function browserIds() {
  let fbc = cookie('_fbc');
  if (!fbc) {
    const clickId = new URLSearchParams(location.search).get('fbclid');
    if (clickId) fbc = `fb.1.${Date.now()}.${clickId}`;
  }
  return { fbp: cookie('_fbp'), fbc };
}

const CONSENT_KEY = 'qf_ads_consent';
const stored = () => { try { return localStorage.getItem(CONSENT_KEY); } catch { return null; } };
const remember = value => { try { localStorage.setItem(CONSENT_KEY, value); } catch { /* sin almacenamiento */ } };
// Decisión del titular (15-oct): la medición está activa salvo que la persona la rechace.
const blocked = () => navigator.globalPrivacyControl === true || navigator.doNotTrack === '1' || stored() === 'no';

/** Aviso de medición con «Rechazar»; se muestra una sola vez por navegador. */
function showNotice() {
  if (stored() || document.getElementById('qf-ads-notice')) return;
  const bar = document.createElement('div');
  bar.id = 'qf-ads-notice';
  bar.setAttribute('role', 'region');
  bar.setAttribute('aria-label', 'Aviso de medición publicitaria');
  bar.innerHTML = '<p>Usamos cookies y el Pixel de Meta para medir nuestros anuncios. Puedes rechazarlo cuando quieras. <a href="/legal/privacidad" target="_blank" rel="noopener">Privacidad</a></p>'
    + '<div><button type="button" data-ads="no">Rechazar</button><button type="button" data-ads="si">Aceptar</button></div>';
  bar.addEventListener('click', event => {
    const choice = event.target?.dataset?.ads;
    if (!choice) return;
    remember(choice);
    if (choice === 'no') { try { window.fbq?.('consent', 'revoke'); } catch { /* sin Pixel */ } }
    bar.remove();
  });
  document.body.append(bar);
}

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

export function init(id, session) {
  if (!id || blocked()) return false;
  try {
    loadSdk();
    window.fbq('init', id, matchingData(session));
    if (!ready) window.fbq('track', 'PageView');
    pixelId = id; ready = true;
    showNotice();
  } catch { return false; }
  return true;
}

/** Vuelve a inicializar con los datos de la cuenta al iniciar sesión (Meta lo admite). */
export function identify(session) {
  if (pixelId && ready) { try { window.fbq('init', pixelId, matchingData(session)); } catch { /* sin Pixel */ } }
}

export function track(event, params = {}, eventID) {
  if (!ready) return;
  try { window.fbq('track', event, params, eventID ? { eventID } : undefined); } catch { /* el Pixel nunca rompe la página */ }
}
