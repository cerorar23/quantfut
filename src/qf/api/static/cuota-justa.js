// Calculadora de cuota justa (F4.2). Sin dependencias, sin red, sin guardar nada: todo ocurre en el navegador.
// Debe decir lo mismo que src/qf/api/cuota_justa.py y src/qf/model/devig.py (tests/datos_cuota_justa.json lo comprueba en Python y en Node).
// Es una herramienta educativa: convierte cuotas y probabilidades; no calcula importes de apuesta.

// ---------- números ----------

export function biseccion(f, a, b, tol = 1e-12) {
  const fa = f(a);
  const fb = f(b);
  if (fa === 0) return a;
  if (fb === 0) return b;
  if (fa * fb > 0) return null;
  let lo = a;
  let hi = b;
  let flo = fa;
  for (let i = 0; i < 200; i += 1) {
    const m = 0.5 * (lo + hi);
    const fm = f(m);
    if (fm === 0 || hi - lo < tol) return m;
    if (flo * fm < 0) {
      hi = m;
    } else {
      lo = m;
      flo = fm;
    }
  }
  return 0.5 * (lo + hi);
}

function validar(cuotas) {
  if (!Array.isArray(cuotas) || cuotas.length < 2 || cuotas.some((c) => !Number.isFinite(c) || c <= 1)) {
    throw new Error("Cuotas decimales inválidas");
  }
  return cuotas;
}

const suma = (xs) => xs.reduce((a, b) => a + b, 0);

// Suma de 1/cuota: 1 + el margen de la casa.
export function sobreredondeo(cuotas) {
  return suma(validar(cuotas).map((c) => 1 / c));
}

export function proporcional(cuotas) {
  const raw = validar(cuotas).map((c) => 1 / c);
  const s = suma(raw);
  return raw.map((r) => r / s);
}

export function potencia(cuotas) {
  const raw = validar(cuotas).map((c) => 1 / c);
  const k = biseccion((x) => suma(raw.map((r) => r ** x)) - 1, 0.35, 3);
  if (k === null) return proporcional(cuotas);
  const p = raw.map((r) => r ** k);
  const s = suma(p);
  return p.map((x) => x / s);
}

// Método de Shin (1993): el que usa el motor por defecto.
export function shin(cuotas) {
  const raw = validar(cuotas).map((c) => 1 / c);
  const s = suma(raw);
  if (s <= 1 + 1e-12) return raw.map((r) => r / s);
  const piDeZ = (z) => raw.map((r) => (Math.sqrt(Math.max(z * z + 4 * (1 - z) * r * r / s, 0)) - z) / (2 * (1 - z)));
  const z = biseccion((x) => suma(piDeZ(x)) - 1, 1e-9, 0.35);
  if (z === null) return potencia(cuotas);
  const p = piDeZ(z).map((x) => Math.min(Math.max(x, 1e-9), 1));
  const t = suma(p);
  return p.map((x) => x / t);
}

export const METODOS = { proporcional, shin, potencia };

export function sinMargen(cuotas, metodo = "shin") {
  const f = METODOS[metodo];
  if (!f) throw new Error(`Método desconocido: ${metodo}`);
  return f(cuotas);
}

export const cuotaJusta = (p) => (p <= 0 ? Infinity : 1 / p);

// ---------- formatos de cuota ----------

const NUM = "\\d+(?:[.,]\\d+)?";
const aNumero = (t) => Number(t.replace(",", "."));

// Texto → cuota decimal (> 1), o null si no se entiende.
export function parsear(texto, formato = "decimal") {
  const t = String(texto ?? "").trim().replace(/−/g, "-");
  if (!t) return null;
  let d = null;
  if (formato === "decimal") {
    if (!new RegExp(`^${NUM}$`).test(t)) return null;
    d = aNumero(t);
  } else if (formato === "fraccionaria") {
    const m = new RegExp(`^(${NUM})\\s*[/:]\\s*(${NUM})$`).exec(t);
    if (!m) return null;
    const a = aNumero(m[1]);
    const b = aNumero(m[2]);
    if (!(b > 0) || !(a > 0)) return null;
    d = 1 + a / b;
  } else if (formato === "americana") {
    const m = new RegExp(`^([+-]?)(${NUM})$`).exec(t);
    if (!m) return null;
    const v = aNumero(m[2]);
    if (v < 100) return null;
    d = m[1] === "-" ? 1 + 100 / v : 1 + v / 100;
  } else {
    return null;
  }
  return Number.isFinite(d) && d > 1 ? d : null;
}

