import { copyFile, mkdir } from 'node:fs/promises';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = dirname(fileURLToPath(import.meta.url));
const source = join(root, 'node_modules', 'cybercore-css');
const target = join(root, 'vendor', 'cybercore');

await mkdir(target, { recursive: true });
await Promise.all([
  copyFile(join(source, 'dist', 'cybercore.min.css'), join(target, 'cybercore.min.css')),
  copyFile(join(source, 'LICENSE'), join(target, 'LICENSE')),
]);

process.stdout.write('CYBERCORE CSS 0.3.0 sincronizado en frontend/vendor/cybercore.\n');
