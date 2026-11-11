// La calculadora de cuota justa (src/qf/api/static/cuota-justa.js) debe decir lo mismo que el módulo de referencia de Python y el de-vig del
// motor: ambos lados comparten los vectores de tests/datos_cuota_justa.json.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

import * as cj from "../src/qf/api/static/cuota-justa.js";

const datos = JSON.parse(readFileSync(new URL("../tests/datos_cuota_justa.json", import.meta.url), "utf8"));
const TOL = 1e-7;
const cerca = (a, b, tol = TOL) => a.length === b.length && a.every((x, i) => Math.abs(x - b[i]) <= tol);

test("importar el módulo no toca el DOM ni falla fuera del navegador", () => {
  assert.equal(typeof document, "undefined");
  assert.equal(typeof cj.shin, "function");
});

for (const caso of datos.metodos) {
  test(`métodos de ${caso.cuotas.join(" / ")} = referencia de Python`, () => {
    assert.ok(Math.abs(cj.sobreredondeo(caso.cuotas) - caso.sobreredondeo) <= 1e-9);
    for (const m of ["proporcional", "shin", "potencia"]) {
      const p = cj.sinMargen(caso.cuotas, m);
      assert.ok(cerca(p, caso[m]), `${m}: ${p} frente a ${caso[m]}`);
      assert.ok(Math.abs(p.reduce((a, b) => a + b, 0) - 1) <= 1e-9, `${m} suma 1`);
    }
  });
}

test("sin margen no cambia nada", () => {
  for (const m of ["proporcional", "shin", "potencia"]) {
    assert.ok(cerca(cj.sinMargen([2, 2], m), [0.5, 0.5]));
    assert.ok(cerca(cj.sinMargen([3, 3, 3], m), [1 / 3, 1 / 3, 1 / 3]));
  }
});

test("cuotas inválidas lanzan error y un método desconocido también", () => {
  for (const malas of [[1, 2], [0.5, 3], [2], [], [NaN, 2], [Infinity, 2], [-2, 2]]) {
    assert.throws(() => cj.shin(malas), /inválidas/);
  }
  assert.throws(() => cj.sinMargen([2, 2], "inventado"), /desconocido/);
});

test("cuota justa es el inverso de la probabilidad", () => {
  assert.equal(cj.cuotaJusta(0.5), 2);
  assert.equal(cj.cuotaJusta(0.25), 4);
  assert.equal(cj.cuotaJusta(0), Infinity);
});

for (const c of datos.parsear) {
  test(`parsear ${c.formato} «${c.texto}»`, () => {
    const r = cj.parsear(c.texto, c.formato);
    if (c.decimal === null) assert.equal(r, null);
    else assert.ok(Math.abs(r - c.decimal) <= 1e-12, `${r} frente a ${c.decimal}`);
  });
}

for (const c of datos.probabilidad) {
  test(`parsearProbabilidad «${c.texto}»`, () => {
    const r = cj.parsearProbabilidad(c.texto);
    if (c.p === null) assert.equal(r, null);
    else assert.ok(Math.abs(r - c.p) <= 1e-12);
  });
}

for (const c of datos.formatear) {
  test(`formatear ${c.decimal} en ${c.formato}`, () => {
    assert.equal(cj.formatear(c.decimal, c.formato), c.texto);
  });
}

test("una fracción que no es exacta se marca como aproximada", () => {
  assert.match(cj.formatear(2.37, "fraccionaria"), /^≈ \d+\/\d+$/);
});

test("ida y vuelta entre formatos no cambia la cuota", () => {
  for (const d of [1.25, 1.5, 1.83, 2.1, 2.5, 3.4, 7.5, 12]) {
    const americana = cj.parsear(cj.formatear(d, "americana"), "americana");
    assert.ok(Math.abs(americana - d) < 0.01 * d, `${d} → ${americana}`);
    assert.equal(cj.parsear(cj.formatear(d, "decimal"), "decimal"), Number(d.toFixed(2)));
  }
});

test("formato de números en español", () => {
  assert.equal(cj.fmtNum(2.1), "2,10");
  assert.equal(cj.fmtPct(0.4587), "45,87 %");
});

test("formato de números y textos en inglés y portugués", () => {
  assert.equal(cj.idiomaBase("en"), "en");
  assert.equal(cj.idiomaBase("pt-BR"), "pt");
  assert.equal(cj.idiomaBase("es-MX"), "es");

  assert.equal(cj.fmtNum(2.1, "en"), "2.10");
  assert.equal(cj.fmtPct(0.4587, "en"), "45.87%");
  assert.equal(cj.formatear(2.1, "decimal", "en"), "2.10");

  assert.equal(cj.fmtNum(2.1, "pt-BR"), "2,10");
  assert.equal(cj.fmtPct(0.4587, "pt-BR"), "45,87%");
  assert.equal(cj.formatear(2.1, "decimal", "pt-BR"), "2,10");

  const en = cj.textosDe("en");
  assert.deepEqual(en.nombres[3], ["Home", "Draw", "Away"]);
  assert.match(en.pieMsg(1.048, 1.0), /bookmaker's margin is 4\.80%/);
  assert.match(en.cuotaMsg(2.1, "decimal"), /Odds of 2\.10 imply a probability of 47\.62%/);

  const pt = cj.textosDe("pt-BR");
  assert.deepEqual(pt.nombres[3], ["Casa", "Empate", "Visitante"]);
  assert.match(pt.pieMsg(1.048, 1.0), /margem da casa é de 4,80%/);
  assert.match(pt.cuotaMsg(2.1, "decimal"), /Uma odd de 2,10 implica uma probabilidade de 47,62%/);
});
