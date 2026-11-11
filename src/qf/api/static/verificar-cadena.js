// Verificador en navegador de la cadena SHA-256 pública de QuantFut (F8).
// Sin dependencias ni envíos al servidor: lee `/chain` (mismo origen) o JSON pegado/local
// y recalcula SHA-256 con Web Crypto (`crypto.subtle`) en el dispositivo de quien audita.

export const GENESIS = "0".repeat(64);
const RE_HASH = /^[0-9a-f]{64}$/;

export function idiomaBase(raw = "") {
  const b = String(raw || "").trim().toLowerCase().split("-")[0];
  return b === "en" || b === "pt" ? b : "es";
}

const TEXTOS = {
  es: {
    cargando: "Consultando /chain y calculando hashes SHA-256…",
    errorRed: (msg) => `No se pudo leer /chain (${msg}).`,
    jsonInvalido: "El texto no es un JSON válido con lotes de /chain.",
    sinLotes: "No se encontraron lotes en la entrada.",
    ok: (n, genesis) =>
      `Cadena íntegra: ${n} lote(s) verificados con SHA-256${genesis ? " desde el génesis." : " en la ventana inspeccionada."}`,
    fallo: (n, errs) => `Verificación fallida (${errs} incidencia(s) en ${n} lote(s)):`,
    estadoOk: "OK",
    estadoFallo: "FALLO",
    formatoInvalido: (et) => `${et}: falta algún hash SHA-256 válido (64 hex).`,
    genesisFallo: (et, g, p) => `${et}: se esperaba enlace al génesis (${g}…) y llega ${p}….`,
    enlaceRoto: (et, esp, obt) => `${et}: enlace prev_sha256 roto (esperado ${esp}…, obtenido ${obt}…).`,
    chainRoto: (et, esp, obt) => `${et}: hash chain_sha256 inconsistente (esperado ${esp}…, obtenido ${obt}…).`,
  },
  en: {
    cargando: "Fetching /chain and verifying SHA-256 hashes…",
    errorRed: (msg) => `Could not fetch /chain (${msg}).`,
    jsonInvalido: "Input is not valid JSON containing /chain batches.",
    sinLotes: "No batches were found in the input.",
    ok: (n, genesis) =>
      `Chain intact: ${n} batch(es) verified with SHA-256${genesis ? " from genesis." : " within the inspected window."}`,
    fallo: (n, errs) => `Verification failed (${errs} issue(s) across ${n} batch(es)):`,
    estadoOk: "OK",
    estadoFallo: "FAIL",
    formatoInvalido: (et) => `${et}: missing valid 64-char hex SHA-256 hash.`,
    genesisFallo: (et, g, p) => `${et}: expected genesis prev_sha256 (${g}…) but got ${p}….`,
    enlaceRoto: (et, esp, obt) => `${et}: broken prev_sha256 link (expected ${esp}…, got ${obt}…).`,
    chainRoto: (et, esp, obt) => `${et}: inconsistent chain_sha256 (expected ${esp}…, got ${obt}…).`,
  },
  pt: {
    cargando: "Consultando /chain e verificando hashes SHA-256…",
    errorRed: (msg) => `Não foi possível ler /chain (${msg}).`,
    jsonInvalido: "O conteúdo não é um JSON válido com lotes de /chain.",
    sinLotes: "Nenhum lote foi encontrado na entrada.",
    ok: (n, genesis) =>
      `Cadeia íntegra: ${n} lote(s) verificados com SHA-256${genesis ? " desde o gênesis." : " na janela inspecionada."}`,
    fallo: (n, errs) => `Verificação falhou (${errs} ocorrência(s) em ${n} lote(s)):`,
    estadoOk: "OK",
    estadoFallo: "FALHA",
    formatoInvalido: (et) => `${et}: falta algum hash SHA-256 válido (64 hex).`,
    genesisFallo: (et, g, p) => `${et}: esperava-se ligação ao gênesis (${g}…), veio ${p}….`,
    enlaceRoto: (et, esp, obt) => `${et}: elo prev_sha256 quebrado (esperado ${esp}…, obtido ${obt}…).`,
    chainRoto: (et, esp, obt) => `${et}: chain_sha256 inconsistente (esperado ${esp}…, obtido ${obt}…).`,
  },
};

