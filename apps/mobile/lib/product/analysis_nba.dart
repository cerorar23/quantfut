import 'package:flutter/material.dart';

import '../l10n/app_locale.dart';
import 'live_api.dart';
import 'qf_charts.dart';
import 'qf_controls.dart';
import 'qf_shapes.dart';
import 'qf_theme.dart';
import 'sport_images.dart';
import 'sports_feed.dart';

/// Pestaña de análisis de NBA CyberCore (F4d).
///
/// Implementa 6 secciones organizadas mediante [QfSectionNav]:
/// 1. Probabilidad: 2 tarjetas de equipo, barra proporcional y 4 factores del partido.
/// 2. Comparativa: 7 filas divergentes y dominancia de métricas.
/// 3. Forma: 6 partidos por equipo con barras de margen [QfMarginBars], racha y promedios.
/// 4. Cara a cara: victorias, barra apilada, promedio de puntos totales y últimos duelos.
/// 5. Clasificación: cinta de 15 casillas [QfSeasonTrack], resumen de puestos y callout.
/// 6. Disponibilidad: estado oficial de lesiones, minutos de bajas y descanso.
class NbaAnalysis extends StatefulWidget {
  const NbaAnalysis({
    super.key,
    required this.event,
    required this.data,
    this.api,
    this.images,
    this.onH2h,
  });

  final SportEvent event;
  final JsonMap data;
  final QuantFutApi? api;
  final ImageCatalog? images;
  final VoidCallback? onH2h;

  @override
  State<NbaAnalysis> createState() => _NbaAnalysisState();
}

class _NbaAnalysisState extends State<NbaAnalysis> {
  int _navIndex = 0;

  final _probKey = GlobalKey();
  final _compKey = GlobalKey();
  final _formaKey = GlobalKey();
  final _h2hKey = GlobalKey();
  final _tablaKey = GlobalKey();
  final _dispKey = GlobalKey();

  Widget _teamLogo(String name, double size) {
    final code = nbaTricode(name);
    final path = code == null ? null : (widget.images?.nbaLogo(code) ?? '/web/imagenes/nba/${code.toUpperCase()}.png');
    final url = widget.api != null ? serverImageUrl(widget.api!, path) : null;
    return QfAvatar(
      url: url,
      name: name,
      size: size,
      shape: AvatarShape.contain,
    );
  }

  JsonMap? _findTeam(List<JsonMap> teams, String name) {
    final tricode = nbaTricode(name);
    for (final t in teams) {
      final tName = '${t['name'] ?? ''}';
      if (tName.toLowerCase() == name.toLowerCase()) return t;
      if (tricode != null && nbaTricode(tName) == tricode) return t;
      if (tName.toLowerCase().contains(name.toLowerCase()) ||
          name.toLowerCase().contains(tName.toLowerCase())) {
        return t;
      }
    }
    return null;
  }

