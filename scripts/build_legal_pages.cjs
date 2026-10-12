// Run with NODE_PATH pointing to a local installation of marked (13.x).
// Trusted repository Markdown is compiled offline; no client tracking or scripts.
const fs = require('node:fs');
const path = require('node:path');
const { marked } = require('marked');
const root = path.resolve(__dirname, '..');
const output = path.join(root, 'src/qf/api/legal_pages');
fs.mkdirSync(output, { recursive: true });
const pages = {
  terminos: ['TERMINOS_QUANTFUT.md', 'Términos de uso'],
  privacidad: ['PRIVACIDAD_QUANTFUT.md', 'Privacidad'],
  'eliminar-cuenta': ['ELIMINAR_CUENTA_QUANTFUT.md', 'Eliminar cuenta'],
};
for (const [slug, [source, title]] of Object.entries(pages)) {
  const markdown = fs.readFileSync(path.join(root, 'docs/legal', source), 'utf8');
  if (/\[(CONFIRMAR|PLAZO)|Borrador|pendiente de completar/.test(markdown)) {
    throw new Error(`Unfinished legal source: ${source}`);
  }
  const body = marked.parse(markdown);
  fs.writeFileSync(path.join(output, `${slug}.html`), `<!doctype html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>${title} · QuantFut</title><meta name="description" content="${title} de QuantFut, servicio de Saptain LTD.">
<style>
:root{color-scheme:light;font-family:system-ui,sans-serif;color:#172329;background:#f5f7f8}
body{margin:0;line-height:1.65}header,main,footer{max-width:850px;margin:auto;padding:24px}
header{display:flex;gap:16px;flex-wrap:wrap;align-items:center}header>a:first-child{font-weight:800;color:#123c31;font-size:1.35rem;margin-right:auto}
a{color:#086647;text-underline-offset:3px}main{background:white;border-radius:12px;overflow-wrap:anywhere}
h1{font-size:clamp(1.7rem,4vw,2.3rem);line-height:1.2}h2{font-size:1.4rem;margin-top:2rem;line-height:1.3}
table{border-collapse:collapse;width:100%;font-size:.95rem}th,td{border:1px solid #d9e0e3;padding:10px;text-align:left;vertical-align:top}th{background:#f1f6f3}
footer{font-size:.9rem;color:#53656e}a:focus-visible{outline:3px solid #ddaa36;outline-offset:4px}
@media(max-width:550px){header,main,footer{padding:18px}main{border-radius:0}th,td{padding:7px}}
</style></head><body><header><a href="/">QuantFut</a><nav aria-label="Documentos legales"><a href="/legal/terminos">Términos</a> · <a href="/legal/privacidad">Privacidad</a> · <a href="/legal/eliminar-cuenta">Eliminar cuenta</a></nav></header>
<main>${body}</main><footer>Saptain LTD · E Coast Rd, Victoria, Seychelles · <a href="mailto:admin@pronosticosdeportivos.pro">admin@pronosticosdeportivos.pro</a></footer></body></html>
`, 'utf8');
}
console.log('Three public legal pages built from versioned sources.');
