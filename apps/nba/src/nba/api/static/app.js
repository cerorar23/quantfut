"use strict";
// Web NBA v2: solo lectura de /nba/v1; todo el texto sale de i18n.json (es, en, pt, fr, it, de); sin tokens ni claves en el navegador.
const API = "/nba/v1";
const IDIOMAS = { es: "Español", en: "English", pt: "Português", fr: "Français", it: "Italiano", de: "Deutsch" };
let T = {};
let lang = "es";
const raiz = document.getElementById("raiz");

const t = (k) => (T[lang] && T[lang][k]) || (T.es && T.es[k]) || k;
const nodo = (tag, attrs = {}, ...hijos) => {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "class") e.className = v; else if (k.startsWith("on")) e.addEventListener(k.slice(2), v); else e.setAttribute(k, v);
  }
  for (const h of hijos.flat()) if (h != null) e.append(h instanceof Node ? h : document.createTextNode(String(h)));
  return e;
};
const pct = (p) => p == null || !Number.isFinite(p) ? "—" : (p * 100).toFixed(0) + " %";
const num = (x, d = 1) => Number(x).toLocaleString(lang, { minimumFractionDigits: d, maximumFractionDigits: d });
const fmtHora = (iso) => new Date(iso).toLocaleTimeString(lang, { hour: "2-digit", minute: "2-digit", timeZone: "America/New_York" }) + " ET";
const fmtFechaHora = (iso) => new Date(iso).toLocaleString(lang, { dateStyle: "short", timeStyle: "short" });
const hoyET = () => new Date().toLocaleDateString("en-CA", { timeZone: "America/New_York" });

async function pedir(ruta) {
  const r = await fetch(API + ruta);
  const cuerpo = await r.json().catch(() => ({}));
  if (!r.ok) {
    const cod = (cuerpo.detail && cuerpo.detail.codigo) || "error";
    throw new Error(T[lang]["err_" + cod] ? t("err_" + cod) : t("error"));
  }
  return cuerpo;
}
const errorEn = (e) => nodo("p", { class: "err", role: "alert" }, e.message);

function etiquetaSello(p, previsto) {
  if (p) return nodo("span", { class: "sello ok" }, t("sellado") + " " + fmtHora(p.sellado_en) + " · #" + p.hash.slice(0, 8));
  return nodo("span", { class: "sello" }, previsto ? t("se_sella") + " " + fmtHora(previsto) : t("pendiente"));
}

async function cartelera() {
  const fecha = sessionStorage.getItem("nba_fecha") || hoyET();
  const entrada = nodo("input", { type: "date", value: fecha, "aria-label": t("fecha"), onchange: (ev) => { sessionStorage.setItem("nba_fecha", ev.target.value); cartelera(); } });
  const lista = nodo("div", { class: "rejilla" }, nodo("p", {}, t("cargando")));
  raiz.replaceChildren(nodo("h1", {}, t("titulo")), nodo("p", { class: "sub" }, t("subtitulo")), nodo("div", { class: "fila" }, t("fecha"), entrada), lista);
  try {
    const d = await pedir("/cartelera?fecha=" + encodeURIComponent(fecha));
    if (!d.partidos.length) return lista.replaceChildren(nodo("p", {}, t("sin_partidos")));
    lista.replaceChildren(...d.partidos.map(tarjetaPartido));
  } catch (e) { lista.replaceChildren(errorEn(e)); }
}

function tarjetaPartido(p) {
  const pr = p.pronostico;
  const cuerpo = [nodo("div", { class: "equipos" }, nodo("span", {}, p.visitante.codigo), nodo("span", {}, "@"), nodo("span", {}, p.local.codigo))];
  if (p.inicio_utc) cuerpo.push(nodo("div", { class: "hora" }, fmtHora(p.inicio_utc)));
  if (pr) {
    const l = pr.p_local;
    cuerpo.push(nodo("div", { class: "barra-prob", role: "img", "aria-label": t("prob_gana") + ": " + p.local.codigo + " " + pct(l) },
      nodo("span", { style: `width:${(l * 100).toFixed(1)}%` }), nodo("span", { style: `width:${((1 - l) * 100).toFixed(1)}%` })));
    cuerpo.push(nodo("div", { class: "pcts" }, nodo("span", {}, p.local.codigo + " " + pct(l)), nodo("span", {}, p.visitante.codigo + " " + pct(1 - l))));
    cuerpo.push(nodo("div", { class: "metricas" },
      nodo("div", { class: "metrica" }, nodo("small", {}, t("marcador")), nodo("b", {}, `${Math.round(pr.mu[1])}–${Math.round(pr.mu[0])}`)),
      nodo("div", { class: "metrica" }, nodo("small", {}, t("handicap")), nodo("b", {}, p.local.codigo + " " + (pr.mediana.margen >= 0 ? "+" : "") + num(pr.mediana.margen, 1))),
      nodo("div", { class: "metrica" }, nodo("small", {}, t("total")), nodo("b", {}, num(pr.mediana.total, 1)))));
  }
  if (p.resultado) cuerpo.push(nodo("div", { class: "hora" }, t("final") + ": " + p.resultado.visitante + "–" + p.resultado.local));
  cuerpo.push(etiquetaSello(pr, p.sello_previsto));
  return nodo("a", { class: "tarjeta", href: "#/partido/" + p.id }, cuerpo);
}