  String _fmtDate(String? raw) {
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
    final event = widget.event;
    final data = widget.data;
    final teams = jsonRows(data['teams']);

    if (teams.isEmpty) {
      return Padding(
        padding: const EdgeInsets.all(16),
        child: Text(
          l10n.nbaNoStats,
          style: const TextStyle(color: QfColors.text2),
          textAlign: TextAlign.center,
        ),
      );
    }

    // Identificar visitante (Team A) y local (Team B)
    final awayTeam = _findTeam(teams, event.away) ?? (teams.length > 1 ? teams[1] : teams[0]);
    final homeTeam = _findTeam(teams, event.home) ?? teams[0];

    final awayName = '${awayTeam['name'] ?? event.away}';
    final homeName = '${homeTeam['name'] ?? event.home}';

    final h2hData = jsonMap(data['h2h']);
    final hasH2h = h2hData.isNotEmpty;

    final formA = jsonMap(awayTeam['form']);
    final formB = jsonMap(homeTeam['form']);
    final hasForm = formA.isNotEmpty || formB.isNotEmpty;

    final standingA = jsonMap(awayTeam['standing']);
    final standingB = jsonMap(homeTeam['standing']);
    final hasStandings = standingA.isNotEmpty || standingB.isNotEmpty;

    final hasAvailability = event.availability != null && event.availability!.isNotEmpty;

    final sections = <(String, GlobalKey)>[
      (l10n.nbaNavProb.toUpperCase(), _probKey),
      (l10n.nbaNavComp.toUpperCase(), _compKey),
      if (hasForm) (l10n.anNavForm.toUpperCase(), _formaKey),
      if (hasH2h) (l10n.anNavH2h.toUpperCase(), _h2hKey),
      if (hasStandings) (l10n.anStandingsTitle.toUpperCase(), _tablaKey),
      if (hasAvailability) (l10n.nbaNavAvail.toUpperCase(), _dispKey),
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
        _buildProbabilidadCard(context, awayTeam, homeTeam, awayName, homeName),
        const SizedBox(height: 14),
        _buildComparativaCard(context, awayTeam, homeTeam, awayName, homeName),
        if (hasForm) ...[
          const SizedBox(height: 14),
          _buildFormaCard(context, awayTeam, homeTeam, awayName, homeName),
        ],
        if (hasH2h) ...[
          const SizedBox(height: 14),
          _buildH2hCard(context, h2hData, awayName, homeName),
        ],
        if (hasStandings) ...[
          const SizedBox(height: 14),
          _buildClasificacionCard(context, awayTeam, homeTeam, awayName, homeName),
        ],
        if (hasAvailability) ...[
          const SizedBox(height: 14),
          _buildDisponibilidadCard(context, awayTeam, homeTeam, awayName, homeName),
        ],
        const SizedBox(height: 24),
      ],
    );
  }

  // ==========================================
  // SECCIÓN 1: PROBABILIDAD DE GANAR
  // ==========================================
  Widget _buildProbabilidadCard(
    BuildContext context,
    JsonMap awayTeam,
    JsonMap homeTeam,
    String awayName,
    String homeName,
  ) {
    final l10n = context.l10n;
    final event = widget.event;

    // Calcular probabilidad de ganador
    double? pHome;
    for (final m in event.markets) {
      final isWinner = m.market == 'winner' || (m.market == null && m.id == 'winner');
      if (isWinner && m.eligible) {
        pHome = m.selection == event.home ? m.probability : 1.0 - m.probability;
        break;
      }
    }

    int? pa;
    int? pb;
    if (pHome != null) {
      pb = (pHome * 100).round();
      pa = 100 - pb;
    }

    final seasonA = jsonMap(awayTeam['season']);
    final seasonB = jsonMap(homeTeam['season']);
    final recA = '${seasonA['won'] ?? 0}–${seasonA['lost'] ?? 0}';
    final recB = '${seasonB['won'] ?? 0}–${seasonB['lost'] ?? 0}';

    // 4 factores del partido calculados
    final factors = _computeFactors(context, awayTeam, homeTeam, awayName, homeName);

    return QfCard(
      key: _probKey,
      strong: true,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const Text(
            '// MODELO QUANTFUT',
            style: TextStyle(
              fontFamily: qfDisplay,
              fontSize: 11,
              fontWeight: FontWeight.w700,
              color: QfColors.cyan,
              letterSpacing: 1.6,
            ),
          ),
          const SizedBox(height: 2),
          Text(
            l10n.nbaWinProbTitle,
            style: const TextStyle(
              fontFamily: qfDisplay,
              fontSize: 22,
              fontWeight: FontWeight.w700,
              color: QfColors.text,
              letterSpacing: .4,
            ),
          ),
          const SizedBox(height: 12),
          if (pHome == null) ...[
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: QfColors.surface,
                border: Border.all(color: QfColors.border),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    l10n.nbaSealHeading,
                    style: const TextStyle(
                      fontFamily: qfMono,
                      fontSize: 11,
                      letterSpacing: .8,
                      color: QfColors.primary,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    l10n.nbaSealPendingTitle,
                    style: const TextStyle(
                      fontSize: 15,
                      fontWeight: FontWeight.w700,
                      color: QfColors.text,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    event.plannedSeal != null
                        ? l10n.nbaSealPendingBody(kickoffText(event.plannedSeal))
                        : l10n.nbaSealPendingSoon,
                    style: const TextStyle(
                      fontSize: 12,
                      color: QfColors.text2,
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 12),
          ],
          // Dos tarjetas de equipo
          Row(
            children: [
              Expanded(
                child: _buildTeamProbCard(
                  name: awayName,
                  percent: pa,
                  subtitle: l10n.nbaAwayRecord(recA),
                  isLeader: pa != null && pb != null ? pa >= pb : false,
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: _buildTeamProbCard(
                  name: homeName,
                  percent: pb,
                  subtitle: l10n.nbaHomeRecord(recB),
                  isLeader: pa != null && pb != null ? pb > pa : false,
                ),
              ),
            ],
          ),
          if (pa != null && pb != null) ...[
            const SizedBox(height: 10),
            // Barra de probabilidad horizontal
            SizedBox(
              height: 10,
              child: Row(
                children: [
                  Expanded(
                    flex: pa.clamp(1, 99),
                    child: Container(color: QfColors.cyan),
                  ),
                  const SizedBox(width: 3),
                  Expanded(
                    flex: pb.clamp(1, 99),
                    child: Container(color: QfColors.slate),
                  ),
                ],
              ),
            ),
          ],
          const SizedBox(height: 14),
          Text(
            l10n.nbaMatchFactors,
            style: const TextStyle(
              fontFamily: qfDisplay,
              fontSize: 12,
              fontWeight: FontWeight.w700,
              color: QfColors.text,
              letterSpacing: 1.4,
            ),
          ),
          const SizedBox(height: 8),
          Container(
            decoration: BoxDecoration(
              border: Border.all(color: QfColors.border),
            ),
            child: Column(
              children: [
                for (var i = 0; i < factors.length; i++) ...[
                  if (i > 0) const Divider(height: 1, color: QfColors.border),
                  _buildFactorRow(factors[i]),
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildTeamProbCard({
    required String name,
    required int? percent,
    required String subtitle,
    required bool isLeader,
  }) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 12),
      decoration: BoxDecoration(
        color: isLeader ? QfColors.cyan.withValues(alpha: .07) : Colors.transparent,
        border: Border.all(
          color: isLeader ? QfColors.cyan : QfColors.border,
          width: 1,
        ),
        boxShadow: isLeader
            ? [
                BoxShadow(
                  color: QfColors.cyan.withValues(alpha: .14),
                  blurRadius: 22,
                ),
              ]
            : null,
      ),
      child: Column(
        children: [
          _teamLogo(name, 56),
          const SizedBox(height: 4),
          Text(
            name,
            style: const TextStyle(
              fontWeight: FontWeight.w700,
              fontSize: 14,
              color: QfColors.text,
            ),
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: 4),
          Text(
            percent != null ? '$percent%' : '—',
            style: TextStyle(
              fontFamily: qfMono,
              fontSize: 32,
              fontWeight: FontWeight.w700,
              color: isLeader ? QfColors.cyan : const Color(0xFFD1D4DE),
              shadows: isLeader
                  ? [
                      Shadow(
                        color: QfColors.cyan.withValues(alpha: .45),
                        blurRadius: 18,
                      ),
                    ]
                  : null,
            ),
          ),
          const SizedBox(height: 2),
          Text(
            subtitle,
            style: const TextStyle(
              fontFamily: qfDisplay,
              fontSize: 10,
              fontWeight: FontWeight.w700,
              color: QfColors.text2,
              letterSpacing: 1.4,
            ),
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            textAlign: TextAlign.center,
          ),
        ],
      ),
    );
  }

  Widget _buildFactorRow(_NbaFactor f) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
      child: Row(
        children: [
          _teamLogo(f.teamName, 30),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  f.title,
                  style: const TextStyle(
                    fontSize: 13,
                    fontWeight: FontWeight.w700,
                    color: QfColors.text,
                  ),
                ),
                Text(
                  f.subtitle,
                  style: const TextStyle(
                    fontSize: 12,
                    color: QfColors.text2,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  List<_NbaFactor> _computeFactors(
    BuildContext context,
    JsonMap awayTeam,
    JsonMap homeTeam,
    String awayName,
    String homeName,
  ) {
    final l10n = context.l10n;
    final list = <_NbaFactor>[];

    // Factor 1: Récord
    final seasonA = jsonMap(awayTeam['season']);
    final seasonB = jsonMap(homeTeam['season']);
    final rateA = (seasonA['rate'] as num?)?.toDouble() ?? 0.0;
    final rateB = (seasonB['rate'] as num?)?.toDouble() ?? 0.0;
    final recA = '${seasonA['won'] ?? 0}–${seasonA['lost'] ?? 0}';
    final recB = '${seasonB['won'] ?? 0}–${seasonB['lost'] ?? 0}';

    if (rateA > rateB) {
      list.add(_NbaFactor(
        teamName: awayName,
        title: l10n.nbaFactorRecordBest,
        subtitle: '$awayName $recA · $homeName $recB',
      ));
    } else if (rateB > rateA) {
      list.add(_NbaFactor(
        teamName: homeName,
        title: l10n.nbaFactorRecordBest,
        subtitle: '$homeName $recB · $awayName $recA',
      ));
    } else {
      list.add(_NbaFactor(
        teamName: awayName,
        title: l10n.nbaFactorRecordTied,
        subtitle: '$awayName $recA · $homeName $recB',
      ));
    }

    // Factor 2: Rendimiento fuera / casa
    final awayStats = jsonMap(awayTeam['away']);
    final homeStats = jsonMap(homeTeam['home']);
    final awayRate = (awayStats['rate'] as num?)?.toDouble() ?? 0.0;
    final homeRate = (homeStats['rate'] as num?)?.toDouble() ?? 0.0;
    final awayRec = '${awayStats['won'] ?? 0}–${awayStats['lost'] ?? 0}';
    final homeRec = '${homeStats['won'] ?? 0}–${homeStats['lost'] ?? 0}';

    if (awayRate >= homeRate) {
      list.add(_NbaFactor(
        teamName: awayName,
        title: l10n.nbaFactorAwayForm,
        subtitle: '$awayName $awayRec (${(awayRate * 100).round()}%) · $homeName $homeRec (${(homeRate * 100).round()}%)',
      ));
    } else {
      list.add(_NbaFactor(
        teamName: homeName,
        title: l10n.nbaFactorHomeForm,
        subtitle: '$homeName $homeRec (${(homeRate * 100).round()}%) · $awayName $awayRec (${(awayRate * 100).round()}%)',
      ));
    }

    // Factor 3: Descanso
    final b2bA = awayTeam['back_to_back'] == true;
    final b2bB = homeTeam['back_to_back'] == true;
    final restA = (awayTeam['rest_days'] as num?)?.toInt() ?? 0;
    final restB = (homeTeam['rest_days'] as num?)?.toInt() ?? 0;

    if (b2bB && !b2bA) {
      list.add(_NbaFactor(
        teamName: awayName,
        title: l10n.nbaFactorRestAdvantage,
        subtitle: l10n.nbaPlayedYesterday(homeName),
      ));
    } else if (b2bA && !b2bB) {
      list.add(_NbaFactor(
        teamName: homeName,
        title: l10n.nbaFactorRestAdvantage,
        subtitle: l10n.nbaPlayedYesterday(awayName),
      ));
    } else if (restA > restB) {
      list.add(_NbaFactor(
        teamName: awayName,
        title: l10n.nbaFactorRestAdvantage,
        subtitle: '$awayName $restA · $homeName $restB',
      ));
    } else if (restB > restA) {
      list.add(_NbaFactor(
        teamName: homeName,
        title: l10n.nbaFactorRestAdvantage,
        subtitle: '$homeName $restB · $awayName $restA',
      ));
    } else {
      list.add(_NbaFactor(
        teamName: awayName,
        title: l10n.nbaFactorRestTied,
        subtitle: '$restA / $restB',
      ));
    }

    // Factor 4: Racha
    final streakA = (awayTeam['streak'] as num?)?.toInt() ?? 0;
    final streakB = (homeTeam['streak'] as num?)?.toInt() ?? 0;

    if (streakA > streakB) {
      list.add(_NbaFactor(
        teamName: awayName,
        title: l10n.nbaFactorStreakBest,
        subtitle: l10n.nbaStreakSummary(awayName, streakA, homeName, streakB),
      ));
    } else if (streakB > streakA) {
      list.add(_NbaFactor(
        teamName: homeName,
        title: l10n.nbaFactorStreakBest,
        subtitle: l10n.nbaStreakSummary(homeName, streakB, awayName, streakA),
      ));
    } else {
      list.add(_NbaFactor(
        teamName: awayName,
        title: l10n.nbaFactorStreakTied,
        subtitle: l10n.nbaStreakSummary(awayName, streakA, homeName, streakB),
      ));
    }

    return list;
  }

  // ==========================================
  // SECCIÓN 2: COMPARATIVA (7 FILAS)
  // ==========================================
  Widget _buildComparativaCard(
    BuildContext context,
    JsonMap awayTeam,
    JsonMap homeTeam,
    String awayName,
    String homeName,
  ) {
    final l10n = context.l10n;
    final temporada = '${widget.data['temporada'] ?? '2026-27'}';

    final seasonA = jsonMap(awayTeam['season']);
    final seasonB = jsonMap(homeTeam['season']);
    final rateA = (seasonA['rate'] as num?)?.toDouble() ?? 0.0;
    final rateB = (seasonB['rate'] as num?)?.toDouble() ?? 0.0;

    final awayStats = jsonMap(awayTeam['away']);
    final homeStats = jsonMap(homeTeam['home']);
    final awayRate = (awayStats['rate'] as num?)?.toDouble() ?? 0.0;
    final homeRate = (homeStats['rate'] as num?)?.toDouble() ?? 0.0;

    final scoringA = jsonMap(awayTeam['scoring']);
    final scoringB = jsonMap(homeTeam['scoring']);
    final pfA = (scoringA['points_for'] as num?)?.toDouble() ?? 0.0;
    final pfB = (scoringB['points_for'] as num?)?.toDouble() ?? 0.0;
    final paA = (scoringA['points_against'] as num?)?.toDouble() ?? 0.0;
    final paB = (scoringB['points_against'] as num?)?.toDouble() ?? 0.0;

    final dfA = pfA - paA;
    final dfB = pfB - paB;

    final last6A = jsonMap(awayTeam['last6']);
    final last6B = jsonMap(homeTeam['last6']);
    final l6RateA = (last6A['rate'] as num?)?.toDouble() ?? 0.0;
    final l6RateB = (last6B['rate'] as num?)?.toDouble() ?? 0.0;

    final restA = (awayTeam['rest_days'] as num?)?.toInt() ?? 0;
    final restB = (homeTeam['rest_days'] as num?)?.toInt() ?? 0;

    // Métricas evaluadas (1 = gana A, -1 = gana B, 0 = empate)
    final winners = <int>[
      rateA == rateB ? 0 : (rateA > rateB ? 1 : -1),
      awayRate == homeRate ? 0 : (awayRate > homeRate ? 1 : -1),
      pfA == pfB ? 0 : (pfA > pfB ? 1 : -1),
      paA == paB ? 0 : (paA < paB ? 1 : -1), // Menos puntos en contra es mejor
      dfA == dfB ? 0 : (dfA > dfB ? 1 : -1),
      l6RateA == l6RateB ? 0 : (l6RateA > l6RateB ? 1 : -1),
      restA == restB ? 0 : (restA > restB ? 1 : -1),
    ];

    return QfCard(
      key: _compKey,
      strong: true,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(
            l10n.nbaSeasonKicker(temporada),
            style: const TextStyle(
              fontFamily: qfDisplay,
              fontSize: 11,
              fontWeight: FontWeight.w700,
              color: QfColors.cyan,
              letterSpacing: 1.6,
            ),
          ),
          const SizedBox(height: 2),
          Text(
            l10n.nbaCompTitle,
            style: const TextStyle(
              fontFamily: qfDisplay,
              fontSize: 22,
              fontWeight: FontWeight.w700,
              color: QfColors.text,
              letterSpacing: .4,
            ),
          ),
          const SizedBox(height: 12),
          // Cabecera con escudos y barras indicadoras
          Row(
            children: [
              _teamLogo(awayName, 30),
              const SizedBox(width: 8),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      awayName,
                      style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 13, color: QfColors.text),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                    const SizedBox(height: 2),
                    Container(width: 22, height: 3, color: QfColors.cyan),
                  ],
                ),
              ),
              Text(
                '// $temporada',
                style: const TextStyle(
                  fontFamily: qfMono,
                  fontSize: 10,
                  color: QfColors.text2,
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.end,
                  children: [
                    Text(
                      homeName,
                      style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 13, color: QfColors.text),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      textAlign: TextAlign.right,
                    ),
                    const SizedBox(height: 2),
                    Container(width: 22, height: 3, color: const Color(0xFFD1D4DE)),
                  ],
                ),
              ),
              const SizedBox(width: 8),
              _teamLogo(homeName, 30),
            ],
          ),
          const SizedBox(height: 12),
          // Dominance dots
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
            decoration: BoxDecoration(border: Border.all(color: QfColors.border)),
            child: QfDominanceDots(
              winners: winners,
              homeName: awayName,
              awayName: homeName,
            ),
          ),
          const SizedBox(height: 12),
          // 7 Filas de métricas
          QfDivergingRow(
            label: l10n.nbaMetricRecord,
            a: rateA * 100,
            b: rateB * 100,
            formatA: '${(rateA * 100).round()}%',
            formatB: '${(rateB * 100).round()}%',
          ),
          QfDivergingRow(
            label: l10n.nbaMetricAwayHome,
            a: awayRate * 100,
            b: homeRate * 100,
            formatA: '${(awayRate * 100).round()}%',
            formatB: '${(homeRate * 100).round()}%',
          ),
          QfDivergingRow(
            label: l10n.nbaMetricPointsFor,
            a: pfA,
            b: pfB,
            formatA: pfA.toStringAsFixed(1),
            formatB: pfB.toStringAsFixed(1),
          ),
          QfDivergingRow(
            label: l10n.nbaMetricPointsAgainst,
            a: paA,
            b: paB,
            lowerIsBetter: true,
            formatA: paA.toStringAsFixed(1),
            formatB: paB.toStringAsFixed(1),
          ),
          QfDivergingRow(
            label: l10n.nbaMetricDiff,
            a: (dfA + 20).clamp(0, 40),
            b: (dfB + 20).clamp(0, 40),
            formatA: '${dfA >= 0 ? '+' : ''}${dfA.toStringAsFixed(1)}',
            formatB: '${dfB >= 0 ? '+' : ''}${dfB.toStringAsFixed(1)}',
          ),
          QfDivergingRow(
            label: l10n.nbaMetricLast6,
            a: l6RateA * 100,
            b: l6RateB * 100,
            formatA: '${(l6RateA * 100).round()}%',
            formatB: '${(l6RateB * 100).round()}%',
          ),
          QfDivergingRow(
            label: l10n.nbaMetricRestDays,
            a: restA,
            b: restB,
            formatA: '$restA',
            formatB: '$restB',
          ),
        ],
      ),
    );
  }

  // ==========================================
  // SECCIÓN 3: FORMA (CON QfMarginBars)
  // ==========================================
  Widget _buildFormaCard(
    BuildContext context,
    JsonMap awayTeam,
    JsonMap homeTeam,
    String awayName,
    String homeName,
  ) {
    final l10n = context.l10n;

    return QfCard(
      key: _formaKey,
      strong: true,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(
            l10n.nbaFormLast6,
            style: const TextStyle(
              fontFamily: qfDisplay,
              fontSize: 11,
              fontWeight: FontWeight.w700,
              color: QfColors.cyan,
              letterSpacing: 1.6,
            ),
          ),
          const SizedBox(height: 2),
          Text(
            l10n.anNavForm.toUpperCase(),
            style: const TextStyle(
              fontFamily: qfDisplay,
              fontSize: 22,
              fontWeight: FontWeight.w700,
              color: QfColors.text,
              letterSpacing: .4,
            ),
          ),
          const SizedBox(height: 12),
          _buildTeamFormBlock(context, awayTeam, awayName),
          const SizedBox(height: 12),
          _buildTeamFormBlock(context, homeTeam, homeName),
          const SizedBox(height: 10),
          // Leyenda de márgenes
          Row(
            children: [
              Container(width: 8, height: 8, color: QfColors.green),
              const SizedBox(width: 4),
              Text(
                l10n.nbaMarginWin,
                style: const TextStyle(
                  fontFamily: qfMono,
                  fontSize: 10,
                  color: QfColors.text2,
                ),
              ),
              const SizedBox(width: 14),
              Container(width: 8, height: 8, color: QfColors.magenta),
              const SizedBox(width: 4),
              Text(
                l10n.nbaMarginLoss,
                style: const TextStyle(
                  fontFamily: qfMono,
                  fontSize: 10,
                  color: QfColors.text2,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildTeamFormBlock(BuildContext context, JsonMap team, String teamName) {
    final l10n = context.l10n;
    final last6 = jsonMap(team['last6']);
    final rec = '${last6['won'] ?? 0}–${last6['lost'] ?? 0}';
    final pf = (last6['points_for'] as num?)?.toDouble().toStringAsFixed(1) ?? '0.0';
    final pa = (last6['points_against'] as num?)?.toDouble().toStringAsFixed(1) ?? '0.0';

    final formMap = jsonMap(team['form']);
    final allMatches = jsonRows(formMap['all']);
    // Tomar 6 partidos e invertirlos cronológicamente (más antiguo a la izquierda, último a la derecha)
    final matches = allMatches.take(6).toList().reversed.toList();

    final streak = (team['streak'] as num?)?.toInt() ?? 0;
    final streakText = streak > 0 ? l10n.anStreakWins(streak) : l10n.anStreakLosses(streak.abs());

    return Container(
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: .02),
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
                    _teamLogo(teamName, 28),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        teamName,
                        style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 14, color: QfColors.text),
                        overflow: TextOverflow.ellipsis,
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
                    rec,
                    style: const TextStyle(fontFamily: qfMono, fontWeight: FontWeight.w700, fontSize: 13, color: QfColors.cyan),
                  ),
                  Text(
                    l10n.nbaPtsAvg(pf, pa),
                    style: const TextStyle(fontFamily: qfMono, fontSize: 11, color: QfColors.text2),
                  ),
                ],
              ),
            ],
          ),
          const SizedBox(height: 10),
          // 6 partidos con margen
          Row(
            children: [
              for (var i = 0; i < matches.length; i++) ...[
                if (i > 0) const SizedBox(width: 4),
                Expanded(child: _buildFormItem(matches[i], isLast: i == matches.length - 1)),
              ],
            ],
          ),
          const SizedBox(height: 8),
          Align(
            alignment: Alignment.centerLeft,
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
              decoration: BoxDecoration(
                border: Border.all(color: QfColors.green.withValues(alpha: .4)),
              ),
              child: Text(
                l10n.nbaStreakLabel(streakText),
                style: const TextStyle(
                  fontFamily: qfDisplay,
                  fontSize: 11,
                  fontWeight: FontWeight.w700,
                  color: QfColors.green,
                  letterSpacing: .8,
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildFormItem(JsonMap match, {required bool isLast}) {
    final l10n = context.l10n;
    final opponent = '${match['opponent'] ?? ''}';
    final oppCode = nbaTricode(opponent) ?? (opponent.length > 3 ? opponent.substring(0, 3).toUpperCase() : opponent);
    final isHome = match['home'] == true;
    final oppLabel = isHome ? 'vs $oppCode' : '@ $oppCode';

    final won = match['won'] == true;
    final pts = (match['points'] as num?)?.toInt() ?? 0;
    final oppPts = (match['opponent_points'] as num?)?.toInt() ?? 0;
    final margin = pts - oppPts;

    final color = won ? QfColors.green : QfColors.magenta;
    final letter = won ? 'G' : 'P';

    // Altura proporcional del margen (máximo 30 puntos normalizado a 22 dp)
    final barHeight = ((margin.abs() / 30.0).clamp(0.1, 1.0) * 22.0).toDouble();

    return Column(
      children: [
        Text(
          oppLabel,
          style: const TextStyle(
            fontFamily: qfMono,
            fontSize: 9,
            color: QfColors.text2,
          ),
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
        ),
        const SizedBox(height: 3),
        Container(
          width: double.infinity,
          height: 34,
          alignment: Alignment.center,
          decoration: ShapeDecoration(
            color: color.withValues(alpha: .12),
            shape: CutCornerBorder(
              cut: 6,
              side: BorderSide(
                color: isLast ? QfColors.cyan : color,
                width: isLast ? 2 : 1,
              ),
            ),
            shadows: isLast
                ? [
                    BoxShadow(
                      color: QfColors.cyan.withValues(alpha: .3),
                      blurRadius: 10,
                    ),
                  ]
                : null,
          ),
          child: Text(
            letter,
            style: TextStyle(
              fontFamily: qfDisplay,
              fontSize: 16,
              fontWeight: FontWeight.w700,
              color: color,
            ),
          ),
        ),
        const SizedBox(height: 3),
        Text(
          '$pts–$oppPts',
          style: const TextStyle(fontFamily: qfMono, fontSize: 10, fontWeight: FontWeight.w700),
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
        ),
        const SizedBox(height: 2),
        // Eje central de márgenes
        SizedBox(
          height: 44,
          child: Column(
            children: [
              // Parte superior (ganancia)
              Expanded(
                child: Align(
                  alignment: Alignment.bottomCenter,
                  child: won
                      ? Container(width: 14, height: barHeight, color: QfColors.green)
                      : const SizedBox.shrink(),
                ),
              ),
              Container(height: 1, color: QfColors.border),
              // Parte inferior (pérdida)
              Expanded(
                child: Align(
                  alignment: Alignment.topCenter,
                  child: !won
                      ? Container(width: 14, height: barHeight, color: QfColors.magenta)
                      : const SizedBox.shrink(),
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 2),
        Text(
          '${margin > 0 ? '+' : '−'}${margin.abs()}',
          style: TextStyle(fontFamily: qfMono, fontSize: 10, fontWeight: FontWeight.w700, color: color),
        ),
        SizedBox(
          height: 12,
          child: isLast
              ? Text(
                  l10n.anLastMatch,
                  style: const TextStyle(
                    fontFamily: qfDisplay,
                    fontSize: 9,
                    fontWeight: FontWeight.w700,
                    color: QfColors.cyan,
                    letterSpacing: .8,
                  ),
                )
              : const SizedBox.shrink(),
        ),
      ],
    );
  }

  // ==========================================
  // SECCIÓN 4: CARA A CARA (H2H)
  // ==========================================
  Widget _buildH2hCard(
    BuildContext context,
    JsonMap h2hData,
    String awayName,
    String homeName,
  ) {
    final l10n = context.l10n;
    final matches = jsonRows(h2hData['matches']);
    final totalMatches = matches.length;

    // Calcular victorias de cada equipo
    final homeWins = (h2hData['home_wins'] as num?)?.toInt() ?? 0;
    final awayWins = (h2hData['away_wins'] as num?)?.toInt() ?? 0;
    final avgTotal = (h2hData['average_total'] as num?)?.toDouble().toStringAsFixed(1) ?? '—';

    // Primeros 4 partidos más recientes
    final recentMatches = matches.take(4).toList();

    return QfCard(
      key: _h2hKey,
      strong: true,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(
            l10n.nbaH2hLastN(totalMatches),
            style: const TextStyle(
              fontFamily: qfDisplay,
              fontSize: 11,
              fontWeight: FontWeight.w700,
              color: QfColors.cyan,
              letterSpacing: 1.6,
            ),
          ),
          const SizedBox(height: 2),
          Text(
            l10n.anNavH2h.toUpperCase(),
            style: const TextStyle(
              fontFamily: qfDisplay,
              fontSize: 22,
              fontWeight: FontWeight.w700,
              color: QfColors.text,
              letterSpacing: .4,
            ),
          ),
          const SizedBox(height: 12),
          // Fila de victorias de cada lado
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Row(
                children: [
                  _teamLogo(awayName, 34),
                  const SizedBox(width: 8),
                  Text(
                    '$awayWins',
                    style: const TextStyle(
                      fontFamily: qfMono,
                      fontSize: 30,
                      fontWeight: FontWeight.w700,
                      color: QfColors.cyan,
                    ),
                  ),
                ],
              ),
              Text(
                l10n.nbaWinsLabel,
                style: const TextStyle(
                  fontFamily: qfDisplay,
                  fontSize: 10,
                  fontWeight: FontWeight.w700,
                  color: QfColors.text2,
                  letterSpacing: 1.2,
                ),
              ),
              Row(
                children: [
                  Text(
                    '$homeWins',
                    style: const TextStyle(
                      fontFamily: qfMono,
                      fontSize: 30,
                      fontWeight: FontWeight.w700,
                      color: Color(0xFFD1D4DE),
                    ),
                  ),
                  const SizedBox(width: 8),
                  _teamLogo(homeName, 34),
                ],
              ),
            ],
          ),
          const SizedBox(height: 10),
          // Barra apilada proporcional
          SizedBox(
            height: 10,
            child: Row(
              children: [
                Expanded(
                  flex: awayWins.clamp(1, 999),
                  child: Container(color: QfColors.cyan),
                ),
                const SizedBox(width: 3),
                Expanded(
                  flex: homeWins.clamp(1, 999),
                  child: Container(color: const Color(0xFFD1D4DE)),
                ),
              ],
            ),
          ),
          const SizedBox(height: 12),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
            decoration: BoxDecoration(border: Border.all(color: QfColors.border)),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  l10n.nbaTotalPtsPerGame,
                  style: const TextStyle(
                    fontFamily: qfDisplay,
                    fontSize: 11,
                    fontWeight: FontWeight.w700,
                    color: QfColors.text2,
                    letterSpacing: 1.2,
                  ),
                ),
                Text(
                  avgTotal,
                  style: const TextStyle(
                    fontFamily: qfMono,
                    fontSize: 18,
                    fontWeight: FontWeight.w700,
                    color: QfColors.cyan,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 12),
          // Lista de partidos recientes
          Container(
            decoration: BoxDecoration(border: Border.all(color: QfColors.border)),
            child: Column(
              children: [
                for (var i = 0; i < recentMatches.length; i++) ...[
                  if (i > 0) const Divider(height: 1, color: QfColors.border),
                  _buildH2hMatchRow(recentMatches[i]),
                ],
              ],
            ),
          ),
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
                    l10n.nbaViewAllH2h,
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

  Widget _buildH2hMatchRow(JsonMap match) {
    final rawDate = '${match['date'] ?? ''}';
    final dateStr = _fmtDate(rawDate);
    final homeTeamStr = '${match['home'] ?? ''}';
    final awayTeamStr = '${match['away'] ?? ''}';
    final homePts = (match['home_points'] as num?)?.toInt() ?? 0;
    final awayPts = (match['away_points'] as num?)?.toInt() ?? 0;

    final winnerName = homePts > awayPts ? homeTeamStr : awayTeamStr;
    final winnerCode = nbaTricode(winnerName) ?? winnerName;

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
      child: Row(
        children: [
          SizedBox(
            width: 75,
            child: Text(
              dateStr,
              style: const TextStyle(fontFamily: qfMono, fontSize: 10, color: QfColors.text2),
            ),
          ),
          Expanded(
            child: Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                _teamLogo(homeTeamStr, 24),
                const SizedBox(width: 8),
                Text(
                  '$homePts–$awayPts',
                  style: const TextStyle(fontFamily: qfMono, fontSize: 14, fontWeight: FontWeight.w700),
                ),
                const SizedBox(width: 8),
                _teamLogo(awayTeamStr, 24),
              ],
            ),
          ),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
            decoration: BoxDecoration(border: Border.all(color: QfColors.cyan)),
            child: Text(
              winnerCode,
              style: const TextStyle(
                fontFamily: qfDisplay,
                fontSize: 11,
                fontWeight: FontWeight.w700,
                color: QfColors.cyan,
              ),
            ),
          ),
        ],
      ),
    );
  }

  // ==========================================
  // SECCIÓN 5: CLASIFICACIÓN (QfSeasonTrack)
  // ==========================================
  Widget _buildClasificacionCard(
    BuildContext context,
    JsonMap awayTeam,
    JsonMap homeTeam,
    String awayName,
    String homeName,
  ) {
    final l10n = context.l10n;
    final standingA = jsonMap(awayTeam['standing']);
    final standingB = jsonMap(homeTeam['standing']);

    final confRaw = '${standingA['conference'] ?? standingB['conference'] ?? 'este'}'.toLowerCase();
    final isWest = confRaw.contains('oeste') || confRaw.contains('west');
    final confName = isWest ? l10n.nbaConfWest : l10n.nbaConfEast;

    final rankA = (standingA['rank'] as num?)?.toInt() ?? 1;
    final rankB = (standingB['rank'] as num?)?.toInt() ?? 1;

    final seasonA = jsonMap(awayTeam['season']);
    final seasonB = jsonMap(homeTeam['season']);
    final rateA = (seasonA['rate'] as num?)?.toDouble() ?? 0.0;
    final rateB = (seasonB['rate'] as num?)?.toDouble() ?? 0.0;

    final lastSeasonA = jsonMap(awayTeam['last_season']);
    final lastSeasonB = jsonMap(homeTeam['last_season']);
    final lastRecA = '${lastSeasonA['won'] ?? 0}–${lastSeasonA['lost'] ?? 0}';
    final lastRecB = '${lastSeasonB['won'] ?? 0}–${lastSeasonB['lost'] ?? 0}';

    final diff = (rankA - rankB).abs();
    final calloutText = rankA < rankB
        ? l10n.nbaStandingsCallout(awayName, diff, homeName, confName)
        : (rankB < rankA
            ? l10n.nbaStandingsCallout(homeName, diff, awayName, confName)
            : l10n.nbaStandingsCalloutTied(awayName, homeName, confName));

    final awayCode = nbaTricode(awayName) ?? awayName;
    final homeCode = nbaTricode(homeName) ?? homeName;

    return QfCard(
      key: _tablaKey,
      strong: true,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(
            l10n.nbaConfStandingsKicker(confName.toUpperCase(), 15),
            style: const TextStyle(
              fontFamily: qfDisplay,
              fontSize: 11,
              fontWeight: FontWeight.w700,
              color: QfColors.cyan,
              letterSpacing: 1.6,
            ),
          ),
          const SizedBox(height: 2),
          Text(
            l10n.anStandingsTitle.toUpperCase(),
            style: const TextStyle(
              fontFamily: qfDisplay,
              fontSize: 22,
              fontWeight: FontWeight.w700,
              color: QfColors.text,
              letterSpacing: .4,
            ),
          ),
          const SizedBox(height: 14),
          // Cinta de 15 casillas con marcadores
          QfSeasonTrack(
            size: 15,
            homeRank: rankB,
            awayRank: rankA,
            homeCode: homeCode,
            awayCode: awayCode,
          ),
          const SizedBox(height: 12),
          // Leyenda de zonas
          Wrap(
            spacing: 12,
            runSpacing: 4,
            children: [
              Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Container(width: 8, height: 8, color: QfColors.cyan),
                  const SizedBox(width: 4),
                  Text(
                    l10n.nbaLegendPlayoffs,
                    style: const TextStyle(fontFamily: qfMono, fontSize: 10, color: QfColors.text2),
                  ),
                ],
              ),
              Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Container(width: 8, height: 8, color: QfColors.slate),
                  const SizedBox(width: 4),
                  Text(
                    l10n.nbaLegendPlayIn,
                    style: const TextStyle(fontFamily: qfMono, fontSize: 10, color: QfColors.text2),
                  ),
                ],
              ),
              Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Container(width: 8, height: 8, color: QfColors.track),
                  const SizedBox(width: 4),
                  Text(
                    l10n.nbaLegendOut,
                    style: const TextStyle(fontFamily: qfMono, fontSize: 10, color: QfColors.text2),
                  ),
                ],
              ),
            ],
          ),
          const SizedBox(height: 12),
          // Dos tarjetas de resumen de puestos
          Row(
            children: [
              Expanded(
                child: Container(
                  padding: const EdgeInsets.all(10),
                  decoration: BoxDecoration(
                    color: QfColors.cyan.withValues(alpha: .06),
                    border: Border.all(color: QfColors.cyan),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        awayName,
                        style: const TextStyle(fontFamily: qfDisplay, fontSize: 11, fontWeight: FontWeight.w700, color: QfColors.text2),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                      Text(
                        l10n.nbaRankOf(rankA, 15),
                        style: const TextStyle(fontFamily: qfMono, fontSize: 20, fontWeight: FontWeight.w700, color: QfColors.cyan),
                      ),
                      Text(
                        '${seasonA['won'] ?? 0}–${seasonA['lost'] ?? 0} · ${(rateA * 100).toStringAsFixed(1)} %',
                        style: const TextStyle(fontFamily: qfMono, fontSize: 11, color: QfColors.text2),
                      ),
                      const SizedBox(height: 2),
                      Text(
                        l10n.nbaLastSeason(lastRecA),
                        style: const TextStyle(fontFamily: qfMono, fontSize: 10, color: QfColors.text2),
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: Container(
                  padding: const EdgeInsets.all(10),
                  decoration: BoxDecoration(
                    border: Border.all(color: QfColors.border),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        homeName,
                        style: const TextStyle(fontFamily: qfDisplay, fontSize: 11, fontWeight: FontWeight.w700, color: QfColors.text2),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                      Text(
                        l10n.nbaRankOf(rankB, 15),
                        style: const TextStyle(fontFamily: qfMono, fontSize: 20, fontWeight: FontWeight.w700, color: Color(0xFFD1D4DE)),
                      ),
                      Text(
                        '${seasonB['won'] ?? 0}–${seasonB['lost'] ?? 0} · ${(rateB * 100).toStringAsFixed(1)} %',
                        style: const TextStyle(fontFamily: qfMono, fontSize: 11, color: QfColors.text2),
                      ),
                      const SizedBox(height: 2),
                      Text(
                        l10n.nbaLastSeason(lastRecB),
                        style: const TextStyle(fontFamily: qfMono, fontSize: 10, color: QfColors.text2),
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),
          // Callout de diferencia
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
            decoration: BoxDecoration(
              color: QfColors.cyan.withValues(alpha: .07),
              border: Border.all(color: QfColors.cyan.withValues(alpha: .4)),
            ),
            child: Text(
              calloutText,
              style: const TextStyle(fontSize: 13, color: QfColors.text),
            ),
          ),
        ],
      ),
    );
  }

  // ==========================================
  // SECCIÓN 6: DISPONIBILIDAD
  // ==========================================
  Widget _buildDisponibilidadCard(
    BuildContext context,
    JsonMap awayTeam,
    JsonMap homeTeam,
    String awayName,
    String homeName,
  ) {
    final l10n = context.l10n;
    final a = widget.event.availability ?? {};

    final isApplied = a['state'] == 'reporte_aplicado';
    final listedCount = (a['listed'] as num?)?.toInt() ?? 0;

    final missingAway = (a['missing_minutes_away'] as num?)?.toInt() ?? 0;
    final missingHome = (a['missing_minutes_home'] as num?)?.toInt() ?? 0;

    return QfCard(
      key: _dispKey,
      strong: true,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(
            l10n.nbaAvailKicker,
            style: const TextStyle(
              fontFamily: qfDisplay,
              fontSize: 11,
              fontWeight: FontWeight.w700,
              color: QfColors.cyan,
              letterSpacing: 1.6,
            ),
          ),
          const SizedBox(height: 2),
          Text(
            l10n.nbaAvailTitle,
            style: const TextStyle(
              fontFamily: qfDisplay,
              fontSize: 22,
              fontWeight: FontWeight.w700,
              color: QfColors.text,
              letterSpacing: .4,
            ),
          ),
          const SizedBox(height: 12),
          _buildTeamAvailBlock(
            context,
            teamName: awayName,
            isApplied: isApplied,
            listedCount: listedCount,
            missingMinutes: missingAway,
            backToBack: awayTeam['back_to_back'] == true,
            restDays: (awayTeam['rest_days'] as num?)?.toInt() ?? 1,
          ),
          const SizedBox(height: 12),
          _buildTeamAvailBlock(
            context,
            teamName: homeName,
            isApplied: isApplied,
            listedCount: listedCount,
            missingMinutes: missingHome,
            backToBack: homeTeam['back_to_back'] == true,
            restDays: (homeTeam['rest_days'] as num?)?.toInt() ?? 0,
          ),
          const SizedBox(height: 8),
          Text(
            l10n.nbaAvailFootnote,
            style: const TextStyle(
              fontSize: 11,
              color: QfColors.text2,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildTeamAvailBlock(
    BuildContext context, {
    required String teamName,
    required bool isApplied,
    required int listedCount,
    required int missingMinutes,
    required bool backToBack,
    required int restDays,
  }) {
    final l10n = context.l10n;

    // Indicador de color para minutos de bajas (< 20 verde, < 50 amarillo, >= 50 magenta)
    Color minColor;
    if (missingMinutes < 20) {
      minColor = QfColors.green;
    } else if (missingMinutes < 50) {
      minColor = QfColors.yellow;
    } else {
      minColor = QfColors.magenta;
    }

    final restText = (backToBack || restDays == 0)
        ? l10n.nbaBackToBackYesterday
        : l10n.nbaRestedDays(restDays);
    final restColor = (backToBack || restDays == 0) ? QfColors.magenta : QfColors.green;

    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: .02),
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
                    _teamLogo(teamName, 28),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        teamName,
                        style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 14, color: QfColors.text),
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 8),
              isApplied
                  ? QfBadge(
                      l10n.sportAvailApplied,
                      color: QfColors.green,
                      icon: Icons.check_circle_outline,
                    )
                  : QfBadge(
                      l10n.sportAvailPending,
                      color: QfColors.text2,
                      icon: Icons.schedule,
                    ),
            ],
          ),
          const SizedBox(height: 8),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            crossAxisAlignment: CrossAxisAlignment.baseline,
            textBaseline: TextBaseline.alphabetic,
            children: [
              Text(
                l10n.sportAvailListed(listedCount > 0 ? listedCount : 1),
                style: const TextStyle(fontSize: 13, color: QfColors.text2),
              ),
              Text(
                l10n.nbaMinutesMissing(missingMinutes),
                style: TextStyle(
                  fontFamily: qfMono,
                  fontSize: 18,
                  fontWeight: FontWeight.w700,
                  color: minColor,
                ),
              ),
            ],
          ),
          const SizedBox(height: 6),
          // Barra de minutos de bajas
          SizedBox(
            height: 8,
            child: Stack(
              children: [
                Container(color: Colors.white.withValues(alpha: .06)),
                FractionallySizedBox(
                  widthFactor: (missingMinutes / 100.0).clamp(0.04, 1.0),
                  child: Container(color: minColor),
                ),
              ],
            ),
          ),
          const SizedBox(height: 8),
          Align(
            alignment: Alignment.centerLeft,
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
              decoration: BoxDecoration(
                border: Border.all(color: restColor.withValues(alpha: .4)),
              ),
              child: Text(
                restText,
                style: TextStyle(
                  fontFamily: qfDisplay,
                  fontSize: 11,
                  fontWeight: FontWeight.w700,
                  color: restColor,
                  letterSpacing: .8,
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _NbaFactor {
  const _NbaFactor({
    required this.teamName,
    required this.title,
    required this.subtitle,
  });

  final String teamName;
  final String title;
  final String subtitle;
}