const mcd = (a, b) => (b === 0 ? a : mcd(b, a % b));

export function idiomaBase(lang) {
  const c = String(lang ?? "es").toLowerCase();
  if (c.startsWith("en")) return "en";
  if (c.startsWith("pt")) return "pt";
  return "es";
}

export const fmtNum = (x, idioma = "es") => (idiomaBase(idioma) === "en" ? x.toFixed(2) : x.toFixed(2).replace(".", ","));

export function fmtPct(x, idioma = "es") {
  const base = idiomaBase(idioma);
  const num = (x * 100).toFixed(2);
  if (base === "en") return `${num}%`;
  if (base === "pt") return `${num.replace(".", ",")}%`;
  return `${num.replace(".", ",")} %`;
}

function fraccion(d, idioma = "es") {
  const x = d - 1;
  let mejor = null;
  for (let den = 1; den <= 20; den += 1) {
    const n = Math.round(x * den);
    if (n < 1) continue;
    const err = Math.abs(n / den - x);
    if (mejor === null || err < mejor.err - 1e-12) mejor = { n, den, err };
  }
  if (mejor === null) return `${fmtNum(x, idioma)}/1`;
  const g = mcd(mejor.n, mejor.den);
  const texto = `${mejor.n / g}/${mejor.den / g}`;
  return mejor.err < 0.0005 ? texto : `≈ ${texto}`;
}

// Cuota decimal → texto en el formato pedido.
export function formatear(d, formato = "decimal", idioma = "es") {
  if (formato === "fraccionaria") return fraccion(d, idioma);
  if (formato === "americana") return d >= 2 ? `+${Math.round((d - 1) * 100)}` : `-${Math.round(100 / (d - 1))}`;
  return fmtNum(d, idioma);
}

// «45», «45,5» o «45 %» → probabilidad entre 0 y 1 (exclusivos), o null.
export function parsearProbabilidad(texto) {
  const t = String(texto ?? "").trim();
  const m = new RegExp(`^(${NUM})\\s*%?$`).exec(t);
  if (!m) return null;
  const p = aNumero(m[1]) / 100;
  return p > 0 && p < 1 ? p : null;
}

// ---------- página ----------