export function textosDe(idioma = "es") {
  return TEXTOS[idiomaBase(idioma)];
}

export function esHashHex(valor) {
  return typeof valor === "string" && RE_HASH.test(valor);
}

export function extraerLotes(datos) {
  if (Array.isArray(datos)) {
    return { lotes: datos, yaCronologico: false };
  }
  if (datos && typeof datos === "object" && Array.isArray(datos.lotes)) {
    return { lotes: datos.lotes, yaCronologico: datos.orden === "asc" };
  }
  throw new Error("invalid_chain_shape");
}

export async function sha256Hex(texto) {
  const bytes = new TextEncoder().encode(texto);
  const digest = await globalThis.crypto.subtle.digest("SHA-256", bytes);
  return Array.from(new Uint8Array(digest), (b) => b.toString(16).padStart(2, "0")).join("");
}

function etiqueta(lote, indice) {
  const fecha = lote?.batch_date || "?";
  const tipo = lote?.batch_kind || "diario";
  const match = lote?.match_id ? ` ${lote.match_id}` : "";
  return `#${indice + 1} (${fecha} ${tipo}${match})`;
}

export async function verificarLotes(
  lotes,
  { exigirGenesis = false, yaCronologico = false, idioma = "es" } = {}
) {
  const tx = textosDe(idioma);
  if (!Array.isArray(lotes) || lotes.length === 0) {
    return {
      ok: false,
      total: 0,
      desdeGenesis: false,
      errores: [tx.sinLotes],
      filas: [],
      primerHash: null,
      ultimoHash: null,
    };
  }

  const cron = yaCronologico ? [...lotes] : [...lotes].reverse();
  const errores = [];
  const filas = [];

  for (let i = 0; i < cron.length; i += 1) {
    const lote = cron[i];
    const et = etiqueta(lote && typeof lote === "object" ? lote : {}, i);
    if (!lote || typeof lote !== "object") {
      errores.push(tx.formatoInvalido(et));
      filas.push({ indice: i + 1, fecha: "?", tipo: "?", payload: "", chain: "", ok: false });
      continue;
    }

    const payload = lote.payload_sha256;
    const prev = lote.prev_sha256;
    const chain = lote.chain_sha256;
    if (!esHashHex(payload) || !esHashHex(prev) || !esHashHex(chain)) {
      errores.push(tx.formatoInvalido(et));
      filas.push({
        indice: i + 1,
        fecha: String(lote.batch_date || "?"),
        tipo: String(lote.batch_kind || "diario"),
        payload: String(payload || ""),
        chain: String(chain || ""),
        ok: false,
      });
      continue;
    }

    let filaOk = true;
    if (i === 0) {
      if (exigirGenesis && prev !== GENESIS) {
        errores.push(tx.genesisFallo(et, GENESIS.slice(0, 16), prev.slice(0, 16)));
        filaOk = false;
      }
    } else {
      const anterior = cron[i - 1];
      const prevReal = anterior && typeof anterior === "object" ? anterior.chain_sha256 : null;
      if (prevReal && prev !== prevReal) {
        errores.push(tx.enlaceRoto(et, prevReal.slice(0, 16), prev.slice(0, 16)));
        filaOk = false;
      }
    }

    const esperado = await sha256Hex(prev + payload);
    if (chain !== esperado) {
      errores.push(tx.chainRoto(et, esperado.slice(0, 16), chain.slice(0, 16)));
      filaOk = false;
    }

    filas.push({
      indice: i + 1,
      fecha: String(lote.batch_date || "?"),
      tipo: String(lote.batch_kind || "diario"),
      payload,
      chain,
      ok: filaOk,
    });
  }

  const primero = cron[0] && typeof cron[0] === "object" ? cron[0] : {};
  const ultimo = cron[cron.length - 1] && typeof cron[cron.length - 1] === "object" ? cron[cron.length - 1] : {};
  return {
    ok: errores.length === 0,
    total: cron.length,
    desdeGenesis: primero.prev_sha256 === GENESIS,
    errores,
    filas,
    primerHash: primero.chain_sha256 || null,
    ultimoHash: ultimo.chain_sha256 || null,
  };
}

