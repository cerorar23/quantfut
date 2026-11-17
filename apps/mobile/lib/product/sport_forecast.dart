import 'package:flutter/material.dart';

import '../l10n/app_locale.dart';
import 'live_api.dart';
import 'live_forecast.dart' show ForecastTile;
import 'live_statistics.dart';
import 'live_widgets.dart';
import 'qf_shapes.dart';
import 'qf_theme.dart';

/// Tarjeta de análisis del pronóstico destacado de tenis: la misma de fútbol, con los datos del deporte.
/// Todo viene del servidor (`/web/deportes/tenis/analisis/{id}`): casillas elegidas según el mercado y resumen
/// redactado. Lo que no llega no se dibuja: una casilla nunca se rellena con «—».
class TennisForecastPanel extends StatelessWidget {
  const TennisForecastPanel({
    super.key,
    required this.analisis,
    required this.pickText,
    required this.probability,
    required this.quote,
    required this.home,
    required this.away,
  });

  final JsonMap analisis;
  final String pickText;
  final double probability;

  /// Etiqueta de cuota ya construida por quien llama (puede ser un widget vacío si no hay cuota).
  final Widget quote;
  final String home, away;

  List<JsonMap> get _casillas {
    final raw = analisis['casillas'];
    return raw is List
        ? [
            for (final c in raw)
              if (c is Map) jsonMap(c),
          ]
        : const [];
  }

  static String _surname(String name) {
    final parts = name.trim().split(RegExp(r'\s+'));
    return parts.isEmpty ? name : parts.last;
  }

  String _pct(dynamic v) => v is num ? '${v.round()} %' : '—';
  String _pair(JsonMap c) => '${_pct(c['a'])} · ${_pct(c['b'])}';

  String _surface(AppLocalizations l10n, dynamic sup) => switch ('$sup') {
    'hard' => l10n.sportSurfaceHard,
    'clay' => l10n.sportSurfaceClay,
    'grass' => l10n.sportSurfaceGrass,
    _ => l10n.tileAllSurfaces,
  };

  ForecastTile _tile(AppLocalizations l10n, JsonMap c) {
    final players = '${_surname(home)} · ${_surname(away)}';
    switch (c['id']) {
      case 'saque':
        return ForecastTile(
          icon: Icons.sports_tennis,
          label: l10n.tileHold,
          color: liveGold,
          value: _pair(c),
          caption: '$players · ${_surface(l10n, c['sup'])}',
        );
      case 'resto':
        return ForecastTile(
          icon: Icons.swap_vert,
          label: l10n.tileBreak,
          color: statsLime,
          value: _pair(c),
          caption: '$players · ${_surface(l10n, c['sup'])}',
        );
      case 'rank':
        return ForecastTile(
          icon: Icons.leaderboard,
          label: l10n.tileRank,
          color: liveCyan,
          value: '#${c['a']} · #${c['b']}',
          caption: players,
        );
      case 'forma':
        return ForecastTile(
          icon: Icons.trending_up,
          label: l10n.tileFormLabel((c['n_a'] as num?)?.toInt() ?? 10),
          color: statsPurple,
          value: '${c['a']} – ${c['b']}',
          caption: players,
        );
      case 'h2h':
        return ForecastTile(
          icon: Icons.compare_arrows,
          label: l10n.tileH2h,
          color: statsPurple,
          value: '${c['a']} – ${c['b']}',
          caption:
              '$players · ${l10n.tileMatchesCount((c['n'] as num?)?.toInt() ?? 0)}',
        );
      case 'superficie':
        return ForecastTile(
          icon: Icons.terrain,
          label: l10n.tileSurfaceWins,
          color: statsLime,
          value: _pair(c),
          caption: '$players · ${_surface(l10n, c['sup'])}',
        );
      default: // 'tres_sets'
        return ForecastTile(
          icon: Icons.format_list_numbered,
          label: l10n.tileThreeSets,
          color: statsLime,
          value: _pair(c),
          caption: players,
        );
    }
  }

  String _summary(AppLocalizations l10n) {
    final redactado = jsonMap(analisis['resumen'])[AppLocale.instance.code];
    if (redactado is String && redactado.trim().isNotEmpty) {
      return redactado.trim();
    }
    return l10n.dictPick(pickText, realPercent(probability));
  }

  Widget _chip(String text, Color color) => Container(
    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
    decoration: ShapeDecoration(
      color: color.withValues(alpha: .12),
      shape: CutCornerBorder(
        cut: 5,
        border: BorderSide(color: color.withValues(alpha: .5)),
      ),
    ),
    child: Text(
      text,
      style: TextStyle(
        fontSize: 10,
        fontWeight: FontWeight.w700,
        letterSpacing: .6,
        color: color,
      ),
    ),
  );

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final c = _casillas;
    final level = probability >= .75
        ? l10n.levelHigh
        : probability >= .6
        ? l10n.levelSolid
        : l10n.levelModerate;
    final probTile = ForecastTile(
      icon: Icons.track_changes,
      label: l10n.tileProbability,
      value: realPercent(probability),
      color: liveCyan,
      caption: l10n.tileFairOdds(
        decimalText(probability > 0 ? 1 / probability : null),
      ),
    );
    Widget slot(int i) => Expanded(
      child: i < c.length ? _tile(l10n, c[i]) : const SizedBox.shrink(),
    );
    return Container(
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
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Flexible(
                child: liveText(
                  l10n.forecastTitle,
                  size: 11,
                  color: liveGreen,
                  bold: true,
                ),
              ),
              _chip(l10n.forecastSourceModel, liveCyan),
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
                    Flexible(child: _chip(l10n.forecastFeatured, liveGreen)),
                    const Spacer(),
                    _chip(level, liveGold),
                    const SizedBox(width: 6),
                    _chip(l10n.forecastFree, liveGold),
                  ],
                ),
                const SizedBox(height: 10),
                Row(
                  crossAxisAlignment: CrossAxisAlignment.center,
                  children: [
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            pickText,
                            maxLines: 2,
                            overflow: TextOverflow.ellipsis,
                            style: const TextStyle(
                              fontSize: 19,
                              fontWeight: FontWeight.w800,
                              color: Colors.white,
                            ),
                          ),
                          const SizedBox(height: 6),
                          quote,
                        ],
                      ),
                    ),
                    const SizedBox(width: 10),
                    Text(
                      realPercent(probability),
                      style: const TextStyle(
                        fontFamily: qfMono,
                        fontWeight: FontWeight.w700,
                        fontSize: 26,
                        color: liveGreen,
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
          const SizedBox(height: 12),
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
                liveText(_summary(l10n), size: 13, color: Colors.white70),
                const SizedBox(height: 8),
                liveText(l10n.forecastCanFail, size: 10, color: liveMuted),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