const TEXTOS = {
  es: {
    ayuda: {
      decimal: "Escribe una cuota decimal mayor que 1 (por ejemplo 2,10).",
      fraccionaria: "Escribe una cuota fraccionaria (por ejemplo 11/10).",
      americana: "Escribe una cuota americana (por ejemplo +110 o -120).",
    },
    nombres: { 3: ["Local", "Empate", "Visitante"], 2: ["Resultado 1", "Resultado 2"] },
    ejemplo: { 3: ["2,10", "3,40", "3,60"], 2: ["1,90", "1,95"] },
    placeholderDecimal: "2,10",
    probInvalido: "Escribe una probabilidad entre 0 y 100 (por ejemplo 45 o 45,5).",
    cuotaMsg: (d, fmt) =>
      `Una cuota de ${formatear(d, fmt, "es")} implica una probabilidad del ${fmtPct(1 / d, "es")} (con el margen de la casa incluido). `
      + `En decimal ${formatear(d, "decimal", "es")}, fraccionaria ${formatear(d, "fraccionaria", "es")}, americana ${formatear(d, "americana", "es")}.`,
    probMsg: (p, j) =>
      `Una probabilidad del ${fmtPct(p, "es")} corresponde a una cuota justa de ${formatear(j, "decimal", "es")} en decimal, `
      + `${formatear(j, "fraccionaria", "es")} en fraccionaria y ${formatear(j, "americana", "es")} en americana. Las casas ofrecen menos, porque cobran un margen.`,
    faltanMsg: (ayuda, n) => `${ayuda} Hacen falta ${n} cuotas.`,
    pieMsg: (total, sinMargenSum) =>
      `Las probabilidades implícitas suman ${fmtPct(total, "es")}: el margen de la casa es del ${fmtPct(total - 1, "es")}. `
      + `Sin margen suman ${fmtPct(sinMargenSum, "es")}.`,
  },
  en: {
    ayuda: {
      decimal: "Enter decimal odds greater than 1 (for example 2.10).",
      fraccionaria: "Enter fractional odds (for example 11/10).",
      americana: "Enter American odds (for example +110 or -120).",
    },
    nombres: { 3: ["Home", "Draw", "Away"], 2: ["Outcome 1", "Outcome 2"] },
    ejemplo: { 3: ["2.10", "3.40", "3.60"], 2: ["1.90", "1.95"] },
    placeholderDecimal: "2.10",
    probInvalido: "Enter a probability between 0 and 100 (for example 45 or 45.5).",
    cuotaMsg: (d, fmt) =>
      `Odds of ${formatear(d, fmt, "en")} imply a probability of ${fmtPct(1 / d, "en")} (including the bookmaker's margin). `
      + `Decimal ${formatear(d, "decimal", "en")}, fractional ${formatear(d, "fraccionaria", "en")}, American ${formatear(d, "americana", "en")}.`,
    probMsg: (p, j) =>
      `A probability of ${fmtPct(p, "en")} corresponds to fair odds of ${formatear(j, "decimal", "en")} in decimal, `
      + `${formatear(j, "fraccionaria", "en")} in fractional and ${formatear(j, "americana", "en")} in American. Bookmakers offer less because they build in a margin.`,
    faltanMsg: (ayuda, n) => `${ayuda} ${n} odds are needed.`,
    pieMsg: (total, sinMargenSum) =>
      `The implied probabilities add up to ${fmtPct(total, "en")}: the bookmaker's margin is ${fmtPct(total - 1, "en")}. `
      + `Without margin they add up to ${fmtPct(sinMargenSum, "en")}.`,
  },
  pt: {
    ayuda: {
      decimal: "Digite uma odd decimal maior que 1 (por exemplo 2,10).",
      fraccionaria: "Digite uma odd fracionária (por exemplo 11/10).",
      americana: "Digite uma odd americana (por exemplo +110 ou -120).",
    },
    nombres: { 3: ["Casa", "Empate", "Visitante"], 2: ["Resultado 1", "Resultado 2"] },
    ejemplo: { 3: ["2,10", "3,40", "3,60"], 2: ["1,90", "1,95"] },
    placeholderDecimal: "2,10",
    probInvalido: "Digite uma probabilidade entre 0 e 100 (por exemplo 45 ou 45,5).",
    cuotaMsg: (d, fmt) =>
      `Uma odd de ${formatear(d, fmt, "pt")} implica uma probabilidade de ${fmtPct(1 / d, "pt")} (com a margem da casa incluída). `
      + `Em decimal ${formatear(d, "decimal", "pt")}, fracionária ${formatear(d, "fraccionaria", "pt")}, americana ${formatear(d, "americana", "pt")}.`,
    probMsg: (p, j) =>
      `Uma probabilidade de ${fmtPct(p, "pt")} corresponde a uma odd justa de ${formatear(j, "decimal", "pt")} em decimal, `
      + `${formatear(j, "fraccionaria", "pt")} em fracionária e ${formatear(j, "americana", "pt")} em americana. As casas oferecem menos, porque embutem uma margem.`,
    faltanMsg: (ayuda, n) => `${ayuda} São necessárias ${n} odds.`,
    pieMsg: (total, sinMargenSum) =>
      `As probabilidades implícitas somam ${fmtPct(total, "pt")}: a margem da casa é de ${fmtPct(total - 1, "pt")}. `
      + `Sem margem somam ${fmtPct(sinMargenSum, "pt")}.`,
  },
};

export const textosDe = (idioma = "es") => TEXTOS[idiomaBase(idioma)];

function celda(tag, texto, atributos = {}) {
  const el = document.createElement(tag);
  el.textContent = texto;
  for (const [k, v] of Object.entries(atributos)) el.setAttribute(k, v);
  return el;
}

