import 'package:flutter/material.dart';

import '../l10n/app_locale.dart';
import '../l10n/pick_labels.dart';
import 'featured_rule.dart';
import 'live_api.dart';
import 'live_statistics.dart';
import 'live_widgets.dart';
import 'qf_shapes.dart';
import 'qf_theme.dart';

export '../l10n/pick_labels.dart' show marketName;

/// Marcador real mientras el partido se juega (`partido.vivo`). Si el servidor
/// no lo manda, no se dibuja nada. Muestra cuánto hace de la última lectura:
/// el dato se refresca por ciclos, no es un directo.
class LiveScoreStrip extends StatelessWidget {
  const LiveScoreStrip({super.key, required this.ficha});
  final JsonMap ficha;

  static String _minute(JsonMap vivo) {
    final status = vivo['estado'];
    final l10n = AppLocale.instance.l10n;
    if (status == 'HT') return l10n.forecastHalfTime;
    final minute = vivo['minuto'];
    return minute is num ? "${minute.toInt()}'" : l10n.forecastInPlay;
  }

  @override
  Widget build(BuildContext context) {
    final vivo = jsonMap(jsonMap(ficha['partido'])['vivo']);
    final score = vivo['marcador'];
    if (score is! List || score.length != 2 || score.any((g) => g is! num)) {
      return const SizedBox.shrink();
    }
    final l10n = context.l10n;
    final home = jsonMap(ficha['local'])['nombre'] ?? l10n.commonHome;
    final away = jsonMap(ficha['visitante'])['nombre'] ?? l10n.commonAway;
    final updated = dateValue(vivo['actualizado']);
    final ago = updated == null
        ? null
        : DateTime.now().difference(updated).inMinutes.clamp(0, 999);
    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(14),
      decoration: const ShapeDecoration(
        color: QfColors.surface,
        shape: CutCornerBorder(
          cut: 10,
          border: BorderSide(color: Color.fromRGBO(5, 255, 161, 0.35)),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                width: 7,
                height: 7,
                decoration: const BoxDecoration(
                  color: liveGreen,
                  shape: BoxShape.circle,
                ),
              ),
              const SizedBox(width: 6),
              liveText(_minute(vivo), size: 12, color: liveGreen, bold: true),
            ],
          ),
          const SizedBox(height: 8),
          Row(
            children: [
              Expanded(
                child: Text(
                  '$home',
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  textAlign: TextAlign.right,
                  style: const TextStyle(
                    fontSize: 13,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ),
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 12),
                child: Text(
                  '${(score[0] as num).toInt()} — ${(score[1] as num).toInt()}',
                  style: const TextStyle(
                    fontSize: 22,
                    fontWeight: FontWeight.w800,
                  ),
                ),
              ),
              Expanded(
                child: Text(
                  '$away',
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    fontSize: 13,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          liveText(
            ago == null
                ? l10n.forecastLiveScore
                : l10n.forecastLiveScoreAgo(ago),
            size: 10,
            color: liveMuted,
          ),
        ],
      ),
    );
  }
}

/// Destacado del partido, «probabilidad máxima segura» (ver `featured_rule.dart`): entre los
/// pronósticos sellados con cuota publicada >= 1,20 y probabilidad >= 75 %, gana el de mayor
/// probabilidad; en empate, el de mayor cuota. Sin candidatos válidos no se destaca ninguno.
JsonMap? featuredPick(List<JsonMap> picks) => bestBySafety<JsonMap>(
  picks,
  (p) => p['prob'],
  (p) => p['ref_price'] ?? p['price'],
);

/// Pronóstico destacado + indicadores + dictamen, todo con datos entregados
/// por el servidor. Lo que no llega se muestra como «—», nunca se rellena.
class ForecastPanel extends StatelessWidget {
  const ForecastPanel({super.key, required this.pick, required this.ficha});
  final JsonMap pick, ficha;

  /// Casillas del análisis que el servidor eligió según el mercado del pick (vacío en servidores antiguos).
  List<JsonMap> get _casillas {
    final raw = jsonMap(pick['analisis'])['casillas'];
    return raw is List
        ? [
            for (final c in raw)
              if (c is Map) jsonMap(c),
          ]
        : const [];
  }