const MERCADOS = ["total", "margen", "puntos_local", "puntos_visitante"];

function histograma(cuantiles, linea) {
  const n = 28, lo = cuantiles[0], hi = cuantiles[cuantiles.length - 1];
  const ancho = (hi - lo) / n || 1, cuentas = new Array(n).fill(0);
  for (const v of cuantiles) cuentas[Math.min(n - 1, Math.floor((v - lo) / ancho))]++;
  const max = Math.max(...cuentas);
  const NS = "http://www.w3.org/2000/svg";
  const svg = document.createElementNS(NS, "svg");
  svg.setAttribute("viewBox", `0 0 ${n * 10} 100`); svg.setAttribute("class", "histo"); svg.setAttribute("preserveAspectRatio", "none");
  svg.setAttribute("role", "img"); svg.setAttribute("aria-label", t("distribucion"));
  cuentas.forEach((c, i) => {
    const r = document.createElementNS(NS, "rect"), h = (c / max) * 96;
    r.setAttribute("x", i * 10 + 1); r.setAttribute("y", 100 - h); r.setAttribute("width", 8); r.setAttribute("height", h);
    if (lo + (i + 1) * ancho > linea) r.setAttribute("class", "sobre");
    svg.append(r);
  });
  return svg;
}

async function partido(id) {
  raiz.replaceChildren(nodo("p", {}, t("cargando")));
  let d;
  try { d = await pedir("/partido/" + id); } catch (e) { return raiz.replaceChildren(nodo("a", { href: "#/" }, t("volver")), errorEn(e)); }
  const pr = d.pronostico;
  const cab = [nodo("a", { href: "#/" }, t("volver")), nodo("h1", {}, `${d.visitante.nombre || d.visitante.codigo} @ ${d.local.nombre || d.local.codigo}`),
    nodo("p", { class: "sub" }, d.fecha + (d.inicio_utc ? " · " + fmtHora(d.inicio_utc) : ""))];
  if (!pr) return raiz.replaceChildren(...cab, etiquetaSello(null, d.sello_previsto), nodo("p", {}, t("err_sin_pronostico")));

  const resumen = nodo("div", { class: "dos" },
    nodo("div", { class: "tarjeta" }, nodo("small", {}, t("prob_gana")), nodo("b", {}, d.local.codigo + " " + pct(pr.p_local)), nodo("span", { class: "hora" }, d.visitante.codigo + " " + pct(1 - pr.p_local))),
    nodo("div", { class: "tarjeta" }, nodo("small", {}, t("marcador")), nodo("b", {}, `${Math.round(pr.mu[1])}–${Math.round(pr.mu[0])}`),
      nodo("span", { class: "hora" }, t("rango") + ": " + t("handicap") + " " + num(pr.margen_p10_p90[0], 0) + " / " + num(pr.margen_p10_p90[1], 0) + " · " + t("total") + " " + num(pr.total_p10_p90[0], 0) + "–" + num(pr.total_p10_p90[1], 0))));
  const zona = nodo("div");
  const pestanas = nodo("div", { class: "pestanas", role: "tablist" });
  const mostrar = (cual) => {
    [...pestanas.children].forEach((b) => b.setAttribute("aria-selected", String(b.dataset.tab === cual)));
    if (cual === "equipo") zona.replaceChildren(panelEquipo(d, pr));
    else if (cual === "jugador") panelJugador(d, zona);
    else zona.replaceChildren(nodo("p", { class: "aviso" }, t("proximamente")));
  };
  for (const k of ["equipo", "jugador", "especiales"]) pestanas.append(nodo("button", { role: "tab", "data-tab": k, onclick: () => mostrar(k) }, t("tab_" + k)));
  raiz.replaceChildren(...cab, resumen, pestanas, zona, pieSello(pr));
  mostrar("equipo");
}

