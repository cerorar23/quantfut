// Planes, cuenta y pedido de la web. Las cuentas son reales (/app/v1, ver
// cuenta-api.js); el pago en línea es el checkout de Whop y solo se ofrece si el servidor lo tiene habilitado.
// Importes, duración y qué planes están a la venta salen del servidor
// (catálogo público de cuenta-api.js, editable en el panel /control): aquí solo viven los textos.
import * as cuenta from './cuenta-api.js?v=b298f1c04385';
import { googleIdToken } from './google-auth.js?v=w2b3c4d5e6f7';
import { init as initPixel, identify, track, browserIds } from './meta-pixel.js?v=m1';
import { mount as mountCheckout, destroy as destroyCheckout } from './whop-checkout.js?v=w1a2b3c4d5e6';

// Un plan nuevo creado en la base sin texto aquí se muestra con su nombre del panel.
const PLAN_COPY = Object.freeze({
  plus_1m: Object.freeze({ name: 'Básico', tag: 'Empieza por un mes' }),
  plus_3m: Object.freeze({ name: 'Estándar', tag: 'Plan destacado' }),
  plus_6m: Object.freeze({ name: 'Premium', tag: 'Mayor ahorro mensual' }),
  club: Object.freeze({ name: 'Club QuantFut', tag: 'Acceso de por vida' }),
});
export const DEFAULT_PLAN = 'plus_3m';

const monthsOf = days => days == null ? null : Math.max(1, Math.round(days / 30));

export function membershipQuote(plans, code) {
  const items = Array.isArray(plans) ? plans : [];
  const plan = items.find(item => item.plan_code === code);
  if (!plan) throw new RangeError('Plan desconocido');
  const months = monthsOf(plan.duration_days);
  // El ahorro se mide contra el plan mensual de la misma lista, si está a la venta.
  const monthly = items.find(item => monthsOf(item.duration_days) === 1 && item.currency === plan.currency);
  return {
    id: plan.plan_code,
    name: PLAN_COPY[plan.plan_code]?.name || plan.name,
    tag: PLAN_COPY[plan.plan_code]?.tag || '',
    months,
    totalCents: plan.price_cents,
    currency: plan.currency,
    monthlyCents: months == null ? null : Math.round(plan.price_cents / months),
    savingsCents: months == null || !monthly ? null : monthly.price_cents * months - plan.price_cents,
    period: months == null ? 'De por vida' : `${months} ${months === 1 ? 'mes' : 'meses'}`,
  };
}

export const membershipMoney = (cents, currency = 'USD') =>
  new Intl.NumberFormat('en-US', { style: 'currency', currency }).format(cents / 100);

