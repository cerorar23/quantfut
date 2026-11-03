// Vista #historial pensada para convertir sin maquillar. Solo resultados reales ya
// liquidados (fútbol del servidor; NBA y tenis de sus motores): la prueba es verlos
// todos, también los fallos, con su cuota y su marcador. Ninguna cifra se inventa:
// el beneficio solo usa cuotas realmente registradas (fútbol) y la muestra siempre
// se enseña al lado del porcentaje. Nada de «segura», «certera» ni «garantizada».

const MUESTRA_MIN = 50;
const PAGINA = 30;
const DIAS_GRAFICA = 10;
const RACHA_FORMA = 30;
const DEPORTE = { futbol: 'Fútbol', nba: 'NBA', tenis: 'Tenis' };
const DEPORTE_ICONO = { futbol: '◉', nba: '◈', tenis: '◎' };

// ------------------------------------------------------------ lógica pura

const valido = r => r && ['win', 'loss'].includes(r.outcome) && Number.isFinite(Date.parse(r.start));
const cuotaReal = r => (Number.isFinite(r.price) && r.price > 1 ? r.price : null);
const probValida = r => (Number.isFinite(r.prob) && r.prob > 0 && r.prob < 1 ? r.prob : null);

// Más antiguo primero. A igualdad de hora, el orden de entrada decide (orden estable).
export function ordenar(rows) {
  return (rows ?? []).filter(valido).map((r, i) => [r, i]).sort((a, b) => Date.parse(a[0].start) - Date.parse(b[0].start) || a[1] - b[1]).map(([r]) => r);
}

// Intervalo de Wilson al 95 %: con muestras pequeñas el porcentaje solo no dice nada.
export function wilson(aciertos, n) {
  if (!n) return null;
  const z = 1.96, p = aciertos / n, z2 = z * z;
  const centro = (p + z2 / (2 * n)) / (1 + z2 / n);
  const mitad = (z * Math.sqrt(p * (1 - p) / n + z2 / (4 * n * n))) / (1 + z2 / n);
  return { bajo: Math.max(0, centro - mitad), alto: Math.min(1, centro + mitad) };
}

// Racha actual (desde el más reciente hacia atrás) y mejor racha de aciertos.
export function rachas(rows) {
  const lista = ordenar(rows).map(r => r.outcome);
  let actual = 0;
  for (let i = lista.length - 1; i >= 0 && lista[i] === 'win'; i--) actual++;
  let mejor = 0, corrida = 0;
  for (const o of lista) { corrida = o === 'win' ? corrida + 1 : 0; mejor = Math.max(mejor, corrida); }
  const ultimoFallo = lista.lastIndexOf('loss');
  return { actual, mejor, desdeUltimoFallo: ultimoFallo === -1 ? null : lista.length - 1 - ultimoFallo };
}

// Beneficio con 1 unidad por pronóstico y solo con cuota real registrada: gana (cuota − 1), pierde 1.
export function beneficio(rows) {
  const con = ordenar(rows).filter(cuotaReal);
  let acumulado = 0;
  const curva = [0];
  for (const r of con) { acumulado += r.outcome === 'win' ? cuotaReal(r) - 1 : -1; curva.push(acumulado); }
  const unidades = acumulado;
  return { n: con.length, unidades, roi: con.length ? unidades / con.length : null, curva, cuotaMedia: con.length ? con.reduce((s, r) => s + cuotaReal(r), 0) / con.length : null };
}

// Lo prometido (probabilidad con que se publicó cada pronóstico) frente a lo que salió.
export function calibrar(rows) {
  const con = ordenar(rows).filter(probValida);
  if (!con.length) return null;
  const prometido = con.reduce((s, r) => s + probValida(r), 0) / con.length;
  const real = con.filter(r => r.outcome === 'win').length / con.length;
  const ee = Math.sqrt(prometido * (1 - prometido) / con.length);
  const diff = real - prometido;
  const estado = Math.abs(diff) <= 2 * ee ? 'dentro' : diff > 0 ? 'encima' : 'debajo';
  return { n: con.length, prometido, real, diff, ee, estado };
}