function panelEquipo(d, pr) {
  const sel = nodo("select", { "aria-label": t("mercado") }, MERCADOS.map((m) => nodo("option", { value: m }, t("m_" + m))));
  const deslizador = nodo("input", { type: "range", "aria-label": t("linea") });
  const lectura = nodo("div", { class: "dos" });
  const grafico = nodo("div");
  const aviso = nodo("p", { class: "aviso" });
  let temporizador;
  const dibujar = async () => {
    const q = d.distribuciones[sel.value], linea = Number(deslizador.value);
    grafico.replaceChildren(histograma(q, linea));
    clearTimeout(temporizador);
    temporizador = setTimeout(async () => {
      try {
        const r = await pedir(`/partido/${d.id}/linea?mercado=${sel.value}&valor=${linea}`);
        lectura.replaceChildren(
          nodo("div", { class: "tarjeta" }, nodo("small", {}, t("mas") + " " + num(linea, 1)), nodo("b", {}, pct(r.p_mas))),
          nodo("div", { class: "tarjeta" }, nodo("small", {}, t("menos") + " " + num(linea, 1)), nodo("b", {}, pct(r.p_menos))));
        aviso.textContent = r.extremo ? t("extremo") : "";
      } catch (e) { aviso.textContent = e.message; }
    }, 120);
  };
  const ajustar = () => {
    const q = d.distribuciones[sel.value];
    deslizador.min = Math.floor(q[0]) + 0.5; deslizador.max = Math.ceil(q[q.length - 1]) - 0.5; deslizador.step = 1;
    deslizador.value = Math.round(q[99] - 0.5) + 0.5;
    dibujar();
  };
  sel.addEventListener("change", ajustar); deslizador.addEventListener("input", dibujar);
  const panel = nodo("div", {}, nodo("div", { class: "control" }, nodo("label", {}, t("mercado"), " ", sel),
    nodo("label", {}, t("linea") + ": ", nodo("output", {}), deslizador)), grafico, lectura, aviso);
  deslizador.addEventListener("input", () => { panel.querySelector("output").textContent = num(deslizador.value, 1); });
  ajustar(); panel.querySelector("output").textContent = num(deslizador.value, 1);
  return panel;
}

function histogramaPmf(pmf, linea) {
  const NS = "http://www.w3.org/2000/svg", max = Math.max(...pmf);
  let ultimo = pmf.length - 1;
  while (ultimo > 3 && pmf[ultimo] < max * 0.005) ultimo--;
  const n = ultimo + 1, svg = document.createElementNS(NS, "svg");
  svg.setAttribute("viewBox", `0 0 ${n * 10} 100`); svg.setAttribute("class", "histo"); svg.setAttribute("preserveAspectRatio", "none");
  svg.setAttribute("role", "img"); svg.setAttribute("aria-label", t("distribucion"));
  for (let k = 0; k < n; k++) {
    const r = document.createElementNS(NS, "rect"), h = (pmf[k] / max) * 96;
    r.setAttribute("x", k * 10 + 1); r.setAttribute("y", 100 - h); r.setAttribute("width", 8); r.setAttribute("height", h);
    if (k > linea) r.setAttribute("class", "sobre");
    svg.append(r);
  }
  return svg;
}