export function createMembershipUI({ state, esc, badge, oddsToggle, leagues, fixtures, matchCard, navigate, render, publicStatus }) {
  const plans = () => state.plans?.status === 'ready' ? state.plans.items : [];
  const selectedCode = () => {
    const items = plans();
    if (items.some(plan => plan.plan_code === state.membershipPlan)) return state.membershipPlan;
    return (items.find(plan => plan.plan_code === DEFAULT_PLAN) || items[0])?.plan_code;
  };
  const selected = () => { const code = selectedCode(); return code ? membershipQuote(plans(), code) : null; };
  const money = q => membershipMoney(q.totalCents, q.currency);
  const plansStatus = () => state.plans?.status === 'error'
    ? '<div class="membership-empty" role="alert"><strong>No se pudieron cargar los precios.</strong><p>Comprueba tu conexión e inténtalo de nuevo.</p><button type="button" class="secondary-button" data-membership-action="reload-plans">Reintentar</button></div>'
    : state.plans?.status === 'ready' ? '<div class="membership-empty"><strong>No hay planes a la venta en este momento.</strong></div>'
    : '<p class="membership-note" role="status">Cargando precios…</p>';
  // El servidor dice si el pago en línea está habilitado; los textos no lo dan por hecho en ningún sentido.
  const payOn = () => state.payConfig?.enabled === true;
  const demoNote = () => payOn()
    ? '<p class="membership-note">Precios vigentes. El pago se procesa en línea con Whop y el acceso se activa al confirmarse el cobro.</p>'
    : '<p class="membership-note">Precios vigentes. El pago en línea todavía no está habilitado: no hay cargos ni renovaciones automáticas.</p>';
  const includes = () => '<ul class="membership-includes"><li>Acceso completo al paquete QuantFut Plus</li><li>Pick del día y detalle de mercados</li><li>Cuota registrada, precio justo y mínimo</li><li>Fichas de partido y combinadas</li><li>Historial público y evidencia de publicación</li></ul>';
  const planButton = plan => {
    const q = membershipQuote(plans(), plan.plan_code);
    const active = selectedCode() === q.id;
    const saving = q.savingsCents > 0 ? `Ahorro de ${membershipMoney(q.savingsCents, q.currency)} frente a meses sueltos` : q.months === 1 ? 'Acceso completo por un mes' : 'Mismo paquete, más tiempo';
    return `<button type="button" class="membership-plan ${active ? 'selected' : ''}" data-membership-plan="${esc(q.id)}" aria-pressed="${active}">${q.tag ? `<span class="plan-ribbon">${esc(q.tag)}</span>` : ''}<span class="plan-name">${esc(q.name)}<i class="plan-radio" aria-hidden="true"></i></span><strong class="plan-period">${q.period}</strong><span class="membership-price">${membershipMoney(q.monthlyCents, q.currency)}<small>/ mes</small></span><span class="plan-total">${money(q)} ${esc(q.currency)} por ${q.period.toLowerCase()}</span><span class="plan-saving">${saving}</span><span class="plan-mini-features">✓ Mismo paquete de picks<br>✓ Análisis y herramientas<br>✓ Historial verificable</span><span class="plan-select">${active ? '✓ Seleccionado' : 'Elegir plan'}</span></button>`;
  };
  const lifetimeButton = plan => {
    const q = membershipQuote(plans(), plan.plan_code);
    const active = selectedCode() === q.id;
    return `<button type="button" class="membership-club ${active ? 'selected' : ''}" data-membership-plan="${esc(q.id)}" aria-pressed="${active}"><div><span class="eyebrow">${esc(q.tag)}</span><h2>${esc(q.name)}</h2><p>Pago único y acceso de por vida al paquete.</p></div><div><strong>${money(q)}<small> ${esc(q.currency)}</small></strong><span>Pago único</span><b>${active ? '✓ Seleccionado' : 'Elegir modalidad ↗'}</b></div></button>`;
  };
  const summary = (checkout = false) => {
    const q = selected();
    if (!q) return `<aside class="order-summary" aria-labelledby="order-title"><p class="eyebrow">TU SELECCIÓN</p><h2 id="order-title">Resumen del pedido</h2>${plansStatus()}</aside>`;
    return `<aside class="order-summary" aria-labelledby="order-title"><p class="eyebrow">${checkout ? 'REVISIÓN' : 'TU SELECCIÓN'}</p><h2 id="order-title">Resumen del pedido</h2><div class="order-product"><span class="order-mark" aria-hidden="true">Q.</span><div><strong>QuantFut Plus</strong><small>Paquete de picks y análisis</small></div></div><dl class="order-details"><div><dt>Modalidad</dt><dd>${esc(q.name)}</dd></div><div><dt>Periodo</dt><dd>${q.period}</dd></div><div><dt>Acceso</dt><dd>Completo</dd></div><div><dt>Moneda</dt><dd>${esc(q.currency)}</dd></div></dl><details class="coupon-details" ${state.couponOpen ? 'open' : ''}><summary>¿Tienes un cupón?</summary><form data-membership-form="coupon"><label for="coupon-code">Código promocional</label><div><input id="coupon-code" name="coupon" placeholder="Código de cupón" maxlength="32" autocomplete="off" /><button type="submit" class="secondary-button">Aplicar</button></div>${state.couponMessage ? `<p role="status">${esc(state.couponMessage)}</p>` : ''}</form></details><div class="order-total"><span>Total</span><strong>${money(q)}<small> ${esc(q.currency)}</small></strong></div><p class="order-period">${q.months == null ? 'Pago único · acceso de por vida' : `${q.period} de acceso · equivalente aprox. ${membershipMoney(q.monthlyCents, q.currency)} / mes`}</p>${checkout ? (state.payConfig?.enabled ? '' : '<button type="button" class="primary-button full" disabled>Cobro todavía no habilitado</button>') : `<button type="button" class="primary-button full" data-membership-action="review-order">${state.session ? 'Revisar pedido' : 'Entrar o crear cuenta'} <span aria-hidden="true">↗</span></button>`}<p class="order-footnote">${checkout && state.payConfig?.enabled ? 'El acceso se activa solo cuando se confirma el cobro.' : 'Esta selección no genera una orden ni concede acceso privado.'}</p><button type="button" class="text-link" data-route="paquetes">Ver qué incluye el paquete ↗</button></aside>`;
  };

  function plansView() {
    const periodic = plans().filter(plan => plan.duration_days != null);
    const lifetime = plans().filter(plan => plan.duration_days == null);
    const grid = periodic.length ? `<div class="membership-plan-grid">${periodic.map(planButton).join('')}</div>${lifetime.map(lifetimeButton).join('')}` : plansStatus();
    return `<section class="membership-heading"><p class="eyebrow">SUSCRIPCIONES / QUANTFUT PLUS</p><h1>Elige tu <em>plan.</em></h1><p>Un mismo paquete de picks, análisis y herramientas. Elige cuánto tiempo quieres explorar el servicio.</p><div class="membership-benefits"><span>✓ Acceso completo</span><span>✓ Historial abierto</span><span>✓ Precio y mínimo visibles</span></div>${demoNote()}</section><div class="membership-layout"><div>${grid}<section class="membership-comparison"><p class="eyebrow">EL MISMO CONTENIDO / DISTINTO PERIODO</p><h2>Todos los planes incluyen</h2>${includes()}<p>El historial y los partidos públicos seguirán disponibles sin contratar. Los pronósticos dependen del criterio de publicación: un plan no implica un número garantizado de picks.</p></section></div>${summary()}</div><section class="membership-faq"><h2>Antes de elegir</h2><details><summary>¿Qué cambia entre Básico, Estándar y Premium?</summary><p>El periodo de acceso y su precio. El paquete de contenido es el mismo en todas las modalidades.</p></details><details><summary>¿Puedo contratarlo ahora?</summary><p>${payOn() ? 'Sí. Crea tu cuenta, elige un plan y paga en línea: el acceso se activa en cuanto se confirma el cobro.' : 'Ya puedes crear tu cuenta. El pago en línea todavía no está habilitado: ningún botón realiza cargos.'}</p></details><details><summary>¿Se renueva automáticamente?</summary><p>No. Cada plan es un periodo de acceso: no hay cobros recurrentes.</p></details><details><summary>¿Qué pasa si no hay picks que cumplan el criterio?</summary><p>El sistema debe dejar la lista vacía. La suscripción no cambia el criterio de publicación ni obliga a recomendar un partido.</p></details><details><summary>¿Incluye una garantía de resultados?</summary><p>No. Las probabilidades y los precios no garantizan un resultado.</p></details></section>`;
  }

  function packagesView() {
    const monthly = plans().filter(plan => plan.duration_days != null).map(plan => membershipQuote(plans(), plan.plan_code))
      .sort((a, b) => a.monthlyCents - b.monthlyCents)[0];
    const price = monthly ? `Desde ${membershipMoney(monthly.monthlyCents, monthly.currency)}<small> ${esc(monthly.currency)} / mes equivalente</small>` : '<small>Consulta los planes</small>';
    return `<section class="membership-heading"><p class="eyebrow">EL PRODUCTO / PAQUETES DE PICKS</p><h1>Todo el análisis.<br><em>En un mismo lugar.</em></h1><p>Consulta lo que ofrece el acceso público y lo que incluye QuantFut Plus. La suscripción amplía el acceso; el criterio conserva la última palabra.</p></section><div class="pick-package-grid"><section class="pick-package"><p class="eyebrow">ACCESO ABIERTO</p><h2>Explorador</h2><p class="package-description">Conoce los partidos y comprueba la evidencia antes de elegir un plan.</p><strong class="package-price">Gratis</strong><ul class="membership-includes"><li>Partidos y fichas disponibles</li><li>Picks públicos cuando se publiquen</li><li>Historial, calibración y verificación</li><li>Lectura del estado de publicación</li></ul><button type="button" class="secondary-button full" data-route="picks">Ver picks públicos ↗</button></section><section class="pick-package highlighted"><p class="eyebrow">PAQUETE COMPLETO</p><h2>QuantFut Plus</h2><p class="package-description">Selecciones del criterio con cuota, mínimo y análisis del partido.</p><strong class="package-price">${price}</strong>${includes()}<button type="button" class="primary-button full" data-route="planes">Elegir periodo de acceso ↗</button><p class="membership-note">${payOn() ? 'Pago en línea con Whop.' : 'El pago en línea todavía no está habilitado.'}</p></section></div><section class="package-delivery"><div><p class="eyebrow">ASÍ SE LEERÍA CADA PICK</p><h2>Lo esencial, sin perder el contexto.</h2><p>Partido y selección, hora de publicación, casa, cuota registrada, precio mínimo y estado. Los resultados conservarán su registro, también cuando fallen.</p><button type="button" class="text-link" data-route="mercados" data-home-market-mode="dia">Ver Pick del día de ejemplo ↗</button></div><div class="delivery-card"><span class="badge muted">Ejemplo de estructura · sin pick privado</span><h3>Partido → selección → precio</h3><dl><div><dt>Selección y mercado</dt><dd>Según publicación autorizada</dd></div><div><dt>Cuota y mínimo</dt><dd>Registrados en el mismo instante</dd></div><div><dt>Inicio y cierre</dt><dd>Fechas visibles</dd></div><div><dt>Resultado</dt><dd>Registro posterior al partido</dd></div></dl></div></section><div class="membership-public-status">${publicStatus()}</div>`;
  }

  const fecha = iso => new Date(iso).toLocaleDateString('es', { day: '2-digit', month: 'short', year: 'numeric' });
  const displayName = account => account.display_name || account.email.split('@')[0];
  const notice = (text, error = false) => text ? `<p class="auth-message ${error ? 'error' : ''}" role="${error ? 'alert' : 'status'}">${esc(text)}</p>` : '';

  function authView() {
    const mode = state.authMode;
    const registration = mode === 'register';
    const recovery = mode === 'recovery';
    const title = recovery ? 'Recupera tu acceso.' : registration ? 'Crea tu cuenta.' : 'Bienvenido de nuevo.';
    const intro = recovery ? 'Escribe tu correo y te enviaremos un enlace para elegir una contraseña nueva.' : registration ? 'Es gratis. Te enviaremos un correo para confirmar tu dirección.' : 'Entra con tu correo y tu contraseña.';
    const busy = state.authBusy ? ' disabled aria-busy="true"' : '';
    const password = recovery ? '' : `<label for="auth-password">Contraseña</label><div class="auth-password"><input id="auth-password" name="password" type="password" required ${registration ? 'minlength="10" autocomplete="new-password"' : 'autocomplete="current-password"'} maxlength="128" /><button type="button" data-membership-action="show-password" aria-pressed="false" aria-controls="auth-password">Mostrar</button></div>${registration ? '<p class="auth-small">Al menos 10 caracteres.</p>' : ''}`;
    return `<div class="auth-layout"><section class="auth-story"><p class="eyebrow">TU ESPACIO / QUANTFUT</p><h1>El análisis.<br><em>A tu manera.</em></h1><p>Tus ligas, tus preferencias y el detalle de tu plan, en un mismo espacio.</p><div class="auth-story-facts"><div><span>01</span><strong>Cuotas claras</strong><small>Formato decimal o americano.</small></div><div><span>02</span><strong>Tu selección de ligas</strong><small>Un filtro que ya funciona en la mesa.</small></div><div><span>03</span><strong>Evidencia abierta</strong><small>Consulta el historial antes de elegir.</small></div></div><button type="button" class="text-link" data-route="paquetes">Conocer los paquetes ↗</button></section><section class="auth-card" aria-labelledby="auth-title"><div class="auth-card-mark" aria-hidden="true">Q.</div><div class="auth-tabs" role="group" aria-label="Tipo de acceso"><button type="button" data-auth-mode="login" aria-pressed="${mode === 'login'}">Iniciar sesión</button><button type="button" data-auth-mode="register" aria-pressed="${registration}">Registro</button></div><h2 id="auth-title" tabindex="-1">${title}</h2><p>${intro}</p>${recovery ? '' : `<button type="button" class="google-button" data-membership-action="google-signin"${busy}><svg viewBox="0 0 18 18" width="18" height="18" aria-hidden="true"><path fill="#4285F4" d="M17.64 9.2c0-.64-.06-1.25-.16-1.84H9v3.48h4.84a4.14 4.14 0 0 1-1.8 2.72v2.26h2.92c1.7-1.57 2.68-3.88 2.68-6.62z"/><path fill="#34A853" d="M9 18c2.43 0 4.47-.8 5.96-2.18l-2.92-2.26c-.8.54-1.84.86-3.04.86-2.34 0-4.32-1.58-5.03-3.7H.96v2.33A9 9 0 0 0 9 18z"/><path fill="#FBBC05" d="M3.97 10.72A5.4 5.4 0 0 1 3.68 9c0-.6.1-1.18.29-1.72V4.95H.96A9 9 0 0 0 0 9c0 1.45.35 2.83.96 4.05l3.01-2.33z"/><path fill="#EA4335" d="M9 3.58c1.32 0 2.5.45 3.44 1.35l2.58-2.58C13.46.9 11.43 0 9 0A9 9 0 0 0 .96 4.95l3.01 2.33C4.68 5.16 6.66 3.58 9 3.58z"/></svg> Continuar con Google</button><label class="google-consent"><input type="checkbox" id="google-terms" /><span>Acepto los <a href="/legal/terminos" target="_blank" rel="noopener">términos</a> y la <a href="/legal/privacidad" target="_blank" rel="noopener">política de privacidad</a> (necesario para crear cuenta nueva).</span></label><p class="auth-or"><span>o con tu correo</span></p>`}<form data-membership-form="${mode}" novalidate>${registration ? `<label for="auth-name">Nombre <small>(opcional)</small></label><input id="auth-name" name="name" maxlength="80" autocomplete="nickname" value="${esc(state.authName || '')}" />` : ''}<label for="auth-email">Correo electrónico</label><input id="auth-email" name="email" type="email" required maxlength="254" autocomplete="${registration || recovery ? 'email' : 'username'}" value="${esc(state.authEmail || '')}" />${password}${!registration && !recovery ? '<div class="auth-form-links"><span></span><button type="button" class="text-link" data-auth-mode="recovery">¿Olvidaste tu contraseña?</button></div>' : ''}<button type="submit" class="primary-button full"${busy}>${state.authBusy ? 'Un momento…' : recovery ? 'Enviar enlace' : registration ? 'Crear cuenta' : 'Entrar'} <span aria-hidden="true">↗</span></button>${notice(state.authMessage, state.authError)}</form><div class="auth-footer">${recovery ? '<button type="button" class="text-link" data-auth-mode="login">Volver a iniciar sesión</button>' : `<span>${registration ? '¿Ya tienes cuenta?' : '¿Todavía no tienes cuenta?'}</span><button type="button" class="text-link" data-auth-mode="${registration ? 'login' : 'register'}">${registration ? 'Iniciar sesión' : 'Crear cuenta'}</button>`}</div><p class="auth-privacy">Tu contraseña se guarda cifrada y nunca se muestra. La sesión se mantiene con una cookie segura de este sitio.</p></section></div>`;
  }

  function checkoutView() {
    if (!state.session) { state.authReturn = 'checkout'; return authView(); }
    const { account } = state.session;
    return `<section class="membership-heading compact"><p class="eyebrow">TU PEDIDO</p><h1>Revisa tu <em>selección.</em></h1><p>El plan elegido, su periodo y su total.</p></section><ol class="checkout-steps" aria-label="Etapas de contratación"><li class="done">1 <span>Cuenta</span></li><li class="current">2 <span>Resumen del pedido</span></li><li>3 <span>Pago</span></li></ol><div class="membership-layout checkout-layout"><section class="checkout-details"><div class="checkout-identity"><p class="eyebrow">TU CUENTA</p><h2>${esc(displayName(account))}</h2><p>${esc(account.email)} · ${account.email_verified ? 'correo verificado' : 'correo sin verificar'}</p></div>${paymentSection(selected())}<div class="checkout-actions"><button type="button" class="secondary-button" data-route="planes">Cambiar plan</button><button type="button" class="text-link" data-route="cuenta">Ir a mi cuenta ↗</button></div></section>${summary(true)}</div>`;
  }

  function preferencesPanel() {
    const zone = Intl.DateTimeFormat().resolvedOptions().timeZone;
    return `<section class="account-section"><p class="eyebrow">PREFERENCIAS</p><h2>Tu forma de ver el análisis.</h2><details class="account-accordion" open><summary>Formato de cuotas <span>${state.oddsFormat === 'us' ? 'Americano' : 'Decimal'}</span></summary><div><p>Se guarda en este navegador y se aplica a la web.</p>${oddsToggle()}</div></details><details class="account-accordion" open><summary>Mis ligas <span>${state.followed.length} seleccionadas</span></summary><div><fieldset class="choice-list"><legend>Filtrar la mesa por mis ligas</legend>${leagues.map(league => `<label><input type="checkbox" data-follow="${esc(league)}" ${state.followed.includes(league) ? 'checked' : ''}> ${esc(league)}</label>`).join('')}</fieldset></div></details><details class="account-accordion"><summary>Idioma y zona horaria <span>Español · automático</span></summary><div><p>Idioma: Español</p><p>Zona detectada: ${esc(zone)}</p><small>Los partidos se presentan con la fecha y hora local del navegador. Otros idiomas y ajustes manuales quedan para la integración de cuentas.</small></div></details></section>`;
  }

  function favouritesPanel() {
    const games = fixtures.filter(fx => state.savedDemoMatches.includes(fx.id));
    const available = fixtures.find(fx => !state.savedDemoMatches.includes(fx.id));
    return `<section class="account-section"><p class="eyebrow">FAVORITOS / DATOS DEMO</p><h2>Partidos para volver a mirar.</h2><p>Guardados solo durante esta sesión visual. Los equipos y partidos son ficticios.</p><div class="account-saved-grid">${games.length ? games.map(fx => `<div>${matchCard(fx)}<button type="button" class="text-link" data-remove-demo-match="${fx.id}">Quitar de favoritos</button></div>`).join('') : '<div class="membership-empty"><strong>Todavía no tienes favoritos.</strong><p>Guarda un partido de ejemplo para recorrer esta sección.</p></div>'}</div>${available ? `<button type="button" class="secondary-button" data-save-demo-match="${available.id}">Guardar ${esc(available.home)} vs ${esc(available.away)}</button>` : ''}</section>`;
  }

  function billingPanel() {
    const q = selected();
    const { plus, subscription } = state.session;
    const status = plus
      ? `<span class="badge">Plus activo</span><h3>${esc(subscription.plan_name)}</h3><p>${subscription.ends_at ? `Acceso hasta el ${esc(fecha(subscription.ends_at))}.` : 'Acceso de por vida.'}</p>`
      : `<span class="badge muted">Sin suscripción activa</span><h3>Acceso público</h3><p>${q ? `Selección en revisión: ${esc(q.name)} · ${q.period} · ${money(q)} ${esc(q.currency)}. ` : ''}${payOn() ? 'Puedes pagar en línea al revisar tu pedido.' : 'El pago en línea todavía no está habilitado.'}</p>${q ? '<button type="button" class="primary-button" data-membership-action="review-order">Revisar selección ↗</button>' : '<button type="button" class="primary-button" data-route="planes">Ver planes ↗</button>'}`;
    return `<section class="account-section"><p class="eyebrow">SUSCRIPCIÓN Y PAGOS</p><h2>Tu suscripción y tus movimientos.</h2><div class="account-plan-status">${status}</div><details class="account-accordion" open><summary>Historial de transacciones <span>0 movimientos</span></summary><div class="membership-empty"><strong>Aún no hay transacciones.</strong><p>Los comprobantes aparecerán después de un pago confirmado.</p></div></details><details class="account-accordion"><summary>Renovación y cancelación <span>${plus ? 'Sin renovación automática' : 'Sin plan activo'}</span></summary><div><p>Los planes son periodos de acceso: no hay cobros recurrentes.</p><button type="button" class="text-link" data-route="planes">Ver planes ↗</button></div></details></section>`;
  }

  function securityPanel() {
    const { account } = state.session;
    return `<section class="account-section"><p class="eyebrow">CUENTA Y SEGURIDAD</p><h2>Los detalles de tu cuenta.</h2>${notice(state.accountMessage, state.accountError)}<details class="account-accordion" open><summary>Detalles de la cuenta <span>${account.email_verified ? 'Correo verificado' : 'Correo sin verificar'}</span></summary><div class="demo-profile-fields"><label for="profile-name">Nombre</label><input id="profile-name" value="${esc(account.display_name || '')}" readonly /><label for="profile-email">Correo</label><input id="profile-email" value="${esc(account.email)}" readonly /><small>Miembro desde el ${esc(fecha(account.created_at))}.</small></div></details><details class="account-accordion"><summary>Sesión <span>Este navegador</span></summary><div class="device-row"><span aria-hidden="true">▣</span><div><strong>Sesión actual</strong><p>Este navegador</p></div><button type="button" class="secondary-button" data-membership-action="logout">Cerrar sesión</button></div></details><details class="account-accordion"><summary>Cambiar contraseña <span>Por correo</span></summary><div><p>Te enviaremos un enlace a ${esc(account.email)} para elegir una nueva. Al cambiarla se cierran todas tus sesiones.</p><button type="button" class="secondary-button" data-membership-action="password-link">Enviarme el enlace</button></div></details><details class="account-accordion account-danger"><summary>Eliminar cuenta <span>Próximamente</span></summary><div><p>La baja de la cuenta todavía no está disponible desde la web.</p></div></details></section>`;
  }

  function accountView() {
    if (!state.session) { state.authReturn = 'cuenta'; return authView(); }
    const { account, plus, subscription } = state.session;
    const name = displayName(account);
    const tabs = [['overview', 'Resumen', '◎'], ['preferences', 'Preferencias', '≡'], ['favourites', 'Favoritos', '☆'], ['billing', 'Suscripción y pagos', '◈'], ['security', 'Cuenta y seguridad', '◉']];
    const access = plus ? (subscription.ends_at ? `Hasta el ${esc(fecha(subscription.ends_at))}` : 'De por vida') : 'Sin suscripción activa';
    const verify = account.email_verified ? '' : `<div class="account-verify" role="status"><div><strong>Confirma tu correo.</strong><p>Te enviamos un enlace a ${esc(account.email)}. Revisa también la carpeta de spam.</p></div><button type="button" class="secondary-button" data-membership-action="resend-verification">Reenviar correo</button></div>`;
    const overview = () => `<section class="account-section"><p class="eyebrow">TU PANEL</p><h2>Hola, ${esc(name)}.</h2>${notice(state.accountMessage, state.accountError)}${verify}<div class="account-metrics"><div><span>MI ACCESO</span><strong>${plus ? 'Plus' : 'Público'}</strong><small>${access}</small></div><div><span>FAVORITOS DEMO</span><strong>${state.savedDemoMatches.length}</strong><small>Partidos de ejemplo</small></div><div><span>MIS LIGAS</span><strong>${state.followed.length}</strong><small>Preferencia del navegador</small></div></div>${plus ? '' : '<div class="account-upgrade"><div><p class="eyebrow">QUANTFUT PLUS</p><h3>Conoce el paquete completo.</h3><p>Elige un periodo y revisa qué incluye tu suscripción.</p></div><button type="button" class="primary-button" data-route="planes">Ver suscripciones ↗</button></div>'}<div class="account-overview-links"><button type="button" class="account-link-card" data-account-section="favourites"><span>☆</span><strong>Tus favoritos</strong><small>Organiza los partidos que quieres revisar.</small></button><button type="button" class="account-link-card" data-route="paquetes"><span>◇</span><strong>Paquetes de picks</strong><small>Compara el acceso abierto y QuantFut Plus.</small></button></div><div class="account-data-note">Tu cuenta y tu plan son reales. Los partidos de ejemplo y los favoritos siguen siendo datos de demostración.</div></section>`;
    const views = { overview, preferences: preferencesPanel, favourites: favouritesPanel, billing: billingPanel, security: securityPanel };
    return `<div class="account-profile-header"><div class="account-profile-avatar" aria-hidden="true">${esc(name.charAt(0).toUpperCase())}</div><div><p class="eyebrow">MI CUENTA</p><h1>${esc(name)}</h1><p>${esc(account.email)}</p></div>${plus ? badge('Plus') : badge('Acceso público', 'muted')}<button type="button" class="secondary-button" data-membership-action="logout">Cerrar sesión</button></div><div class="member-account-layout"><aside class="account-navigation" aria-label="Secciones de la cuenta">${tabs.map(([id, label, icon]) => `<button type="button" data-account-section="${id}" ${state.accountSection === id ? 'aria-current="page"' : ''}><span aria-hidden="true">${icon}</span>${label}</button>`).join('')}<div class="account-nav-note"><strong>Tu evidencia, abierta.</strong><button type="button" class="text-link" data-route="historial">Ver historial ↗</button></div></aside><div class="account-content">${(views[state.accountSection] || overview)()}</div></div>`;
  }

  // Acciones con el servidor: el botón se desactiva mientras dura la petición
  // y el resultado se enseña como mensaje, nunca como alert().
  async function accountAction(button, run) {
    button.disabled = true;
    try {
      state.accountMessage = await run();
      state.accountError = false;
    } catch (error) {
      if (error.status === 401) { state.session = null; state.authReturn = 'cuenta'; navigate('acceso'); return; }
      state.accountMessage = error.message;
      state.accountError = true;
    }
    render();
  }

  function handleClick(button) {
    const data = button.dataset;
    const keepFocus = selector => { render(); document.querySelector(selector)?.focus(); };
    if (data.membershipPlan) {
      if (!plans().some(plan => plan.plan_code === data.membershipPlan)) return true;
      state.membershipPlan = data.membershipPlan;
      keepFocus(`[data-membership-plan="${data.membershipPlan}"]`);
      return true;
    }
    if (data.authMode) { state.authMode = data.authMode; state.authMessage = ''; state.authError = false; render(); document.querySelector('#auth-title')?.focus({ preventScroll: true }); return true; }
    if (data.accountSection) { state.accountSection = data.accountSection; state.accountMessage = ''; keepFocus(`[data-account-section="${data.accountSection}"]`); return true; }
    if (data.saveDemoMatch && fixtures.some(fx => fx.id === data.saveDemoMatch)) { state.savedDemoMatches = [...new Set([...state.savedDemoMatches, data.saveDemoMatch])]; keepFocus(`[data-remove-demo-match="${data.saveDemoMatch}"]`); return true; }
    if (data.removeDemoMatch) { state.savedDemoMatches = state.savedDemoMatches.filter(id => id !== data.removeDemoMatch); keepFocus('[data-save-demo-match]'); return true; }
    if (!data.membershipAction) return false;
    switch (data.membershipAction) {
      case 'reload-plans': loadPlans(); break;
      case 'review-order': state.authReturn = 'checkout'; state.authMode = 'login'; state.authMessage = ''; navigate(state.session ? 'checkout' : 'acceso'); break;
      case 'show-password': {
        // Sin volver a pintar: se perdería lo que ya está escrito.
        const input = document.getElementById('auth-password');
        const show = input?.type === 'password';
        if (input) input.type = show ? 'text' : 'password';
        button.textContent = show ? 'Ocultar' : 'Mostrar';
        button.setAttribute('aria-pressed', String(show));
        break;
      }
      case 'start-payment':
        startPayment();
        break;
      case 'google-signin':
        if (state.authBusy) break;
        signInWithGoogle();
        break;
      case 'logout':
        button.disabled = true;
        cuenta.logout().catch(() => {}).finally(() => {
          state.session = null; state.authMode = 'login'; state.authReturn = 'cuenta'; state.authMessage = ''; state.accountMessage = '';
          navigate('acceso');
        });
        break;
      case 'resend-verification':
        accountAction(button, async () => {
          const result = await cuenta.resendVerification();
          if (result?.status === 'ya_verificado') { state.session = await cuenta.me(); return 'Tu correo ya estaba verificado.'; }
          return 'Te enviamos un correo nuevo. El enlace caduca en 48 horas.';
        });
        break;
      case 'password-link':
        accountAction(button, async () => {
          await cuenta.forgotPassword(state.session.account.email);
          return 'Te enviamos un enlace para cambiar la contraseña. Caduca en 60 minutos.';
        });
        break;
    }
    return true;
  }

  // El servidor manda el mismo evento por la Conversions API con este eventID: Meta lo deduplica.
  function trackRegistration(session, method) {
    if (!session?.account) return;
    identify(session);
    track('CompleteRegistration', { registration_method: method }, `reg:${session.account.account_id}`);
  }

  async function signInWithGoogle() {
    const accepted = Boolean(document.getElementById('google-terms')?.checked);
    state.authBusy = true; state.authMessage = ''; state.authError = false;
    render();
    try {
      const token = await googleIdToken(await cuenta.googleConfig());
      if (token) {
        state.session = await cuenta.googleLogin(token, accepted);
        // Cuenta recién creada (el acceso de una cuenta existente no es un registro).
        if (Date.now() - new Date(state.session.account.created_at).getTime() < 120000) trackRegistration(state.session, 'google');
        state.accountMessage = ''; state.accountError = false; state.accountSection = 'overview';
        state.authBusy = false; state.authMessage = '';
        navigate(state.authReturn === 'checkout' ? 'checkout' : 'cuenta');
        return;
      }
    } catch (error) {
      state.authError = true;
      state.authMessage = error.code === 'vinculacion_requerida'
        ? 'Ya existe una cuenta con ese correo. Entra con tu contraseña; la vinculación con Google estará disponible en tu cuenta.'
        : error.message;
    }
    state.authBusy = false;
    render();
    document.querySelector('#auth-title')?.focus({ preventScroll: true });
  }

  async function submitAuth(form, action) {
    const fields = new FormData(form);
    const email = String(fields.get('email') || '').trim();
    const password = String(fields.get('password') || '');
    state.authEmail = email;
    state.authName = String(fields.get('name') || '').trim();
    if (!email) { state.authError = true; state.authMessage = 'Escribe tu correo.'; render(); return; }
    if (action === 'register' && password.length < 10) { state.authError = true; state.authMessage = 'La contraseña debe tener al menos 10 caracteres.'; render(); return; }
    state.authBusy = true; state.authMessage = ''; state.authError = false;
    render();
    try {
      if (action === 'recovery') {
        await cuenta.forgotPassword(email);
        state.authMessage = 'Si existe una cuenta con ese correo, te llegará un enlace en unos minutos. Revisa también la carpeta de spam.';
      } else {
        state.session = action === 'login' ? await cuenta.login(email, password) : await cuenta.register(email, password, state.authName);
        if (action === 'register') trackRegistration(state.session, 'email');
        state.accountMessage = action === 'register' ? 'Cuenta creada. Te enviamos un correo para confirmar tu dirección.' : '';
        state.accountError = false;
        state.accountSection = 'overview';
        state.authBusy = false; state.authMessage = ''; state.authName = '';
        navigate(state.authReturn === 'checkout' ? 'checkout' : 'cuenta');
        return;
      }
    } catch (error) {
      state.authError = true;
      state.authMessage = error.message;
    }
    state.authBusy = false;
    render();
    document.querySelector('#auth-title')?.focus({ preventScroll: true });
  }

  function handleSubmit(form) {
    const action = form.dataset.membershipForm;
    if (!action) return false;
    if (action === 'coupon') { state.couponOpen = true; state.couponMessage = 'No hay cupones activos todavía. El total de referencia no cambia.'; render(); document.querySelector('#coupon-code')?.focus(); return true; }
    if (['login', 'register', 'recovery'].includes(action)) { if (!state.authBusy) submitAuth(form, action); return true; }
    return false;
  }

  // Solo repinta donde se ven precios: en el formulario de acceso un repintado
  // borraría lo que la persona ya está escribiendo.
  async function loadPlans() {
    state.plans = { status: 'loading' };
    try {
      state.plans = { status: 'ready', items: await cuenta.plans() };
    } catch {
      state.plans = { status: 'error' };
    }
    if (['planes', 'paquetes', 'checkout', 'cuenta'].includes(state.route)) render();
  }


  // --- Pago: checkout embebido de Whop. El servidor crea la configuración; el acceso lo concede el webhook.
  const pay = () => state.pay || (state.pay = { phase: 'idle' });

  function paymentSection(q) {
    const config = state.payConfig;
    const p = pay();
    if (!config || config.status === 'loading') return '<section class="checkout-payment"><p class="eyebrow">PAGO</p><h2>Preparando el pago…</h2></section>';
    if (!config.enabled) return `<section class="checkout-payment"><p class="eyebrow">PAGO / TODAVÍA NO HABILITADO</p><h2>La activación se completará aquí.</h2><p>Cuando el pago en línea esté conectado, el acceso se activará al confirmarse el cobro. Por ahora no se solicita tarjeta ni se crea una orden.</p><div class="payment-placeholder"><span aria-hidden="true">▣</span><strong>Pago en línea no disponible</strong><small>No se solicita tarjeta ni se crea una orden.</small></div><div class="checkout-gate">${publicStatus()}</div></section>`;
    if (p.phase === 'paid') return `<section class="checkout-payment" aria-live="polite"><p class="eyebrow">PAGO / RECIBIDO</p><h2>${state.session?.plus ? 'Tu acceso ya está activo.' : 'Pago recibido. Activando tu acceso…'}</h2><p>${state.session?.plus ? 'Ya puedes entrar a tu cuenta para verlo.' : 'La confirmación del cobro puede tardar unos segundos. No cierres esta página.'}</p><div class="checkout-actions"><button type="button" class="primary-button" data-route="cuenta">Ir a mi cuenta <span aria-hidden="true">↗</span></button></div></section>`;
    if (p.phase === 'ready') return '<section class="checkout-payment"><p class="eyebrow">PAGO SEGURO</p><h2>Datos de pago.</h2><div id="whop-checkout" class="whop-mount" aria-live="polite"></div><p class="auth-small">El pago lo procesa Whop; QuantFut no ve ni guarda los datos de tu tarjeta.</p></section>';
    const busy = p.phase === 'preparing' ? ' disabled aria-busy="true"' : '';
    return `<section class="checkout-payment"><p class="eyebrow">PAGO</p><h2>Paga y activa tu acceso.</h2><p>El acceso se activa solo cuando se confirma el cobro.</p>${q ? `<button type="button" class="primary-button full" data-membership-action="start-payment"${busy}>${p.phase === 'preparing' ? 'Preparando…' : `Continuar al pago · ${esc(membershipMoney(q.totalCents, q.currency))}`} <span aria-hidden="true">↗</span></button>` : ''}${notice(p.message, true)}</section>`;
  }

  async function startPayment() {
    const q = selected();
    if (!q || pay().phase === 'preparing') return;
    state.pay = { phase: 'preparing' };
    render();
    try {
      const ids = browserIds();
      const out = await cuenta.createCheckout({ plan_code: q.id, fbp: ids.fbp, fbc: ids.fbc, source_url: `${location.origin}/#checkout` });
      identify(state.session);
      track('InitiateCheckout', { currency: q.currency, value: q.totalCents / 100, content_ids: [q.id], content_type: 'product', num_items: 1 }, out.initiate_event_id);
      state.pay = { phase: 'ready', checkoutId: out.checkout_id, eventId: out.event_id, plan: q };
    } catch (error) {
      state.pay = { phase: 'error', message: error.message };
    }
    render();
  }

  // Tras el cobro, el webhook tarda unos segundos: se consulta la cuenta hasta ver el acceso.
  async function waitForAccess() {
    for (let i = 0; i < 20 && !state.session?.plus; i += 1) {
      await new Promise(resolve => setTimeout(resolve, 3000));
      try { state.session = await cuenta.me(); } catch { /* se reintenta */ }
      if (state.route === 'checkout') render();
    }
  }

  function paid() {
    destroyCheckout();
    state.pay = { ...pay(), phase: 'paid' };
    render();
    waitForAccess();
  }

  /** Se llama tras cada pintado: el formulario de Whop vive en un nodo que `render()` recrea. */
  function afterRender() {
    const p = pay();
    const node = document.getElementById('whop-checkout');
    if (state.route !== 'checkout' || p.phase !== 'ready' || !node) return;
    mountCheckout(node, {
      checkoutId: p.checkoutId,
      email: state.session?.account?.email,
      returnUrl: `${location.origin}/?checkout=1#checkout`,
      onComplete: result => {
        if (result?.result !== 'payment') return;
        const q = p.plan;
        // Mismo eventID que el Purchase de la Conversions API (lo manda el servidor al confirmarse el pago).
        track('Purchase', { currency: q.currency, value: q.totalCents / 100, content_ids: [q.id], content_type: 'product', num_items: 1 }, p.eventId);
        paid();
      },
      onError: () => { state.pay = { phase: 'error', message: 'No se pudo mostrar el formulario de pago. Inténtalo de nuevo.' }; render(); },
    }).catch(error => { state.pay = { phase: 'error', message: error.message }; render(); });
  }

  /** Vuelta de un paso externo (3D Secure): Whop añade ?payment=…&status=… a la URL de retorno. */
  function handleReturn() {
    const params = new URLSearchParams(location.search);
    if (!params.get('checkout') || !params.get('status')) return;
    history.replaceState(null, '', `${location.pathname}#checkout`);
    if (params.get('status') === 'succeeded') { state.pay = { phase: 'paid' }; waitForAccess(); }
    else state.pay = { phase: 'error', message: params.get('status') === 'canceled' ? 'Cancelaste el pago. Puedes intentarlo de nuevo.' : 'El pago no se completó. Revisa los datos e inténtalo de nuevo.' };
    state.route = 'checkout';
  }

  async function loadPaymentConfig() {
    state.payConfig = { status: 'loading' };
    try {
      const config = await cuenta.paymentConfig();
      state.payConfig = { status: 'ready', enabled: Boolean(config.enabled), pixelId: config.pixelId };
      initPixel(config.pixelId, state.session);
    } catch {
      state.payConfig = { status: 'ready', enabled: false };
    }
    if (['checkout', 'planes', 'paquetes', 'cuenta'].includes(state.route)) render();
  }

  /** Al cargar la página: si la cookie de sesión sigue viva, entra sin pedir contraseña. */
  async function restoreSession() {
    const session = await cuenta.restore();
    if (session) { state.session = session; identify(session); render(); }
  }

  return { plansView, packagesView, authView, checkoutView, accountView, handleClick, handleSubmit, restoreSession, loadPlans, loadPaymentConfig, afterRender, handleReturn };
}
