import 'dart:math' as math;
import 'package:flutter/material.dart';

import '../l10n/app_locale.dart';
import 'live_api.dart';
import 'qf_charts.dart';
import 'qf_controls.dart';
import 'qf_shapes.dart';
import 'qf_standings.dart';
import 'qf_theme.dart';
import 'sport_images.dart';

/// Pestaña de análisis de fútbol CyberCore (F4c).
///
/// Reúne en una sola pestaña con gráficos 4 tarjetas:
/// 1. Resumen «Cómo llegan» (interruptor TODOS | CASA·FUERA, dots, QfRadar, 10 QfDivergingRow).
/// 2. Forma (5 QfFormPills de más antiguo a más reciente con último resaltado, chips racha y goles).
/// 3. Cara a cara (QfStackedBar, 3 chips, 3 últimos cruces con escudos, botón «VER LOS N PARTIDOS»).
/// 4. Clasificación (callout de diferencia, QfStandingsTable con filas alrededor de ambos equipos).
class FootballAnalysis extends StatefulWidget {
  const FootballAnalysis({
    super.key,
    required this.ficha,
    required this.api,
    this.onH2h,
    this.onAlerts,
  });

  final JsonMap ficha;
  final QuantFutApi api;
  final VoidCallback? onH2h;
  final VoidCallback? onAlerts;

  @override
  State<FootballAnalysis> createState() => _FootballAnalysisState();
}

class _FootballAnalysisState extends State<FootballAnalysis> {
  String _scope = 'todos'; // 'todos' o 'cf'
  int _navIndex = 0;

  final _resumenKey = GlobalKey();
  final _formaKey = GlobalKey();
  final _h2hKey = GlobalKey();
  final _tablaKey = GlobalKey();

  num _num(dynamic v) {
    if (v is num) return v;
    if (v is String) return num.tryParse(v) ?? 0;
    return 0;
  }

  String _fmt(dynamic v, int dec, String localeCode) {
    if (v == null) return '—';
    final n = _num(v);
    if (dec == 0) return '${n.round()} %';
    final s = n.toDouble().toStringAsFixed(dec);
    return localeCode == 'es' || localeCode == 'de' || localeCode == 'fr' || localeCode == 'it' || localeCode == 'pt'
        ? s.replaceAll('.', ',')
        : s;
  }