async function panelJugador(d, zona) {
  zona.replaceChildren(nodo("p", {}, t("cargando")));
  let lista;
  try { lista = (await pedir(`/partido/${d.id}/jugadores`)).jugadores; } catch (e) { return zona.replaceChildren(errorEn(e)); }
  if (!lista.length) return zona.replaceChildren(nodo("p", { class: "aviso" }, t("sin_jugadores")));
  const equipo = (j) => (j.lado === "local" ? d.local.codigo : d.visitante.codigo);
  const selJ = nodo("select", { "aria-label": t("jugador") }, lista.map((j, i) => nodo("option", { value: i }, `${equipo(j)} · ${j.nombre}`)));
  const selM = nodo("select", { "aria-label": t("mercado") }, ["puntos", "rebotes", "asistencias", "triples"].map((m) => nodo("option", { value: m }, t(m))));
  const desliz = nodo("input", { type: "range", "aria-label": t("linea"), min: 0.5, step: 1 });
  const salida = nodo("output");
  const info = nodo("dl", { class: "sello-datos" }), grafico = nodo("div"), lectura = nodo("div", { class: "dos" }), aviso = nodo("p", { class: "aviso" });
  let temporizador, pmfActual = [];
  const pintar = () => {
    const j = lista[selJ.value], m = j.mercados[selM.value];
    info.replaceChildren(
      nodo("dt", {}, t("estado_parte")), nodo("dd", {}, j.estado ? t("est_" + j.estado) : t("sin_parte")),
      nodo("dt", {}, t("p_juega")), nodo("dd", {}, pct(j.p_juega)),
      nodo("dt", {}, t("minutos_esp")), nodo("dd", {}, `${num(j.minutos_si_juega[1], 0)} (${num(j.minutos_si_juega[0], 0)}–${num(j.minutos_si_juega[2], 0)})`),
      nodo("dt", {}, `${t(selM.value)} · ${t("rango")}`), nodo("dd", {}, `${num(m.media, 1)} (${m.p10}–${m.p90})`));
  };
  const cargar = async () => {
    const j = lista[selJ.value], m = j.mercados[selM.value];
    desliz.max = Math.max(m.p90 + 3, 3) - 0.5;
    desliz.value = Math.min(Math.max(m.p50 - 0.5, 0.5), desliz.max);
    salida.textContent = num(desliz.value, 1);
    pintar();
    try { pmfActual = (await pedir(`/partido/${d.id}/jugador/${j.id}`)).mercados["jugador:" + selM.value].distribucion.pmf; } catch (e) { aviso.textContent = e.message; return; }
    dibujar();
  };
  const dibujar = () => {
    const j = lista[selJ.value], linea = Number(desliz.value);
    salida.textContent = num(linea, 1);
    grafico.replaceChildren(histogramaPmf(pmfActual, linea));
    clearTimeout(temporizador);
    temporizador = setTimeout(async () => {
      try {
        const r = await pedir(`/partido/${d.id}/jugador/${j.id}/linea?mercado=${selM.value}&valor=${linea}`);
        lectura.replaceChildren(
          nodo("div", { class: "tarjeta" }, nodo("small", {}, `${t("si_juega")}: ${t("mas")} ${num(linea, 1)}`), nodo("b", {}, pct(r.p_mas))),
          nodo("div", { class: "tarjeta" }, nodo("small", {}, `${t("si_juega")}: ${t("menos")} ${num(linea, 1)}`), nodo("b", {}, pct(r.p_menos))));
        aviso.textContent = r.extremo ? t("extremo") : "";
      } catch (e) { aviso.textContent = e.message; }
    }, 120);
  };
  selJ.addEventListener("change", cargar); selM.addEventListener("change", cargar); desliz.addEventListener("input", dibujar);
  zona.replaceChildren(nodo("div", { class: "control" }, nodo("label", {}, t("jugador"), " ", selJ), nodo("label", {}, t("mercado"), " ", selM),
    nodo("label", {}, t("linea") + ": ", salida, desliz)), info, grafico, lectura, aviso);
  cargar();
}

function pieSello(pr) {
  const salida = nodo("div", { role: "status" });
  const boton = nodo("button", { class: "accion", onclick: async () => {
    try {
      const v = await pedir("/sello/" + pr.hash);
      salida.replaceChildren(nodo("span", { class: "sello " + (v.valido ? "ok" : "mal") }, v.valido ? t("sello_valido") : t("sello_invalido")),
        nodo("p", { class: "aviso" }, t("posicion") + ": " + v.posicion));
    } catch (e) { salida.replaceChildren(errorEn(e)); }
  } }, t("verificar"));
  return nodo("section", {}, nodo("h2", {}, t("sello_titulo")),
    nodo("dl", { class: "sello-datos" },
      nodo("dt", {}, "#"), nodo("dd", {}, pr.hash), nodo("dt", {}, t("sellado")), nodo("dd", {}, fmtFechaHora(pr.sellado_en)),
      nodo("dt", {}, t("corte")), nodo("dd", {}, fmtFechaHora(pr.objetivo_en)), nodo("dt", {}, t("modelo")), nodo("dd", {}, pr.version_modelo)),
    nodo("div", { class: "fila" }, boton, nodo("a", { href: "#/calibracion" }, t("ver_calibracion"))), salida);
}

