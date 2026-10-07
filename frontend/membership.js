// Planes, cuenta y pedido de la web. Las cuentas son reales (/app/v1, ver
// cuenta-api.js); el pago todavía no existe y ningún botón crea una orden.
// Los importes son centavos de USD de referencia, los mismos que db/043.
import * as cuenta from './cuenta-api.js?v=67130d3ba6e2';

export const MEMBERSHIP_PLANS = Object.freeze([
  Object.freeze({ id: 'basic', name: 'Básico', months: 1, totalCents: 1499, tag: 'Empieza por un mes' }),
  Object.freeze({ id: 'standard', name: 'Estándar', months: 3, totalCents: 3399, tag: 'Plan destacado' }),
  Object.freeze({ id: 'premium', name: 'Premium', months: 6, totalCents: 5399, tag: 'Mayor ahorro mensual' }),
  Object.freeze({ id: 'club', name: 'Club QuantFut', months: null, totalCents: 17999, tag: 'Opción de por vida · propuesta' }),
]);

export function membershipQuote(id) {
  const plan = MEMBERSHIP_PLANS.find(item => item.id === id);
  if (!plan) throw new RangeError('Plan desconocido');
  return {
    ...plan,
    monthlyCents: plan.months == null ? null : Math.round(plan.totalCents / plan.months),
    savingsCents: plan.months == null ? null : MEMBERSHIP_PLANS[0].totalCents * plan.months - plan.totalCents,
    period: plan.months == null ? 'De por vida · propuesta' : `${plan.months} ${plan.months === 1 ? 'mes' : 'meses'}`,
  };
}

export const membershipMoney = cents => `$${(cents / 100).toFixed(2)}`;

