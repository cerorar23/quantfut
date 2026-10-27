import { createServer } from 'node:http';
import { readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const root = dirname(fileURLToPath(import.meta.url));
const files = new Map([
  ['/', ['index.html', 'text/html; charset=utf-8']],
  ['/index.html', ['index.html', 'text/html; charset=utf-8']],
  ['/styles.css', ['styles.css', 'text/css; charset=utf-8']],
  ['/future.css', ['future.css', 'text/css; charset=utf-8']],
  ['/vendor/cybercore/cybercore.min.css', ['vendor/cybercore/cybercore.min.css', 'text/css; charset=utf-8']],
  ['/app.js', ['app.js', 'text/javascript; charset=utf-8']],
  ['/real-views.js', ['real-views.js', 'text/javascript; charset=utf-8']],
  ['/sports-data.js', ['sports-data.js', 'text/javascript; charset=utf-8']],
  ['/ergonomic-views.js', ['ergonomic-views.js', 'text/javascript; charset=utf-8']],
  ['/public-data.js', ['public-data.js', 'text/javascript; charset=utf-8']],
  ['/fichas-data.js', ['fichas-data.js', 'text/javascript; charset=utf-8']],
  ['/membership.js', ['membership.js', 'text/javascript; charset=utf-8']],
  ['/membership.css', ['membership.css', 'text/css; charset=utf-8']],
  ['/cuenta-api.js', ['cuenta-api.js', 'text/javascript; charset=utf-8']],
  ['/google-auth.js', ['google-auth.js', 'text/javascript; charset=utf-8']],
  ['/meta-pixel.js', ['meta-pixel.js', 'text/javascript; charset=utf-8']],
  ['/whop-checkout.js', ['whop-checkout.js', 'text/javascript; charset=utf-8']],
]);
const port = Number(process.env.PORT || 5173);
const host = process.env.HOST || '127.0.0.1';

createServer(async (request, response) => {
  const pathname = new URL(request.url || '/', 'http://localhost').pathname;
  const file = files.get(pathname);
  if (!file) {
    response.writeHead(404, { 'Content-Type': 'text/plain; charset=utf-8' });
    response.end('No encontrado');
    return;
  }
  try {
    const body = await readFile(join(root, file[0]));
    response.writeHead(200, {
      'Content-Type': file[1],
      'Cache-Control': 'no-store',
      'X-Content-Type-Options': 'nosniff',
      'Content-Security-Policy': "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; object-src 'none'; base-uri 'none'",
    });
    response.end(body);
  } catch {
    response.writeHead(500, { 'Content-Type': 'text/plain; charset=utf-8' });
    response.end('No se pudo cargar el prototipo');
  }
}).listen(port, host, () => {
  process.stdout.write(`QuantFut demo: http://${host}:${port}\n`);
});