function pintarResultado(resultado, idioma) {
  const tx = textosDe(idioma);
  const salida = document.getElementById("vc-resultado");
  const listaErrores = document.getElementById("vc-errores");
  const tbody = document.querySelector("#vc-tabla-js tbody");
  const contenedor = document.getElementById("vc-tabla-env");
  if (!salida || !listaErrores || !tbody || !contenedor) return;

  listaErrores.replaceChildren();
  tbody.replaceChildren();
  if (resultado.ok) {
    salida.textContent = tx.ok(resultado.total, resultado.desdeGenesis);
    salida.dataset.estado = "ok";
  } else {
    salida.textContent = tx.fallo(resultado.total, resultado.errores.length);
    salida.dataset.estado = "fallo";
    for (const err of resultado.errores.slice(0, 12)) {
      const li = document.createElement("li");
      li.textContent = err;
      listaErrores.appendChild(li);
    }
  }

  const recientes = resultado.filas.slice(-20).reverse();
  for (const fila of recientes) {
    const tr = document.createElement("tr");
    const valores = [
      fila.fecha,
      fila.tipo,
      fila.payload ? `${fila.payload.slice(0, 16)}…` : "—",
      fila.chain ? `${fila.chain.slice(0, 16)}…` : "—",
      fila.ok ? tx.estadoOk : tx.estadoFallo,
    ];
    for (const texto of valores) {
      const td = document.createElement("td");
      td.textContent = texto;
      tr.appendChild(td);
    }
    tbody.appendChild(tr);
  }
  contenedor.hidden = recientes.length === 0;
}

export function iniciar() {
  const btnCargar = document.getElementById("vc-cargar");
  const btnJson = document.getElementById("vc-verificar-json");
  const entradaJson = document.getElementById("vc-json");
  const entradaArchivo = document.getElementById("vc-archivo");
  const chkGenesis = document.getElementById("vc-genesis");
  const salida = document.getElementById("vc-resultado");
  if (!btnCargar || !btnJson || !entradaJson || !salida) return;

  const idioma = idiomaBase(document.documentElement?.lang);
  const tx = textosDe(idioma);

  async function auditarObjeto(datos) {
    const { lotes, yaCronologico } = extraerLotes(datos);
    const exigirGenesis = Boolean(chkGenesis?.checked);
    const res = await verificarLotes(lotes, { exigirGenesis, yaCronologico, idioma });
    pintarResultado(res, idioma);
  }

  btnCargar.addEventListener("click", async () => {
    salida.textContent = tx.cargando;
    salida.dataset.estado = "cargando";
    try {
      const resp = await fetch("/chain?limit=365", { cache: "no-store", headers: { Accept: "application/json" } });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const datos = await resp.json();
      entradaJson.value = JSON.stringify(datos, null, 2);
      await auditarObjeto(datos);
    } catch (err) {
      salida.textContent = tx.errorRed(err?.message || String(err));
      salida.dataset.estado = "fallo";
    }
  });

  btnJson.addEventListener("click", async () => {
    try {
      const datos = JSON.parse(entradaJson.value);
      await auditarObjeto(datos);
    } catch {
      salida.textContent = tx.jsonInvalido;
      salida.dataset.estado = "fallo";
    }
  });

  if (entradaArchivo) {
    entradaArchivo.addEventListener("change", async () => {
      const file = entradaArchivo.files?.[0];
      if (!file) return;
      try {
        const texto = await file.text();
        entradaJson.value = texto;
        await auditarObjeto(JSON.parse(texto));
      } catch {
        salida.textContent = tx.jsonInvalido;
        salida.dataset.estado = "fallo";
      }
    });
  }
}

if (typeof document !== "undefined") iniciar();