  String get dictamen {
    final redactado = jsonMap(
      jsonMap(pick['analisis'])['resumen'],
    )[AppLocale.instance.code];
    final l10n = AppLocale.instance.l10n;
    if (redactado is String && redactado.trim().isNotEmpty) {
      // El precio nunca lo redacta la IA: va con el texto fijo, correcto en los 6 idiomas.
      final precio = _priceSentence(l10n);
      return precio == null ? redactado.trim() : '${redactado.trim()} $precio';
    }
    final local = jsonMap(ficha['local'])['nombre'] ?? l10n.dictHomeDefault;
    final away = jsonMap(ficha['visitante'])['nombre'] ?? l10n.dictAwayDefault;
    final parts = <String>[
      l10n.dictPick(
        pick['market'] == null && pick['texto'] == null
            ? l10n.dictPickDefault
            : pickText(pick, home: local, away: away),
        realPercent(pick['prob']),
      ),
    ];
    final xg = jsonMap(pick['xg']);
    if (xg['total'] is num) {
      parts.add(
        l10n.dictXg(
          decimalText(xg['total']),
          '$local',
          decimalText(xg['local']),
          '$away',
          decimalText(xg['visita']),
        ),
      );
    }
    final precio = _priceSentence(l10n);
    if (precio != null) parts.add(precio);
    return parts.join(' ');
  }

  /// Cuota publicada frente a la justa del modelo (null si falta alguna de las dos).
  String? _priceSentence(AppLocalizations l10n) {
    final price = pick['ref_price'] ?? pick['price'];
    final prob = pick['prob'];
    if (price is num && prob is num && prob > 0) {
      final edge = price * prob - 1;
      return edge >= 0
          ? l10n.dictOddsAbove(decimalText(1 / prob))
          : l10n.dictOddsBelow(decimalText(1 / prob));
    }
    return null;
  }

  String _pct(dynamic v) => v is num ? '${v.round()} %' : '—';
  String _pair(JsonMap c) => '${_pct(c['a'])} · ${_pct(c['b'])}';
  String _signed(dynamic v) =>
      v is num ? '${v > 0 ? '+' : ''}${decimalText(v, 1)}' : '—';

  /// Primera fila: probabilidad + primera casilla del servidor; segunda fila: las otras dos.
  List<Widget> _analysisRows(
    BuildContext context,
    List<JsonMap> c,
    dynamic prob,
    String home,
    String away,
  ) {
    final l10n = context.l10n;
    final probTile = _Tile(
      icon: Icons.track_changes,
      label: l10n.tileProbability,
      value: realPercent(prob),
      color: liveCyan,
      caption: l10n.tileFairOdds(
        decimalText(prob is num && prob > 0 ? 1 / prob : null),
      ),
    );
    Widget slot(int i) => Expanded(
      child: i < c.length
          ? _analysisTile(l10n, c[i], home, away)
          : const SizedBox.shrink(),
    );
    return [
      Row(
        children: [
          Expanded(child: probTile),
          const SizedBox(width: 10),
          slot(0),
        ],
      ),
      if (c.length > 1) ...[
        const SizedBox(height: 10),
        Row(children: [slot(1), const SizedBox(width: 10), slot(2)]),
      ],
    ];
  }