export function createMembershipUI({ state, esc, badge, oddsToggle, leagues, fixtures, matchCard, navigate, render, publicStatus }) {
  const selected = () => membershipQuote(state.membershipPlan);
  const demoNote = '<p class="membership-note">Vista previa del producto. Precios de referencia en USD; no hay cargos ni suscripciones activas.</p>';
  const includes = () => '<ul class="membership-includes"><li>Acceso completo al paquete QuantFut Plus</li><li>Pick del día y detalle de mercados</li><li>Cuota registrada, precio justo y mínimo</li><li>Fichas de partido y combinadas</li><li>Historial público y evidencia de publicación</li></ul>';
  const planButton = plan => {
    const q = membershipQuote(plan.id);
    const active = state.membershipPlan === plan.id;
    return `<button type="button" class="membership-plan ${active ? 'selected' : ''}" data-membership-plan="${plan.id}" aria-pressed="${active}"><span class="plan-ribbon">${plan.tag}</span><span class="plan-name">${plan.name}<i class="plan-radio" aria-hidden="true"></i></span><strong class="plan-period">${q.period}</strong><span class="membership-price">${membershipMoney(q.monthlyCents)}<small>/ mes</small></span><span class="plan-total">${membershipMoney(q.totalCents)} USD por ${q.period.toLowerCase()}</span><span class="plan-saving">${q.savingsCents ? `Ahorro de ${membershipMoney(q.savingsCents)} frente a meses sueltos` : 'Acceso completo por un mes'}</span><span class="plan-mini-features">✓ Mismo paquete de picks<br>✓ Análisis y herramientas<br>✓ Historial verificable</span><span class="plan-select">${active ? '✓ Seleccionado' : 'Elegir plan'}</span></button>`;
  };
  const summary = (checkout = false) => {
    const q = selected();
    return `<aside class="order-summary" aria-labelledby="order-title"><p class="eyebrow">${checkout ? 'REVISIÓN / DEMO' : 'TU SELECCIÓN'}</p><h2 id="order-title">Resumen del pedido</h2><div class="order-product"><span class="order-mark" aria-hidden="true">Q.</span><div><strong>QuantFut Plus</strong><small>Paquete de picks y análisis</small></div></div><dl class="order-details"><div><dt>Modalidad</dt><dd>${q.name}</dd></div><div><dt>Periodo</dt><dd>${q.period}</dd></div><div><dt>Acceso</dt><dd>Completo · propuesto</dd></div><div><dt>Moneda</dt><dd>USD</dd></div></dl><details class="coupon-details" ${state.couponOpen ? 'open' : ''}><summary>¿Tienes un cupón?</summary><form data-membership-form="coupon"><label for="coupon-code">Código promocional de ejemplo</label><div><input id="coupon-code" name="coupon" placeholder="Código de cupón" maxlength="32" autocomplete="off" /><button type="submit" class="secondary-button">Aplicar</button></div>${state.couponMessage ? `<p role="status">${esc(state.couponMessage)}</p>` : ''}</form></details><div class="order-total"><span>Total de referencia</span><strong>${membershipMoney(q.totalCents)}<small> USD</small></strong></div><p class="order-period">${q.months == null ? 'Pago único · propuesta de por vida' : `${q.period} de acceso · equivalente aprox. ${membershipMoney(q.monthlyCents)} / mes`}</p>${checkout ? '<button type="button" class="primary-button full" disabled>Cobro todavía no habilitado</button>' : `<button type="button" class="primary-button full" data-membership-action="review-order">${state.session ? 'Revisar pedido' : 'Entrar o crear cuenta'} <span aria-hidden="true">↗</span></button>`}<p class="order-footnote">Esta selección no genera una orden ni concede acceso privado.</p><button type="button" class="text-link" data-route="paquetes">Ver qué incluye el paquete ↗</button></aside>`;
  };

  function plansView() {
    const club = MEMBERSHIP_PLANS[3];
    return `<section class="membership-heading"><p class="eyebrow">SUSCRIPCIONES / QUANTFUT PLUS</p><h1>Elige tu <em>plan.</em></h1><p>Un mismo paquete de picks, análisis y herramientas. Elige cuánto tiempo quieres explorar el servicio.</p><div class="membership-benefits"><span>✓ Acceso completo propuesto</span><span>✓ Historial abierto</span><span>✓ Precio y mínimo visibles</span></div>${demoNote}</section><div class="membership-layout"><div><div class="membership-plan-grid">${MEMBERSHIP_PLANS.slice(0, 3).map(planButton).join('')}</div><button type="button" class="membership-club ${state.membershipPlan === 'club' ? 'selected' : ''}" data-membership-plan="club" aria-pressed="${state.membershipPlan === 'club'}"><div><span class="eyebrow">${club.tag}</span><h2>${club.name}</h2><p>Pago único y acceso de por vida al paquete.<br>Condiciones y alcance pendientes de definición.</p></div><div><strong>${membershipMoney(club.totalCents)}<small> USD</small></strong><span>Pago único · referencia</span><b>${state.membershipPlan === 'club' ? '✓ Seleccionado' : 'Elegir modalidad ↗'}</b></div></button><section class="membership-comparison"><p class="eyebrow">EL MISMO CONTENIDO / DISTINTO PERIODO</p><h2>Todos los planes incluyen</h2>${includes()}<p>El historial y los partidos públicos seguirán disponibles sin contratar. Los pronósticos dependen del criterio de publicación: un plan no implica un número garantizado de picks.</p></section></div>${summary()}</div><section class="membership-faq"><h2>Antes de elegir</h2><details><summary>¿Qué cambia entre Básico, Estándar y Premium?</summary><p>El periodo de acceso y su precio de referencia. El paquete de contenido es el mismo en las tres modalidades.</p></details><details><summary>¿Puedo contratarlo ahora?</summary><p>Ya puedes crear tu cuenta. El pago en línea todavía no está habilitado: ningún botón realiza cargos.</p></details><details><summary>¿Se renueva automáticamente?</summary><p>La política de renovación y cancelación aún no está definida para QuantFut. El diseño muestra periodos de acceso; no se ha autorizado ningún cobro recurrente.</p></details><details><summary>¿Qué pasa si no hay picks que cumplan el criterio?</summary><p>El sistema debe dejar la lista vacía. La suscripción no cambia el criterio de publicación ni obliga a recomendar un partido.</p></details><details><summary>¿Incluye una garantía de resultados?</summary><p>No. Las probabilidades y los precios no garantizan un resultado. Cualquier política comercial de devolución deberá definirse por separado antes de habilitar la venta.</p></details></section>`;
  }

  function packagesView() {
    return `<section class="membership-heading"><p class="eyebrow">EL PRODUCTO / PAQUETES DE PICKS</p><h1>Todo el análisis.<br><em>En un mismo lugar.</em></h1><p>Consulta lo que ofrece el acceso público y cómo se organizaría QuantFut Plus. La suscripción amplía el acceso; el criterio conserva la última palabra.</p></section><div class="pick-package-grid"><section class="pick-package"><p class="eyebrow">ACCESO ABIERTO</p><h2>Explorador</h2><p class="package-description">Conoce los partidos y comprueba la evidencia antes de elegir un plan.</p><strong class="package-price">Gratis</strong><ul class="membership-includes"><li>Partidos y fichas disponibles</li><li>Picks públicos cuando se publiquen</li><li>Historial, calibración y verificación</li><li>Lectura del estado de publicación</li></ul><button type="button" class="secondary-button full" data-route="picks">Ver picks públicos ↗</button></section><section class="pick-package highlighted"><p class="eyebrow">PAQUETE COMPLETO / PROPUESTA</p><h2>QuantFut Plus</h2><p class="package-description">Selecciones del criterio con cuota, mínimo y análisis del partido.</p><strong class="package-price">Desde ${membershipMoney(membershipQuote('premium').monthlyCents)}<small> USD / mes equivalente</small></strong>${includes()}<button type="button" class="primary-button full" data-route="planes">Elegir periodo de acceso ↗</button><p class="membership-note">Precio de referencia. Acceso privado no habilitado.</p></section></div><section class="package-delivery"><div><p class="eyebrow">ASÍ SE LEERÍA CADA PICK</p><h2>Lo esencial, sin perder el contexto.</h2><p>Partido y selección, hora de publicación, casa, cuota registrada, precio mínimo y estado. Los resultados conservarán su registro, también cuando fallen.</p><button type="button" class="text-link" data-route="mercados" data-home-market-mode="dia">Ver Pick del día de ejemplo ↗</button></div><div class="delivery-card"><span class="badge muted">Ejemplo de estructura · sin pick privado</span><h3>Partido → selección → precio</h3><dl><div><dt>Selección y mercado</dt><dd>Según publicación autorizada</dd></div><div><dt>Cuota y mínimo</dt><dd>Registrados en el mismo instante</dd></div><div><dt>Inicio y cierre</dt><dd>Fechas visibles</dd></div><div><dt>Resultado</dt><dd>Registro posterior al partido</dd></div></dl></div></section><div class="membership-public-status">${publicStatus()}</div>`;
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
    return `<div class="auth-layout"><section class="auth-story"><p class="eyebrow">TU ESPACIO / QUANTFUT</p><h1>El análisis.<br><em>A tu manera.</em></h1><p>Tus ligas, tus preferencias y el detalle de tu plan, en un mismo espacio.</p><div class="auth-story-facts"><div><span>01</span><strong>Cuotas claras</strong><small>Formato decimal o americano.</small></div><div><span>02</span><strong>Tu selección de ligas</strong><small>Un filtro que ya funciona en la mesa.</small></div><div><span>03</span><strong>Evidencia abierta</strong><small>Consulta el historial antes de elegir.</small></div></div><button type="button" class="text-link" data-route="paquetes">Conocer los paquetes ↗</button></section><section class="auth-card" aria-labelledby="auth-title"><div class="auth-card-mark" aria-hidden="true">Q.</div><div class="auth-tabs" role="group" aria-label="Tipo de acceso"><button type="button" data-auth-mode="login" aria-pressed="${mode === 'login'}">Iniciar sesión</button><button type="button" data-auth-mode="register" aria-pressed="${registration}">Registro</button></div><h2 id="auth-title" tabindex="-1">${title}</h2><p>${intro}</p><form data-membership-form="${mode}" novalidate>${registration ? `<label for="auth-name">Nombre <small>(opcional)</small></label><input id="auth-name" name="name" maxlength="80" autocomplete="nickname" value="${esc(state.authName || '')}" />` : ''}<label for="auth-email">Correo electrónico</label><input id="auth-email" name="email" type="email" required maxlength="254" autocomplete="${registration || recovery ? 'email' : 'username'}" value="${esc(state.authEmail || '')}" />${password}${!registration && !recovery ? '<div class="auth-form-links"><span></span><button type="button" class="text-link" data-auth-mode="recovery">¿Olvidaste tu contraseña?</button></div>' : ''}<button type="submit" class="primary-button full"${busy}>${state.authBusy ? 'Un momento…' : recovery ? 'Enviar enlace' : registration ? 'Crear cuenta' : 'Entrar'} <span aria-hidden="true">↗</span></button>${notice(state.authMessage, state.authError)}</form><div class="auth-footer">${recovery ? '<button type="button" class="text-link" data-auth-mode="login">Volver a iniciar sesión</button>' : `<span>${registration ? '¿Ya tienes cuenta?' : '¿Todavía no tienes cuenta?'}</span><button type="button" class="text-link" data-auth-mode="${registration ? 'login' : 'register'}">${registration ? 'Iniciar sesión' : 'Crear cuenta'}</button>`}</div><p class="auth-privacy">Tu contraseña se guarda cifrada y nunca se muestra. La sesión se mantiene con una cookie segura de este sitio.</p></section></div>`;
  }

  function checkoutView() {
    if (!state.session) { state.authReturn = 'checkout'; return authView(); }
    const { account } = state.session;
    return `<section class="membership-heading compact"><p class="eyebrow">TU PEDIDO</p><h1>Revisa tu <em>selección.</em></h1><p>El plan elegido, su periodo y su total de referencia. El pago en línea todavía no está disponible.</p></section><ol class="checkout-steps" aria-label="Etapas de contratación"><li class="done">1 <span>Cuenta</span></li><li class="current">2 <span>Resumen del pedido</span></li><li>3 <span>Pago pendiente</span></li></ol><div class="membership-layout checkout-layout"><section class="checkout-details"><div class="checkout-identity"><p class="eyebrow">TU CUENTA</p><h2>${esc(displayName(account))}</h2><p>${esc(account.email)} · ${account.email_verified ? 'correo verificado' : 'correo sin verificar'}</p></div><section class="checkout-payment"><p class="eyebrow">PAGO / TODAVÍA NO HABILITADO</p><h2>La activación se completará aquí.</h2><p>Cuando el proveedor de pagos esté conectado, el acceso se activará al confirmarse el cobro. Por ahora no se solicita tarjeta ni se crea una orden.</p><div class="payment-placeholder"><span aria-hidden="true">▣</span><strong>Formulario de pago pendiente</strong><small>No se solicita tarjeta ni se crea una orden.</small></div><div class="checkout-gate">${publicStatus()}</div></section><div class="checkout-actions"><button type="button" class="secondary-button" data-route="planes">Cambiar plan</button><button type="button" class="text-link" data-route="cuenta">Ir a mi cuenta ↗</button></div></section>${summary(true)}</div>`;
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
      : `<span class="badge muted">Sin suscripción activa</span><h3>Acceso público</h3><p>Selección en revisión: ${q.name} · ${q.period} · ${membershipMoney(q.totalCents)} USD. El pago en línea todavía no está habilitado.</p><button type="button" class="primary-button" data-membership-action="review-order">Revisar selección ↗</button>`;
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
      if (!MEMBERSHIP_PLANS.some(plan => plan.id === data.membershipPlan)) return true;
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

  /** Al cargar la página: si la cookie de sesión sigue viva, entra sin pedir contraseña. */
  async function restoreSession() {
    const session = await cuenta.restore();
    if (session) { state.session = session; render(); }
  }

  return { plansView, packagesView, authView, checkoutView, accountView, handleClick, handleSubmit, restoreSession };
}
