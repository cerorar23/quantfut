import test from 'node:test';
import assert from 'node:assert/strict';
import crypto from 'node:crypto';
import { GENESIS, esHashHex, extraerLotes, sha256Hex, verificarLotes, textosDe, idiomaBase } from '../src/qf/api/static/verificar-cadena.js';

function shaSync(txt) {
  return crypto.createHash('sha256').update(txt, 'utf8').digest('hex');
}

function construirCadenaDesc(n = 3) {
  let prev = '0'.repeat(64);
  const cron = [];
  for (let i = 1; i <= n; i += 1) {
    const fecha = `2026-11-${String(i).padStart(2, '0')}`;
    const payload = shaSync(JSON.stringify({ dia: fecha, n: i }));
    const chain = shaSync(prev + payload);
    cron.push({
      batch_date: fecha,
      batch_kind: 'diario',
      match_id: null,
      payload_sha256: payload,
      prev_sha256: prev,
      chain_sha256: chain,
    });
    prev = chain;
  }
  return [...cron].reverse();
}

test('Web Crypto SHA-256 coincide exactamente con Node crypto y hashchain', async () => {
  assert.equal(GENESIS, '0'.repeat(64));
  assert.equal(await sha256Hex('abc' + 'def'), shaSync('abcdef'));
  assert.equal(esHashHex(shaSync('ok')), true);
  assert.equal(esHashHex('no-hex'), false);
});

test('verificarLotes valida respuesta DESC de /chain y detecta rotura desde génesis o en ventana parcial', async () => {
  const desc = construirCadenaDesc(4);
  const full = await verificarLotes(desc, { exigirGenesis: true });
  assert.equal(full.ok, true);
  assert.equal(full.total, 4);
  assert.equal(full.desdeGenesis, true);
  assert.equal(full.ultimoHash, desc[0].chain_sha256);

  const parcial = desc.slice(0, 2);
  const okParcial = await verificarLotes(parcial, { exigirGenesis: false });
  assert.equal(okParcial.ok, true);
  assert.equal(okParcial.desdeGenesis, false);

  const fallaGenesis = await verificarLotes(parcial, { exigirGenesis: true });
  assert.equal(fallaGenesis.ok, false);
  assert.match(fallaGenesis.errores[0], /génesis/);
});

test('verificarLotes soporta extraerLotes en modo objeto y detecta alteraciones en cualquier hash', async () => {
  const desc = construirCadenaDesc(3);
  const asc = [...desc].reverse();
  assert.deepEqual(extraerLotes({ lotes: asc, orden: 'asc' }), { lotes: asc, yaCronologico: true });
  assert.deepEqual(extraerLotes({ lotes: desc }), { lotes: desc, yaCronologico: false });
  assert.throws(() => extraerLotes({ otro: 1 }));

  for (const campo of ['payload_sha256', 'prev_sha256', 'chain_sha256']) {
    const copia = desc.map((x) => ({ ...x }));
    copia[1][campo] = 'f'.repeat(64);
    const res = await verificarLotes(copia, { exigirGenesis: true });
    assert.equal(res.ok, false, campo);
    assert.ok(res.errores.length >= 1, campo);
  }
});

test('verificarLotes y textosDe localizan mensajes en es, en y pt', async () => {
  assert.equal(idiomaBase('pt-BR'), 'pt');
  assert.equal(idiomaBase('en-US'), 'en');
  assert.equal(idiomaBase('es'), 'es');

  const desc = construirCadenaDesc(2);
  desc[0].chain_sha256 = 'a'.repeat(64);
  const resEn = await verificarLotes(desc, { idioma: 'en' });
  assert.equal(resEn.ok, false);
  assert.match(resEn.errores[0], /inconsistent chain_sha256/);
  assert.match(textosDe('pt').ok(2, true), /Cadeia íntegra: 2 lote/);
});