  _Tile _analysisTile(
    AppLocalizations l10n,
    JsonMap c,
    String home,
    String away,
  ) {
    switch (c['id']) {
      case 'xg':
        return _Tile(
          icon: Icons.sports_soccer,
          label: l10n.tileXg,
          color: liveGold,
          value: decimalText(c['total']),
          caption: l10n.tileXgCaption(decimalText(c['a']), decimalText(c['b'])),
        );
      case 'xg_equipo':
        return _Tile(
          icon: Icons.sports_soccer,
          label: l10n.tileXg,
          color: liveGold,
          value: decimalText(c['a']),
          caption: c['equipo'] == 'a' ? home : away,
        );
      case 'empate':
        return _Tile(
          icon: Icons.compare_arrows,
          label: l10n.tileDraws,
          color: statsPurple,
          value: _pair(c),
          caption: c['liga'] is num
              ? l10n.tileDrawsCaption('${c['liga']}')
              : l10n.tileSplitCaption,
        );
      case 'forma':
        return _Tile(
          icon: Icons.trending_up,
          label: l10n.tileFormLabel((c['n_a'] as num?)?.toInt() ?? 5),
          color: statsPurple,
          value: '${c['a']} – ${c['b']}',
          caption: l10n.tileFormCaption,
        );
      case 'xgd':
        return _Tile(
          icon: Icons.bar_chart,
          label: l10n.tileXgd,
          color: statsLime,
          value: '${_signed(c['a'])} · ${_signed(c['b'])}',
          caption: l10n.tileXgdCaption,
        );
      case 'tendencia':
        return _Tile(
          icon: Icons.bar_chart,
          label: l10n.tileGoalsTrend,
          color: statsLime,
          value: _pair(c),
          caption: l10n.tileTrendCaption,
        );
      case 'ambos':
        return _Tile(
          icon: Icons.swap_horiz,
          label: l10n.tileBtts,
          color: statsPurple,
          value: _pair(c),
          caption: l10n.tileBttsCaption,
        );
      case 'goles_partido':
        return _Tile(
          icon: Icons.sports_soccer,
          label: l10n.tileGoalsMatch,
          color: liveGold,
          value: '${decimalText(c['a'], 1)} · ${decimalText(c['b'], 1)}',
          caption: l10n.tileGoalsMatchCaption,
        );
      case 'marca':
        return _Tile(
          icon: Icons.sports_soccer,
          label: l10n.tileScores,
          color: statsLime,
          value: _pct(c['a']),
          caption: l10n.tileScoresCaption,
        );
      case 'concede':
        return _Tile(
          icon: Icons.shield_outlined,
          label: l10n.tileConcedes,
          color: statsPurple,
          value: decimalText(c['a'], 1),
          caption: l10n.tilePerMatch,
        );
      default: // 'locvis'
        return _Tile(
          icon: Icons.home_outlined,
          label: l10n.tileHomeAway,
          color: statsPurple,
          value: _pair(c),
          caption: l10n.tileSplitCaption,
        );
    }
  }

  Widget _resultBanner(JsonMap pick) {
    final outcome = pick['outcome'];
    final won = outcome == 'win';
    final color = outcome == null
        ? liveGold
        : won
        ? liveGreen
        : const Color(0xffe85667);
    final score = pick['home_goals'] is num && pick['away_goals'] is num
        ? ' · ${pick['home_goals']}-${pick['away_goals']}'
        : '';
    final l10n = AppLocale.instance.l10n;
    final label = outcome == null
        ? (awaitingResult(pick['kickoff_utc'])
              ? l10n.bannerAwaiting
              : l10n.bannerLive)
        : won
        ? l10n.bannerWon(score)
        : l10n.bannerLost(score);
    return _chip(label, color);
  }