function iniciar() {
  const $ = (id) => document.getElementById(id);
  const formato = $("cj-formato");
  if (!formato) return;
  const idioma = idiomaBase(document.documentElement?.lang);
  const T = textosDe(idioma);

  // --- A: cuota ↔ probabilidad ---
  const cuotaIn = $("cj-cuota");
  const probIn = $("cj-prob");
  const cuotaOut = $("cj-cuota-resultado");
  const probOut = $("cj-prob-resultado");

  function actualizarA() {
    const fmt = formato.value;
    const d = parsear(cuotaIn.value, fmt);
    if (d === null) {
      cuotaOut.textContent = cuotaIn.value.trim() ? T.ayuda[fmt] : "";
      cuotaIn.setAttribute("aria-invalid", cuotaIn.value.trim() ? "true" : "false");
    } else {
      cuotaIn.setAttribute("aria-invalid", "false");
      cuotaOut.textContent = T.cuotaMsg(d, fmt);
    }
    const p = parsearProbabilidad(probIn.value);
    if (p === null) {
      probOut.textContent = probIn.value.trim() ? T.probInvalido : "";
      probIn.setAttribute("aria-invalid", probIn.value.trim() ? "true" : "false");
    } else {
      probIn.setAttribute("aria-invalid", "false");
      probOut.textContent = T.probMsg(p, cuotaJusta(p));
    }
  }

  // --- B: quitar el margen ---
  const cuantos = $("cj-n");
  const metodo = $("cj-metodo");
  const campos = $("cj-campos");
  const tabla = $("cj-tabla").querySelector("tbody");
  const pie = $("cj-pie");
  const aviso = $("cj-aviso");
  let entradas = [];

  function dibujarCampos(n, valores) {
    campos.replaceChildren();
    entradas = [];
    T.nombres[n].forEach((nombre, i) => {
      const fila = document.createElement("div");
      fila.className = "cj-campo";
      const etiqueta = celda("label", nombre, { for: `cj-o${i}` });
      const input = document.createElement("input");
      input.id = `cj-o${i}`;
      input.type = "text";
      input.inputMode = "text";
      input.autocomplete = "off";
      input.value = valores[i] ?? "";
      input.addEventListener("input", actualizarB);
      fila.append(etiqueta, input);
      campos.append(fila);
      entradas.push(input);
    });
  }

  function actualizarB() {
    const fmt = formato.value;
    const n = Number(cuantos.value);
    const ds = entradas.map((e) => parsear(e.value, fmt));
    entradas.forEach((e, i) => e.setAttribute("aria-invalid", ds[i] === null && e.value.trim() ? "true" : "false"));
    tabla.replaceChildren();
    pie.textContent = "";
    if (ds.some((d) => d === null)) {
      aviso.textContent = entradas.some((e) => e.value.trim()) ? T.faltanMsg(T.ayuda[fmt], n) : "";
      return;
    }
    aviso.textContent = "";
    const imp = ds.map((d) => 1 / d);
    const sm = sinMargen(ds, metodo.value);
    const total = suma(imp);
    T.nombres[n].forEach((nombre, i) => {
      const tr = document.createElement("tr");
      tr.append(celda("th", nombre, { scope: "row" }), celda("td", formatear(ds[i], fmt, idioma)), celda("td", fmtPct(imp[i], idioma)),
        celda("td", fmtPct(sm[i], idioma)), celda("td", fmtNum(cuotaJusta(sm[i]), idioma)));
      tabla.append(tr);
    });
    pie.textContent = T.pieMsg(total, suma(sm));
  }

  function cambiarFormato(anterior) {
    // Al cambiar de formato se reescriben los valores válidos en el formato nuevo, para no obligar a teclear otra vez.
    const nuevo = formato.value;
    const reescribir = (el) => {
      const d = parsear(el.value, anterior);
      if (d !== null) el.value = formatear(d, nuevo, idioma).replace(/^≈ /, "");
    };
    reescribir(cuotaIn);
    entradas.forEach(reescribir);
    cuotaIn.placeholder = nuevo === "fraccionaria" ? "11/10" : nuevo === "americana" ? "+110" : T.placeholderDecimal;
    actualizarA();
    actualizarB();
  }

  let formatoAnterior = formato.value;
  formato.addEventListener("change", () => {
    cambiarFormato(formatoAnterior);
    formatoAnterior = formato.value;
  });
  cuotaIn.addEventListener("input", actualizarA);
  probIn.addEventListener("input", actualizarA);
  metodo.addEventListener("change", actualizarB);
  cuantos.addEventListener("change", () => {
    const n = Number(cuantos.value);
    dibujarCampos(n, T.ejemplo[n].map((t) => {
      const d = parsear(t, "decimal");
      return formatear(d, formato.value, idioma).replace(/^≈ /, "");
    }));
    actualizarB();
  });

  // Estado inicial: los valores que trae el HTML (el ejemplo resuelto del servidor).
  const n0 = Number(cuantos.value);
  dibujarCampos(n0, Array.from($("cj-campos").querySelectorAll("input"), (e) => e.value));
  actualizarA();
  actualizarB();
}

if (typeof document !== "undefined") {
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", iniciar);
  else iniciar();
}
