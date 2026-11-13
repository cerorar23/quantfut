
import fs from 'node:fs';
import { publicForecasts } from 'file:///C:/Users/huye/Documents/apuesta%20proyec/.claude/worktrees/contrato-adaptador-futbol-e61217/frontend/fichas-data.js';
const src = fs.readFileSync('C:/Users/huye/Documents/apuesta proyec/.claude/worktrees/contrato-adaptador-futbol-e61217/frontend/ergonomic-views.js', 'utf8');
const ini = src.indexOf('function football(entry)');
let prof = 0, fin = -1;
for (let k = src.indexOf('{', ini); k < src.length; k++) {
  if (src[k] === '{') prof++;
  else if (src[k] === '}' && --prof === 0) { fin = k + 1; break; }
}
const football = new Function('publicForecasts', 'results', src.slice(ini, fin) + '; return football;');
const entrada = JSON.parse(fs.readFileSync(0, 'utf8'));
const f = football(publicForecasts, () => ({ featured: entrada.featured }));
process.stdout.write(JSON.stringify(f({ status: 'ready', data: entrada.home })));