  /// Porcentaje de partidos recientes con más de 2,5 goles (promedio de ambos equipos).
  double? get _trend {
    double? share(JsonMap team) {
      final v = jsonMap(jsonMap(team['promedios'])['todos'])['pct_mas_2_5'];
      return v is num && v.isFinite && v >= 0 && v <= 100 ? v.toDouble() : null;
    }

    final a = share(jsonMap(ficha['local'])),
        b = share(jsonMap(ficha['visitante']));
    return a != null && b != null ? (a + b) / 2 : null;
  }

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final prob = pick['prob'];
    final price = pick['ref_price'] ?? pick['price'];
    final xg = jsonMap(pick['xg']);
    final modelo = jsonMap(ficha['modelo']);
    final probs = jsonMap(ficha['probabilities']);
    final local = jsonMap(ficha['local']), away = jsonMap(ficha['visitante']);
    final free = pick['free'] == true;
    final rawBook = pick['ref_book'] ?? pick['book'];
    final book = rawBook == null ? null : bookName(rawBook);
    // Favorito 1X2: del modelo (o del 1X2 guardado), el lado con más probabilidad.
    final side = <(String, num)>[
      if ((modelo['local'] ?? probs['home']) is num)
        (
          '${local['nombre'] ?? l10n.commonHome}',
          (modelo['local'] ?? probs['home']) as num,
        ),
      if ((modelo['visita'] ?? probs['away']) is num)
        (
          '${away['nombre'] ?? l10n.commonAway}',
          (modelo['visita'] ?? probs['away']) as num,
        ),
    ]..sort((a, b) => b.$2.compareTo(a.$2));
    final over25 = modelo['mas_2_5'] is num
        ? (modelo['mas_2_5'] as num) * 100
        : _trend;
    final level = prob is num
        ? (prob >= .75
              ? l10n.levelHigh
              : prob >= .6
              ? l10n.levelSolid
              : l10n.levelModerate)
        : null;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Container(
          padding: const EdgeInsets.all(14),
          decoration: const ShapeDecoration(
            color: QfColors.surface,
            shape: CutCornerBorder(
              cut: 12,
              border: BorderSide(color: QfColors.border),
            ),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Expanded(
                    child: liveText(
                      l10n.forecastTitle,
                      size: 12,
                      color: liveGreen,
                      bold: true,
                    ),
                  ),
                  _chip(
                    modelo['fuente'] == 'mercado'
                        ? l10n.forecastSourceMarket
                        : l10n.forecastSourceModel,
                    liveCyan,
                  ),
                ],
              ),
              const SizedBox(height: 12),
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(14),
                decoration: const ShapeDecoration(
                  color: Color.fromRGBO(5, 255, 161, 0.06),
                  shape: CutCornerBorder(
                    cut: 10,
                    border: BorderSide(
                      color: Color.fromRGBO(5, 255, 161, 0.4),
                      width: 1,
                    ),
                  ),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Flexible(
                          child: _chip(l10n.forecastFeatured, liveGreen),
                        ),
                        const Spacer(),
                        if (level != null) ...[
                          _chip(level, liveGold),
                          const SizedBox(width: 6),
                        ],
                        _chip(
                          free ? l10n.forecastFree : l10n.forecastUnlocked,
                          liveGold,
                        ),
                      ],
                    ),
                    if (pick['started'] == true) ...[
                      const SizedBox(height: 10),
                      _resultBanner(pick),
                    ],
                    const SizedBox(height: 12),
                    Row(
                      crossAxisAlignment: CrossAxisAlignment.center,
                      children: [
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                pickText(
                                  pick,
                                  home: local['nombre'],
                                  away: away['nombre'],
                                ),
                                style: const TextStyle(
                                  fontSize: 20,
                                  fontWeight: FontWeight.w800,
                                  height: 1.15,
                                ),
                              ),
                              const SizedBox(height: 6),
                              liveText(
                                marketName(pick['market']),
                                size: 12,
                                color: liveGreen,
                                bold: true,
                              ),
                            ],
                          ),
                        ),
                        const SizedBox(width: 12),
                        Column(
                          children: [
                            Container(
                              padding: const EdgeInsets.symmetric(
                                horizontal: 14,
                                vertical: 9,
                              ),
                              decoration: BoxDecoration(
                                color: liveGreen.withValues(alpha: .18),
                                borderRadius: BorderRadius.circular(12),
                              ),
                              child: liveText(
                                '@${decimalText(price)}',
                                size: 20,
                                color: liveGreen,
                                bold: true,
                              ),
                            ),
                            const SizedBox(height: 6),
                            liveText(
                              l10n.forecastProbCalc(realPercent(prob)),
                              size: 10,
                              color: liveGreen,
                            ),
                          ],
                        ),
                      ],
                    ),
                    if (book != null || pick['odds_as_of'] != null) ...[
                      const SizedBox(height: 10),
                      liveText(
                        '${l10n.forecastOddsAtPublish}${book != null ? ' · $book' : ''}${pick['odds_as_of'] != null ? ' · ${kickoffText(pick['odds_as_of'])}' : ''}',
                        size: 10,
                        color: liveMuted,
                      ),
                    ],
                  ],
                ),
              ),
              const SizedBox(height: 10),
              if (_casillas.isNotEmpty)
                ..._analysisRows(
                  context,
                  _casillas,
                  prob,
                  '${local['nombre'] ?? l10n.commonHome}',
                  '${away['nombre'] ?? l10n.commonAway}',
                )
              else ...[
                Row(
                  children: [
                    Expanded(
                      child: _Tile(
                        icon: Icons.track_changes,
                        label: l10n.tileProbability,
                        value: realPercent(prob),
                        color: liveCyan,
                        caption: l10n.tileFairOdds(
                          decimalText(
                            prob is num && prob > 0 ? 1 / prob : null,
                          ),
                        ),
                      ),
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: _Tile(
                        icon: Icons.sports_soccer,
                        label: l10n.tileXg,
                        value: decimalText(xg['total']),
                        color: liveGold,
                        caption: xg['total'] is num
                            ? l10n.tileXgCaption(
                                decimalText(xg['local']),
                                decimalText(xg['visita']),
                              )
                            : l10n.tileXgNA,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 10),
                Row(
                  children: [
                    Expanded(
                      child: _Tile(
                        icon: Icons.compare_arrows,
                        label: l10n.tileFavorite,
                        value: side.isEmpty ? '—' : realPercent(side.first.$2),
                        color: statsPurple,
                        caption: side.isEmpty
                            ? l10n.tileFavoriteNA
                            : side.length > 1
                            ? l10n.tileFavoriteLead(
                                side.first.$1,
                                ((side.first.$2 - side.last.$2) * 100).round(),
                              )
                            : side.first.$1,
                      ),
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: _Tile(
                        icon: Icons.bar_chart,
                        label: l10n.tileGoalsTrend,
                        value: over25 == null ? '—' : realPercent(over25 / 100),
                        color: statsLime,
                        caption: over25 == null
                            ? l10n.tileGoalsNA
                            : modelo['mas_2_5'] is num
                            ? l10n.tileOver25Model
                            : l10n.tileOver25Recent,
                      ),
                    ),
                  ],
                ),
              ],
              const SizedBox(height: 12),
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(14),
                decoration: const ShapeDecoration(
                  color: QfColors.bg,
                  shape: CutCornerBorder(
                    cut: 8,
                    border: BorderSide(color: QfColors.border),
                  ),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    liveText(
                      l10n.forecastVerdictTitle,
                      size: 11,
                      color: liveCyan,
                      bold: true,
                    ),
                    const SizedBox(height: 8),
                    liveText(dictamen, size: 13, color: Colors.white70),
                    if (modelo['fuente'] == 'mercado') ...[
                      const SizedBox(height: 8),
                      liveText(
                        l10n.forecastMarketNote,
                        size: 10,
                        color: liveMuted,
                      ),
                    ],
                    const SizedBox(height: 8),
                    liveText(l10n.forecastCanFail, size: 10, color: liveMuted),
                  ],
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 18),
      ],
    );
  }

  Widget _chip(String text, Color color) => Container(
    padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 5),
    decoration: BoxDecoration(
      color: color.withValues(alpha: .14),
      borderRadius: BorderRadius.circular(8),
      border: Border.all(color: color.withValues(alpha: .4)),
    ),
    child: Text(
      text,
      maxLines: 1,
      overflow: TextOverflow.ellipsis,
      style: TextStyle(fontSize: 10, fontWeight: FontWeight.w800, color: color),
    ),
  );
}