async function calibracion() {
  raiz.replaceChildren(nodo("p", {}, t("cargando")));
  let d;
  try { d = await pedir("/calibracion"); } catch (e) { return raiz.replaceChildren(errorEn(e)); }
  const h = d.historico, p = d.prospectivo, fila = (...c) => nodo("tr", {}, c.map((x) => nodo("td", {}, x)));
  const partes = [nodo("h1", {}, t("calib_titulo")), nodo("p", { class: "sub" }, t("calib_nota"))];
  if (h) {
    const e = h.equipo;
    partes.push(nodo("h2", {}, t("calib_hist") + " · " + h.temporada),
      nodo("p", { class: "sub" }, t("modelo") + ": " + (d.historico_version_modelo || "—")),
      nodo("table", {}, nodo("thead", {}, nodo("tr", {}, nodo("th", {}), nodo("th", {}, "QuantFut"), nodo("th", {}, t("mercado")))),
        nodo("tbody", {}, fila(t("brier"), num(e.modelo.brier_ganador, 4), num(e.mercado.brier_ganador, 4)), fila(t("rmse_margen"), num(e.modelo.rmse_margen, 2), num(e.mercado.rmse_margen, 2)),
          fila(t("rmse_total"), num(e.modelo.rmse_total, 2), num(e.mercado.rmse_total, 2)))),
      nodo("table", {}, nodo("thead", {}, nodo("tr", {}, nodo("th", {}), nodo("th", {}, t("mase")), nodo("th", {}, t("cobertura")), nodo("th", {}, t("n")))),
        nodo("tbody", {}, Object.entries(h.props).map(([k, v]) => fila(t(k), num(v.mase, 3), pct(v.cobertura80), v.n.toLocaleString(lang))))));
  }
  partes.push(nodo("h2", {}, t("calib_prosp")), nodo("p", {}, `${t("sellados")}: ${p.sellados} · ${t("con_resultado")}: ${p.con_resultado}` + (p.brier_ganador != null ? ` · ${t("brier")}: ${num(p.brier_ganador, 4)}` : "")));
  partes.push(nodo("p", { class: "sub" }, t("modelo") + ": " + (p.version_modelo || "—")));
  if (p.logloss_ganador != null) partes.push(nodo("p", {}, `${t("logloss")}: ${num(p.logloss_ganador, 4)}`));
  if (p.fiabilidad.length) partes.push(nodo("table", {}, nodo("thead", {}, nodo("tr", {}, ["tramo", "n", "prob_media", "observado"].map((k) => nodo("th", {}, t(k))))),
    nodo("tbody", {}, p.fiabilidad.map((b) => fila(`${pct(b.desde)}–${pct(b.hasta)}`, b.n, pct(b.prob_media), pct(b.tasa_observada))))));
  else partes.push(nodo("p", { class: "aviso" }, t("sin_datos")));
  raiz.replaceChildren(...partes);
}

function ruta() {
  const h = location.hash.replace(/^#\/?/, "");
  document.getElementById("nav-cartelera").setAttribute("aria-current", h === "" ? "page" : "false");
  document.getElementById("nav-calibracion").setAttribute("aria-current", h === "calibracion" ? "page" : "false");
  if (h.startsWith("partido/")) return partido(h.split("/")[1]);
  if (h === "calibracion") return calibracion();
  return cartelera();
}

function textosFijos() {
  document.documentElement.lang = lang;
  document.title = t("titulo");
  document.getElementById("nav-cartelera").textContent = t("nav_cartelera");
  document.getElementById("nav-calibracion").textContent = t("nav_calibracion");
  document.getElementById("etq-idioma").textContent = t("idioma");
  document.getElementById("aviso").textContent = t("aviso");
}

async function iniciar() {
  T = await (await fetch("i18n.json")).json();
  const guardado = (() => { try { return localStorage.getItem("nba_lang"); } catch { return null; } })();
  const nav = (navigator.language || "es").slice(0, 2);
  lang = IDIOMAS[guardado] ? guardado : IDIOMAS[nav] ? nav : "es";
  const sel = document.getElementById("sel-idioma");
  for (const [k, v] of Object.entries(IDIOMAS)) sel.append(nodo("option", { value: k }, v));
  sel.value = lang;
  sel.addEventListener("change", () => { lang = sel.value; try { localStorage.setItem("nba_lang", lang); } catch { /* sin almacenamiento */ } textosFijos(); ruta(); });
  textosFijos();
  window.addEventListener("hashchange", ruta);
  ruta();
}
iniciar();
