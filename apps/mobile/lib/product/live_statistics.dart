import 'dart:math' as math;

import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';

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
    const metrics = {
      'goles_favor': 'Goles a favor',
      'goles_contra': 'Goles recibidos',
      'tiros_favor': 'Remates',
      'tiros_puerta_favor': 'Remates a puerta',
      'corners_favor': 'Córners',
      'pct_porteria_cero': 'Portería a cero',
      'pct_ambos_marcan': 'Ambos marcan',
      'pct_mas_2_5': 'Más de 2,5 goles',
      'xg_favor': 'xG histórico',
    };
    const radarLabels = {
      'goles_favor': 'Goles a favor',
      'tiros_favor': 'Remates',
      'tiros_puerta_favor': 'A puerta',
      'corners_favor': 'Córners',
      'pct_porteria_cero': 'Portería a cero',
      'goles_contra': 'Goles recibidos',
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
        statisticsHeading('Resumen de predicción'),
        MatchProbabilitySummary(
          probabilities: jsonMap(ficha['probabilities']),
          local: '${local['nombre'] ?? 'Local'}',
          away: '${away['nombre'] ?? 'Visitante'}',
        ),
        if (picks.isNotEmpty)
          statisticsCard(
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                liveText('PRONÓSTICO PUBLICADO', size: 10, color: liveMuted),
                const SizedBox(height: 8),
                liveText(
                  '${picks.first['texto'] ?? ''}',
                  color: statsLime,
                  bold: true,
                  size: 17,
                ),
                const SizedBox(height: 8),
                liveText(
                  'Probabilidad ${realPercent(picks.first['prob'])} · Cuota @ ${decimalText(picks.first['ref_price'] ?? picks.first['price'])}',
                  size: 12,
                ),
              ],
            ),
          )
        else if (data['locked'] == true)
          statisticsCard(
            liveText(
              'El pronóstico de este partido requiere acceso VIP o un desbloqueo con monedas.',
              color: liveMuted,
              size: 12,
            ),
          ),
        statisticsCard(
          Column(
            children: [
              liveText(
                'PROMEDIO HISTÓRICO DE GOLES',
                size: 10,
                color: liveMuted,
              ),
              const SizedBox(height: 14),
              Row(
                children: [
                  Expanded(child: _goalAverage(local, lm, statsPurple)),
                  liveText('vs', color: liveMuted, size: 12),
                  Expanded(child: _goalAverage(away, am, statsLime)),
                ],
              ),
              const SizedBox(height: 10),
              liveText(
                'Goles a favor por partido; no es la proyección de goles del modelo.',
                color: liveMuted,
                size: 11,
              ),
            ],
          ),
        ),
        statisticsHeading('Forma de los equipos'),
        Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Expanded(child: _form(local, statsPurple)),
            const SizedBox(width: 10),
            Expanded(child: _form(away, statsLime)),
          ],
        ),
        liveText(
          'G: ganado · E: empate · P: perdido. Más reciente a la izquierda.',
          color: liveMuted,
          size: 10,
        ),
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
                      'En ${hs['n']} cruces registrados: ${local['nombre']} ganó ${hs['victorias_local'] ?? '—'}, ${away['nombre']} ganó ${hs['victorias_visitante'] ?? '—'} y hubo ${hs['empates'] ?? '—'} empates.',
                      size: 12,
                    ),
                  ),
                ],
              ),
            ),
          ),
        statisticsHeading('Estadísticas del equipo'),
        liveText(
          'Promedios de ${lm['n'] ?? 0} partidos del local y ${am['n'] ?? 0} del visitante. La cobertura de remates, córners y xG puede ser parcial.',
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
                    'La comparación gráfica necesita al menos tres métricas disponibles de ambos equipos.',
                    color: liveMuted,
                    size: 12,
                  ),
                ),
              _legend(local, away),
              const SizedBox(height: 12),
              liveText(
                'Escala relativa por eje. Un área mayor no implica mayor probabilidad de ganar.',
                color: liveMuted,
                size: 10,
              ),
            ],
          ),
        ),
        statisticsHeading('Comparación de equipos'),
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
              liveText(
                'Las barras comparan los valores registrados; no representan probabilidades de victoria. Menos goles recibidos es mejor.',
                color: liveMuted,
                size: 10,
              ),
            ],
          ),
        ),
        statisticsHeading('Goles por minuto'),
        statisticsCard(
          liveText(
            'La distribución por minutos no está disponible para este partido.',
            color: liveMuted,
            size: 12,
          ),
        ),
        statisticsHeading('Temporada y resultados recientes'),
        for (final entry in [(local, statsPurple), (away, statsLime)])
          _season(entry.$1, entry.$2),
        if (featureEnabled(data, 'h2h')) ...[
          statisticsHeading('Cara a cara'),
          if (jsonRows(h2h['partidos']).isEmpty)
            statisticsCard(
              liveText(
                'No hay enfrentamientos registrados para este partido.',
                color: liveMuted,
                size: 12,
              ),
            )
          else
            ...jsonRows(h2h['partidos']).map((p) => h2hResult(p, local, away)),
        ],
        statisticsHeading('Distribución de goles Poisson'),
        statisticsCard(
          liveText(
            'La distribución Poisson y los marcadores probables aún no están disponibles en la entrega de este partido.',
            color: liveMuted,
            size: 12,
          ),
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

  Widget _form(JsonMap team, Color color) {
    final rows = jsonRows(jsonMap(team['forma'])['partidos']);
    return statisticsCard(
      Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          liveText('${team['nombre'] ?? ''}', bold: true, size: 12),
          const SizedBox(height: 12),
          if (rows.isEmpty)
            liveText('Forma no disponible.', color: liveMuted, size: 11)
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
                    child: liveText(result, size: 11, bold: true),
                  ),
                );
              }).toList(),
            ),
          const SizedBox(height: 9),
          liveText(
            '${rows.length} resultados disponibles',
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

  Widget _season(JsonMap team, Color color) {
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
                liveText('Posición ${table['posicion'] ?? '—'}', size: 12),
                liveText('${table['puntos'] ?? '—'} puntos', size: 12),
                liveText('${table['jugados'] ?? '—'} partidos', size: 12),
              ],
            ),
          ] else ...[
            const SizedBox(height: 8),
            liveText(
              'Clasificación no disponible.',
              color: liveMuted,
              size: 11,
            ),
          ],
          const Divider(height: 26, color: Colors.white10),
          liveText(
            'Últimos ${rows.length} partidos registrados',
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
                  ('Mejor triunfo en casa', best(true)),
                  ('Mejor triunfo fuera', best(false)),
                  ('Racha de victorias', rows.isEmpty ? '—' : '${streak('G')}'),
                  ('Racha de empates', rows.isEmpty ? '—' : '${streak('E')}'),
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
        : '${decimalText(n, percentage ? 1 : 2)}${percentage ? ' %' : ''}';
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
    final names = [local, 'Empate', away];
    const colors = [statsPurple, Color(0xff8993a6), statsLime];
    return statisticsCard(
      Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          liveText(
            'PROBABILIDAD DE VICTORIA · 1X2',
            size: 10,
            color: liveMuted,
          ),
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
            liveText(
              'Probabilidades del modelo todavía no disponibles.',
              color: liveMuted,
              size: 11,
            ),
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
    const months = [
      'ENE',
      'FEB',
      'MAR',
      'ABR',
      'MAY',
      'JUN',
      'JUL',
      'AGO',
      'SEP',
      'OCT',
      'NOV',
      'DIC',
    ];
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
                      ? 'POR CONFIRMAR'
                      : '${kickoff.day} ${months[kickoff.month - 1]}',
                  size: 10,
                  color: liveMuted,
                ),
                const SizedBox(height: 8),
                liveText(
                  score is List && score.length == 2
                      ? '${score[0]}–${score[1]}'
                      : kickoff == null
                      ? '—'
                      : '${kickoff.hour.toString().padLeft(2, '0')}:${kickoff.minute.toString().padLeft(2, '0')}',
                  color: statsLime,
                  bold: true,
                  size: 22,
                ),
                const SizedBox(height: 8),
                if (future && match['estado'] == 'scheduled') ...[
                  liveText('EMPIEZA EN', size: 8, color: liveMuted),
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
                        ? 'FINALIZADO'
                        : match['estado'] == 'live'
                        ? 'EN VIVO'
                        : 'HORA LOCAL',
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