export function resumir(rows) {
  const lista = ordenar(rows);
  const aciertos = lista.filter(r => r.outcome === 'win').length;
  const n = lista.length;
  return { n, aciertos, fallos: n - aciertos, acierto: n ? aciertos / n : null, intervalo: wilson(aciertos, n),
    desde: n ? lista[0].start : null, hasta: n ? lista[n - 1].start : null, rachas: rachas(lista), beneficio: beneficio(lista), calibracion: calibrar(lista) };
}

export function porDeporte(rows) {
  return Object.keys(DEPORTE).map(sport => {
    const lista = (rows ?? []).filter(r => valido(r) && r.sport === sport);
    const aciertos = lista.filter(r => r.outcome === 'win').length;
    return { sport, n: lista.length, aciertos, fallos: lista.length - aciertos, acierto: lista.length ? aciertos / lista.length : null };
  }).filter(d => d.n);
}

// `dia` convierte el instante en la clave de día local (la inyecta la vista).
export function porDia(rows, dia) {
  const dias = new Map();
  for (const r of ordenar(rows)) {
    const clave = dia(r.start);
    const d = dias.get(clave) ?? { dia: clave, n: 0, aciertos: 0, fallos: 0, rows: [] };
    d.n++; r.outcome === 'win' ? d.aciertos++ : d.fallos++; d.rows.push(r);
    dias.set(clave, d);
  }
  return [...dias.values()];
}

// ------------------------------------------------------------ vistas

