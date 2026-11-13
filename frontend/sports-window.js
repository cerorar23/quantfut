import { imageMarkup, playerPhoto } from './sport-images.js?v=imagenes-20261028b';
import { withNbaMarkets, marketQuote, featuredSportMarket, hayLiquidado, ordenLiquidado, withDetalle, familiasDeEvento } from './sports-data.js?v=generica-20261113';
// Ventana única de NBA y tenis: pronóstico y estadísticas del mismo evento, con el diseño de la de fútbol.
// Solo presenta lo que publican los motores; no calcula probabilidades ni inventa cuotas.
// La «cuota del modelo» es 1 ÷ probabilidad y se rotula como tal: ninguna casa publica estos mercados.

export function createSportWindow(ctx) {
  const { state, esc, badge, fmtPct, fmtOdds, realDate, realTime, dateFmt, addDays, localDay, dayLabel,
    ensureSport, ensureImages, nbaCode } = ctx;
  const ROW_LIMIT = 24;
  const SPORT_NAME = { nba: 'NBA', tenis: 'Tenis' };
  // Deporte del catálogo sin pantalla propia (Fase 4 · 4.4): todo lo que no es nba ni tenis (el fútbol no llega a esta ventana). `ctx.generico(id)` lo da app.js:
  // {nombre, orden: [id de familia], nombreFamilia(id), pantallaDeporte, pantallaPartido (listas de bloques o null)}.
  const isGeneric = sport => !SPORT_NAME[sport];
  const genericInfo = sport => ctx.generico?.(sport) || {};
  const nameOf = sport => SPORT_NAME[sport] ?? genericInfo(sport).nombre ?? String(sport);
  const keyOf = event => `${event.sport}:${event.id}`;
  const portrait = (event, player) => playerPhoto('nba', event.v2 ? player.photo_id : player.player_id);
  const num = (value, digits = 1) => (Number.isFinite(value) ? Number(value).toLocaleString('es-MX', { minimumFractionDigits: digits, maximumFractionDigits: digits }) : '—');
  const marks = name => esc(String(name || '?').split(/\s+/).filter(Boolean).slice(0, 2).map(part => part[0]).join('').toUpperCase() || '?');
  // Imágenes del manifiesto para NBA y tenis, tanto en la lista como en el encabezado.
  const ownImage = src => (typeof src === 'string' && /^\/web\/[\w./-]+\.(png|jpe?g|webp|svg)$/i.test(src) ? src : null);
  const mark = (name, sport, img) => {
    if (isGeneric(sport)) {
      const src = ownImage(img);
      return src ? `<img class="win-crest is-logo" src="${esc(src)}" alt="" data-image-name="${esc(name)}" loading="lazy" decoding="async">` : `<span class="win-crest is-initial" aria-hidden="true">${marks(name)}</span>`;
    }
    const index = ensureImages?.();
    const key = sport === 'nba' ? nbaCode?.(name) : String(name || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
    const hit = sport === 'nba' ? index?.nba?.[key] : index?.tenis?.[key];
    const file = typeof hit?.f === 'string' && /^[a-z0-9][a-z0-9-]*\.(png|jpg)$/i.test(hit.f) ? hit.f : null;
    const credit = sport === 'tenis' && hit ? ` title="${esc(`Foto: ${hit.a} · ${hit.l} (${hit.fuente || 'Wikimedia Commons'})`)}"` : '';
    return file ? `<img class="win-crest ${sport === 'tenis' ? 'is-photo' : 'is-logo'}" src="/web/imagenes/${sport}/${esc(file)}" alt="" data-image-name="${esc(name)}" loading="lazy" decoding="async"${credit}>`
      : `<span class="win-crest is-initial" aria-hidden="true">${marks(name)}</span>`;
  };
  const statusText = event => (event.generico && event.status === 'live' ? 'En vivo' : event.generico && event.status === 'cancelled' ? 'Cancelado' : event.status === 'finished' ? 'Final' : event.status === 'awaiting_result' ? 'Esperando resultado' : new Date(event.start) <= new Date() ? 'En curso o por confirmar' : 'Programado');
  const statusKind = event => (event.generico && event.status === 'cancelled' ? 'warn' : event.status === 'finished' ? 'muted' : event.status === 'awaiting_result' ? 'warn' : '');

  function family(event, m) {
    if (event.sport === 'tenis') {
      if (m.id === 'winner') return 'Ganador';
      if (/^(Ganador de set|Sets totales|Hándicap de sets)/.test(m.label)) return 'Sets';
      if (/^(Juegos totales|Hándicap de juegos)/.test(m.label)) return 'Juegos';
      if (/^Tie-break/.test(m.label)) return 'Tie-break';
      return 'Otros';
    }
    if (['winner', 'handicap', 'game_total', 'team_points'].includes(m.market)) return 'Partido';
    return { player_points: 'Puntos', player_rebounds: 'Rebotes', player_assists: 'Asistencias', player_threes: 'Triples' }[m.market] || 'Combinados y otros';
  }
  const FAMILY_ORDER = ['Partido', 'Ganador', 'Sets', 'Juegos', 'Tie-break', 'Puntos', 'Rebotes', 'Asistencias', 'Triples', 'Combinados y otros', 'Otros'];

  function outcomeBadge(m) {
    if (m.outcome === 'win') return badge('Acertó', 'good');
    if (m.outcome === 'loss') return badge('Falló', 'warn');
    if (m.outcome === 'push') return badge('Devolución', 'muted');
    if (m.outcome === 'void') return badge('Anulada', 'muted');
    return m.revised ? badge('Revisión', 'muted') : badge('Pendiente', 'muted');
  }

  function dayEvents(events, offset = state.winDay) {
    const day = localDay(addDays(offset, 12));
    return events.filter(e => localDay(new Date(e.start)) === day).sort((a, b) => new Date(a.start) - new Date(b.start));
  }

  const bar = (label, probability, note = '') => `<div class="win-bar"><span>${esc(label)}${note ? `<small>${esc(note)}</small>` : ''}</span><div class="cyber-progress cyber-progress--green" data-value="${(probability * 100).toFixed(1)}" role="progressbar" aria-label="${esc(label)}" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${(probability * 100).toFixed(1)}"><div class="cyber-progress__bar"></div></div><b>${fmtPct(probability)}</b></div>`;
  const kv = (label, value) => `<div class="win-kv"><span>${esc(label)}</span><strong>${value}</strong></div>`;
  const lineOf = selection => { const found = /([0-9]+(?:[.,][0-9]+)?)\s*$/.exec(String(selection)); return found ? Number(found[1].replace(',', '.')) : 0; };

  // Probabilidad de cada lado a partir del mercado «ganador» (la selección publicada y su complemento).
  function duel(event) {
    const winner = event.markets.find(m => (m.id === 'winner' || m.market === 'winner') && !m.revised) || event.markets.find(m => m.id === 'winner' || m.market === 'winner');
    if (!winner) return '';
    const homeWins = String(winner.selection).includes(event.home) || String(winner.selection) === event.home;
    const home = homeWins ? winner.probability : 1 - winner.probability;
    return `<div class="win-panel-box"><p class="eyebrow">PROBABILIDAD DE GANAR</p>${bar(event.home, home)}${bar(event.away, 1 - home)}</div>`;
  }

  // Piezas compartidas con la pantalla genérica (mismo marcado que siempre para NBA y tenis).
  function pickCard(event, feat) {
    const quote = feat ? marketQuote(feat) : null;
    const rule = 'cuota de 1,20 o más y probabilidad de 75 % o más';
    return feat
      ? `<p class="eyebrow">PRONÓSTICO DESTACADO</p><div class="win-pick-grid"><div>${feat.player ? imageMarkup(portrait(event, feat), feat.player, esc) : ""}<h2>${esc(feat.selection)}</h2><p class="win-sub">${esc(feat.label)} · ${esc(event.league)} · ${esc(event.home)} vs ${esc(event.away)}</p></div><div class="win-odd"><small>${quote.model ? 'Cuota del modelo' : feat.price_book ? 'Cuota de referencia' : 'Cuota de la casa'}</small><strong>${fmtOdds(quote.price)}</strong><em>${quote.model ? '1 ÷ probabilidad' : esc(quote.source)}</em></div></div><div class="win-prob"><b>${fmtPct(feat.probability)}</b><div class="cyber-progress cyber-progress--green" data-value="${(feat.probability * 100).toFixed(1)}" role="progressbar" aria-label="Probabilidad del pronóstico destacado" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${(feat.probability * 100).toFixed(1)}"><div class="cyber-progress__bar"></div></div></div><p class="win-sub">${outcomeBadge(feat)}</p>`
      : `<p class="eyebrow">PRONÓSTICO DESTACADO</p><h2>Sin pronóstico destacado</h2><p class="win-sub">${event.markets.length && event.markets.every(m => m.revised) ? 'Los mercados de este evento son revisiones posteriores al inicio y no cuentan como pronóstico previo.' : `Ningún mercado publicado de este evento cumple la regla del destacado: ${rule}.`}</p>`;
  }
  function marketLine(event, feat) {
    return m => {
      const q = marketQuote(m);
      return `<tr${m === feat ? ' class="win-feat"' : ''}><td>${esc(m.label)}</td><td>${m.player ? imageMarkup(portrait(event, m), m.player, esc) : ""}${esc(m.selection)}${m === feat ? '<small class="win-cell-note">Pronóstico destacado</small>' : ''}${m.estimate != null && event.sport === 'nba' ? `<small class="win-cell-note">Proyección ${num(m.estimate)}</small>` : ''}${m.conditional ? '<small class="win-cell-note">Si el jugador participa</small>' : ''}</td><td class="n">${fmtPct(m.probability)}${m.push_probability ? `<small class="win-cell-note">Devol. ${fmtPct(m.push_probability)}</small>` : ''}</td><td class="n">${q.price != null ? `${fmtOdds(q.price)}<small class="win-cell-note">${esc(q.source)}</small>` : '—'}</td><td>${outcomeBadge(m)}</td></tr>`;
    };
  }
  function masMercados(all, criterio) {
    return all.length > ROW_LIMIT ? `<div class="win-vipbar"><p>${state.winAll ? `Se muestran los ${all.length} mercados.` : `Se muestran ${ROW_LIMIT} de ${all.length} mercados, ${criterio}.`}</p><button type="button" class="cyber-btn cyber-btn--sm" data-win-all="1">${state.winAll ? 'Ver menos' : 'Ver todos'}</button></div>` : '';
  }
  function tablaMercados(shown, line, nba) {
    return `<div class="win-table ${nba ? 'win-nba-table' : ''}" tabindex="0" role="region" aria-label="Mercados del evento"><table class="cyber-table cyber-table--compact"><thead><tr><th scope="col">Mercado</th><th scope="col">Selección</th><th scope="col" class="n">Prob.</th><th scope="col" class="n">Cuota</th><th scope="col">Estado</th></tr></thead><tbody>${shown.map(line).join('')}</tbody></table></div>`;
  }

  // ---- pronóstico (izquierda)
  function forecast(event) {
    if (event.markets_status === 'loading') return '<p class="win-sub" role="status">Cargando mercados del partido y de los jugadores…</p>';
    if (event.markets_status === 'error') return '<p class="win-sub" role="status">No se pudieron cargar los mercados. <button type="button" class="text-link" data-action="refresh-public">Reintentar</button></p>';
    const feat = featuredSportMarket(event);
    const card = pickCard(event, feat);
    const families = [...new Set(event.markets.map(m => family(event, m)))].sort((a, b) => FAMILY_ORDER.indexOf(a) - FAMILY_ORDER.indexOf(b));
    const fam = families.includes(state.winSportFam) ? state.winSportFam : families[0];
    const nba = event.sport === 'nba' && event.v2;
    const porProbabilidad = event.markets.filter(m => family(event, m) === fam && (!nba || state.winAllOdds || marketQuote(m).price >= 1.2))
      .sort((a, b) => b.probability - a.probability || marketQuote(b).price - marketQuote(a).price);
    const liquidado = hayLiquidado(porProbabilidad, m => m.outcome);
    const all = ordenLiquidado(porProbabilidad, { resultado: m => m.outcome, cuota: m => marketQuote(m).price, prob: m => m.probability });
    const criterio = liquidado ? 'acertados primero, de mayor a menor cuota' : 'de mayor a menor probabilidad';
    const shown = state.winAll ? all : all.slice(0, ROW_LIMIT);
    const line = marketLine(event, feat);
    const more = masMercados(all, criterio);
    const projections = playerProjections(event);
    if (event.v2 && !event.markets.length) return projections || (event.markets_status === 'ready' ? '<p class="win-sub">Todavía no hay mercados publicados para este partido.</p>' : '');
    const controls = nba ? `<div class="win-market-tools"><div class="win-chips" role="group" aria-label="Filtrar por cuota"><button type="button" class="chip ${!state.winAllOdds ? 'selected' : ''}" data-win-odds="min" aria-pressed="${!state.winAllOdds}">Cuotas ≥ 1,20</button><button type="button" class="chip ${state.winAllOdds ? 'selected' : ''}" data-win-odds="all" aria-pressed="${Boolean(state.winAllOdds)}">Todas las cuotas</button></div><p class="win-sub">${liquidado ? 'Acertados primero, de mayor a menor cuota' : 'De mayor a menor probabilidad'}</p></div>` : '';
    const markets = nba && fam !== 'Partido' ? playerMarkets(event, all, feat, fam)
      : all.length ? `${tablaMercados(shown, line, nba)}${more}`
      : '<p class="win-sub" role="status">No hay mercados con la cuota seleccionada en esta categoría.</p>';
    return `<article class="win-pick cyber-card" aria-label="Pronóstico destacado">${card}</article>
      <section aria-label="Mercados"><div class="win-mk-head"><h3>Mercados</h3><div class="win-chips" role="group" aria-label="Familia de mercado">${families.map(f => `<button type="button" class="chip ${fam === f ? 'selected' : ''}" data-win-sport-fam="${esc(f)}" aria-pressed="${fam === f}">${esc(f)}</button>`).join('')}</div></div>
      ${controls}${markets}</section>${projections}`;
  }
  function playerMarkets(event, markets, feat, fam) {
    const normalize = s => String(s || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
    const query = normalize(state.winPlayerSearch);
    const groups = new Map();
    for (const m of markets) {
      if (!normalize(`${m.player} ${m.team}`).includes(query)) continue;
      if (!groups.has(m.player_id)) groups.set(m.player_id, []);
      groups.get(m.player_id).push(m);
    }
    const players = [...groups.values()];
    const shown = state.winAll ? players : players.slice(0, 6);
    const row = m => {
      const q = marketQuote(m);
      return `<tr${m === feat ? ' class="win-feat"' : ''}><td>${esc(m.selection)}${m === feat ? '<small class="win-cell-note">Pronóstico destacado</small>' : ''}${m.push_probability ? `<small class="win-cell-note">Devol. ${fmtPct(m.push_probability)}</small>` : ''}</td><td class="n">${fmtPct(m.probability)}</td><td class="n">${fmtOdds(q.price)}<small class="win-cell-note">${esc(q.source)}</small></td><td>${outcomeBadge(m)}</td></tr>`;
    };
    const table = rows => `<div class="win-table win-player-lines"><table class="cyber-table cyber-table--compact"><thead><tr><th scope="col">Selección</th><th scope="col" class="n">Prob.</th><th scope="col" class="n">Cuota</th><th scope="col">Estado</th></tr></thead><tbody>${rows.map(row).join('')}</tbody></table></div>`;
    const cards = shown.map(rows => {
      const m = rows[0];
      return `<article class="win-player-card ${rows.includes(feat) ? 'is-featured' : ''}" aria-label="${esc(`${fam} de ${m.player}`)}"><header class="win-player-head">${imageMarkup(portrait(event, m), m.player, esc)}<div><h4>${esc(m.player)}</h4><p>${esc(m.team || '')} · ${esc(fam)}</p>${m.estimate != null ? `<p>Proyección <strong>${num(m.estimate)}</strong> · Si participa</p>` : ''}</div></header>${table(rows.slice(0, 3))}${rows.length > 3 ? `<details class="win-player-more"><summary>Ver ${rows.length - 3} línea${rows.length === 4 ? '' : 's'} más</summary>${table(rows.slice(3))}</details>` : ''}</article>`;
    }).join('');
    return `<label class="win-player-search"><span>Buscar jugador o equipo</span><input type="search" id="win-player-search" data-input="win-player-search" value="${esc(state.winPlayerSearch || '')}" placeholder="Nombre del jugador o equipo" autocomplete="off"></label>${players.length ? `<div class="win-player-grid">${cards}</div>` : '<p class="win-sub" role="status">No hay jugadores con estos filtros.</p>'}${players.length > 6 ? `<div class="win-vipbar"><p>${shown.length} de ${players.length} jugadores</p><button type="button" class="cyber-btn cyber-btn--sm" data-win-all="1">${state.winAll ? 'Ver menos' : 'Ver todos los jugadores'}</button></div>` : ''}`;
  }

  function playerProjections(event) {
    if (!event.projections?.length) return '';
    const names = { puntos: 'Puntos', rebotes: 'Rebotes', asistencias: 'Asistencias', triples: 'Triples' };
    const players = new Map();
    for (const p of event.projections) {
      if (!players.has(p.player_id)) players.set(p.player_id, []);
      players.get(p.player_id).push(p);
    }
    return `<details class="win-projections"><summary>Proyecciones de jugadores <span>${players.size} jugadores</span></summary><p class="win-sub">Valores esperados si el jugador participa.</p><div class="win-player-grid">${[...players.values()].map(stats => {
      const p = stats[0];
      return `<article class="win-player-card"><header class="win-player-head">${imageMarkup(portrait(event, p), p.player, esc)}<div><h4>${esc(p.player)}</h4><p>${esc(p.team || '')}</p><p>Prob. de jugar ${fmtPct(p.p_juega)}</p></div></header><dl class="win-player-stats">${stats.map(s => `<div><dt>${names[s.market]}</dt><dd>${num(s.estimate)}</dd><small>P10–P90: ${num(s.p10)}–${num(s.p90)}</small></div>`).join('')}</dl></article>`;
    }).join('')}</div></details>`;
  }

  // ---- estadísticas (derecha)
  // ---- tenis: estadísticas de los jugadores (API-Tennis, resumidas por el servidor)
  const rate = r => (r && r.rate != null ? fmtPct(r.rate) : '—');
  const rec = r => (r && (r.won || r.lost) ? `${r.won}-${r.lost}` : '—');
  const ROUNDS = [[/Qualification/g, 'Clasificación'], [/Semi-?finals?/gi, 'Semifinales'], [/Quarter-?finals?/gi, 'Cuartos de final'], [/1\/8-finals/g, 'Octavos de final'],
    [/1\/16-finals/g, 'Dieciseisavos'], [/1\/32-finals/g, 'Ronda de 64'], [/1\/64-finals/g, 'Ronda de 128'], [/\bRound\b/g, 'Ronda']];
  const es = text => ROUNDS.reduce((out, [pattern, word]) => out.replace(pattern, word), String(text || ''));
  const count = (n, one, many) => `${n} ${n === 1 ? one : many}`;
  const normal = text => String(text || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().replace(/[^a-z]/g, '');

  // El servidor entrega [primer jugador, segundo jugador]; se comprueba contra los nombres del evento.
  function sides(event, data) {
    const [a, b] = data.players;
    const swapped = normal(a.name) === normal(event.away) && normal(b.name) === normal(event.home);
    return swapped ? [b, a] : [a, b];
  }

  function tennisStats(event) {
    const entry = ctx.ensureTennisStats(event.id);
    if (entry.status === 'loading') return { note: '<div class="win-panel-box"><p class="eyebrow">ESTADÍSTICAS DE LOS JUGADORES</p><p class="win-sub">Consultando los datos de los jugadores…</p></div>' };
    if (entry.status !== 'ready') return { note: '<div class="win-panel-box"><p class="eyebrow">ESTADÍSTICAS DE LOS JUGADORES</p><p class="win-sub">Todavía no hay estadísticas publicadas para este partido. Se actualizan varias veces al día para los partidos de ayer a pasado mañana.</p></div>' };
    return { data: entry.data, players: sides(event, entry.data) };
  }

  function badges(player, surface) {
    const out = [];
    const f = player.form;
    if (f && f.streak >= 3) out.push(['En racha: ' + f.streak + ' victorias', 'good']);
    if (f && f.streak <= -3) out.push(['Racha negativa: ' + Math.abs(f.streak) + ' derrotas', 'warn']);
    if (f && f.matches.length >= 6 && f.index >= 70) out.push(['En buena forma', 'good']);
    if (f && f.matches.length >= 6 && f.index <= 30) out.push(['Bajo de forma', 'warn']);
    const s = player.surfaces?.[surface];
    const n = s ? s.career.won + s.career.lost : 0;
    if (s && n >= 15 && s.career.rate >= 0.65) out.push(['Fuerte en esta superficie', 'good']);
    if (s && n >= 15 && s.career.rate <= 0.45) out.push(['Débil en esta superficie', 'warn']);
    const early = f?.stages?.inicial;
    if (early && early.matches >= 3 && early.rate <= 0.4) out.push(['Sufre en primeras rondas', 'warn']);
    return out;
  }
  const surfaceKey = event => ({ hard: 'hard', clay: 'clay', grass: 'grass' })[String(event.surface || '').toLowerCase()] || null;
  const SURFACE_NAME = { hard: 'Pista dura', clay: 'Tierra batida', grass: 'Hierba' };

  // Fila «valor · etiqueta · valor» con el mejor lado resaltado (`lower`: gana el número menor, como el ranking).
  // `shown`: texto a mostrar de cada lado cuando no es el propio valor comparado; `neutral`: no resalta a nadie.
  function versus(label, a, b, { lower = false, text = v => (v == null ? '—' : String(v)), shown = null, neutral = false } = {}) {
    const better = neutral || a == null || b == null || a === b ? '' : (lower ? a < b : a > b) ? 'a' : 'b';
    const show = (v, i) => (shown ? shown[i] : text(v));
    return `<div class="win-vsrow"><b class="${better === 'a' ? 'is-better' : ''}">${show(a, 0)}</b><span>${esc(label)}</span><b class="${better === 'b' ? 'is-better' : ''}">${show(b, 1)}</b></div>`;
  }

  function tennisSummary(event) {
    const t = tennisStats(event);
    if (!t.players) return duel(event) + t.note;
    const [a, b] = t.players;
    const surface = surfaceKey(event);
    const badgeRow = p => `<div class="win-badges" aria-label="Etiquetas de ${esc(p.name || '')}">${badges(p, surface).map(([text, kind]) => badge(esc(text), kind)).join('') || '<span class="win-sub">Sin etiquetas destacadas.</span>'}</div>`;
    const rank = p => (p.rank != null ? `#${p.rank}` : '—');
    const hist = [...new Set([...a.ranking_history.map(h => h.season), ...b.ranking_history.map(h => h.season)])].sort((x, y) => y - x).slice(0, 5);
    const rankIn = (p, season) => p.ranking_history.find(h => h.season === season)?.rank;
    return `${duel(event)}
      <div class="win-panel-box"><p class="eyebrow">COMPARATIVA</p><div class="win-vshead"><strong>${esc(event.home)}</strong><strong>${esc(event.away)}</strong></div>
        ${versus('Ranking', a.rank, b.rank, { lower: true, text: v => (v == null ? '—' : `#${v}`) })}
        ${versus('Puntos', a.points, b.points, { text: v => (v == null ? '—' : num(v, 0)) })}
        ${versus('Edad', a.age, b.age, { text: v => (v == null ? '—' : `${v} años`) })}
        ${versus('Récord de la temporada', a.season?.rate, b.season?.rate, { text: v => (v == null ? '—' : fmtPct(v)) })}
        ${versus('Títulos esta temporada', a.season?.titles, b.season?.titles)}
        ${versus('Récord de carrera', a.career.rate, b.career.rate, { text: v => (v == null ? '—' : fmtPct(v)) })}
        ${versus('Índice de forma (0–100)', a.form?.index, b.form?.index)}
        <p class="win-sub">${esc(a.country || '—')} · ${esc(b.country || '—')}</p></div>
      <div class="win-panel-box"><p class="eyebrow">ETIQUETAS</p><p class="win-sub"><strong>${esc(event.home)}</strong></p>${badgeRow(a)}<p class="win-sub"><strong>${esc(event.away)}</strong></p>${badgeRow(b)}</div>
      ${hist.length ? `<div class="win-panel-box"><p class="eyebrow">RANKING POR TEMPORADA</p><div class="win-vshead"><strong>${esc(event.home)}</strong><strong>${esc(event.away)}</strong></div>${hist.map(season => versus(String(season), rankIn(a, season), rankIn(b, season), { lower: true, text: v => (v == null ? '—' : `#${v}`) })).join('')}<p class="win-sub">Mejor posición de cada temporada en individuales. Actual: ${rank(a)} · ${rank(b)}.</p></div>` : ''}`;
  }

  function formBlock(event, player, side) {
    const f = player.form;
    const title = `<p class="eyebrow">${esc(side)}</p>`;
    if (!f) return `<div class="win-panel-box">${title}<p class="win-sub">Sin partidos recientes registrados.</p></div>`;
    const chips = f.matches.map(m => `<i class="win-res ${m.won ? 'is-win' : 'is-loss'}" title="${esc(m.date)} · ${esc(m.opponent)}">${m.won ? 'G' : 'P'}</i>`).join('');
    const w = f.windows;
    const stage = (name, label) => (f.stages[name].matches ? kv(label, `${rec(f.stages[name])} <small>${rate(f.stages[name])} · ${count(f.stages[name].matches, 'partido', 'partidos')}</small>`) : '');
    const last = f.matches.slice(0, 5).map(m => `<li><span class="win-d">${esc(m.date.slice(5))}</span><span>${esc(m.opponent || '—')}<small>${esc(es(m.tournament))} · ${esc(es(m.round))}${m.qualification && !/Clasificaci/.test(es(m.tournament) + es(m.round)) ? ' · Clasificación' : ''}</small></span><span class="win-sc">${esc(m.score || '—')}</span><span class="win-res ${m.won ? 'is-win' : 'is-loss'}">${m.won ? 'G' : 'P'}</span></li>`).join('');
    return `<div class="win-panel-box">${title}
      ${bar('Índice de forma', f.index / 100, `Últimos ${f.matches.length} partidos, los recientes pesan más`)}
      <div class="win-chipline" aria-label="Últimos partidos, del más reciente al más antiguo">${chips}</div>
      ${kv('Racha actual', f.streak > 0 ? `${f.streak} ${f.streak === 1 ? 'victoria' : 'victorias'}` : `${Math.abs(f.streak)} ${f.streak === -1 ? 'derrota' : 'derrotas'}`)}
      ${kv('Últimos 30 días', `${rec(w['30'])} <small>${rate(w['30'])} · ${count(w['30'].matches, 'partido', 'partidos')}</small>`)}
      ${kv('Últimos 90 días', `${rec(w['90'])} <small>${rate(w['90'])} · ${count(w['90'].matches, 'partido', 'partidos')}</small>`)}
      ${kv('Últimos 360 días', `${rec(w['360'])} <small>${rate(w['360'])} · ${count(w['360'].matches, 'partido', 'partidos')}</small>`)}
      ${f.over_2_5_sets != null ? kv('Partidos de más de 2,5 sets', `${fmtPct(f.over_2_5_sets)} <small>de ${f.complete_matches}</small>`) : ''}
      ${f.tiebreaks != null ? kv('Partidos con tie-break', `${fmtPct(f.tiebreaks)} <small>de ${f.complete_matches}</small>`) : ''}
      ${stage('inicial', 'Primeras rondas')}${stage('avanzada', 'Cuartos, semifinal y final')}
      ${f.qualification.matches ? kv('Clasificación', `${rec(f.qualification)} <small>${rate(f.qualification)} · ${count(f.qualification.matches, 'partido', 'partidos')}</small>`) : ''}
      <ul class="win-list">${last}</ul></div>`;
  }

  function tennisForm(event) {
    const t = tennisStats(event);
    if (!t.players) return t.note;
    return `${formBlock(event, t.players[0], event.home)}${formBlock(event, t.players[1], event.away)}`;
  }

  function tennisSurface(event) {
    const t = tennisStats(event);
    if (!t.players) return t.note;
    const [a, b] = t.players;
    const current = surfaceKey(event);
    const rows = ['hard', 'clay', 'grass'].map(name => {
      const row = (p, kind) => {
        const r = p.surfaces[name][kind];
        return r && r.rate != null ? bar(`${p === a ? event.home : event.away}`, r.rate, `${rec(r)} (${kind === 'career' ? 'carrera' : 'temporada'})`) : '';
      };
      return `<div class="win-panel-box"><p class="eyebrow">${SURFACE_NAME[name].toUpperCase()}${current === name ? ' · ESTE PARTIDO' : ''}</p>${row(a, 'career')}${row(b, 'career')}${row(a, 'season')}${row(b, 'season')}${!a.surfaces[name].career.rate && !b.surfaces[name].career.rate ? '<p class="win-sub">Sin partidos registrados en esta superficie.</p>' : ''}</div>`;
    });
    return `${rows.join('')}`;
  }

  function tennisH2H(event) {
    const t = tennisStats(event);
    if (!t.players) return t.note;
    const swapped = t.players[0] !== t.data.players[0];
    const h = t.data.h2h;
    const winsHome = swapped ? h.second_wins : h.first_wins;
    const winsAway = swapped ? h.first_wins : h.second_wins;
    if (!h.matches.length) return '<div class="win-panel-box"><p class="eyebrow">CARA A CARA</p><p class="win-sub">Sin enfrentamientos previos registrados entre estos jugadores.</p></div>';
    const list = h.matches.map(m => {
      const homeWon = swapped ? !m.won : m.won;
      const score = swapped ? String(m.score || '').split(' ').map(set => set.split('-').reverse().join('-')).join(' ') : m.score;
      return `<li><span class="win-d">${esc(m.date.slice(0, 7))}</span><span>${esc(homeWon ? event.home : event.away)}<small>${esc(es(m.tournament))} · ${esc(es(m.round))}</small></span><span class="win-sc">${esc(score || '—')}</span><span></span></li>`;
    }).join('');
    return `<div class="win-panel-box"><p class="eyebrow">CARA A CARA</p><div class="win-duelscore"><strong>${winsHome}</strong><span>${esc(event.home)}</span><span>${esc(event.away)}</span><strong>${winsAway}</strong></div><ul class="win-list">${list}</ul><p class="win-sub">El marcador va desde el punto de vista del jugador que figura primero en la fuente.</p></div>`;
  }

  function tennisModel(event) {
    return `${games(event)}${registry(event)}`;
  }

  // ---- estadísticas de equipos de NBA: marcadores finales de la temporada regular, resumidos por el servidor «a la fecha» del partido
  // y pedidos solo al abrir una pestaña de estadísticas.
  // No hay alineaciones, estadio ni cuotas por cuarto en ninguna fuente validada: no se inventan.
  function nbaStats(event) {
    const entry = ctx.ensureNbaStats(event.id);
    const head = '<div class="win-panel-box"><p class="eyebrow">ESTADÍSTICAS DE LOS EQUIPOS</p>';
    if (entry.status === 'loading') return { note: `${head}<p class="win-sub">Consultando los marcadores de la temporada…</p></div>` };
    if (entry.status !== 'ready') return { note: `${head}<p class="win-sub">Todavía no hay estadísticas publicadas para este partido. Se calculan con los marcadores finales de la NBA.</p></div>` };
    const [a, b] = entry.data.teams;
    const swapped = normal(a.name) === normal(event.away) && normal(b.name) === normal(event.home);
    return { data: entry.data, teams: swapped ? [b, a] : [a, b] };
  }
  const shortDate = date => { const [y, m, d] = String(date).split('-'); return `${d}/${m}/${String(y).slice(2)}`; };
  const streakText = n => (!n ? '—' : n > 0 ? `${n} ${n === 1 ? 'victoria' : 'victorias'}` : `${-n} ${n === -1 ? 'derrota' : 'derrotas'}`);
  const restText = t => (t.rest_days == null ? '—' : t.back_to_back ? 'Back-to-back' : `${t.rest_days} ${t.rest_days === 1 ? 'día libre' : 'días libres'}`);
  const recRate = r => `${rec(r)} · ${rate(r)}`;

  function nbaCompare(event) {
    const n = nbaStats(event);
    if (!n.teams) return n.note;
    const [h, a] = n.teams;
    const played = t => t.season.won + t.season.lost;
    const diff = t => (t.scoring.points_for == null ? null : Math.round((t.scoring.points_for - t.scoring.points_against) * 10) / 10);
    const place = t => (t.standing.rank == null ? '—' : `#${t.standing.rank} ${t.standing.conference === 'este' ? 'Este' : 'Oeste'}`);
    const pts = v => (v == null ? '—' : num(v));
    const source = n.data.temporada ? `<p class="win-sub">Temporada regular ${esc(n.data.temporada)}: ${n.data.games_used} marcadores finales de la liga registrados antes de este partido.</p>` : '';
    return `<div class="win-panel-box"><p class="eyebrow">COMPARATIVA</p>${source}<div class="win-vshead"><strong>${esc(event.home)}</strong><strong>${esc(event.away)}</strong></div>
      ${versus('Partidos jugados', played(h), played(a), { neutral: true })}
      ${versus('Récord de la temporada', h.season.rate, a.season.rate, { shown: [recRate(h.season), recRate(a.season)] })}
      ${versus('Posición en su conferencia', h.standing.rank, a.standing.rank, { lower: true, shown: [place(h), place(a)] })}
      ${versus('Últimos 6 partidos', h.last6.rate, a.last6.rate, { shown: [recRate(h.last6), recRate(a.last6)] })}
      ${versus('Local en casa · visitante fuera', h.home.rate, a.away.rate, { shown: [recRate(h.home), recRate(a.away)] })}
      ${versus('Puntos a favor por partido', h.scoring.points_for, a.scoring.points_for, { text: pts })}
      ${versus('Puntos en contra por partido', h.scoring.points_against, a.scoring.points_against, { lower: true, text: pts })}
      ${versus('Diferencial por partido', diff(h), diff(a), { text: v => (v == null ? '—' : `${v > 0 ? '+' : ''}${num(v)}`) })}
      ${versus('Racha actual', h.streak, a.streak, { shown: [streakText(h.streak), streakText(a.streak)] })}
      ${versus('Descanso antes del partido', h.back_to_back ? -1 : h.rest_days, a.back_to_back ? -1 : a.rest_days, { shown: [restText(h), restText(a)] })}
      ${versus('Récord de la temporada pasada', h.last_season.rate, a.last_season.rate, { shown: [recRate(h.last_season), recRate(a.last_season)] })}
      </div>`;
  }

  function nbaForm(event) {
    const n = nbaStats(event);
    if (!n.teams) return n.note;
    const scope = ['all', 'home', 'away'].includes(state.winFormScope) ? state.winFormScope : 'all';
    const filter = `<div class="win-chips" role="group" aria-label="Partidos a mostrar">${[['all', 'Todos'], ['home', 'En casa'], ['away', 'Fuera']].map(([id, label]) => `<button type="button" class="chip ${scope === id ? 'selected' : ''}" data-win-form-scope="${id}" aria-pressed="${scope === id}">${label}</button>`).join('')}</div>`;
    const block = (t, name) => {
      const rows = t.form[scope];
      const won = rows.filter(r => r.won).length;
      const avg = key => (rows.length ? num(rows.reduce((sum, r) => sum + r[key], 0) / rows.length) : '—');
      const chips = rows.map(r => `<i class="win-res ${r.won ? 'is-win' : 'is-loss'}" title="${esc(shortDate(r.date))} · ${esc(r.opponent)}">${r.won ? 'G' : 'P'}</i>`).join('');
      const list = rows.map(r => `<li><span class="win-d">${esc(shortDate(r.date))}</span><span>${r.home ? 'vs' : '@'} ${esc(r.opponent)}<small>${r.home ? 'En casa' : 'Fuera'}</small></span><span class="win-sc">${r.points}-${r.opponent_points}</span><span class="win-res ${r.won ? 'is-win' : 'is-loss'}">${r.won ? 'G' : 'P'}</span></li>`).join('');
      return `<div class="win-panel-box"><p class="eyebrow">${esc(String(name).toUpperCase())}</p>${rows.length ? `<div class="win-chipline" aria-label="Partidos, del más reciente al más antiguo">${chips}</div>
        ${kv('Victorias · derrotas', `${won}-${rows.length - won} <small>${count(rows.length, 'partido', 'partidos')}</small>`)}
        ${kv('Puntos a favor · en contra', `${avg('points')} · ${avg('opponent_points')} <small>por partido</small>`)}
        <ul class="win-list win-list--dated">${list}</ul>` : '<p class="win-sub">Sin partidos registrados con este filtro.</p>'}</div>`;
    };
    return `<div class="win-panel-box"><p class="eyebrow">FORMA RECIENTE</p>${filter}</div>${block(n.teams[0], event.home)}${block(n.teams[1], event.away)}`;
  }

  function nbaH2H(event) {
    const n = nbaStats(event);
    if (!n.teams) return n.note;
    const h = n.data.h2h;
    // `home_wins` cuenta al primer equipo del feed; si la ficha los pone en el orden contrario, se intercambian.
    const swapped = n.teams[0] !== n.data.teams[0];
    const winsHome = swapped ? h.away_wins : h.home_wins, winsAway = swapped ? h.home_wins : h.away_wins;
    if (!h.matches.length) return '<div class="win-panel-box"><p class="eyebrow">CARA A CARA</p><p class="win-sub">Sin enfrentamientos registrados entre estos equipos en las últimas temporadas.</p></div>';
    const list = h.matches.map(m => `<li><span class="win-d">${esc(shortDate(m.date))}</span><span>${esc(m.home)}<small>vs ${esc(m.away)}</small></span><span class="win-sc">${m.home_points}-${m.away_points}</span><span class="win-res ${m.home_points > m.away_points ? 'is-win' : 'is-loss'}" title="Ganó ${esc(m.home_points > m.away_points ? m.home : m.away)}">${m.home_points > m.away_points ? 'L' : 'V'}</span></li>`).join('');
    return `<div class="win-panel-box"><p class="eyebrow">CARA A CARA · ÚLTIMOS ${h.matches.length}</p><p class="win-sub">Solo temporada regular.</p><div class="win-duelscore"><strong>${winsHome}</strong><span>${esc(event.home)}</span><span>${esc(event.away)}</span><strong>${winsAway}</strong></div>
      ${h.average_total != null ? kv('Total medio de puntos', num(h.average_total)) : ''}<ul class="win-list win-list--dated">${list}</ul>
      </div>`;
  }

  function nbaStandings(event) {
    const n = nbaStats(event);
    if (!n.teams) return n.note;
    const conf = t => (t.standing.conference === 'este' ? 'Conferencia Este' : t.standing.conference === 'oeste' ? 'Conferencia Oeste' : '');
    const row = t => `<tr><td class="n">${t.standing.rank == null ? '—' : t.standing.rank}</td><td>${esc(t.name)}<small class="win-cell-note">${conf(t)}</small></td><td class="n">${t.season.won + t.season.lost}</td><td class="n">${t.season.won}</td><td class="n">${t.season.lost}</td><td class="n">${rate(t.season)}</td><td class="n">${num(t.scoring.points_for)}</td><td class="n">${num(t.scoring.points_against)}</td><td class="n">${t.streak > 0 ? `${t.streak}V` : t.streak < 0 ? `${-t.streak}D` : '—'}</td></tr>`;
    return `<div class="win-panel-box"><p class="eyebrow">CLASIFICACIÓN</p><div class="win-table win-table--all"><table class="cyber-table cyber-table--compact"><thead><tr><th class="n">Pos.</th><th>Equipo</th><th class="n">J</th><th class="n">V</th><th class="n">D</th><th class="n">%</th><th class="n">PF</th><th class="n">PC</th><th class="n">Racha</th></tr></thead><tbody>${n.teams.map(row).join('')}</tbody></table></div>
      </div>`;
  }

  const TABS = { tenis: [['resumen', 'Resumen'], ['forma', 'Forma'], ['superficie', 'Superficie'], ['h2h', 'Cara a cara'], ['modelo', 'Modelo'], ['resultado', 'Resultado']],
    nba: [['resumen', 'Resumen'], ['comparativa', 'Comparativa'], ['forma', 'Forma'], ['h2h', 'Cara a cara'], ['clasificacion', 'Clasificación'],
      ['disponibilidad', 'Disponibilidad'], ['resultado', 'Resultado'], ['registro', 'Registro']] };

  function summary(event) {
    const parts = [duel(event)];
    if (event.sport === 'tenis') {
      parts.push(`<div class="win-panel-box"><p class="eyebrow">EL ENCUENTRO</p>${kv('Torneo', esc(event.league))}${event.surface ? kv('Superficie', esc(event.surface)) : ''}${kv('Hora', `${realDate(event.start)} ${realTime(event.start)}`)}${kv('Estado', esc(statusText(event)))}</div>`);
      const sets = event.markets.filter(m => /^Sets totales/.test(m.label) && !m.revised).sort((a, b) => lineOf(a.selection) - lineOf(b.selection));
      const tie = event.markets.find(m => /^Tie-break/.test(m.label));
      parts.push(`<div class="win-panel-box"><p class="eyebrow">CÓMO SE PROYECTA</p>${sets.map(m => bar(m.selection, m.probability, 'Sets totales')).join('')}${tie ? bar(`Tie-break: ${tie.selection}`, tie.probability) : ''}</div>`);
    } else {
      const total = event.markets.find(m => m.market === 'game_total' && !m.revised);
      const teams = event.markets.filter(m => m.market === 'team_points' && !m.revised);
      parts.push(`<div class="win-panel-box"><p class="eyebrow">EL PARTIDO</p>${kv('Hora', `${realDate(event.start)} ${realTime(event.start)}`)}${kv('Estado', esc(statusText(event)))}${event.score ? kv('Marcador', esc(event.score)) : ''}${event.official_url ? kv('Ficha oficial', `<a class="text-link" href="${esc(event.official_url)}" target="_blank" rel="noopener noreferrer">NBA.com ↗</a>`) : ''}</div>`);
      if (event.v2) {
        const p = event.team_projection;
        parts.push(`<div class="win-panel-box"><p class="eyebrow">PUNTOS ESPERADOS</p>${p ? kv(esc(event.home), num(p[0])) + kv(esc(event.away), num(p[1])) : '<p class="win-sub">Sin proyección de puntos publicada.</p>'}</div>`);
        return parts.join('');
      }
      parts.push(`<div class="win-panel-box"><p class="eyebrow">PROYECCIONES DEL MOTOR</p>${total ? kv('Total de puntos', `${num(total.estimate)} <small>(línea ${num(lineOf(total.selection))} · más de ${fmtPct(total.probability)})</small>`) : ''}${teams.map(m => kv(String(m.selection).split(' · ')[0], `${num(m.estimate)} <small>(línea ${num(lineOf(m.selection))} · más de ${fmtPct(m.probability)})</small>`)).join('')}${!total && !teams.length ? '<p class="win-sub">Sin proyecciones de equipo publicadas.</p>' : ''}</div>`);
    }
    return parts.join('');
  }

  function games(event) {
    const totals = event.markets.filter(m => /^Juegos totales/.test(m.label) && !m.revised).sort((a, b) => lineOf(a.selection) - lineOf(b.selection));
    const setWinners = event.markets.filter(m => /^Ganador de set/.test(m.label) && !m.revised);
    return `<div class="win-panel-box"><p class="eyebrow">JUEGOS TOTALES</p>${totals.length ? totals.map(m => bar(m.selection, m.probability)).join('') : '<p class="win-sub">Sin mercados de juegos publicados.</p>'}</div><div class="win-panel-box"><p class="eyebrow">GANADOR DE CADA SET</p>${setWinners.length ? setWinners.map(m => bar(`${m.selection}`, m.probability, m.label.replace('Ganador de set · ', ''))).join('') : '<p class="win-sub">Sin mercados de sets publicados.</p>'}</div>`;
  }

  function availability(event) {
    const a = event.availability;
    if (!a) return '<div class="win-panel-box"><p class="eyebrow">DISPONIBILIDAD</p><p class="win-sub">Este partido no trae reporte de lesiones del motor.</p></div>';
    const label = a.state === 'reporte_aplicado' ? 'Reporte oficial aplicado' : String(a.state || 'Sin dato').replace(/_/g, ' ');
    return `<div class="win-panel-box"><p class="eyebrow">REPORTE OFICIAL DE LESIONES</p>${kv('Estado', esc(label))}${kv('Jugadores listados', num(a.listed, 0))}${kv('Jugadores con historial usado', num(a.used, 0))}${a.report_timestamp_utc ? kv('Reporte de', `${realDate(a.report_timestamp_utc)} ${realTime(a.report_timestamp_utc)}`) : ''}${typeof a.report_url === 'string' && a.report_url.startsWith('https://') ? kv('Documento', `<a class="text-link" href="${esc(a.report_url)}" target="_blank" rel="noopener noreferrer">PDF oficial ↗</a>`) : ''}</div><div class="win-panel-box"><p class="eyebrow">LO QUE FALTA POR BAJAS</p>${kv(`Puntos · ${esc(event.home)}`, num(a.missing_points_home))}${kv(`Puntos · ${esc(event.away)}`, num(a.missing_points_away))}${kv(`Minutos · ${esc(event.home)}`, num(a.missing_minutes_home))}${kv(`Minutos · ${esc(event.away)}`, num(a.missing_minutes_away))}</div>`;
  }

  function result(event) {
    const decided = event.markets.filter(m => ['win', 'loss', 'push'].includes(m.outcome));
    if (!event.score && !decided.length) return '<div class="win-panel-box"><p class="eyebrow">RESULTADO</p><p class="win-sub">Se publica al terminar el encuentro.</p></div>';
    const wins = decided.filter(m => m.outcome === 'win').length, losses = decided.filter(m => m.outcome === 'loss').length;
    return `<div class="win-panel-box"><p class="eyebrow">RESULTADO</p>${event.score ? kv('Marcador', esc(event.score)) : ''}${kv('Mercados acertados', num(wins, 0))}${kv('Mercados fallados', num(losses, 0))}</div>${decided.length ? `<div class="win-panel-box"><p class="eyebrow">MERCADOS RESUELTOS</p>${decided.slice(0, 30).map(m => kv(`${m.label} · ${m.selection}`, `${fmtPct(m.probability)} ${outcomeBadge(m)}`)).join('')}${decided.length > 30 ? `<p class="win-sub">Y ${decided.length - 30} más.</p>` : ''}</div>` : ''}`;
  }

  function registry(event) {
    if (!event.seal) return `<div class="win-panel-box"><p class="eyebrow">REGISTRO DEL ANÁLISIS</p><p class="win-sub">${event.planned_seal ? `Aún no hay sello. Se registra alrededor de las ${realTime(event.planned_seal)} del ${realDate(event.planned_seal)}.` : 'Este partido no tiene un análisis sellado.'}</p></div>`;
    return `<div class="win-panel-box"><p class="eyebrow">REGISTRO DEL ANÁLISIS</p>${kv('Publicado', `${realDate(event.sealed_at)} ${realTime(event.sealed_at)}`)}<code class="win-code">${esc(event.seal)}</code></div>`;
  }

  function stats(event) {
    const tabs = TABS[event.sport];
    const tab = tabs.some(([id]) => id === state.winSportTab) ? state.winSportTab : 'resumen';
    const tennis = { resumen: () => tennisSummary(event), forma: () => tennisForm(event), superficie: () => tennisSurface(event), h2h: () => tennisH2H(event), modelo: () => tennisModel(event), resultado: () => result(event) };
    const body = (event.sport === 'tenis' ? tennis : { resumen: () => summary(event), comparativa: () => nbaCompare(event), forma: () => nbaForm(event), h2h: () => nbaH2H(event), clasificacion: () => nbaStandings(event),
      disponibilidad: () => availability(event), resultado: () => result(event), registro: () => registry(event) })[tab]();
    return `<div class="win-tabs-wrap"><div class="cyber-tabs cyber-tabs--pills cyber-tabs--scrollable" role="tablist" aria-label="Secciones de estadísticas">${tabs.map(([id, label]) => `<button type="button" role="tab" id="win-stab-${id}" aria-controls="win-stats-panel" aria-selected="${tab === id}" class="cyber-tab ${tab === id ? 'cyber-tab--active' : ''}" data-win-sport-tab="${id}">${label}</button>`).join('')}</div></div><div id="win-stats-panel" role="tabpanel" aria-labelledby="win-stab-${tab}" class="win-panel">${body}</div>`;
  }


  // ===== Pantalla genérica de un deporte del catálogo (Fase 4 · 4.4) =====
  // Reutiliza las piezas de arriba (tarjeta del pronóstico, tabla de mercados, `bar`, `kv`, `registry`) con los datos del contrato. NO pinta nada atado
  // a nba o tenis: ni jugadores, ni proyecciones, ni superficie, ni pestañas de estadísticas, ni cuotas de casas por `/web/deportes/…`.
  const SECCIONES_DEPORTE = ['dias', 'resumen', 'partidos'];                       // el orden de hoy; `destacado` solo si la definición lo pide
  const SECCIONES_PARTIDO = ['cabecera', 'pronostico', 'mercados', 'contenido', 'sello'];
  const porDefecto = lista => lista.map(seccion => ({ id: seccion, tipo: 'seccion', seccion, visible: true }));
  const hayCelda = v => (v == null ? '—' : typeof v === 'number' ? Number(v).toLocaleString('es-MX', { maximumFractionDigits: 3 }) : esc(v));

  function avisoMarkup(bloque) {
    const aviso = ctx.aviso?.(bloque);
    if (!aviso) return '';
    const variante = { exito: ' cyber-alert--success', aviso: ' cyber-alert--warning', peligro: ' cyber-alert--error' }[aviso.tono] || '';
    return `<div class="cyber-alert${variante}" role="status"><p>${esc(aviso.texto)}</p>${aviso.enlace ? `<a class="text-link" href="${esc(aviso.enlace)}">Ver más ↗</a>` : ''}</div>`;
  }
  const vipMarkup = () => '<div class="win-vipbar"><p><strong>Acceso VIP</strong>Conoce los planes para ver más análisis.</p><button type="button" class="cyber-btn cyber-btn--green cyber-btn--sm" data-route="planes">Acceso VIP ↗</button></div>';

  // Bloques de contenido del servidor (`partido.bloques`): cada tipo con un componente que ya existe. Todo texto se escapa.
  function bloqueContenido(b) {
    const titulo = `<p class="eyebrow">${esc(b.titulo)}</p>`;
    if (b.tipo === 'tabla') {
      const numerica = i => b.filas.length > 0 && b.filas.every(f => f[i] == null || typeof f[i] === 'number');
      return `<div class="win-panel-box">${titulo}<div class="win-table" tabindex="0" role="region" aria-label="${esc(b.titulo)}"><table class="cyber-table cyber-table--compact"><thead><tr>${b.columnas.map((c, i) => `<th scope="col"${numerica(i) ? ' class="n"' : ''}>${esc(c)}</th>`).join('')}</tr></thead><tbody>${b.filas.map(f => `<tr>${f.map((c, i) => `<td${numerica(i) ? ' class="n"' : ''}>${hayCelda(c)}</td>`).join('')}</tr>`).join('')}</tbody></table></div></div>`;
    }
    if (b.tipo === 'barras') return `<div class="win-panel-box">${titulo}${b.items.map(i => bar(i.etiqueta, i.valor, i.nota)).join('')}</div>`;
    if (b.tipo === 'pares') return `<div class="win-panel-box">${titulo}${b.items.map(i => kv(i.etiqueta, hayCelda(i.valor))).join('')}</div>`;
    return `<div class="cyber-alert" role="note"><p class="cyber-alert__title">${esc(b.titulo)}</p><p>${esc(b.cuerpo)}</p></div>`;
  }
  function contenido(event) {
    if (event.markets_status === 'loading') return '<div class="win-panel-box"><p class="eyebrow">ESTADÍSTICAS</p><p class="win-sub" role="status">Consultando las estadísticas del partido…</p></div>';
    if (event.markets_status === 'error') return '<div class="win-panel-box"><p class="eyebrow">ESTADÍSTICAS</p><p class="win-sub" role="status">No se pudieron cargar las estadísticas. <button type="button" class="text-link" data-action="refresh-public">Reintentar</button></p></div>';
    return event.bloques?.length ? event.bloques.map(bloqueContenido).join('') : '<div class="win-panel-box"><p class="eyebrow">ESTADÍSTICAS</p><p class="win-sub">Este partido no tiene estadísticas publicadas.</p></div>';
  }

  // Mercados por familia del catálogo (nombre en el idioma de la página; `otros` al final), con la misma tabla y el mismo límite de filas que NBA y tenis.
  function mercadosGenerico(event) {
    const info = genericInfo(event.sport);
    const name = id => info.nombreFamilia?.(id) ?? id;
    const cabecera = '<section aria-label="Mercados"><div class="win-mk-head"><h3>Mercados</h3></div>';
    if (event.markets_status === 'loading') return `${cabecera}<p class="win-sub" role="status">Cargando mercados del partido…</p></section>`;
    if (event.markets_status === 'error') return `${cabecera}<p class="win-sub" role="status">No se pudieron cargar los mercados. <button type="button" class="text-link" data-action="refresh-public">Reintentar</button></p></section>`;
    const familias = familiasDeEvento(event, info.orden || []);
    if (!familias.length) return `${cabecera}<p class="win-sub">Todavía no hay mercados publicados para este partido.</p></section>`;
    const feat = featuredSportMarket(event);
    const actual = familias.find(f => f.id === state.winSportFam) || familias[0];
    const porProbabilidad = [...actual.markets].sort((a, b) => b.probability - a.probability || (marketQuote(b).price || 0) - (marketQuote(a).price || 0));
    const liquidado = hayLiquidado(porProbabilidad, m => m.outcome);
    const all = ordenLiquidado(porProbabilidad, { resultado: m => m.outcome, cuota: m => marketQuote(m).price, prob: m => m.probability });
    const shown = state.winAll ? all : all.slice(0, ROW_LIMIT);
    const chips = familias.length > 1 ? `<div class="win-chips" role="group" aria-label="Familia de mercado">${familias.map(f => `<button type="button" class="chip ${actual.id === f.id ? 'selected' : ''}" data-win-sport-fam="${esc(f.id)}" aria-pressed="${actual.id === f.id}">${esc(name(f.id))}</button>`).join('')}</div>` : '';
    return `<section aria-label="Mercados"><div class="win-mk-head"><h3>Mercados</h3>${chips}</div>${tablaMercados(shown, marketLine(event, feat), false)}${masMercados(all, liquidado ? 'acertados primero, de mayor a menor cuota' : 'de mayor a menor probabilidad')}</section>`;
  }
  function pronosticoGenerico(event) {
    return `<article class="win-pick cyber-card" aria-label="Pronóstico destacado">${pickCard(event, featuredSportMarket(event))}</article>`;
  }

  // Destacado del día: entre los eventos del día, el pronóstico que ya marcó el servidor como destacado con mayor probabilidad. No calcula nada nuevo.
  function destacadoDia(list) {
    let mejor = null;
    for (const e of list) { const m = featuredSportMarket(e); if (m && (!mejor || m.probability > mejor.m.probability)) mejor = { e, m }; }
    if (!mejor) return '';
    const { e, m } = mejor, pct = (m.probability * 100).toFixed(1);
    return `<aside class="cyber-card cyber-card--green win-pk-featured" aria-label="Pronóstico destacado del día"><p class="eyebrow">Pronóstico destacado</p><span class="win-pk-league">${esc(e.league)} · ${realDate(e.start)} ${realTime(e.start)}</span><div class="win-pk-pick is-single"><div class="win-pk-sel"><small>${esc(e.home)} vs ${esc(e.away)}</small><strong>${esc(m.selection)}</strong></div></div><div class="win-pk-prob"><span>Probabilidad del modelo</span><b>${fmtPct(m.probability)}</b><div class="cyber-progress cyber-progress--green cyber-progress--sm" data-value="${pct}" role="progressbar" aria-label="Probabilidad del pronóstico destacado" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${pct}"><div class="cyber-progress__bar"></div></div></div><button type="button" class="cyber-btn cyber-btn--sm cyber-btn--green win-pk-go" data-win-event="${esc(keyOf(e))}">Ver análisis y mercados ↗</button></aside>`;
  }

  // Panel del partido según la pantalla `partido`: pronóstico y mercados a la izquierda; contenido y sello a la derecha. Un aviso o la llamada VIP van con la
  // sección anterior (o con la siguiente si abren la lista). `estadisticas`, `h2h` y `alertas` no existen en un deporte nuevo y se ignoran.
  function panesGenerico(event, bloques) {
    const donde = { pronostico: 'pron', mercados: 'pron', contenido: 'stats', sello: 'stats' };
    const pieza = { pronostico: () => pronosticoGenerico(event), mercados: () => mercadosGenerico(event), contenido: () => contenido(event), sello: () => registry(event) };
    const items = bloques.filter(b => b.visible && (b.tipo !== 'seccion' || donde[b.seccion])).map(b => ({ b, pane: b.tipo === 'seccion' ? donde[b.seccion] : null }));
    let previo = null;
    for (const it of items) { if (it.pane) previo = it.pane; else it.pane = previo; }
    const primero = items.find(it => it.pane)?.pane || 'pron';
    for (const it of items) if (!it.pane) it.pane = primero;
    const out = { pron: [], stats: [] };
    for (const { b, pane } of items) out[pane].push(b.tipo === 'seccion' ? pieza[b.seccion]() : b.tipo === 'aviso' ? avisoMarkup(b) : vipMarkup());
    const vacio = '<p class="win-sub">Sin contenido en esta vista.</p>';
    return { pron: out.pron.join('') || vacio, stats: out.stats.join('') || vacio };
  }

  // Montaje de la ventana de un deporte genérico: las mismas zonas que NBA y tenis, ordenadas y filtradas por la pantalla `deporte`.
  function layoutGenerico({ sport, list, entry, event, dayNav, chipsDia, rail, matchbar }) {
    const info = genericInfo(sport);
    const deporte = info.pantallaDeporte?.length ? info.pantallaDeporte : porDefecto(SECCIONES_DEPORTE);
    const partido = info.pantallaPartido?.length ? info.pantallaPartido : porDefecto(SECCIONES_PARTIDO);
    const visible = nombre => deporte.some(b => b.tipo === 'seccion' && b.seccion === nombre && b.visible);
    const cabecera = partido.find(b => b.tipo === 'seccion' && b.seccion === 'cabecera');
    const conLista = visible('partidos');
    const panes = event ? panesGenerico(event, partido) : null;
    let cuerpo;
    if (event) {
      cuerpo = `<div class="win-switch" role="tablist" aria-label="Vista del evento"><button type="button" role="tab" aria-selected="${state.winPane === 'pron'}" data-win-pane="pron">Pronóstico</button><button type="button" role="tab" aria-selected="${state.winPane === 'stats'}" data-win-pane="stats">Estadísticas</button></div><div class="win-split"><div class="win-pane" id="win-pane-pron" aria-label="Pronóstico">${panes.pron}</div><div class="win-pane" id="win-pane-stats" aria-label="Estadísticas">${panes.stats}</div></div>`;
    } else if (entry.status === 'error') {
      cuerpo = '<div class="empty-state"><span aria-hidden="true">◎</span><h3>No se pudo consultar este deporte</h3><p>El servidor no respondió con la cartelera.</p><button type="button" class="text-link" data-action="refresh-public">Volver a consultar ↻</button></div>';
    } else {
      cuerpo = `<div class="empty-state"><span class="empty-symbol">◷</span><h3>${entry.status === 'loading' ? 'Cargando eventos…' : 'Sin eventos este día'}</h3><p>${entry.status === 'loading' ? 'Consultando la publicación del motor.' : 'Prueba con otro día.'}</p></div>`;
    }
    const work = `<div class="win-work"${conLista ? '' : ' style="grid-template-columns:minmax(0,1fr)"'}>${conLista ? `<aside class="win-rail" aria-label="Eventos del día">${rail}</aside>` : ''}<section class="win-main" aria-label="Evento seleccionado"><div class="win-matchbar">${cabecera && !cabecera.visible ? matchbar.split('<div class="win-team">')[0] : matchbar}</div>${cuerpo}</section></div>`;
    const piezas = [];
    let tira = '';
    const vaciarTira = () => { if (tira) piezas.push(`<div class="win-strip" role="toolbar" aria-label="Fecha">${tira}</div>`); tira = ''; };
    let puesta = false;
    for (const b of deporte) {
      if (!b.visible) continue;
      if (b.tipo === 'seccion' && (b.seccion === 'dias' || b.seccion === 'resumen')) { tira += b.seccion === 'dias' ? dayNav : chipsDia; continue; }
      vaciarTira();
      if (b.tipo === 'aviso') piezas.push(avisoMarkup(b));
      else if (b.tipo === 'vip') piezas.push(vipMarkup());
      else if (b.seccion === 'destacado') piezas.push(destacadoDia(list));
      else if (b.seccion === 'partidos' && !puesta) { piezas.push(work); puesta = true; }
    }
    vaciarTira();
    if (!puesta) piezas.push(work);          // sin la lista visible el detalle se pinta igual, a todo el ancho
    return `<div class="win" data-pane="${state.winPane}">${piezas.join('')}</div>`;
  }

  // ---- ventana completa
  function view() {
    const sport = state.sport;
    const entry = ensureSport(sport);
    const events = entry.status === 'ready' ? entry.events : [];
    let list = dayEvents(events);
    // Sin día elegido por la persona, se abre el día más cercano que tenga eventos publicados.
    if (entry.status === 'ready' && !list.length && !state.winDayPinned) {
      const near = [-1, 1, -2, 2, -3, 3].find(offset => dayEvents(events, offset).length);
      if (near !== undefined) { state.winDay = near; list = dayEvents(events); }
    }
    // Mientras cargan los eventos la lista está vacía: no se borra el partido que pidió la URL (/nba/<partido>/).
    if (entry.status === 'ready' && !list.some(e => keyOf(e) === state.winEvent)) state.winEvent = keyOf(list.find(e => e.status !== 'finished') || list[0] || { sport, id: '' });
    const selected = list.find(e => keyOf(e) === state.winEvent);
    const event = selected?.sport === 'nba' && selected.v2 ? withNbaMarkets(selected, ctx.ensureNbaMarkets?.(selected))
      : selected?.generico ? withDetalle(selected, ctx.ensureDetalle?.(selected.sport, selected.id)) : selected;
    state.winResetFlag = state.winLastEvent !== state.winEvent;
    if (state.winResetFlag) { state.winSportFam = ''; state.winAll = false; state.winPlayerSearch = ''; }
    state.winLastEvent = state.winEvent;
    state.winEvList = list.map(keyOf);
    const index = state.winEvList.indexOf(state.winEvent);
    const leagues = [...new Set(list.map(e => e.league))];
    let rail;
    if (entry.status === 'loading') rail = '<p class="rail-empty">Cargando eventos…</p>';
    else if (entry.status !== 'ready') rail = '<p class="rail-empty">No se pudo cargar la fuente. <button type="button" class="text-link" data-action="refresh-public">Reintentar ↻</button></p>';
    else if (!list.length) rail = '<p class="rail-empty">No hay eventos publicados este día.</p>';
    else rail = leagues.map(league => `<h3 class="win-league">${esc(league)}</h3>${list.filter(e => e.league === league).map(e => `<button type="button" class="win-row" data-win-event="${esc(keyOf(e))}" aria-pressed="${keyOf(e) === state.winEvent}" ${keyOf(e) === state.winEvent ? 'aria-current="true"' : ''}><span class="win-when"><b>${realTime(e.start)}</b>${e.status === 'finished' ? '<small>Final</small>' : ''}</span><span class="win-names"><span>${mark(e.home, e.sport, e.home_img)}<span>${esc(e.home)}</span></span><span>${mark(e.away, e.sport, e.away_img)}<span>${esc(e.away)}</span></span></span></button>`).join('')}`).join('');
    const days = [-3, -2, -1, 0, 1, 2, 3];
    const dayNav = `<div class="win-day"><button type="button" data-win-day="${Math.max(-3, state.winDay - 1)}" aria-label="Día anterior" ${state.winDay <= -3 ? 'disabled' : ''}>‹</button><strong>${esc(dayLabel(state.winDay))} · ${dateFmt(addDays(state.winDay), { day: 'numeric', month: 'short' })}</strong><button type="button" data-win-day="${Math.min(3, state.winDay + 1)}" aria-label="Día siguiente" ${state.winDay >= 3 ? 'disabled' : ''}>›</button></div>`;
    const chipsDia = `<div class="win-chips" role="group" aria-label="${nameOf(sport)}: eventos del día"><span class="chip selected" aria-hidden="true">${nameOf(sport)} <b>${list.length}</b></span></div>`;
    const strip = dayNav + chipsDia;
    const bar0 = event
      ? `<div class="win-picker"><button type="button" data-win-ev-step="-1" aria-label="Evento anterior" ${index <= 0 ? 'disabled' : ''}>‹</button><label class="win-select"><span class="sr-only">Elegir evento</span><select id="win-event-select">${list.map(e => `<option value="${esc(keyOf(e))}" ${keyOf(e) === state.winEvent ? 'selected' : ''}>${realTime(e.start)} · ${esc(e.home)} vs ${esc(e.away)}</option>`).join('')}</select></label><button type="button" data-win-ev-step="1" aria-label="Evento siguiente" ${index >= list.length - 1 ? 'disabled' : ''}>›</button></div><div class="win-team">${mark(event.home, event.sport)}<div><strong>${esc(event.home)}</strong><small>${sport === 'tenis' ? esc(event.league) : 'Local'}</small></div></div><span class="win-vs ${event.score ? 'score' : ''}">${event.score ? esc(event.score) : 'VS'}</span><div class="win-team is-away">${mark(event.away, event.sport)}<div><strong>${esc(event.away)}</strong><small>${sport === 'tenis' ? esc(event.surface || 'Individual') : 'Visitante'}</small></div></div><div class="win-meta"><span>${esc(event.league)} · ${dateFmt(new Date(event.start), { weekday: 'short', day: 'numeric', month: 'short' })} ${realTime(event.start)}</span>${badge(statusText(event), statusKind(event))}</div>`
      : '';
    if (isGeneric(sport)) return { markup: layoutGenerico({ sport, list, entry, event, dayNav, chipsDia, rail, matchbar: bar0 }), days };
    const body = event
      ? `<div class="win-switch" role="tablist" aria-label="Vista del evento"><button type="button" role="tab" aria-selected="${state.winPane === 'pron'}" data-win-pane="pron">Pronóstico</button><button type="button" role="tab" aria-selected="${state.winPane === 'stats'}" data-win-pane="stats">Estadísticas</button></div><div class="win-split"><div class="win-pane" id="win-pane-pron" aria-label="Pronóstico">${forecast(event)}</div><div class="win-pane" id="win-pane-stats" aria-label="Estadísticas">${stats(event)}</div></div>`
      : `<div class="empty-state"><span class="empty-symbol">◷</span><h3>${entry.status === 'loading' ? 'Cargando eventos…' : 'Sin eventos este día'}</h3><p>${entry.status === 'loading' ? 'Consultando la publicación del motor.' : 'Prueba con otro día.'}</p></div>`;
    return { markup: `<div class="win" data-pane="${state.winPane}"><div class="win-strip" role="toolbar" aria-label="Fecha">${strip}</div><div class="win-work"><aside class="win-rail" aria-label="Eventos del día">${rail}</aside><section class="win-main" aria-label="Evento seleccionado"><div class="win-matchbar">${bar0}</div>${body}</section></div></div>`, days };
  }

  return { view: () => view().markup };
}
