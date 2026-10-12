import 'dart:math' as math;

import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';

import '../l10n/app_locale.dart';
import '../l10n/pick_labels.dart';

import 'package:intl/intl.dart';

import 'live_api.dart';
import 'live_widgets.dart';
import '../widgets/countdown_timer.dart';

const statsPurple = Color(0xff7650ff), statsLime = Color(0xffbbf32a);
const statsPanel = Color(0xff1b1d20);

double? statisticNumber(dynamic value) =>
    value is num && value.isFinite && value >= 0 ? value.toDouble() : null;

Widget statisticsCard(Widget child) => Container(
  width: double.infinity,
  margin: const EdgeInsets.only(bottom: 12),
  padding: const EdgeInsets.all(16),
  decoration: BoxDecoration(
    color: statsPanel,
    borderRadius: BorderRadius.circular(16),
    border: Border.all(color: Colors.white.withValues(alpha: .04)),
  ),
  child: child,
);

Widget statisticsHeading(String text) => Padding(
  padding: const EdgeInsets.fromLTRB(0, 18, 0, 12),
  child: liveText(text.toUpperCase(), size: 12, bold: true),
);

class MatchStatistics extends StatelessWidget {
  const MatchStatistics({super.key, required this.data, required this.api});
  final JsonMap data;
  final QuantFutApi api;

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
    final h2h = featureEnabled(data, 'h2h')
        ? jsonMap(ficha['cara_a_cara'])
        : <String, dynamic>{};
    final hs = jsonMap(h2h['resumen']);
    final picks = jsonRows(data['picks']);
    final metrics = {
      'goles_favor': l10n.statGoalsFor,
      'goles_contra': l10n.statGoalsAgainst,
      'tiros_favor': l10n.statShots,
      'tiros_puerta_favor': l10n.statShotsOnTarget,
      'corners_favor': l10n.marketCorners,
      'pct_porteria_cero': l10n.statCleanSheet,
      'pct_ambos_marcan': l10n.marketBtts,
      'pct_mas_2_5': l10n.statOver25,
      'xg_favor': l10n.statXgHistoric,
    };
    final radarLabels = {
      'goles_favor': l10n.statGoalsFor,
      'tiros_favor': l10n.statShots,
      'tiros_puerta_favor': l10n.statOnTargetShort,
      'corners_favor': l10n.marketCorners,
      'pct_porteria_cero': l10n.statCleanSheet,
      'goles_contra': l10n.statGoalsAgainst,
      'xg_favor': 'xG',
    };
    final radarKeys = radarLabels.keys
        .where(
          (k) =>
              statisticNumber(lm[k]) != null && statisticNumber(am[k]) != null,
        )
        .toList();
    final hasRadar =
        radarKeys.length >= 3 &&
        radarKeys.any(
          (k) =>
              (statisticNumber(lm[k]) ?? 0) + (statisticNumber(am[k]) ?? 0) > 0,
        );

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        statisticsHeading(l10n.statSummaryTitle),
        MatchProbabilitySummary(
          probabilities: jsonMap(ficha['probabilities']),
          local: '${local['nombre'] ?? l10n.commonHome}',
          away: '${away['nombre'] ?? l10n.commonAway}',
        ),
        if (picks.isNotEmpty)
          statisticsCard(
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                liveText(l10n.statPublishedPick, size: 10, color: liveMuted),
                const SizedBox(height: 8),
                liveText(
                  pickText(
                    picks.first,
                    home: local['nombre'],
                    away: away['nombre'],
                  ),
                  color: statsLime,
                  bold: true,
                  size: 17,
                ),
                const SizedBox(height: 8),
                liveText(
                  l10n.statPickProbOdds(
                    realPercent(picks.first['prob']),
                    decimalText(
                      picks.first['ref_price'] ?? picks.first['price'],
                    ),
                  ),
                  size: 12,
                ),
              ],
            ),
          )
        else if (data['locked'] == true)
          statisticsCard(
            liveText(l10n.statNeedsAccess, color: liveMuted, size: 12),
          ),
        statisticsCard(
          Column(
            children: [
              liveText(l10n.statGoalsAvgTitle, size: 10, color: liveMuted),
              const SizedBox(height: 14),
              Row(
                children: [
                  Expanded(child: _goalAverage(local, lm, statsPurple)),
                  liveText('vs', color: liveMuted, size: 12),
                  Expanded(child: _goalAverage(away, am, statsLime)),
                ],
              ),
              const SizedBox(height: 10),
              liveText(l10n.statGoalsAvgNote, color: liveMuted, size: 11),
            ],
          ),
        ),
        statisticsHeading(l10n.statFormTitle),
        Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Expanded(child: _form(context, local, statsPurple)),
            const SizedBox(width: 10),
            Expanded(child: _form(context, away, statsLime)),
          ],
        ),
        liveText(l10n.statFormLegend, color: liveMuted, size: 10),
        if ((statisticNumber(hs['n']) ?? 0) > 0)
          Padding(
            padding: const EdgeInsets.only(top: 16),
            child: statisticsCard(
              Row(
                children: [
                  const Icon(Icons.history, color: statsLime, size: 19),
                  const SizedBox(width: 10),
                  Expanded(
                    child: liveText(
                      l10n.statH2hSummary(
                        hs['n'] ?? '—',
                        local['nombre'] ?? '',
                        hs['victorias_local'] ?? '—',
                        away['nombre'] ?? '',
                        hs['victorias_visitante'] ?? '—',
                        hs['empates'] ?? '—',
                      ),
                      size: 12,
                    ),
                  ),
                ],
              ),
            ),
          ),
        statisticsHeading(l10n.statTeamStatsTitle),
        liveText(
          l10n.statAveragesNote(lm['n'] ?? 0, am['n'] ?? 0),
          color: liveMuted,
          size: 11,
        ),
        const SizedBox(height: 12),
        statisticsCard(
          Column(
            children: [
              if (hasRadar)
                SizedBox(
                  height: 260,
                  child: Padding(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 28,
                      vertical: 22,
                    ),
                    child: RadarChart(
                      RadarChartData(
                        radarShape: RadarShape.polygon,
                        tickCount: 4,
                        ticksTextStyle: const TextStyle(
                          color: Colors.transparent,
                          fontSize: 1,
                        ),
                        tickBorderData: const BorderSide(color: Colors.white10),
                        gridBorderData: const BorderSide(color: Colors.white10),
                        radarBorderData: const BorderSide(
                          color: Colors.white12,
                        ),
                        titleTextStyle: const TextStyle(
                          color: liveMuted,
                          fontSize: 9,
                          fontFamily: 'Gilroy Medium',
                        ),
                        getTitle: (i, angle) => RadarChartTitle(
                          text: radarLabels[radarKeys[i]]!,
                          angle: 0,
                        ),
                        radarTouchData: RadarTouchData(enabled: false),
                        dataSets: [
                          for (final entry in [
                            (lm, statsPurple),
                            (am, statsLime),
                          ])
                            RadarDataSet(
                              borderColor: entry.$2,
                              fillColor: entry.$2.withValues(alpha: .2),
                              entryRadius: 1.5,
                              dataEntries: radarKeys
                                  .map(
                                    (k) => RadarEntry(
                                      value:
                                          statisticNumber(entry.$1[k])! /
                                          math
                                              .max(
                                                statisticNumber(lm[k])!,
                                                statisticNumber(am[k])!,
                                              )
                                              .clamp(.0001, double.infinity) *
                                          100,
                                    ),
                                  )
                                  .toList(),
                            ),
                        ],
                      ),
                    ),
                  ),
                )
              else
                Padding(
                  padding: const EdgeInsets.symmetric(vertical: 24),
                  child: liveText(
                    l10n.statRadarNeeds,
                    color: liveMuted,
                    size: 12,
                  ),
                ),
              _legend(local, away),
              const SizedBox(height: 12),
              liveText(l10n.statRadarNote, color: liveMuted, size: 10),
            ],
          ),
        ),
        statisticsHeading(l10n.statCompareTitle),
        statisticsCard(
          Column(
            children: [
              _legend(local, away),
              const SizedBox(height: 14),
              for (final e in metrics.entries)
                HistoricalComparison(
                  label: e.value,
                  local: statisticNumber(lm[e.key]),
                  away: statisticNumber(am[e.key]),
                  percentage: e.key.startsWith('pct_'),
                ),
              liveText(l10n.statCompareNote, color: liveMuted, size: 10),
            ],
          ),
        ),
        statisticsHeading(l10n.statMinutesTitle),
        statisticsCard(
          liveText(l10n.statMinutesNA, color: liveMuted, size: 12),
        ),
        statisticsHeading(l10n.statSeasonTitle),
        for (final entry in [(local, statsPurple), (away, statsLime)])
          _season(context, entry.$1, entry.$2),
        if (featureEnabled(data, 'h2h')) ...[
          statisticsHeading(l10n.statH2hTitle),
          if (jsonRows(h2h['partidos']).isEmpty)
            statisticsCard(
              liveText(l10n.detailNoH2h, color: liveMuted, size: 12),
            )
          else
            ...jsonRows(h2h['partidos']).map((p) => h2hResult(p, local, away)),
        ],
        statisticsHeading(l10n.statPoissonTitle),
        statisticsCard(
          liveText(l10n.statPoissonNA, color: liveMuted, size: 12),
        ),
      ],
    );
  }

  Widget _goalAverage(JsonMap team, JsonMap averages, Color color) => Column(
    children: [
      liveText(
        decimalText(averages['goles_favor']),
        size: 28,
        bold: true,
        color: color,
      ),
      const SizedBox(height: 5),
      liveText('${team['nombre'] ?? ''}', size: 11),
    ],
  );

  Widget _form(BuildContext context, JsonMap team, Color color) {
    final l10n = context.l10n;
    final rows = jsonRows(jsonMap(team['forma'])['partidos']);
    return statisticsCard(
      Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          liveText('${team['nombre'] ?? ''}', bold: true, size: 12),
          const SizedBox(height: 12),
          if (rows.isEmpty)
            liveText(l10n.statFormNA, color: liveMuted, size: 11)
          else
            Wrap(
              spacing: 4,
              runSpacing: 4,
              children: rows.take(5).map((p) {
                final result = '${p['res'] ?? '—'}';
                final c = result == 'G'
                    ? const Color(0xff21af62)
                    : result == 'P'
                    ? const Color(0xffe85667)
                    : const Color(0xff5c6070);
                return Tooltip(
                  message:
                      '${kickoffText(p['fecha'])} · ${p['rival']} · ${p['marcador']}',
                  child: Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 7,
                      vertical: 5,
                    ),
                    decoration: BoxDecoration(
                      color: c,
                      borderRadius: BorderRadius.circular(5),
                    ),
                    child: liveText(resultLetter(result), size: 11, bold: true),
                  ),
                );
              }).toList(),
            ),
          const SizedBox(height: 9),
          liveText(
            l10n.statResultsAvailable(rows.length),
            color: color,
            size: 10,
          ),
        ],
      ),
    );
  }

  Widget _legend(JsonMap local, JsonMap away) => Row(
    children: [
      for (final entry in [(local, statsPurple), (away, statsLime)])
        Expanded(
          child: Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Container(width: 9, height: 9, color: entry.$2),
              const SizedBox(width: 6),
              Flexible(
                child: liveText('${entry.$1['nombre'] ?? ''}', size: 10),
              ),
            ],
          ),
        ),
    ],
  );

  Widget _season(BuildContext context, JsonMap team, Color color) {
    final l10n = context.l10n;
    final table = jsonMap(team['clasificacion']);
    final rows = jsonRows(jsonMap(team['forma'])['partidos']);
    String best(bool home) {
      final wins =
          rows
              .where(
                (p) =>
                    p['local'] == home &&
                    p['res'] == 'G' &&
                    statisticNumber(p['gf']) != null &&
                    statisticNumber(p['gc']) != null,
              )
              .toList()
            ..sort(
              (a, b) => ((b['gf'] as num) - (b['gc'] as num)).compareTo(
                (a['gf'] as num) - (a['gc'] as num),
              ),
            );
      return wins.isEmpty ? '—' : '${wins.first['marcador']}';
    }

    int streak(String result) =>
        rows.takeWhile((p) => p['res'] == result).length;
    return statisticsCard(
      Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          liveText('${team['nombre'] ?? ''}', color: color, bold: true),
          if (table.isNotEmpty) ...[
            const SizedBox(height: 8),
            liveText(
              '${table['liga'] ?? ''} · ${table['grupo'] ?? ''}',
              color: liveMuted,
              size: 11,
            ),
            const SizedBox(height: 10),
            Wrap(
              spacing: 16,
              runSpacing: 8,
              children: [
                liveText(l10n.statPosition(table['posicion'] ?? '—'), size: 12),
                liveText(l10n.statPoints(table['puntos'] ?? '—'), size: 12),
                liveText(l10n.statPlayed(table['jugados'] ?? '—'), size: 12),
              ],
            ),
          ] else ...[
            const SizedBox(height: 8),
            liveText(l10n.statStandingNA, color: liveMuted, size: 11),
          ],
          const Divider(height: 26, color: Colors.white10),
          liveText(
            l10n.statLastMatches(rows.length),
            color: liveMuted,
            size: 10,
          ),
          const SizedBox(height: 10),
          LayoutBuilder(
            builder: (context, constraints) => Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                for (final item in [
                  (l10n.statBestHome, best(true)),
                  (l10n.statBestAway, best(false)),
                  (l10n.statWinStreak, rows.isEmpty ? '—' : '${streak('G')}'),
                  (l10n.statDrawStreak, rows.isEmpty ? '—' : '${streak('E')}'),
                ])
                  Container(
                    width: (constraints.maxWidth - 8) / 2,
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: Colors.white.withValues(alpha: .03),
                      borderRadius: BorderRadius.circular(10),
                    ),
                    child: Column(
                      children: [
                        liveText(item.$2, color: color, bold: true, size: 19),
                        const SizedBox(height: 5),
                        liveText(item.$1, size: 10),
                      ],
                    ),
                  ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget h2hResult(JsonMap p, JsonMap local, JsonMap away) => statisticsCard(
    Column(
      children: [
        for (final side
            in p['local'] == true
                ? [(local, p['gf']), (away, p['gc'])]
                : [(away, p['gc']), (local, p['gf'])])
          Padding(
            padding: const EdgeInsets.symmetric(vertical: 5),
            child: Row(
              children: [
                TeamCrest(team: side.$1, api: api, size: 20),
                const SizedBox(width: 8),
                Expanded(
                  child: liveText(
                    '${side.$1['nombre'] ?? ''}',
                    bold: true,
                    size: 12,
                  ),
                ),
                liveText('${side.$2 ?? '—'}', bold: true),
              ],
            ),
          ),
        const Divider(color: Colors.white10),
        Align(
          alignment: Alignment.centerLeft,
          child: liveText(
            '${kickoffText(p['fecha'])} · ${p['competicion'] ?? ''}',
            color: liveMuted,
            size: 10,
          ),
        ),
      ],
    ),
  );
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
      padding: const EdgeInsets.only(bottom: 17),
      child: Column(
        children: [
          Row(
            children: [
              liveText(value(local), color: statsPurple, size: 11, bold: true),
              Expanded(
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 10),
                  child: Text(
                    label,
                    textAlign: TextAlign.center,
                    style: const TextStyle(fontSize: 11),
                  ),
                ),
              ),
              liveText(value(away), color: statsLime, size: 11, bold: true),
            ],
          ),
          const SizedBox(height: 7),
          ClipRRect(
            borderRadius: BorderRadius.circular(5),
            child: SizedBox(
              height: 5,
              child: available
                  ? LayoutBuilder(
                      builder: (context, constraints) => Row(
                        children: [
                          SizedBox(
                            width:
                                constraints.maxWidth *
                                local! /
                                (local! + away!),
                            child: Container(color: statsPurple),
                          ),
                          Expanded(child: Container(color: statsLime)),
                        ],
                      ),
                    )
                  : Container(color: Colors.white10),
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
    final valid =
        values.every((v) => v != null && v <= 1) &&
        (values.fold<double>(0, (sum, v) => sum + (v ?? 0)) - 1).abs() < .05;
    final names = [local, context.l10n.commonDraw, away];
    const colors = [statsPurple, Color(0xff8993a6), statsLime];
    return statisticsCard(
      Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          liveText(context.l10n.statProbTitle, size: 10, color: liveMuted),
          const SizedBox(height: 16),
          if (valid)
            ClipRRect(
              borderRadius: BorderRadius.circular(5),
              child: SizedBox(
                height: 7,
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
              height: 7,
              decoration: BoxDecoration(
                color: Colors.white10,
                borderRadius: BorderRadius.circular(5),
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
                      liveText(
                        valid ? realPercent(values[i]) : '—',
                        bold: true,
                        color: colors[i],
                        size: 17,
                      ),
                      const SizedBox(height: 6),
                      Text(
                        names[i],
                        textAlign: TextAlign.center,
                        style: const TextStyle(fontSize: 10, color: liveMuted),
                      ),
                    ],
                  ),
                ),
            ],
          ),
          if (!valid) ...[
            const SizedBox(height: 12),
            liveText(context.l10n.statProbNA, color: liveMuted, size: 11),
          ],
        ],
      ),
    );
  }
}