  String _fmtH2hDate(String? raw) {
    if (raw == null || raw.isEmpty) return '';
    try {
      final dt = DateTime.parse(raw);
      const months = ['ENE', 'FEB', 'MAR', 'ABR', 'MAY', 'JUN', 'JUL', 'AGO', 'SEP', 'OCT', 'NOV', 'DIC'];
      return '${dt.day} ${months[dt.month - 1]} ${dt.year}';
    } catch (_) {
      return raw;
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final localeCode = Localizations.localeOf(context).languageCode;
    final ficha = widget.ficha;

    final local = jsonMap(ficha['local']);
    final away = jsonMap(ficha['visitante']);
    final homeName = '${local['nombre'] ?? local['name'] ?? ''}';
    final awayName = '${away['nombre'] ?? away['name'] ?? ''}';
    final homeCrest = serverImageUrl(widget.api, local['escudo'] as String?);
    final awayCrest = serverImageUrl(widget.api, away['escudo'] as String?);

    final localPromedios = jsonMap(local['promedios']);
    final awayPromedios = jsonMap(away['promedios']);
    final hasCasaFuera = localPromedios['casa'] != null && awayPromedios['fuera'] != null;

    final localTodos = jsonMap(localPromedios['todos']);
    final awayTodos = jsonMap(awayPromedios['todos']);
    final hasPromedios = (localPromedios.isNotEmpty && ((localTodos['n'] as num?)?.toInt() ?? 1) > 0) ||
        (awayPromedios.isNotEmpty && ((awayTodos['n'] as num?)?.toInt() ?? 1) > 0);

    final A = (_scope == 'cf' && hasCasaFuera)
        ? jsonMap(localPromedios['casa'])
        : jsonMap(localPromedios['todos']);
    final B = (_scope == 'cf' && hasCasaFuera)
        ? jsonMap(awayPromedios['fuera'])
        : jsonMap(awayPromedios['todos']);

    final localForma = jsonMap(local['forma']);
    final awayForma = jsonMap(away['forma']);
    final localMatches = jsonRows(localForma['partidos']);
    final awayMatches = jsonRows(awayForma['partidos']);
    final hasForm = localMatches.isNotEmpty || awayMatches.isNotEmpty;

    final caraACara = jsonMap(ficha['cara_a_cara']);
    final h2hResumen = jsonMap(caraACara['resumen']);
    final h2hMatches = jsonRows(caraACara['partidos']);
    final h2hN = (h2hResumen['n'] as num?)?.toInt() ?? 0;
    final hasH2h = h2hN > 0 || h2hMatches.isNotEmpty;

    final tablaRaw = ficha['tabla'] is List ? (ficha['tabla'] as List) : null;
    final hasStandings = tablaRaw != null && tablaRaw.isNotEmpty;

    final sections = <(String, GlobalKey)>[
      if (hasPromedios) (l10n.anNavSummary.toUpperCase(), _resumenKey),
      if (hasForm) (l10n.anNavForm.toUpperCase(), _formaKey),
      if (hasH2h) (l10n.anNavH2h.toUpperCase(), _h2hKey),
      if (hasStandings) (l10n.anNavStandings.toUpperCase(), _tablaKey),
    ];

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        if (sections.isNotEmpty)
          Padding(
            padding: const EdgeInsets.only(bottom: 12),
            child: QfSectionNav(
              sections: sections,
              selectedIndex: _navIndex.clamp(0, sections.length - 1),
              onSelected: (i) => setState(() => _navIndex = i),
            ),
          ),
        if (hasPromedios) ...[
          _buildResumenCard(
            context,
            A: A,
            B: B,
            homeName: homeName,
            awayName: awayName,
            homeCrest: homeCrest,
            awayCrest: awayCrest,
            hasCasaFuera: hasCasaFuera,
            localeCode: localeCode,
          ),
          const SizedBox(height: 14),
        ],
        if (hasForm) ...[
          _buildFormaCard(
            context,
            local: local,
            away: away,
            homeName: homeName,
            awayName: awayName,
            homeCrest: homeCrest,
            awayCrest: awayCrest,
            localMatches: localMatches,
            awayMatches: awayMatches,
            localResumen: jsonMap(localForma['resumen']),
            awayResumen: jsonMap(awayForma['resumen']),
          ),
          const SizedBox(height: 14),
        ],
        if (hasH2h) ...[
          _buildH2hCard(
            context,
            caraACara: caraACara,
            resumen: h2hResumen,
            matches: h2hMatches,
            homeName: homeName,
            awayName: awayName,
            homeCrest: homeCrest,
            awayCrest: awayCrest,
            localeCode: localeCode,
          ),
          const SizedBox(height: 14),
        ],
        if (hasStandings) ...[
          _buildStandingsCard(
            context,
            tablaRaw: tablaRaw,
            local: local,
            away: away,
            homeName: homeName,
            awayName: awayName,
            homeCrest: homeCrest,
            awayCrest: awayCrest,
          ),
        ],
      ],
    );
  }

  Widget _buildResumenCard(
    BuildContext context, {
    required JsonMap A,
    required JsonMap B,
    required String homeName,
    required String awayName,
    required String? homeCrest,
    required String? awayCrest,
    required bool hasCasaFuera,
    required String localeCode,
  }) {
    final l10n = context.l10n;

    // Normalización de radar según §5.9
    final gfA = _num(A['goles_favor']).toDouble();
    final gcA = _num(A['goles_contra']).toDouble();
    final xfA = A['xg_favor'] != null ? _num(A['xg_favor']).toDouble() : null;
    final spA = _num(A['tiros_puerta_favor']).toDouble();
    final cA = _num(A['corners_favor']).toDouble();

    final gfB = _num(B['goles_favor']).toDouble();
    final gcB = _num(B['goles_contra']).toDouble();
    final xfB = B['xg_favor'] != null ? _num(B['xg_favor']).toDouble() : null;
    final spB = _num(B['tiros_puerta_favor']).toDouble();
    final cB = _num(B['corners_favor']).toDouble();

    final na = [
      math.max(0.08, math.min(gfA / 2.5, 1.0)),
      math.max(0.08, math.min((xfA ?? 0.08) / 2.5, 1.0)),
      math.max(0.08, math.min(spA / 7.0, 1.0)),
      math.max(0.08, math.min(cA / 9.0, 1.0)),
      math.max(0.08, 1.0 - math.min(gcA / 2.5, 1.0)),
    ];
    final nb = [
      math.max(0.08, math.min(gfB / 2.5, 1.0)),
      math.max(0.08, math.min((xfB ?? 0.08) / 2.5, 1.0)),
      math.max(0.08, math.min(spB / 7.0, 1.0)),
      math.max(0.08, math.min(cB / 9.0, 1.0)),
      math.max(0.08, 1.0 - math.min(gcB / 2.5, 1.0)),
    ];

    // Métricas para las 10 filas divergentes y dominance dots
    final metrics = [
      (l10n.anMetricGoalsFor, 'goles_favor', false, 1),
      (l10n.anMetricGoalsAgainst, 'goles_contra', true, 1),
      (l10n.anMetricXgFor, 'xg_favor', false, 2),
      (l10n.anMetricXgAgainst, 'xg_contra', true, 2),
      (l10n.anMetricShots, 'tiros_favor', false, 1),
      (l10n.anMetricShotsOnTarget, 'tiros_puerta_favor', false, 1),
      (l10n.anMetricCorners, 'corners_favor', false, 1),
      (l10n.anMetricBtts, 'pct_ambos_marcan', false, 0),
      (l10n.anMetricOver25, 'pct_mas_2_5', false, 0),
      (l10n.anMetricCleanSheet, 'pct_porteria_cero', false, 0),
    ];

    final winners = <int>[];
    for (final m in metrics) {
      final key = m.$2;
      final lowerIsBetter = m.$3;
      final rawA = A[key];
      final rawB = B[key];
      if (rawA == null || rawB == null) {
        winners.add(0);
      } else {
        final va = _num(rawA).toDouble();
        final vb = _num(rawB).toDouble();
        if ((va - vb).abs() < 0.0001) {
          winners.add(0);
        } else if (lowerIsBetter) {
          winners.add(va < vb ? 1 : -1);
        } else {
          winners.add(va > vb ? 1 : -1);
        }
      }
    }

    return QfCard(
      key: _resumenKey,
      strong: true,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // Cabecera con título e interruptor
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      l10n.anAveragesLast10.toUpperCase(),
                      style: const TextStyle(
                        fontFamily: qfDisplay,
                        fontSize: 11,
                        fontWeight: FontWeight.w700,
                        letterSpacing: 1.6,
                        color: QfColors.cyan,
                      ),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      l10n.anHowTheyArrive.toUpperCase(),
                      style: const TextStyle(
                        fontFamily: qfDisplay,
                        fontSize: 22,
                        fontWeight: FontWeight.w700,
                        letterSpacing: .4,
                        color: QfColors.text,
                      ),
                    ),
                  ],
                ),
              ),
              if (hasCasaFuera)
                Container(
                  padding: const EdgeInsets.all(3),
                  decoration: BoxDecoration(
                    color: const Color(0xB8030911),
                    border: Border.all(color: QfColors.border),
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      _ScopeButton(
                        label: l10n.anScopeAll,
                        selected: _scope == 'todos',
                        onTap: () => setState(() => _scope = 'todos'),
                      ),
                      _ScopeButton(
                        label: l10n.anScopeHomeAway,
                        selected: _scope == 'cf',
                        onTap: () => setState(() => _scope = 'cf'),
                      ),
                    ],
                  ),
                ),
            ],
          ),
          const SizedBox(height: 12),
          // Subtítulo con escudos y rayitas de color
          Row(
            children: [
              Expanded(
                child: Row(
                  children: [
                    QfAvatar(
                      url: homeCrest,
                      name: homeName,
                      size: 30,
                      shape: AvatarShape.contain,
                    ),
                    const SizedBox(width: 8),
                    Flexible(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            homeName,
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: const TextStyle(
                              fontFamily: qfBody,
                              fontSize: 13,
                              fontWeight: FontWeight.w700,
                              color: QfColors.text,
                            ),
                          ),
                          const SizedBox(height: 2),
                          Container(width: 22, height: 3, color: QfColors.cyan),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 6),
                child: Text(
                  _scope == 'todos' ? l10n.anScopeLast10Caption : l10n.anScopeHomeAwayCaption,
                  style: const TextStyle(
                    fontFamily: qfMono,
                    fontSize: 10,
                    fontWeight: FontWeight.w500,
                    color: QfColors.muted,
                  ),
                ),
              ),
              Expanded(
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.end,
                  children: [
                    Flexible(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.end,
                        children: [
                          Text(
                            awayName,
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: const TextStyle(
                              fontFamily: qfBody,
                              fontSize: 13,
                              fontWeight: FontWeight.w700,
                              color: QfColors.text,
                            ),
                          ),
                          const SizedBox(height: 2),
                          Container(width: 22, height: 3, color: QfColors.chrome),
                        ],
                      ),
                    ),
                    const SizedBox(width: 8),
                    QfAvatar(
                      url: awayCrest,
                      name: awayName,
                      size: 30,
                      shape: AvatarShape.contain,
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          // Dominance Dots
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
            decoration: BoxDecoration(
              border: Border.all(color: QfColors.border),
            ),
            child: QfDominanceDots(
              winners: winners,
              homeName: homeName,
              awayName: awayName,
            ),
          ),
          const SizedBox(height: 12),
          // Radar
          Center(
            child: QfRadar(
              labels: [
                l10n.anRadarAttack,
                l10n.anRadarCreation,
                l10n.anRadarFinishing,
                l10n.anRadarCorners,
                l10n.anRadarDefense,
              ],
              a: na,
              b: nb,
              size: 200,
              colorA: QfColors.cyan,
              colorB: QfColors.chrome,
            ),
          ),
          const SizedBox(height: 12),
          // 10 Filas divergentes
          for (final m in metrics) ...[
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 2),
              child: QfDivergingRow(
                label: m.$1,
                a: A[m.$2] != null ? _num(A[m.$2]) : null,
                b: B[m.$2] != null ? _num(B[m.$2]) : null,
                lowerIsBetter: m.$3,
                formatA: _fmt(A[m.$2], m.$4, localeCode),
                formatB: _fmt(B[m.$2], m.$4, localeCode),
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildFormaCard(
    BuildContext context, {
    required JsonMap local,
    required JsonMap away,
    required String homeName,
    required String awayName,
    required String? homeCrest,
    required String? awayCrest,
    required List<JsonMap> localMatches,
    required List<JsonMap> awayMatches,
    required JsonMap localResumen,
    required JsonMap awayResumen,
  }) {
    final l10n = context.l10n;

    return QfCard(
      key: _formaKey,
      strong: true,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(
            l10n.anLast5Matches.toUpperCase(),
            style: const TextStyle(
              fontFamily: qfDisplay,
              fontSize: 11,
              fontWeight: FontWeight.w700,
              letterSpacing: 1.6,
              color: QfColors.cyan,
            ),
          ),
          const SizedBox(height: 2),
          Text(
            l10n.anNavForm.toUpperCase(),
            style: const TextStyle(
              fontFamily: qfDisplay,
              fontSize: 22,
              fontWeight: FontWeight.w700,
              letterSpacing: .4,
              color: QfColors.text,
            ),
          ),
          const SizedBox(height: 12),
          if (localMatches.isNotEmpty)
            _buildTeamFormCard(
              context,
              name: homeName,
              crest: homeCrest,
              matches: localMatches,
              resumen: localResumen,
            ),
          if (localMatches.isNotEmpty && awayMatches.isNotEmpty)
            const SizedBox(height: 10),
          if (awayMatches.isNotEmpty)
            _buildTeamFormCard(
              context,
              name: awayName,
              crest: awayCrest,
              matches: awayMatches,
              resumen: awayResumen,
            ),
        ],
      ),
    );
  }

  Widget _buildTeamFormCard(
    BuildContext context, {
    required String name,
    required String? crest,
    required List<JsonMap> matches,
    required JsonMap resumen,
  }) {
    final l10n = context.l10n;

    // Racha: cuenta partidos consecutivos invictos desde el más reciente (matches[0])
    var unbeatenStreak = 0;
    while (unbeatenStreak < matches.length &&
        matches[unbeatenStreak]['res'] != 'P' &&
        matches[unbeatenStreak]['res'] != 'L') {
      unbeatenStreak++;
    }

    String streakText;
    if (unbeatenStreak > 0) {
      streakText = l10n.anStreakUnbeaten(unbeatenStreak);
    } else {
      var lossStreak = 0;
      while (lossStreak < matches.length &&
          (matches[lossStreak]['res'] == 'P' || matches[lossStreak]['res'] == 'L')) {
        lossStreak++;
      }
      streakText = l10n.anStreakLosses(lossStreak > 0 ? lossStreak : 1);
    }

    // Invertir lista para pintar de más antiguo (izq.) a más reciente (der.)
    final pillsMatches = matches.reversed.toList();
    final results = <QfFormResult>[];
    for (var i = 0; i < pillsMatches.length; i++) {
      final p = pillsMatches[i];
      final isLast = i == pillsMatches.length - 1;
      final res = '${p['res'] ?? 'E'}';
      final isHome = p['local'] == true;
      final rivalEscudo = serverImageUrl(widget.api, p['rival_escudo'] as String?);
      results.add(
        QfFormResult(
          result: res,
          score: '${p['marcador'] ?? '${p['gf'] ?? 0}–${p['gc'] ?? 0}'}',
          opponent: '${p['rival'] ?? ''}',
          isHome: isHome,
          isLast: isLast,
          opponentCrestUrl: rivalEscudo,
          venueLabel: isHome ? l10n.anVenueHome : l10n.anVenueAway,
          tag: isLast ? l10n.anLastMatch : null,
        ),
      );
    }

    final pts = (resumen['puntos'] as num?)?.toInt() ??
        ((resumen['G'] as num?)?.toInt() ?? 0) * 3 + ((resumen['E'] as num?)?.toInt() ?? 0);
    final w = (resumen['G'] as num?)?.toInt() ?? 0;
    final d = (resumen['E'] as num?)?.toInt() ?? 0;
    final l = (resumen['P'] as num?)?.toInt() ?? 0;
    final gf = (resumen['gf'] as num?)?.toInt() ?? 0;
    final gc = (resumen['gc'] as num?)?.toInt() ?? 0;

    return Container(
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(
        border: Border.all(color: QfColors.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Expanded(
                child: Row(
                  children: [
                    QfAvatar(
                      url: crest,
                      name: name,
                      size: 28,
                      shape: AvatarShape.contain,
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        name,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(
                          fontFamily: qfBody,
                          fontSize: 15,
                          fontWeight: FontWeight.w700,
                          color: QfColors.text,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 8),
              Column(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  Text(
                    l10n.anPointsOutOf(pts),
                    style: const TextStyle(
                      fontFamily: qfDisplay,
                      fontSize: 12,
                      fontWeight: FontWeight.w700,
                      letterSpacing: .8,
                      color: QfColors.cyan,
                    ),
                  ),
                  Text(
                    'G$w · E$d · P$l',
                    style: const TextStyle(
                      fontFamily: qfMono,
                      fontSize: 11,
                      fontWeight: FontWeight.w500,
                      color: QfColors.muted,
                    ),
                  ),
                ],
              ),
            ],
          ),
          const SizedBox(height: 10),
          // 5 Píldoras de forma expandidas a todo el ancho
          QfFormPills(
            results: results,
            expanded: true,
          ),
          const SizedBox(height: 10),
          // Chips de racha y goles
          Wrap(
            spacing: 8,
            runSpacing: 4,
            children: [
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                decoration: ShapeDecoration(
                  shape: const CutCornerBorder(
                    cut: 4,
                    side: BorderSide(color: QfColors.border),
                  ),
                  color: QfColors.cyan.withValues(alpha: .06),
                ),
                child: Text(
                  streakText.toUpperCase(),
                  style: const TextStyle(
                    fontFamily: qfDisplay,
                    fontSize: 11,
                    fontWeight: FontWeight.w700,
                    letterSpacing: .8,
                    color: QfColors.cyan,
                  ),
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                decoration: const ShapeDecoration(
                  shape: CutCornerBorder(
                    cut: 4,
                    side: BorderSide(color: QfColors.border),
                  ),
                ),
                child: Text(
                  l10n.anGoalsDiff(gf, gc),
                  style: const TextStyle(
                    fontFamily: qfDisplay,
                    fontSize: 11,
                    fontWeight: FontWeight.w700,
                    letterSpacing: .8,
                    color: QfColors.muted,
                  ),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildH2hCard(
    BuildContext context, {
    required JsonMap caraACara,
    required JsonMap resumen,
    required List<JsonMap> matches,
    required String homeName,
    required String awayName,
    required String? homeCrest,
    required String? awayCrest,
    required String localeCode,
  }) {
    final l10n = context.l10n;

    final n = (resumen['n'] as num?)?.toInt() ?? matches.length;
    final homeWins = (resumen['victorias_local'] as num?)?.toInt() ?? 0;
    final draws = (resumen['empates'] as num?)?.toInt() ?? 0;
    final awayWins = (resumen['victorias_visitante'] as num?)?.toInt() ?? 0;

    final golesMedia = resumen['goles_media'] != null ? _num(resumen['goles_media']).toDouble() : 0.0;
    final pctBtts = resumen['pct_ambos_marcan'] != null ? _num(resumen['pct_ambos_marcan']).toDouble() : 0.0;
    final pctOver25 = resumen['pct_mas_2_5'] != null ? _num(resumen['pct_mas_2_5']).toDouble() : 0.0;

    final lastMatches = matches.take(3).toList();

    return QfCard(
      key: _h2hKey,
      strong: true,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    l10n.anH2hMatchCount(n),
                    style: const TextStyle(
                      fontFamily: qfDisplay,
                      fontSize: 11,
                      fontWeight: FontWeight.w700,
                      letterSpacing: 1.6,
                      color: QfColors.cyan,
                    ),
                  ),
                  const SizedBox(height: 2),
                  Text(
                    l10n.anNavH2h.toUpperCase(),
                    style: const TextStyle(
                      fontFamily: qfDisplay,
                      fontSize: 22,
                      fontWeight: FontWeight.w700,
                      letterSpacing: .4,
                      color: QfColors.text,
                    ),
                  ),
                ],
              ),
              Text(
                l10n.anSeenFrom(homeName).toUpperCase(),
                style: const TextStyle(
                  fontFamily: qfMono,
                  fontSize: 10,
                  fontWeight: FontWeight.w500,
                  color: QfColors.muted,
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          // Resumen de victorias y empates
          Row(
            children: [
              Expanded(
                child: Row(
                  children: [
                    QfAvatar(
                      url: homeCrest,
                      name: homeName,
                      size: 34,
                      shape: AvatarShape.contain,
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            '$homeWins',
                            style: const TextStyle(
                              fontFamily: qfMono,
                              fontSize: 30,
                              fontWeight: FontWeight.w700,
                              color: QfColors.cyan,
                            ),
                          ),
                          Text(
                            l10n.anWinsTeam(homeWins, homeName).toUpperCase(),
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: const TextStyle(
                              fontFamily: qfDisplay,
                              fontSize: 10,
                              fontWeight: FontWeight.w700,
                              letterSpacing: .8,
                              color: QfColors.muted,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 4),
                child: Column(
                  children: [
                    Text(
                      '$draws',
                      style: const TextStyle(
                        fontFamily: qfMono,
                        fontSize: 22,
                        fontWeight: FontWeight.w700,
                        color: QfColors.chrome,
                      ),
                    ),
                    Text(
                      l10n.anDrawsCount(draws).toUpperCase(),
                      style: const TextStyle(
                        fontFamily: qfDisplay,
                        fontSize: 10,
                        fontWeight: FontWeight.w700,
                        letterSpacing: .8,
                        color: QfColors.muted,
                      ),
                    ),
                  ],
                ),
              ),
              Expanded(
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.end,
                  children: [
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.end,
                        children: [
                          Text(
                            '$awayWins',
                            style: const TextStyle(
                              fontFamily: qfMono,
                              fontSize: 30,
                              fontWeight: FontWeight.w700,
                              color: QfColors.text,
                            ),
                          ),
                          Text(
                            l10n.anWinsTeam(awayWins, awayName).toUpperCase(),
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            textAlign: TextAlign.right,
                            style: const TextStyle(
                              fontFamily: qfDisplay,
                              fontSize: 10,
                              fontWeight: FontWeight.w700,
                              letterSpacing: .8,
                              color: QfColors.muted,
                            ),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(width: 8),
                    QfAvatar(
                      url: awayCrest,
                      name: awayName,
                      size: 34,
                      shape: AvatarShape.contain,
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          // QfStackedBar
          QfStackedBar(
            height: 10,
            parts: [
              (homeName, homeWins.toDouble(), QfColors.cyan),
              (l10n.anDrawsCount(draws), draws.toDouble(), QfColors.slate),
              (awayName, awayWins.toDouble(), QfColors.chrome),
            ],
          ),
          const SizedBox(height: 12),
          // 3 Chips de estadísticas
          Row(
            children: [
              Expanded(
                child: _H2hStatBox(
                  value: _fmt(golesMedia, 1, localeCode),
                  label: l10n.anGoalsPerMatchShort,
                ),
              ),
              const SizedBox(width: 6),
              Expanded(
                child: _H2hStatBox(
                  value: '${pctBtts.round()}%',
                  label: l10n.anBttsShort,
                ),
              ),
              const SizedBox(width: 6),
              Expanded(
                child: _H2hStatBox(
                  value: '${pctOver25.round()}%',
                  label: l10n.anOver25Short,
                ),
              ),
            ],
          ),
          if (lastMatches.isNotEmpty) ...[
            const SizedBox(height: 12),
            Container(
              decoration: BoxDecoration(
                border: Border.all(color: QfColors.border),
              ),
              child: Column(
                children: [
                  for (var i = 0; i < lastMatches.length; i++) ...[
                    if (i > 0) const Divider(height: 1, color: QfColors.border),
                    _buildH2hMatchRow(
                      context,
                      match: lastMatches[i],
                      homeName: homeName,
                      homeCrest: homeCrest,
                    ),
                  ],
                ],
              ),
            ),
          ],
          if (widget.onH2h != null) ...[
            const SizedBox(height: 12),
            Material(
              color: QfColors.cyan.withValues(alpha: .06),
              shape: const CutCornerBorder(
                cut: 6,
                side: BorderSide(color: QfColors.borderStrong),
              ),
              child: InkWell(
                onTap: widget.onH2h,
                customBorder: const CutCornerBorder(cut: 6),
                child: Container(
                  height: 44,
                  alignment: Alignment.center,
                  child: Text(
                    l10n.anViewAllMatches(n),
                    style: const TextStyle(
                      fontFamily: qfDisplay,
                      fontSize: 14,
                      fontWeight: FontWeight.w700,
                      letterSpacing: 1.0,
                      color: QfColors.cyan,
                    ),
                  ),
                ),
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildH2hMatchRow(
    BuildContext context, {
    required JsonMap match,
    required String homeName,
    required String? homeCrest,
  }) {
    final rawDate = match['fecha'] as String?;
    final dateStr = _fmtH2hDate(rawDate);
    final isHome = match['local'] == true;
    final rivalCrest = serverImageUrl(widget.api, match['rival_escudo'] as String?);

    // Escudos en orden: izquierda = local del partido, derecha = visitante del partido
    final leftCrest = isHome ? homeCrest : rivalCrest;
    final leftName = isHome ? homeName : '${match['rival'] ?? ''}';
    final rightCrest = isHome ? rivalCrest : homeCrest;
    final rightName = isHome ? '${match['rival'] ?? ''}' : homeName;

    final score = '${match['marcador'] ?? '${match['gf'] ?? 0}-${match['gc'] ?? 0}'}';

    // Resultado visto desde el local de la ficha
    final rawRes = '${match['res'] ?? 'E'}'.toUpperCase();
    String res;
    if (isHome) {
      res = rawRes;
    } else {
      res = rawRes == 'G' ? 'P' : (rawRes == 'P' ? 'G' : 'E');
    }

    Color resColor;
    if (res == 'G' || res == 'W') {
      resColor = QfColors.green;
    } else if (res == 'E' || res == 'D') {
      resColor = QfColors.slate;
    } else {
      resColor = QfColors.magenta;
    }

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
      child: Row(
        children: [
          SizedBox(
            width: 74,
            child: Text(
              dateStr,
              style: const TextStyle(
                fontFamily: qfMono,
                fontSize: 11,
                fontWeight: FontWeight.w500,
                color: QfColors.muted,
              ),
            ),
          ),
          Expanded(
            child: Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                QfAvatar(
                  url: leftCrest,
                  name: leftName,
                  size: 26,
                  shape: AvatarShape.contain,
                ),
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 10),
                  child: Text(
                    score,
                    style: const TextStyle(
                      fontFamily: qfMono,
                      fontSize: 16,
                      fontWeight: FontWeight.w700,
                      color: QfColors.text,
                    ),
                  ),
                ),
                QfAvatar(
                  url: rightCrest,
                  name: rightName,
                  size: 26,
                  shape: AvatarShape.contain,
                ),
              ],
            ),
          ),
          Container(
            width: 28,
            height: 28,
            alignment: Alignment.center,
            decoration: BoxDecoration(
              border: Border.all(color: resColor),
              color: resColor.withValues(alpha: .12),
            ),
            child: Text(
              res,
              style: TextStyle(
                fontFamily: qfDisplay,
                fontSize: 14,
                fontWeight: FontWeight.w700,
                color: resColor,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildStandingsCard(
    BuildContext context, {
    required List<dynamic> tablaRaw,
    required JsonMap local,
    required JsonMap away,
    required String homeName,
    required String awayName,
    required String? homeCrest,
    required String? awayCrest,
  }) {
    final l10n = context.l10n;
    final partido = jsonMap(widget.ficha['partido']);
    final liga = jsonMap(partido['liga']);
    final ligaNombre = '${liga['nombre'] ?? partido['competicion'] ?? ''}'.toUpperCase();
    final jornada = '${partido['jornada'] ?? ''}';

    final rows = <JsonMap>[];
    for (final item in tablaRaw) {
      if (item is Map) rows.add(jsonMap(item));
    }

    // Identificar fila de cada equipo
    final localId = '${local['id'] ?? local['team_id'] ?? ''}';
    final awayId = '${away['id'] ?? away['team_id'] ?? ''}';

    JsonMap? homeRow;
    JsonMap? awayRow;
    for (final r in rows) {
      final tid = '${r['team_id'] ?? ''}';
      final ename = '${r['equipo'] ?? ''}'.toLowerCase();
      if ((localId.isNotEmpty && tid == localId) || ename == homeName.toLowerCase()) {
        homeRow = r;
      }
      if ((awayId.isNotEmpty && tid == awayId) || ename == awayName.toLowerCase()) {
        awayRow = r;
      }
    }

    String? calloutText;
    if (homeRow != null && awayRow != null) {
      final posH = (homeRow['posicion'] as num?)?.toInt() ?? 0;
      final ptsH = (homeRow['puntos'] as num?)?.toInt() ?? 0;
      final posA = (awayRow['posicion'] as num?)?.toInt() ?? 0;
      final ptsA = (awayRow['puntos'] as num?)?.toInt() ?? 0;

      if (ptsH > ptsA) {
        calloutText = l10n.anStandingsCalloutAhead(homeName, posH, ptsH, ptsH - ptsA, awayName, posA, ptsA);
      } else if (ptsA > ptsH) {
        calloutText = l10n.anStandingsCalloutAhead(awayName, posA, ptsA, ptsA - ptsH, homeName, posH, ptsH);
      } else {
        calloutText = l10n.anStandingsCalloutTied(homeName, awayName, ptsH);
      }
    }

    // Seleccionar filas alrededor de ambos equipos (1-2 antes y después)
    final wantedPositions = <int>{};
    if (homeRow != null) {
      final p = (homeRow['posicion'] as num?)?.toInt() ?? 1;
      for (var offset = -2; offset <= 2; offset++) {
        if (p + offset > 0) wantedPositions.add(p + offset);
      }
    }
    if (awayRow != null) {
      final p = (awayRow['posicion'] as num?)?.toInt() ?? 1;
      for (var offset = -2; offset <= 2; offset++) {
        if (p + offset > 0) wantedPositions.add(p + offset);
      }
    }

    // Si no se encontraron los equipos, mostramos los primeros 6
    if (wantedPositions.isEmpty) {
      for (var i = 1; i <= math.min(6, rows.length); i++) {
        wantedPositions.add(i);
      }
    }

    final standingRows = <QfStandingRow>[];
    var hasZones = false;
    for (final r in rows) {
      final pos = (r['posicion'] as num?)?.toInt() ?? 0;
      if (wantedPositions.contains(pos)) {
        final desc = '${r['descripcion'] ?? ''}'.toLowerCase();
        Color? zoneColor;
        if (desc.contains('ascenso') || desc.contains('champions')) {
          zoneColor = QfColors.green;
          hasZones = true;
        } else if (desc.contains('play-off') ||
            desc.contains('promoción') || // l10n-ignore
            desc.contains('promocion') ||
            desc.contains('europa')) {
          zoneColor = QfColors.cyan;
          hasZones = true;
        } else if (desc.contains('descenso')) {
          zoneColor = QfColors.magenta;
          hasZones = true;
        }

        standingRows.add(
          QfStandingRow(
            position: pos,
            teamId: '${r['team_id'] ?? r['equipo']}',
            teamName: '${r['equipo'] ?? ''}',
            crestUrl: serverImageUrl(widget.api, r['escudo'] as String?),
            played: (r['jugados'] as num?)?.toInt() ?? 0,
            diffGoals: ((r['goles_favor'] as num?)?.toInt() ?? 0) - ((r['goles_contra'] as num?)?.toInt() ?? 0),
            points: (r['puntos'] as num?)?.toInt() ?? 0,
            form: '${r['forma'] ?? ''}',
            zoneColor: zoneColor,
          ),
        );
      }
    }

    final highlightIds = <String>{
      if (homeRow != null) '${homeRow['team_id'] ?? homeRow['equipo']}',
      if (awayRow != null) '${awayRow['team_id'] ?? awayRow['equipo']}',
      localId,
      awayId,
    };

    final headerKicker = jornada.isNotEmpty
        ? l10n.anLeagueRound(ligaNombre, jornada).toUpperCase()
        : '// $ligaNombre';

    return QfCard(
      key: _tablaKey,
      strong: true,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(
            headerKicker,
            style: const TextStyle(
              fontFamily: qfDisplay,
              fontSize: 11,
              fontWeight: FontWeight.w700,
              letterSpacing: 1.6,
              color: QfColors.cyan,
            ),
          ),
          const SizedBox(height: 2),
          Text(
            l10n.anStandingsTitle.toUpperCase(),
            style: const TextStyle(
              fontFamily: qfDisplay,
              fontSize: 22,
              fontWeight: FontWeight.w700,
              letterSpacing: .4,
              color: QfColors.text,
            ),
          ),
          const SizedBox(height: 12),
          if (calloutText != null) ...[
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
              decoration: ShapeDecoration(
                color: QfColors.cyan.withValues(alpha: .07),
                shape: const CutCornerBorder(
                  cut: 6,
                  side: BorderSide(color: Color(0x6600F0FF)),
                ),
              ),
              child: Row(
                children: [
                  QfAvatar(
                    url: homeCrest,
                    name: homeName,
                    size: 24,
                    shape: AvatarShape.contain,
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      calloutText,
                      style: const TextStyle(
                        fontFamily: qfBody,
                        fontSize: 13,
                        fontWeight: FontWeight.w500,
                        color: QfColors.text,
                      ),
                    ),
                  ),
                  const SizedBox(width: 8),
                  QfAvatar(
                    url: awayCrest,
                    name: awayName,
                    size: 24,
                    shape: AvatarShape.contain,
                  ),
                ],
              ),
            ),
            const SizedBox(height: 12),
          ],
          // Tabla con QfStandingsTable
          Container(
            decoration: BoxDecoration(
              border: Border.all(color: QfColors.border),
            ),
            child: QfStandingsTable(
              rows: standingRows,
              highlightIds: highlightIds,
            ),
          ),
          if (hasZones) ...[
            const SizedBox(height: 10),
            Row(
              children: [
                _ZoneLegendItem(color: QfColors.green, label: l10n.anPromotion),
                const SizedBox(width: 12),
                _ZoneLegendItem(color: QfColors.cyan, label: l10n.anPlayoff),
                const SizedBox(width: 12),
                _ZoneLegendItem(color: QfColors.magenta, label: l10n.anRelegation),
              ],
            ),
          ],
        ],
      ),
    );
  }
}

class _ScopeButton extends StatelessWidget {
  const _ScopeButton({
    required this.label,
    required this.selected,
    required this.onTap,
  });

  final String label;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: selected ? QfColors.cyan.withValues(alpha: .12) : Colors.transparent,
      child: InkWell(
        onTap: onTap,
        child: Container(
          height: 36,
          padding: const EdgeInsets.symmetric(horizontal: 10),
          alignment: Alignment.center,
          child: Text(
            label.toUpperCase(),
            style: TextStyle(
              fontFamily: qfDisplay,
              fontSize: 12,
              fontWeight: FontWeight.w700,
              letterSpacing: .6,
              color: selected ? QfColors.cyan : QfColors.muted,
            ),
          ),
        ),
      ),
    );
  }
}

class _H2hStatBox extends StatelessWidget {
  const _H2hStatBox({
    required this.value,
    required this.label,
  });

  final String value;
  final String label;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(vertical: 8, horizontal: 6),
      decoration: BoxDecoration(
        border: Border.all(color: QfColors.border),
      ),
      child: Column(
        children: [
          Text(
            value,
            style: const TextStyle(
              fontFamily: qfMono,
              fontSize: 16,
              fontWeight: FontWeight.w700,
              color: QfColors.cyan,
            ),
          ),
          const SizedBox(height: 2),
          Text(
            label.toUpperCase(),
            textAlign: TextAlign.center,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: const TextStyle(
              fontFamily: qfDisplay,
              fontSize: 10,
              fontWeight: FontWeight.w700,
              letterSpacing: 1.0,
              color: QfColors.muted,
            ),
          ),
        ],
      ),
    );
  }
}

class _ZoneLegendItem extends StatelessWidget {
  const _ZoneLegendItem({required this.color, required this.label});
  final Color color;
  final String label;

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(width: 8, height: 8, color: color),
        const SizedBox(width: 4),
        Text(
          label.toUpperCase(),
          style: const TextStyle(
            fontFamily: qfMono,
            fontSize: 10,
            fontWeight: FontWeight.w500,
            color: QfColors.muted,
          ),
        ),
      ],
    );
  }
}