export function createHistorialViews({ esc, state, fmtOdds, realTime, localDay, getResults }) {
  const num = (v, d = 0) => Number(v).toLocaleString('es-MX', { minimumFractionDigits: d, maximumFractionDigits: d });
  const pct = (v, d = 0) => `${num(v * 100, d)} %`;
  const signo = v => (v > 0 ? '+' : v < 0 ? '−' : '');
  const unidades = v => `${signo(v)}${num(Math.abs(v), 2)} u`;
  const odds = v => (fmtOdds ? fmtOdds(v) : num(v, 2));
  const corto = clave => new Date(`${clave}T12:00:00`).toLocaleDateString('es-MX', { day: 'numeric', month: 'short' }).replace('.', '');
  const largo = clave => new Date(`${clave}T12:00:00`).toLocaleDateString('es-MX', { weekday: 'long', day: 'numeric', month: 'long' });
  const dia = start => (localDay ? localDay(new Date(start)) : new Date(start).toISOString().slice(0, 10));

  const icon = body => `<svg class="cyber-icon cv-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="square" stroke-linejoin="miter" focusable="false" aria-hidden="true">${body}</svg>`;
  const ICON = {
    predict: icon('<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="4"/><path d="M12 1v4M23 12h-4M12 23v-4M1 12h4"/>'),
    seal: icon('<path d="M12 3 20 6v5c0 5-3.4 8.4-8 10-4.6-1.6-8-5-8-10V6l8-3Z"/><path d="m9 12 2 2 4-5"/>'),
    publish: icon('<path d="M4 12h12M12 6l6 6-6 6"/><path d="M20 4v16"/>'),
  };

  // -------- gráficas SVG (sin estilos en línea: la CSP no los admite; el color va por clases)
  function curvaSvg(curva) {
    if (curva.length < 3) return '<p class="cv-hist-nota">Aún no hay suficientes pronósticos con cuota registrada para dibujar la curva.</p>';
    const W = 640, H = 230, L = 46, R = 16, T = 18, B = 26;
    const min = Math.min(...curva, 0), max = Math.max(...curva, 0);
    const span = max - min || 1;
    const x = i => L + (i / (curva.length - 1)) * (W - L - R);
    const y = v => T + (1 - (v - min) / span) * (H - T - B);
    const puntos = curva.map((v, i) => `${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(' ');
    const base = y(0).toFixed(1);
    const area = `${x(0).toFixed(1)},${base} ${puntos} ${x(curva.length - 1).toFixed(1)},${base}`;
    const fin = curva[curva.length - 1];
    const marcas = [...new Set([max, 0, min])].map(v => `<g><line class="cv-hist-grid" x1="${L}" x2="${W - R}" y1="${y(v).toFixed(1)}" y2="${y(v).toFixed(1)}"/><text class="cv-hist-axis" x="${L - 6}" y="${(y(v) + 4).toFixed(1)}" text-anchor="end">${v === 0 ? '0' : signo(v) + num(Math.abs(v), 1)}</text></g>`).join('');
    const etiqueta = `Beneficio acumulado en fútbol: ${unidades(fin)} tras ${curva.length - 1} pronósticos con cuota. Mínimo ${num(min, 1)} u, máximo ${num(max, 1)} u.`;
    return `<svg class="cv-hist-chart" viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(etiqueta)}">${marcas}<polygon class="cv-hist-area ${fin >= 0 ? 'win' : 'loss'}" points="${area}"/><polyline class="cv-hist-line ${fin >= 0 ? 'win' : 'loss'}" points="${puntos}" fill="none"/><circle class="cv-hist-end ${fin >= 0 ? 'win' : 'loss'}" cx="${x(curva.length - 1).toFixed(1)}" cy="${y(fin).toFixed(1)}" r="5"/><text class="cv-hist-axis" x="${L}" y="${H - 6}">Primer pronóstico</text><text class="cv-hist-axis" x="${W - R}" y="${H - 6}" text-anchor="end">Último (${curva.length - 1})</text></svg>`;
  }

  function diasSvg(dias) {
    const visibles = dias.slice(-DIAS_GRAFICA);
    if (!visibles.length) return '';
    const W = 640, H = 230, L = 10, R = 10, T = 28, B = 28;
    const tope = Math.max(...visibles.map(d => d.n));
    const ancho = (W - L - R) / visibles.length, barra = Math.min(46, ancho * 0.62);
    const alto = n => (n / tope) * (H - T - B);
    const columnas = visibles.map((d, i) => {
      const cx = L + ancho * i + ancho / 2, x0 = cx - barra / 2;
      const hA = alto(d.aciertos), hF = alto(d.fallos), yBase = H - B;
      return `<g><rect class="cv-hist-bar win" x="${x0.toFixed(1)}" y="${(yBase - hA).toFixed(1)}" width="${barra.toFixed(1)}" height="${hA.toFixed(1)}"/>${d.fallos ? `<rect class="cv-hist-bar loss" x="${x0.toFixed(1)}" y="${(yBase - hA - hF).toFixed(1)}" width="${barra.toFixed(1)}" height="${hF.toFixed(1)}"/>` : ''}<text class="cv-hist-val" x="${cx.toFixed(1)}" y="${(yBase - hA - hF - 7).toFixed(1)}" text-anchor="middle">${pct(d.aciertos / d.n)}</text><text class="cv-hist-axis" x="${cx.toFixed(1)}" y="${H - 8}" text-anchor="middle">${esc(corto(d.dia))}</text></g>`;
    }).join('');
    const etiqueta = `Acierto por día: ${visibles.map(d => `${corto(d.dia)} ${d.aciertos} de ${d.n}`).join('; ')}.`;
    return `<svg class="cv-hist-chart" viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(etiqueta)}"><line class="cv-hist-grid" x1="${L}" x2="${W - R}" y1="${H - B}" y2="${H - B}"/>${columnas}</svg>`;
  }

  function deportesBloque(deportes) {
    return `<ul class="cv-hist-sports">${deportes.map(d => `<li><span class="cv-hist-sport-name"><i aria-hidden="true">${DEPORTE_ICONO[d.sport]}</i>${DEPORTE[d.sport]}</span><svg class="cv-hist-meter" viewBox="0 0 100 8" preserveAspectRatio="none" role="presentation"><rect class="track" x="0" y="0" width="100" height="8"/><rect class="fill" x="0" y="0" width="${(d.acierto * 100).toFixed(1)}" height="8"/></svg><strong>${pct(d.acierto)}</strong><small>${num(d.aciertos)} de ${num(d.n)}${d.n < MUESTRA_MIN ? ' · muestra pequeña' : ''}</small></li>`).join('')}</ul>`;
  }

  function forma(lista) {
    const ultimos = ordenar(lista).slice(-RACHA_FORMA);
    if (!ultimos.length) return '';
    const g = ultimos.filter(r => r.outcome === 'win').length;
    const label = `Últimos ${ultimos.length}: ${g} acertados y ${ultimos.length - g} fallados. De más antiguo a más reciente: ${ultimos.map(r => (r.outcome === 'win' ? 'acertado' : 'fallado')).join(', ')}.`;
    return `<div class="cv-streak"><div class="cv-streak-head"><strong>Últimos ${ultimos.length} resultados</strong><span>${num(g)} ✓ · ${num(ultimos.length - g)} ✗</span></div><ol class="cv-dots" role="img" aria-label="${esc(label)}">${ultimos.map(r => `<li class="cv-dot ${r.outcome}"><span aria-hidden="true">${r.outcome === 'win' ? '✓' : '✗'}</span></li>`).join('')}</ol><p class="cv-streak-note">Los ✗ se quedan. Es lo que hace creíble a los ✓.</p></div>`;
  }

  // -------- bloques
  function hero(r) {
    const e = r.intervalo;
    const pequena = r.n < MUESTRA_MIN;
    const titulo = `${num(r.aciertos)} de ${num(r.n)} pronósticos acertados.<br><em>Y los ${num(r.fallos)} fallos, a la vista.</em>`;
    const grados = Math.round((r.acierto ?? 0) * 100);
    const circ = 2 * Math.PI * 52, relleno = ((r.acierto ?? 0) * circ).toFixed(1);
    const anillo = `<svg class="cv-hist-ring" viewBox="0 0 120 120" role="img" aria-label="Acierto ${grados} por ciento"><circle class="track" cx="60" cy="60" r="52" fill="none"/><circle class="fill" cx="60" cy="60" r="52" fill="none" stroke-dasharray="${relleno} ${circ.toFixed(1)}" transform="rotate(-90 60 60)"/></svg>`;
    return `<section class="cv-hero cyber-card cyber-card--holo" aria-label="Resumen de resultados">
      <div class="cv-hero-copy"><p class="eyebrow">EVIDENCIA / REGISTRO REAL</p><h1>${titulo}</h1>
        <p class="lead">Esto es lo que pasó con los pronósticos que publicamos: cuál era, a qué cuota y cómo terminó. Cada uno se selló antes del partido, así que nadie puede cambiarlo después.</p>
        <div class="cv-chips"><span class="cyber-badge cyber-badge--green">✓ ${num(r.aciertos)} acertados</span><span class="cyber-badge cyber-badge--magenta">✗ ${num(r.fallos)} fallados</span><span class="cyber-badge">${esc(corto(dia(r.desde)))} – ${esc(corto(dia(r.hasta)))}</span>${pequena ? '<span class="cyber-badge cyber-badge--yellow">Muestra en construcción</span>' : ''}</div>
        <div class="cv-actions"><button type="button" class="primary-button" data-route="planes">Ver planes VIP</button><button type="button" class="text-link" data-action="cv-scroll" data-target="cv-hist-lista">Ver cada resultado ↓</button></div></div>
      <div class="cv-hero-proof"><div class="cv-hist-ringbox">${anillo}<span class="cv-hist-ringnum cyber-text-glow cyber-text-glow--green">${pct(r.acierto)}</span></div><span class="cv-big-label">Acierto real</span>
        <p class="cv-big-sub">${num(r.aciertos)} de ${num(r.n)} liquidados${e ? ` · rango probable ${pct(e.bajo)} – ${pct(e.alto)}` : ''}</p>
        <p class="cv-fine">${pequena ? `Con pocos pronósticos el porcentaje se mueve mucho: pedimos ${MUESTRA_MIN} antes de sacar conclusiones.` : 'El rango probable (IC 95 %) muestra cuánto podría moverse esta cifra.'}</p></div>
    </section>`;
  }

  function kpis(r) {
    const { rachas: ra, beneficio: b, calibracion: c } = r;
    const rachaTexto = ra.actual ? `${num(ra.actual)} ✓ seguidos` : 'Último: fallo ✗';
    const cal = c ? `<div class="cv-hist-kpi"><span>Prometido frente a real</span><strong>${pct(c.prometido)} → ${pct(c.real)}</strong><small>${c.estado === 'dentro' ? 'Dentro del margen de error: lo prometido se cumple' : c.estado === 'encima' ? 'Por encima de lo prometido' : 'Por debajo de lo prometido; lo decimos igual'}</small></div>` : '';
    const ben = b.n ? `<div class="cv-hist-kpi"><span>Beneficio · 1 u por pronóstico</span><strong class="${b.unidades >= 0 ? 'pos' : 'neg'}">${b.unidades >= 0 ? '▲' : '▼'} ${unidades(b.unidades)}</strong><small>Solo fútbol con cuota registrada: ${num(b.n)} pronósticos, cuota media ${odds(b.cuotaMedia)}</small></div>` : '';
    return `<section class="cv-hist-kpis" aria-label="Indicadores clave"><div class="cv-hist-kpi"><span>Racha actual</span><strong>${rachaTexto}</strong><small>Mejor racha: ${num(ra.mejor)} ✓ seguidos${ra.actual ? '' : ' · la racha se corta con el último fallo'}</small></div>${cal}${ben}<div class="cv-hist-kpi"><span>Muestra</span><strong>${num(r.n)} liquidados</strong><small>${r.n < MUESTRA_MIN ? 'Aún pequeña: cada resultado pesa mucho' : 'Suficiente para ver una tendencia, no una garantía'}</small></div></section>`;
  }

  function graficas(r, rows) {
    const dias = porDia(rows, dia);
    const deportes = porDeporte(rows);
    const curva = r.beneficio.curva;
    return `<section class="cv-section" aria-label="Gráficas de rendimiento"><div class="cv-section-head"><p class="eyebrow">EL RENDIMIENTO, A SIMPLE VISTA</p><h2>Lo que pasó, sin adornos</h2></div>
      <div class="cv-hist-charts">
        <article class="cyber-card cv-hist-card cv-hist-wide"><h3>Beneficio acumulado en fútbol</h3><p class="cv-hist-sub">Si hubieras puesto 1 unidad en cada pronóstico con cuota registrada. Sube cuando acertamos y baja cuando fallamos.</p>${curvaSvg(curva)}${r.beneficio.n ? `<p class="cv-hist-foot">Cuotas bajas (media ${odds(r.beneficio.cuotaMedia)}): se acierta mucho y se gana poco por pronóstico. Un fallo borra varios aciertos.</p>` : ''}</article>
        <article class="cyber-card cv-hist-card"><h3>Acierto por día</h3><p class="cv-hist-sub">Verde: acertados. Magenta: fallados. Encima, el porcentaje del día.</p>${diasSvg(dias)}</article>
        <article class="cyber-card cv-hist-card"><h3>Por deporte</h3><p class="cv-hist-sub">Cada motor tiene su propia muestra: míralas por separado.</p>${deportesBloque(deportes)}${forma(rows)}</article>
      </div></section>`;
  }

  function cuotaCelda(row) {
    const real = cuotaReal(row);
    if (real) return `<strong class="cv-hist-odds">${odds(real)}</strong><small>cuota</small>`;
    const p = probValida(row);
    if (p) return `<strong class="cv-hist-odds model">≈ ${odds(1 / p)}</strong><small>justa del modelo</small>`;
    return '<strong class="cv-hist-odds none">—</strong><small>sin cuota</small>';
  }

  function fila(row) {
    const ok = row.outcome === 'win';
    const p = probValida(row);
    return `<li class="cv-hist-row ${row.outcome}"><span class="cv-hist-state ${row.outcome}"><b aria-hidden="true">${ok ? '✓' : '✗'}</b><span>${ok ? 'Acertado' : 'Fallado'}</span></span>
      <div class="cv-hist-match"><span class="cv-hist-tag">${DEPORTE[row.sport]} · ${esc(realTime ? realTime(row.start) : '')}</span><strong>${esc(row.home)} vs ${esc(row.away)}</strong><span class="cv-hist-pick">${esc(row.text)}${p ? ` <i>· prob. ${pct(p)}</i>` : ''}</span></div>
      <div class="cv-hist-cuota">${cuotaCelda(row)}</div>
      <div class="cv-hist-score"><strong>${esc(row.score || 'Registrado')}</strong><small>resultado</small></div></li>`;
  }

  function lista(rows) {
    const orden = state.resultOutcome || 'todos';
    const deporte = state.resultSport || 'todos';
    const todos = ordenar(rows).reverse();
    const visibles = todos.filter(r => (deporte === 'todos' || r.sport === deporte) && (orden === 'todos' || r.outcome === (orden === 'acertados' ? 'win' : 'loss')));
    const limite = state.resultLimit || PAGINA;
    const cortados = visibles.slice(0, limite);
    const grupos = porDia(cortados.slice().reverse(), dia).reverse();
    const chips = (attr, actual, items) => items.map(([id, label]) => `<button type="button" class="chip ${actual === id ? 'selected' : ''}" data-${attr}="${id}" aria-pressed="${actual === id}">${label}</button>`).join('');
    const filtros = `<div class="cv-hist-filters"><div class="chip-row" role="group" aria-label="Filtrar por deporte">${chips('result-sport', deporte, [['todos', 'Todos'], ['futbol', 'Fútbol'], ['nba', 'NBA'], ['tenis', 'Tenis']])}</div><div class="chip-row" role="group" aria-label="Filtrar por resultado">${chips('result-outcome', orden, [['todos', 'Todos los resultados'], ['acertados', '✓ Acertados'], ['fallados', '✗ Fallados']])}</div></div>`;
    const cuerpo = grupos.length
      ? grupos.map(g => `<section class="cv-hist-day" aria-label="${esc(largo(g.dia))}"><header><h3>${esc(largo(g.dia))}</h3><span>${num(g.aciertos)} ✓ · ${num(g.fallos)} ✗ · ${pct(g.aciertos / g.n)}</span></header><ol class="cv-hist-rows">${g.rows.slice().reverse().map(fila).join('')}</ol></section>`).join('')
      : '<p class="cv-hist-nota">Ningún resultado con estos filtros.</p>';
    const mas = visibles.length > limite ? `<button type="button" class="secondary-button cv-hist-more" data-result-more="1">Mostrar ${num(Math.min(PAGINA, visibles.length - limite))} más ↓</button>` : '';
    return `<section class="cv-section" id="cv-hist-lista" tabindex="-1" aria-label="Todos los resultados"><div class="cv-section-head"><p class="eyebrow">CADA RESULTADO, CON SU CUOTA</p><h2>El registro completo, día por día</h2></div>${filtros}<p class="cv-hist-count" aria-live="polite">Mostrando ${num(cortados.length)} de ${num(visibles.length)} resultados</p>${cuerpo}${mas}
</section>`;
  }

  function sello() {
    const paso = (n, ic, titulo, texto) => `<li><span class="cv-step-n">${n}</span><span class="cv-step-ic">${ic}</span><div><strong>${titulo}</strong><p>${texto}</p></div></li>`;
    return `<section class="cv-section" aria-label="Cómo se comprueba"><div class="cv-section-head"><p class="eyebrow">POR QUÉ PUEDES CREERLO</p><h2>Nadie puede cambiar un pronóstico después</h2></div><ol class="cv-steps">${paso(1, ICON.predict, 'Se predice', 'El modelo calcula la probabilidad y se guarda la cuota del momento.')}${paso(2, ICON.seal, 'Se sella', 'El pronóstico entra en una cadena de huellas (hash). Cambiarlo rompería la cadena.')}${paso(3, ICON.publish, 'Se publica', 'Sale antes del partido. Después se liquida y el resultado se queda, sea bueno o malo.')}</ol></section>`;
  }

  function cierre(r) {
    const preguntas = [
      ['Si acertáis tanto, ¿ganaré dinero seguro?', `No. Acertar mucho con cuotas bajas deja poco margen: ${r.beneficio.n ? `en fútbol, ${num(r.beneficio.n)} pronósticos con 1 unidad cada uno suman ${unidades(r.beneficio.unidades)}. ` : ''}Un fallo borra varios aciertos. Por eso enseñamos la cuota de cada uno y el beneficio real, no solo el porcentaje.`],
      ['¿Qué significa «prometido frente a real»?', 'Cada pronóstico sale con una probabilidad. Si el promedio de lo prometido se parece a lo que acierta de verdad, el modelo está bien calibrado. Si no, lo verás aquí.'],
      ['¿Por qué NBA y tenis no traen cuota de casa?', 'Porque esos motores publican probabilidades estadísticas, no cuotas de una casa. Mostramos la cuota justa del modelo, marcada con ≈, y no la usamos en ningún beneficio.'],
      ['¿Podéis borrar o editar un resultado?', 'No. Cada pronóstico se sella antes del partido en una cadena de huellas; tocarlo la rompería. Los fallos están ahí, como los aciertos.'],
    ];
    return `<section class="cv-cta cyber-card cyber-card--green" aria-label="Acceso VIP"><div><p class="eyebrow">DE LA PRUEBA A LA DECISIÓN</p><h2>Ya viste el registro entero. ¿Quieres los pronósticos antes del partido?</h2><p>Con VIP ves todos los pronósticos de cada lote, con su probabilidad, cuota y casa de referencia, sellados antes de empezar.</p></div><button type="button" class="primary-button" data-route="planes">Ver planes VIP</button></section>
      <section class="cv-section" aria-label="Preguntas frecuentes"><div class="cv-section-head"><p class="eyebrow">LAS DUDAS DE SIEMPRE</p><h2>Preguntas, con respuestas sin maquillar</h2></div><div class="cv-faq">${preguntas.map(([q, a]) => `<details><summary>${q}</summary><p>${a}</p></details>`).join('')}</div></section>
      <div class="cv-sticky" role="complementary" aria-label="Acceso VIP"><span>${pct(r.acierto)} · ${num(r.n)} liquidados</span><button type="button" class="primary-button" data-route="planes">Ver planes VIP</button></div>`;
  }

  function estado(titulo, texto, reintentar = true) {
    return `<section class="cv-state cyber-card" role="status"><h2>${esc(titulo)}</h2><p>${esc(texto)}</p>${reintentar ? '<button type="button" class="secondary-button" data-action="refresh-public">Actualizar ↻</button>' : ''}</section>`;
  }

  // `rows`: [{sport, home, away, start, text, outcome, price, prob, score}] ya liquidados.
  function historyView(rows, cargando) {
    const lista_ = ordenar(rows);
    const cabecera = '<div class="view-title"><div><p class="eyebrow">EVIDENCIA / REGISTRO REAL</p><h1>Historial verificable</h1></div></div>';
    if (!lista_.length) {
      return `${cabecera}${estado(cargando ? 'Consultando resultados…' : 'Sin resultados disponibles', cargando ? 'Un momento: cargamos el historial.' : 'El historial aparece cuando los resultados están confirmados.', !cargando)}`;
    }
    const r = resumir(lista_);
    return `${hero(r)}${kpis(r)}${graficas(r, lista_)}${lista(lista_)}${sello()}${cierre(r)}`;
  }

  return { historyView, PAGINA };
}