class MatchFixtureHeader extends StatelessWidget {
  const MatchFixtureHeader({super.key, required this.ficha, required this.api});
  final JsonMap ficha;
  final QuantFutApi api;
  @override
  Widget build(BuildContext context) {
    final match = jsonMap(ficha['partido']);
    final kickoff = dateValue(match['kickoff_utc'])?.toLocal();
    final score = match['marcador'];
    final future = kickoff != null && kickoff.isAfter(DateTime.now());
    final l10n = context.l10n;
    Widget team(String side) {
      final t = jsonMap(ficha[side]);
      return Expanded(
        child: Column(
          children: [
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: statsPanel,
                shape: BoxShape.circle,
                border: Border.all(color: Colors.white12),
              ),
              child: TeamCrest(team: t, api: api, size: 38),
            ),
            const SizedBox(height: 12),
            Text(
              '${t['nombre'] ?? ''}',
              textAlign: TextAlign.center,
              style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13),
            ),
          ],
        ),
      );
    }

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 12),
      child: Row(
        children: [
          team('local'),
          Container(
            width: 96,
            margin: const EdgeInsets.symmetric(horizontal: 8),
            padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 14),
            decoration: BoxDecoration(
              color: statsPanel,
              borderRadius: BorderRadius.circular(15),
              border: Border.all(color: Colors.white10),
            ),
            child: Column(
              children: [
                liveText(
                  kickoff == null
                      ? l10n.fixtureTbd
                      : localDate(DateFormat.MMMd, kickoff).toUpperCase(),
                  size: 10,
                  color: liveMuted,
                ),
                const SizedBox(height: 8),
                liveText(
                  score is List && score.length == 2
                      ? '${score[0]}–${score[1]}'
                      : kickoff == null
                      ? '—'
                      : localDate(DateFormat.Hm, kickoff),
                  color: statsLime,
                  bold: true,
                  size: 22,
                ),
                const SizedBox(height: 8),
                if (future && match['estado'] == 'scheduled') ...[
                  liveText(l10n.fixtureStartsIn, size: 8, color: liveMuted),
                  const SizedBox(height: 5),
                  CountdownTimer(
                    endTime: kickoff.millisecondsSinceEpoch,
                    textStyle: const TextStyle(
                      color: statsLime,
                      fontSize: 11,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ] else
                  liveText(
                    match['estado'] == 'finished'
                        ? l10n.fixtureFinished
                        : match['estado'] == 'live'
                        ? l10n.fixtureLive
                        : l10n.fixtureLocalTime,
                    size: 8,
                    color: liveMuted,
                  ),
              ],
            ),
          ),
          team('visitante'),
        ],
      ),
    );
  }
}
