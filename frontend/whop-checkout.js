// Checkout embebido de Whop (@whop/elements, cargado desde su CDN). La configuración (ch_) la crea el servidor:
// aquí solo se monta. El acceso lo concede el webhook, no `onComplete`.
const SRC = 'https://cdn.whop.com/elements/amber/elements.js';
let loading = null;
let handle = null;

function load() {
  loading ??= new Promise((resolve, reject) => {
    if (window.WhopElements) { resolve(); return; }
    const script = document.createElement('script');
    script.src = SRC;
    script.setAttribute('data-whop-elements', '');
    script.onload = () => resolve();
    script.onerror = () => { loading = null; reject(new Error('No se pudo cargar el formulario de pago. Revisa tu conexión e inténtalo de nuevo.')); };
    document.head.append(script);
  });
  return loading;
}

export function destroy() {
  try { handle?.destroy(); } catch { /* ya destruido */ }
  handle = null;
}

/** Monta el formulario de pago en `target` (selector o elemento). */
export async function mount(target, { checkoutId, email, returnUrl, onComplete, onReady, onError }) {
  await load();
  destroy();
  handle = window.WhopElements({ locale: 'es' }).checkout.create({ checkoutConfiguration: checkoutId, returnUrl, onComplete });
  handle.create('checkout', { buyerEmail: email || '', onReady, onError }).mount(target);
}
