import 'package:flutter/material.dart';

import '../l10n/app_locale.dart';
import '../l10n/pick_labels.dart';
import 'live_api.dart';
import 'live_statistics.dart';
import 'live_widgets.dart';

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
      decoration: BoxDecoration(
        color: statsPanel,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: liveGreen.withValues(alpha: .35)),
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

/// El único pronóstico destacado de un partido: el de mayor probabilidad; si empatan,
/// el de la cuota más alta. Los que no traen probabilidad numérica no compiten (si ninguno
/// la trae, se muestra el primero).
JsonMap? featuredPick(List<JsonMap> picks) {
  double number(dynamic value) =>
      value is num && value.isFinite ? value.toDouble() : double.negativeInfinity;
  JsonMap? best;
  for (final pick in picks) {
    if (number(pick['prob']) == double.negativeInfinity) continue;
    if (best == null) {
      best = pick;
      continue;
    }
    final byProb = number(pick['prob']).compareTo(number(best['prob']));
    final byPrice = number(pick['ref_price'] ?? pick['price']).compareTo(
      number(best['ref_price'] ?? best['price']),
    );
    if (byProb > 0 || (byProb == 0 && byPrice > 0)) best = pick;
  }
  return best ?? (picks.isEmpty ? null : picks.first);
}

/// Pronóstico destacado + indicadores + dictamen, todo con datos entregados
/// por el servidor. Lo que no llega se muestra como «—», nunca se rellena.
class ForecastPanel extends StatelessWidget {
  const ForecastPanel({super.key, required this.pick, required this.ficha});
  final JsonMap pick, ficha;

  String get dictamen {
    final l10n = AppLocale.instance.l10n;
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
    final price = pick['ref_price'] ?? pick['price'];
    final prob = pick['prob'];
    if (price is num && prob is num && prob > 0) {
      final edge = price * prob - 1;
      parts.add(
        edge >= 0
            ? l10n.dictOddsAbove(decimalText(1 / prob))
            : l10n.dictOddsBelow(decimalText(1 / prob)),
      );
    }
    return parts.join(' ');
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
        ? l10n.bannerLive
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
    final book = pick['ref_book'] ?? pick['book'];
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
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(20),
            border: Border.all(color: liveGreen.withValues(alpha: .45)),
            gradient: LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: [
                liveGreen.withValues(alpha: .08),
                const Color(0xff0c1520),
              ],
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
                decoration: BoxDecoration(
                  color: liveGreen.withValues(alpha: .07),
                  borderRadius: BorderRadius.circular(16),
                  border: Border.all(color: liveGreen.withValues(alpha: .3)),
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
              Row(
                children: [
                  Expanded(
                    child: _Tile(
                      icon: '🎯',
                      label: l10n.tileProbability,
                      value: realPercent(prob),
                      color: liveCyan,
                      caption: l10n.tileFairOdds(
                        decimalText(prob is num && prob > 0 ? 1 / prob : null),
                      ),
                    ),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: _Tile(
                      icon: '⚽',
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
                      icon: '⚔',
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
                      icon: '📊',
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
              const SizedBox(height: 12),
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(14),
                decoration: BoxDecoration(
                  color: Colors.black.withValues(alpha: .25),
                  borderRadius: BorderRadius.circular(14),
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
      style: TextStyle(fontSize: 9, fontWeight: FontWeight.w800, color: color),
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
  final String icon, label, value, caption;
  final Color color;

  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.all(12),
    decoration: BoxDecoration(
      color: Colors.white.withValues(alpha: .04),
      borderRadius: BorderRadius.circular(14),
      border: Border.all(color: Colors.white.withValues(alpha: .07)),
    ),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        Text(
          '$icon  ${label.toUpperCase()}',
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
          style: const TextStyle(
            fontSize: 9,
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
