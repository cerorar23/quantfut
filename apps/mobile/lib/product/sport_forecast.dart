import 'package:flutter/material.dart';

import '../l10n/app_locale.dart';
import 'live_api.dart';
import 'live_forecast.dart' show ForecastTile;
import 'live_statistics.dart';
import 'live_widgets.dart';
import 'qf_shapes.dart';
import 'qf_theme.dart';

/// Tarjeta de análisis del pronóstico destacado de tenis o NBA: la misma de fútbol, con los datos del deporte.
/// Todo viene del servidor (`/web/deportes/{tenis,nba}/analisis/{id}`): casillas elegidas según el mercado y resumen
/// redactado. Lo que no llega no se dibuja: una casilla nunca se rellena con «—».
class SportForecastPanel extends StatelessWidget {
  const SportForecastPanel({
    super.key,
    required this.analisis,
    required this.pickText,
    required this.probability,
    required this.quote,
    required this.home,
    required this.away,
    this.nba = false,
  });

  final JsonMap analisis;
  final String pickText;
  final double probability;

  /// Etiqueta de cuota ya construida por quien llama (puede ser un widget vacío si no hay cuota).
  final Widget quote;
  final String home, away;

  /// Las casillas son las de NBA (si no, las de tenis).
  final bool nba;

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

  String _signed(dynamic v) =>
      v is num ? '${v > 0 ? '+' : ''}${decimalText(v, 1)}' : '—';

  String _dec(dynamic v) => v is num ? decimalText(v, 1) : '—';

  ForecastTile _nbaTile(AppLocalizations l10n, JsonMap c) {
    final pair = '${c['a']} · ${c['b']}';
    switch (c['id']) {
      case 'proy_total':
        return ForecastTile(
          icon: Icons.sports_basketball,
          label: l10n.tileProjTotal,
          color: liveGold,
          value: _dec(c['total']),
          caption: l10n.tileXgCaption(_dec(c['a']), _dec(c['b'])),
        );
      case 'proy_margen':
        return ForecastTile(
          icon: Icons.sports_basketball,
          label: l10n.tileProjMargin,
          color: liveGold,
          value: _signed(c['margen']),
          caption: l10n.tileXgCaption(_dec(c['a']), _dec(c['b'])),
        );
      case 'proy_equipo':
        return ForecastTile(
          icon: Icons.sports_basketball,
          label: l10n.tileProjTeamPoints,
          color: liveGold,
          value: _dec(c['a']),
          caption: c['equipo'] == 'a' ? home : away,
        );
      case 'ritmo':
        return ForecastTile(
          icon: Icons.speed,
          label: l10n.tilePace,
          color: statsLime,
          value: _dec(c['pos']),
          caption: l10n.tilePaceCaption,
        );
      case 'forma':
        return ForecastTile(
          icon: Icons.trending_up,
          label: l10n.tileFormLabel((c['n'] as num?)?.toInt() ?? 6),
          color: statsPurple,
          value: '${c['a_w']}-${c['a_l']} · ${c['b_w']}-${c['b_l']}',
          caption: l10n.tileRecordCaption,
        );
      case 'dif':
        return ForecastTile(
          icon: Icons.bar_chart,
          label: l10n.tilePointDiff,
          color: statsLime,
          value: '${_signed(c['a'])} · ${_signed(c['b'])}',
          caption: l10n.tilePointDiffCaption,
        );
      case 'ataque':
        return ForecastTile(
          icon: Icons.sports_basketball,
          label: l10n.tilePointsFor,
          color: statsLime,
          value: '${_dec(c['a'])} · ${_dec(c['b'])}',
          caption: l10n.tilePointsForCaption,
        );
      case 'ataque_defensa':
        return ForecastTile(
          icon: Icons.shield_outlined,
          label: l10n.tileAttackDefense,
          color: statsPurple,
          value: '${_dec(c['a'])} vs ${_dec(c['b'])}',
          caption: l10n.tileAttackDefenseCaption,
        );
      case 'h2h_total':
        return ForecastTile(
          icon: Icons.compare_arrows,
          label: l10n.tileH2hTotal,
          color: statsPurple,
          value: _dec(c['avg']),
          caption: l10n.tileMatchesCount((c['n'] as num?)?.toInt() ?? 0),
        );
      case 'descanso':
        return ForecastTile(
          icon: Icons.bedtime_outlined,
          label: l10n.tileRest,
          color: statsPurple,
          value: pair,
          caption: l10n.tileRestCaption,
        );
      default: // 'bajas'
        return ForecastTile(
          icon: Icons.healing,
          label: l10n.tileOut,
          color: liveGold,
          value: pair,
          caption: l10n.tileOutCaption,
        );
    }
  }

  ForecastTile _tile(AppLocalizations l10n, JsonMap c) {
    if (nba) return _nbaTile(l10n, c);
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