/// Recuadro de un indicador: icono + etiqueta, valor grande y una línea de contexto.
class _Tile extends StatelessWidget {
  const _Tile({
    required this.icon,
    required this.label,
    required this.value,
    required this.color,
    required this.caption,
  });
  final IconData icon;
  final String label, value, caption;
  final Color color;

  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.all(12),
    decoration: const ShapeDecoration(
      color: QfColors.surface,
      shape: CutCornerBorder(
        cut: 8,
        border: BorderSide(color: QfColors.border),
      ),
    ),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        Text.rich(
          TextSpan(
            children: [
              WidgetSpan(
                alignment: PlaceholderAlignment.middle,
                child: Icon(icon, size: 12, color: liveMuted),
              ),
              TextSpan(text: '  ${label.toUpperCase()}'),
            ],
          ),
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
          style: const TextStyle(
            fontSize: 10,
            letterSpacing: .4,
            fontWeight: FontWeight.w700,
            color: liveMuted,
          ),
        ),
        const SizedBox(height: 8),
        FittedBox(
          fit: BoxFit.scaleDown,
          alignment: Alignment.centerLeft,
          child: Text(
            value,
            style: TextStyle(
              fontSize: 24,
              fontWeight: FontWeight.w800,
              color: color,
            ),
          ),
        ),
        const SizedBox(height: 4),
        Text(
          caption,
          maxLines: 2,
          overflow: TextOverflow.ellipsis,
          style: const TextStyle(fontSize: 10, color: liveMuted),
        ),
      ],
    ),
  );
}
