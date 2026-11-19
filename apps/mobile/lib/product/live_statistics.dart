import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../l10n/app_locale.dart';
import 'analysis_football.dart';
import 'live_api.dart';
import 'live_match_facts.dart';
import 'live_widgets.dart';
import 'qf_shapes.dart';
import 'qf_theme.dart';

const statsPurple = QfColors.cyan;
const statsLime = QfColors.chrome;
const statsPanel = QfColors.surface;

double? statisticNumber(dynamic value) =>
    value is num && value.isFinite && value >= 0 ? value.toDouble() : null;

Widget statisticsCard(Widget child) => Container(
  width: double.infinity,
  margin: const EdgeInsets.only(bottom: 12),
  padding: const EdgeInsets.all(14),
  decoration: const ShapeDecoration(
    color: QfColors.surface,
    shape: CutCornerBorder(
      cut: 8,
      side: BorderSide(color: QfColors.border),
    ),
  ),
  child: child,
);

Widget statisticsHeading(String text) => Padding(
  padding: const EdgeInsets.fromLTRB(0, 14, 0, 8),
  child: Text(
    text.toUpperCase(),
    style: const TextStyle(
      fontFamily: qfDisplay,
      fontSize: 12,
      fontWeight: FontWeight.w700,
      letterSpacing: 1.2,
      color: QfColors.cyan,
    ),
  ),
);

class MatchStatistics extends StatelessWidget {
  const MatchStatistics({
    super.key,
    required this.data,
    required this.api,
    this.onAlerts,
    this.onH2h,
  });

  final JsonMap data;
  final QuantFutApi api;

  /// Abre la pestaña de alertas desde la tarjeta de datos del partido.
  final VoidCallback? onAlerts;

  /// Abre la pestaña H2H.
  final VoidCallback? onH2h;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    if (!featureEnabled(data, 'estadisticas')) {
      return training(featureMessage(data, 'estadisticas'));
    }
    final ficha = jsonMap(data['ficha']);
    final local = jsonMap(ficha['local']), away = jsonMap(ficha['visitante']);
    final lm = jsonMap(jsonMap(local['promedios'])['todos']);
    final am = jsonMap(jsonMap(away['promedios'])['todos']);
    final ln = (lm['n'] as num?)?.toInt() ?? 0;
    final an = (am['n'] as num?)?.toInt() ?? 0;
    final hasZeroMatches = ln == 0 && an == 0;

    final probMap = jsonMap(ficha['probabilities']);
    final hasProbabilities = probMap.isNotEmpty;
    final hasFacts = ficha['bajas'] != null ||
        local['ultimo_once'] != null ||
        away['ultimo_once'] != null;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        if (hasProbabilities) ...[
          statisticsHeading(l10n.statSummaryTitle),
          MatchProbabilitySummary(
            probabilities: probMap,
            local: '${local['nombre'] ?? l10n.commonHome}',
            away: '${away['nombre'] ?? l10n.commonAway}',
          ),
        ],
        if (hasFacts) ...[
          statisticsCard(
            MatchFacts(ficha: ficha, api: api, onAlerts: onAlerts),
          ),
        ],
        if (hasZeroMatches)
          Padding(
            padding: const EdgeInsets.symmetric(vertical: 8),
            child: Text(
              l10n.statAveragesNote(ln, an),
              style: const TextStyle(
                fontFamily: qfMono,
                fontSize: 11,
                color: QfColors.muted,
              ),
            ),
          ),
        FootballAnalysis(
          ficha: ficha,
          api: api,
          onH2h: onH2h,
          onAlerts: onAlerts,
        ),
      ],
    );
  }
}

class HistoricalComparison extends StatelessWidget {
  const HistoricalComparison({
    super.key,
    required this.label,
    this.local,
    this.away,
    this.percentage = false,
  });

  final String label;
  final double? local, away;
  final bool percentage;

  @override
  Widget build(BuildContext context) {
    final available = local != null && away != null && local! + away! > 0;
    String value(double? n) => n == null
        ? '—'
        : percentage
            ? percentText(n, 1)
            : decimalText(n, 2);
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Column(
        children: [
          Row(
            children: [
              Text(
                value(local),
                style: const TextStyle(
                  fontFamily: qfMono,
                  fontSize: 12,
                  fontWeight: FontWeight.w700,
                  color: QfColors.cyan,
                ),
              ),
              Expanded(
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 10),
                  child: Text(
                    label,
                    textAlign: TextAlign.center,
                    style: const TextStyle(
                      fontFamily: qfDisplay,
                      fontSize: 11,
                      fontWeight: FontWeight.w700,
                      color: QfColors.muted,
                    ),
                  ),
                ),
              ),
              Text(
                value(away),
                style: const TextStyle(
                  fontFamily: qfMono,
                  fontSize: 12,
                  fontWeight: FontWeight.w700,
                  color: QfColors.chrome,
                ),
              ),
            ],
          ),
          const SizedBox(height: 6),
          ClipRRect(
            borderRadius: BorderRadius.circular(2),
            child: SizedBox(
              height: 4,
              child: available
                  ? LayoutBuilder(
                      builder: (context, constraints) => Row(
                        children: [
                          SizedBox(
                            width: constraints.maxWidth * local! / (local! + away!),
                            child: Container(color: QfColors.cyan),
                          ),
                          Expanded(child: Container(color: QfColors.chrome)),
                        ],
                      ),
                    )
                  : Container(color: QfColors.track),
            ),
          ),
        ],
      ),
    );
  }
}

class MatchProbabilitySummary extends StatelessWidget {
  const MatchProbabilitySummary({
    super.key,
    required this.probabilities,
    required this.local,
    required this.away,
  });

  final JsonMap probabilities;
  final String local, away;

  @override
  Widget build(BuildContext context) {
    final values = [
      'home',
      'draw',
      'away',
    ].map((k) => statisticNumber(probabilities[k])).toList();
    final valid = values.every((v) => v != null && v <= 1) &&
        (values.fold<double>(0, (sum, v) => sum + (v ?? 0)) - 1).abs() < .05;
    final names = [local, context.l10n.commonDraw, away];
    const colors = [QfColors.cyan, QfColors.slate, QfColors.chrome];

    return statisticsCard(
      Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            context.l10n.statProbTitle.toUpperCase(),
            style: const TextStyle(
              fontFamily: qfDisplay,
              fontSize: 11,
              fontWeight: FontWeight.w700,
              letterSpacing: 1.2,
              color: QfColors.cyan,
            ),
          ),
          const SizedBox(height: 12),
          if (valid)
            ClipRRect(
              borderRadius: BorderRadius.circular(2),
              child: SizedBox(
                height: 6,
                child: Row(
                  children: [
                    for (var i = 0; i < 3; i++)
                      if (values[i]! > 0)
                        Expanded(
                          flex: math.max(1, (values[i]! * 10000).round()),
                          child: Container(color: colors[i]),
                        ),
                  ],
                ),
              ),
            )
          else
            Container(
              height: 6,
              decoration: BoxDecoration(
                color: QfColors.track,
                borderRadius: BorderRadius.circular(2),
              ),
            ),
          const SizedBox(height: 12),
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              for (var i = 0; i < 3; i++)
                Expanded(
                  child: Column(
                    children: [
                      Text(
                        valid ? realPercent(values[i]) : '—',
                        style: TextStyle(
                          fontFamily: qfMono,
                          fontSize: 18,
                          fontWeight: FontWeight.w700,
                          color: colors[i],
                        ),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        names[i],
                        textAlign: TextAlign.center,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(
                          fontFamily: qfBody,
                          fontSize: 11,
                          fontWeight: FontWeight.w500,
                          color: QfColors.muted,
                        ),
                      ),
                    ],
                  ),
                ),
            ],
          ),
        ],
      ),
    );
  }
}
