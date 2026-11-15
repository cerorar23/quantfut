import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:gobet/l10n/pick_labels.dart';

import '../l10n/app_locale.dart';
import 'live_api.dart';
import 'qf_charts.dart';
import 'qf_controls.dart';
import 'qf_shapes.dart';
import 'qf_theme.dart';
import 'sport_images.dart';
import 'sports_feed.dart';

/// Pestaña de Análisis de Tenis con estética CyberCore.
///
/// Presenta 5 secciones navegables mediante [QfSectionNav]:
/// 1. Probabilidad: 2 tarjetas de jugador con foto redonda (76 dp), porcentaje mono
///    con resplandor, ranking, puntos, edad, país, barra proporcional y brecha de ranking.
/// 2. Forma: tarjeta por tenista con índice de forma (0–100), 5 últimos partidos con
///    ronda traducida y marcador, racha, porcentaje a 3 sets y tie-breaks.
/// 3. Superficie: rendimiento en pista dura, tierra y hierba (carrera y temporada),
///    marcando la superficie del partido de hoy con «HOY».
/// 4. Cara a cara: estado «0 – 0 · PRIMER DUELO» cuando no hay enfrentamientos directos,
///    o historial de partidos con barra apilada y botón «VER TODOS EN H2H».
/// 5. Modelo: expectativas del modelo de QuantFut a partir de los mercados sellados
///    (duración en sets, victoria por set, barras de juegos totales, hándicap y tie-break).
class TennisAnalysis extends StatefulWidget {
  const TennisAnalysis({
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
  State<TennisAnalysis> createState() => _TennisAnalysisState();
}

class _TennisAnalysisState extends State<TennisAnalysis> {
  int _navIndex = 0;

  final _probKey = GlobalKey();
  final _formaKey = GlobalKey();
  final _supKey = GlobalKey();
  final _h2hKey = GlobalKey();
  final _modeloKey = GlobalKey();

  Widget _playerAvatar(String name, double size, {bool isLeader = false}) {
    final photo = widget.images?.tennisPhoto(name);
    final url = photo != null && widget.api != null
        ? serverImageUrl(widget.api!, photo.path)
        : null;

    return Container(
      width: size,
      height: size,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        border: Border.all(
          color: isLeader ? QfColors.cyan : QfColors.cyan.withValues(alpha: .55),
          width: 2,
        ),
      ),
      child: ClipOval(
        child: QfAvatar(
          url: url,
          name: name,
          size: size,
        ),
      ),
    );
  }

  String _shortName(String fullName) {
    final parts = fullName.trim().split(RegExp(r'\s+'));
    if (parts.isEmpty) return fullName;
    if (parts.length == 1) return parts.first;
    // Retorna el apellido o último token significativo
    return parts.last;
  }

  JsonMap? _findPlayer(List<dynamic> players, String targetName) {
    final targetNorm = targetName.trim().toLowerCase();
    for (final item in players) {
      if (item is Map) {
        final p = item as JsonMap;
        final name = '${p['name'] ?? ''}'.trim().toLowerCase();
        if (name == targetNorm) return p;
        // Coincidencia parcial si están invertidos
        final parts1 = targetNorm.split(RegExp(r'\s+')).where((s) => s.length > 2).toSet();
        final parts2 = name.split(RegExp(r'\s+')).where((s) => s.length > 2).toSet();
        if (parts1.isNotEmpty && parts2.isNotEmpty && parts1.intersection(parts2).length >= 2) {
          return p;
        }
      }
    }
    return null;
  }

  String _translateSurfaceName(AppLocalizations l10n, String surface) {
    final s = surface.trim().toLowerCase();
    return switch (s) {
      'clay' || 'tierra' || 'arcilla' => l10n.tenSurfaceClay,
      'hard' || 'dura' => l10n.tenSurfaceHard,
      'grass' || 'hierba' => l10n.tenSurfaceGrass,
      _ => surface.toUpperCase(),
    };
  }

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final event = widget.event;
    final data = widget.data;

    final players = jsonRows(data['players']);
    if (players.isEmpty) {
      return QfCard(
        child: Row(
          children: [
            const Icon(Icons.info_outline, color: QfColors.text2, size: 18),
            const SizedBox(width: 10),
            Expanded(
              child: Text(
                l10n.sportStatsUnavailable,
                style: const TextStyle(color: QfColors.text2),
              ),
            ),
          ],
        ),
      );
    }

    final playerA = _findPlayer(players, event.home) ?? players[0];
    final playerB = _findPlayer(players, event.away) ?? (players.length > 1 ? players[1] : players[0]);

    final nameA = event.home;
    final nameB = event.away;

    final formA = jsonMap(playerA['form']);
    final formB = jsonMap(playerB['form']);
    final hasForm = formA.isNotEmpty || formB.isNotEmpty;

    final surfacesA = jsonMap(playerA['surfaces']);
    final surfacesB = jsonMap(playerB['surfaces']);
    final hasSurface = surfacesA.isNotEmpty || surfacesB.isNotEmpty;

    final h2hData = jsonMap(data['h2h']);
    final hasH2h = h2hData.isNotEmpty || data.containsKey('h2h');

    // Comprobar mercados del modelo
    final markets = event.markets;
    final hasModel = markets.any((m) =>
        m.id.startsWith('sets_total') ||
        m.id.startsWith('set_winner') ||
        m.id.startsWith('games_total') ||
        m.id.startsWith('games_handicap') ||
        m.id.startsWith('tiebreak'));

    final sections = <(String, GlobalKey)>[
      (l10n.tenNavProb.toUpperCase(), _probKey),
      if (hasForm) (l10n.anNavForm.toUpperCase(), _formaKey),
      if (hasSurface) (l10n.tenNavSurface.toUpperCase(), _supKey),
      if (hasH2h) (l10n.anNavH2h.toUpperCase(), _h2hKey),
      if (hasModel) (l10n.tenNavModel.toUpperCase(), _modeloKey),
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
        _buildProbabilidadCard(context, playerA, playerB, nameA, nameB),
        if (hasForm) ...[
          const SizedBox(height: 14),
          _buildFormaCard(context, playerA, playerB, nameA, nameB),
        ],
        if (hasSurface) ...[
          const SizedBox(height: 14),
          _buildSuperficieCard(context, playerA, playerB, nameA, nameB),
        ],
        if (hasH2h) ...[
          const SizedBox(height: 14),
          _buildH2hCard(context, h2hData, nameA, nameB),
        ],
        if (hasModel) ...[
          const SizedBox(height: 14),
          _buildModeloCard(context, nameA, nameB),
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
    JsonMap playerA,
    JsonMap playerB,
    String nameA,
    String nameB,
  ) {
    final l10n = context.l10n;
    final event = widget.event;

    // Obtener probabilidad del ganador
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
      pa = (pHome * 100).round();
      pb = 100 - pa;
    }

    int? toInt(dynamic v) {
      if (v is num) return v.toInt();
      if (v is String) return int.tryParse(v);
      return null;
    }

    final rankA = toInt(playerA['rank']);
    final rankB = toInt(playerB['rank']);
    final ptsA = playerA['points'];
    final ptsB = playerB['points'];
    final ageA = toInt(playerA['age']);
    final ageB = toInt(playerB['age']);
    final countryA = '${playerA['country'] ?? ''}';
    final countryB = '${playerB['country'] ?? ''}';
    final mvA = '${playerA['movement'] ?? ''}'.toLowerCase() == 'up'
        ? '▲'
        : ('${playerA['movement'] ?? ''}'.toLowerCase() == 'down' ? '▼' : '');
    final mvB = '${playerB['movement'] ?? ''}'.toLowerCase() == 'up'
        ? '▲'
        : ('${playerB['movement'] ?? ''}'.toLowerCase() == 'down' ? '▼' : '');

    final circuit = '${widget.data['circuit'] ?? (event.league.contains('WTA') ? 'WTA' : 'ATP')}';

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
            l10n.tenWinProbTitle,
            style: const TextStyle(
              fontFamily: qfDisplay,
              fontSize: 22,
              fontWeight: FontWeight.w700,
              color: QfColors.text,
              letterSpacing: .4,
            ),
          ),
          const SizedBox(height: 12),
          Row(
            children: [
              Expanded(
                child: _buildPlayerProbCard(
                  name: nameA,
                  percent: pa,
                  rank: rankA,
                  points: ptsA,
                  movement: mvA,
                  age: ageA,
                  country: countryA,
                  isLeader: pa != null && pb != null ? pa >= pb : false,
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: _buildPlayerProbCard(
                  name: nameB,
                  percent: pb,
                  rank: rankB,
                  points: ptsB,
                  movement: mvB,
                  age: ageB,
                  country: countryB,
                  isLeader: pa != null && pb != null ? pb > pa : false,
                ),
              ),
            ],
          ),
          if (pa != null && pb != null) ...[
            const SizedBox(height: 10),
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
          if (rankA != null && rankB != null) ...[
            const SizedBox(height: 12),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
              decoration: BoxDecoration(
                color: QfColors.cyan.withValues(alpha: .07),
                border: Border.all(color: QfColors.cyan.withValues(alpha: .4)),
              ),
              child: Text(
                rankA < rankB
                    ? l10n.tenGapLeader(_shortName(nameA), rankB - rankA, circuit)
                    : (rankB < rankA
                        ? l10n.tenGapLeader(_shortName(nameB), rankA - rankB, circuit)
                        : l10n.tenGapTied(_shortName(nameA), _shortName(nameB), circuit)),
                style: const TextStyle(
                  fontSize: 13,
                  fontWeight: FontWeight.w600,
                  color: QfColors.text,
                ),
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildPlayerProbCard({
    required String name,
    required int? percent,
    required int? rank,
    required dynamic points,
    required String movement,
    required int? age,
    required String country,
    required bool isLeader,
  }) {
    final l10n = context.l10n;
    final rankStr = rank != null ? l10n.tenRankNumber(rank) : '—';
    final ptsStr = points != null ? '$points' : '—';
    final rankPts = '$rankStr · $ptsStr pts $movement'.trim();
    final ageCountry = age != null ? l10n.tenAgeYears(age, country) : country;

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 12),
      decoration: BoxDecoration(
        color: isLeader ? QfColors.cyan.withValues(alpha: .07) : Colors.white.withValues(alpha: .02),
        border: Border.all(
          color: isLeader ? QfColors.cyan : QfColors.border,
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
          _playerAvatar(name, 76, isLeader: isLeader),
          const SizedBox(height: 6),
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
          const SizedBox(height: 2),
          Text(
            percent != null ? '$percent%' : '—',
            style: TextStyle(
              fontFamily: qfMono,
              fontSize: 34,
              fontWeight: FontWeight.w700,
              color: isLeader ? QfColors.cyan : const Color(0xFFD1D4DE),
              height: 1.1,
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
          const SizedBox(height: 4),
          Text(
            rankPts,
            style: const TextStyle(
              fontFamily: qfMono,
              fontSize: 11,
              fontWeight: FontWeight.w500,
              color: QfColors.slate,
            ),
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: 2),
          Text(
            ageCountry,
            style: const TextStyle(
              fontFamily: qfDisplay,
              fontSize: 10,
              fontWeight: FontWeight.w700,
              letterSpacing: 1.2,
              color: QfColors.text2,
            ),
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            textAlign: TextAlign.center,
          ),
        ],
      ),
    );
  }

  // ==========================================
  // SECCIÓN 2: FORMA
  // ==========================================
  Widget _buildFormaCard(
    BuildContext context,
    JsonMap playerA,
    JsonMap playerB,
    String nameA,
    String nameB,
  ) {
    final l10n = context.l10n;

    return QfCard(
      key: _formaKey,
      strong: true,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(
            l10n.tenFormKicker,
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
          _buildPlayerFormCard(playerA, nameA),
          const SizedBox(height: 12),
          _buildPlayerFormCard(playerB, nameB),
        ],
      ),
    );
  }

  Widget _buildPlayerFormCard(JsonMap player, String playerName) {
    final l10n = context.l10n;
    final form = jsonMap(player['form']);
    final rawMatches = jsonRows(form['matches']);
    final matches = rawMatches.take(5).toList();

    final wonCount = rawMatches.where((m) => m['won'] == true).length;
    final lostCount = rawMatches.length - wonCount;
    final rec = '$wonCount–$lostCount';

    final idx = (form['index'] as num?)?.toInt() ?? 50;
    final streak = (form['streak'] as num?)?.toInt() ?? 0;
    final overSets = (form['over_2_5_sets'] as num?)?.toDouble() ?? 0.0;
    final tiebreaks = (form['tiebreaks'] as num?)?.toDouble() ?? 0.0;

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
                    _playerAvatar(playerName, 34),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        playerName,
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
                    l10n.tenLastMatchesCount(rawMatches.length),
                    style: const TextStyle(fontFamily: qfMono, fontSize: 10, color: QfColors.text2),
                  ),
                ],
              ),
            ],
          ),
          const SizedBox(height: 10),
          // Barra de índice de forma
          Row(
            children: [
              Text(
                l10n.tenFormIndex,
                style: const TextStyle(fontFamily: qfDisplay, fontSize: 10, fontWeight: FontWeight.w700, color: QfColors.text2),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: ClipRRect(
                  borderRadius: BorderRadius.circular(2),
                  child: Container(
                    height: 6,
                    color: QfColors.track,
                    child: Align(
                      alignment: Alignment.centerLeft,
                      child: FractionallySizedBox(
                        widthFactor: (idx / 100.0).clamp(0.05, 1.0),
                        child: Container(color: QfColors.cyan),
                      ),
                    ),
                  ),
                ),
              ),
              const SizedBox(width: 8),
              Text(
                '$idx / 100',
                style: const TextStyle(fontFamily: qfMono, fontSize: 11, fontWeight: FontWeight.w700, color: QfColors.cyan),
              ),
            ],
          ),
          const SizedBox(height: 10),
          // 5 últimos partidos
          for (final m in matches) ...[
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 4),
              child: Row(
                children: [
                  Container(
                    width: 24,
                    height: 24,
                    alignment: Alignment.center,
                    decoration: ShapeDecoration(
                      color: m['won'] == true
                          ? QfColors.green.withValues(alpha: .14)
                          : QfColors.magenta.withValues(alpha: .14),
                      shape: const CutCornerBorder(cut: 4),
                    ),
                    child: Text(
                      m['won'] == true ? 'G' : 'P',
                      style: TextStyle(
                        fontFamily: qfDisplay,
                        fontSize: 13,
                        fontWeight: FontWeight.w700,
                        color: m['won'] == true ? QfColors.green : QfColors.magenta,
                      ),
                    ),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'vs ${m['opponent'] ?? ''}',
                          style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 13, color: QfColors.text),
                          overflow: TextOverflow.ellipsis,
                        ),
                        Text(
                          '${tennisRoundLabel('${m['round'] ?? ''}')} · ${m['tournament'] ?? ''}',
                          style: const TextStyle(fontSize: 11, color: QfColors.slate),
                          overflow: TextOverflow.ellipsis,
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(width: 8),
                  Text(
                    '${m['score'] ?? ''}',
                    style: const TextStyle(fontFamily: qfMono, fontWeight: FontWeight.w700, fontSize: 12, color: QfColors.text),
                  ),
                ],
              ),
            ),
          ],
          const SizedBox(height: 8),
          // Chips de racha y métricas
          Wrap(
            spacing: 6,
            runSpacing: 6,
            children: [
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                decoration: BoxDecoration(
                  border: Border.all(
                    color: streak >= 0 ? QfColors.green.withValues(alpha: .4) : QfColors.magenta.withValues(alpha: .4),
                  ),
                  color: streak >= 0 ? QfColors.green.withValues(alpha: .06) : QfColors.magenta.withValues(alpha: .06),
                ),
                child: Text(
                  'RACHA: $streakText'.toUpperCase(),
                  style: TextStyle(
                    fontFamily: qfDisplay,
                    fontSize: 11,
                    fontWeight: FontWeight.w700,
                    letterSpacing: .8,
                    color: streak >= 0 ? QfColors.green : QfColors.magenta,
                  ),
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                decoration: BoxDecoration(
                  border: Border.all(color: QfColors.border),
                ),
                child: Text(
                  l10n.tenThreeSets((overSets * 100).round()),
                  style: const TextStyle(fontFamily: qfMono, fontSize: 11, color: QfColors.text2),
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                decoration: BoxDecoration(
                  border: Border.all(color: QfColors.border),
                ),
                child: Text(
                  l10n.tenTiebreakPct((tiebreaks * 100).round()),
                  style: const TextStyle(fontFamily: qfMono, fontSize: 11, color: QfColors.text2),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  // ==========================================
  // SECCIÓN 3: SUPERFICIE
  // ==========================================
  Widget _buildSuperficieCard(
    BuildContext context,
    JsonMap playerA,
    JsonMap playerB,
    String nameA,
    String nameB,
  ) {
    final l10n = context.l10n;
    final surface = widget.event.surface ?? 'Hard';
    final surfaceKey = surface.trim().toLowerCase();

    final surfacesA = jsonMap(playerA['surfaces']);
    final surfacesB = jsonMap(playerB['surfaces']);

    // Identificar superficie de hoy
    final todayKey = surfaceKey.contains('clay') || surfaceKey.contains('tierra') || surfaceKey.contains('arcilla')
        ? 'clay'
        : (surfaceKey.contains('grass') || surfaceKey.contains('hierba') ? 'grass' : 'hard');

    final otherKeys = ['hard', 'clay', 'grass'].where((k) => k != todayKey).toList();

    return QfCard(
      key: _supKey,
      strong: true,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(
            l10n.tenSurfaceKicker,
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
            l10n.tenSurfaceTitle,
            style: const TextStyle(
              fontFamily: qfDisplay,
              fontSize: 22,
              fontWeight: FontWeight.w700,
              color: QfColors.text,
              letterSpacing: .4,
            ),
          ),
          const SizedBox(height: 12),
          // Cabecera de jugadores
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Expanded(
                child: Row(
                  children: [
                    _playerAvatar(nameA, 28),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        _shortName(nameA),
                        style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 13, color: QfColors.cyan),
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.end,
                  children: [
                    Expanded(
                      child: Text(
                        _shortName(nameB),
                        style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 13, color: Color(0xFFD1D4DE)),
                        textAlign: TextAlign.end,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                    const SizedBox(width: 8),
                    _playerAvatar(nameB, 28),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          // Filas de superficie de hoy (destacadas con badge HOY)
          _buildSurfaceRow(
            todayKey,
            'career',
            '${_translateSurfaceName(l10n, todayKey)} · CARRERA',
            surfacesA,
            surfacesB,
            isToday: true,
          ),
          const SizedBox(height: 6),
          _buildSurfaceRow(
            todayKey,
            'season',
            '${_translateSurfaceName(l10n, todayKey)} · ESTA TEMPORADA',
            surfacesA,
            surfacesB,
            isToday: true,
          ),
          for (final key in otherKeys) ...[
            const SizedBox(height: 6),
            _buildSurfaceRow(
              key,
              'career',
              _translateSurfaceName(l10n, key),
              surfacesA,
              surfacesB,
              isToday: false,
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildSurfaceRow(
    String surfaceKey,
    String scopeKey, // 'career' o 'season'
    String label,
    JsonMap surfacesA,
    JsonMap surfacesB, {
    required bool isToday,
  }) {
    final sA = jsonMap(jsonMap(surfacesA[surfaceKey])[scopeKey]);
    final sB = jsonMap(jsonMap(surfacesB[surfaceKey])[scopeKey]);

    final rateA = (sA['rate'] as num?)?.toDouble() ?? 0.0;
    final rateB = (sB['rate'] as num?)?.toDouble() ?? 0.0;
    final wonA = (sA['won'] as num?)?.toInt() ?? 0;
    final lostA = (sA['lost'] as num?)?.toInt() ?? 0;
    final wonB = (sB['won'] as num?)?.toInt() ?? 0;
    final lostB = (sB['lost'] as num?)?.toInt() ?? 0;

    final pA = (rateA * 100).round();
    final pB = (rateB * 100).round();

    final homeText = '$wonA–$lostA · $pA %';
    final awayText = '$wonB–$lostB · $pB %';

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
      decoration: BoxDecoration(
        color: isToday ? QfColors.cyan.withValues(alpha: .06) : Colors.transparent,
        border: Border.all(
          color: isToday ? QfColors.cyan.withValues(alpha: .4) : QfColors.border,
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                homeText,
                style: TextStyle(
                  fontFamily: qfMono,
                  fontSize: 11,
                  fontWeight: rateA > rateB ? FontWeight.w700 : FontWeight.w500,
                  color: rateA > rateB ? QfColors.cyan : QfColors.text2,
                ),
              ),
              Flexible(
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 4),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Flexible(
                        child: Text(
                          label,
                          style: TextStyle(
                            fontFamily: qfDisplay,
                            fontSize: 10,
                            fontWeight: FontWeight.w700,
                            letterSpacing: .8,
                            color: isToday ? QfColors.cyan : QfColors.slate,
                          ),
                          overflow: TextOverflow.ellipsis,
                          maxLines: 1,
                        ),
                      ),
                      if (isToday) ...[
                        const SizedBox(width: 4),
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 1),
                          color: QfColors.cyan,
                          child: const Text(
                            'HOY',
                            style: TextStyle(
                              fontFamily: qfDisplay,
                              fontSize: 8,
                              fontWeight: FontWeight.w800,
                              color: QfColors.bg,
                            ),
                          ),
                        ),
                      ],
                    ],
                  ),
                ),
              ),
              Text(
                awayText,
                style: TextStyle(
                  fontFamily: qfMono,
                  fontSize: 11,
                  fontWeight: rateB > rateA ? FontWeight.w700 : FontWeight.w500,
                  color: rateB > rateA ? QfColors.text : QfColors.text2,
                ),
              ),
            ],
          ),
          const SizedBox(height: 6),
          QfStackedBar(
            height: 6,
            parts: [
              (
                homeText,
                math.max(0.1, rateA * 100),
                rateA >= rateB ? QfColors.cyan : QfColors.cyan.withValues(alpha: .35),
              ),
              (
                awayText,
                math.max(0.1, rateB * 100),
                rateB > rateA ? const Color(0xFFD1D4DE) : const Color(0xFFD1D4DE).withValues(alpha: .35),
              ),
            ],
          ),
        ],
      ),
    );
  }

  // ==========================================
  // SECCIÓN 4: CARA A CARA (H2H)
  // ==========================================
  Widget _buildH2hCard(
    BuildContext context,
    JsonMap h2hData,
    String nameA,
    String nameB,
  ) {
    final l10n = context.l10n;
    final matches = jsonRows(h2hData['matches']);
    final firstWins = (h2hData['first_wins'] as num?)?.toInt() ?? 0;
    final secondWins = (h2hData['second_wins'] as num?)?.toInt() ?? 0;
    final surfaceName = _translateSurfaceName(l10n, widget.event.surface ?? 'Hard').toLowerCase();

    final isFirstDuel = matches.isEmpty && firstWins == 0 && secondWins == 0;

    return QfCard(
      key: _h2hKey,
      strong: true,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const Text(
            '// HISTORIAL DIRECTO',
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
          if (isFirstDuel) ...[
            // Estado «0 – 0 · PRIMER DUELO»
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceEvenly,
              children: [
                Column(
                  children: [
                    _playerAvatar(nameA, 64),
                    const SizedBox(height: 6),
                    Text(
                      _shortName(nameA),
                      style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 13, color: QfColors.text),
                    ),
                  ],
                ),
                Column(
                  children: [
                    const Text(
                      '0 – 0',
                      style: TextStyle(
                        fontFamily: qfMono,
                        fontSize: 32,
                        fontWeight: FontWeight.w700,
                        color: QfColors.cyan,
                        height: 1.0,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      l10n.tenH2hFirstDuel,
                      style: const TextStyle(
                        fontFamily: qfDisplay,
                        fontSize: 10,
                        fontWeight: FontWeight.w700,
                        letterSpacing: 1.4,
                        color: QfColors.slate,
                      ),
                    ),
                  ],
                ),
                Column(
                  children: [
                    _playerAvatar(nameB, 64),
                    const SizedBox(height: 6),
                    Text(
                      _shortName(nameB),
                      style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 13, color: QfColors.text),
                    ),
                  ],
                ),
              ],
            ),
            const SizedBox(height: 12),
            Text(
              l10n.tenH2hFirstDuelDesc(surfaceName),
              style: const TextStyle(fontSize: 12, color: QfColors.slate, height: 1.4),
            ),
          ] else ...[
            // Resumen de duelos registrados
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Row(
                  children: [
                    _playerAvatar(nameA, 34),
                    const SizedBox(width: 8),
                    Text(
                      '$firstWins',
                      style: const TextStyle(fontFamily: qfMono, fontSize: 30, fontWeight: FontWeight.w700, color: QfColors.cyan),
                    ),
                  ],
                ),
                Text(
                  l10n.nbaWinsLabel,
                  style: const TextStyle(fontFamily: qfDisplay, fontSize: 10, fontWeight: FontWeight.w700, letterSpacing: 1.2, color: QfColors.text2),
                ),
                Row(
                  children: [
                    Text(
                      '$secondWins',
                      style: const TextStyle(fontFamily: qfMono, fontSize: 30, fontWeight: FontWeight.w700, color: Color(0xFFD1D4DE)),
                    ),
                    const SizedBox(width: 8),
                    _playerAvatar(nameB, 34),
                  ],
                ),
              ],
            ),
            const SizedBox(height: 8),
            QfStackedBar(
              height: 8,
              parts: [
                (nameA, math.max(0.1, firstWins.toDouble()), QfColors.cyan),
                (nameB, math.max(0.1, secondWins.toDouble()), const Color(0xFFD1D4DE)),
              ],
            ),
            const SizedBox(height: 12),
            for (final m in matches.take(4)) ...[
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
                decoration: const BoxDecoration(
                  border: Border(bottom: BorderSide(color: QfColors.border)),
                ),
                child: Row(
                  children: [
                    Text(
                      '${m['date'] ?? ''}',
                      style: const TextStyle(fontFamily: qfMono, fontSize: 10, color: QfColors.slate),
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        '${m['tournament'] ?? ''} · ${m['surface'] ?? ''}',
                        style: const TextStyle(fontSize: 12, color: QfColors.text2),
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                    const SizedBox(width: 8),
                    Text(
                      '${m['score'] ?? ''}',
                      style: const TextStyle(fontFamily: qfMono, fontWeight: FontWeight.w700, fontSize: 13, color: QfColors.text),
                    ),
                  ],
                ),
              ),
            ],
            if (widget.onH2h != null) ...[
              const SizedBox(height: 12),
              OutlinedButton(
                onPressed: widget.onH2h,
                style: OutlinedButton.styleFrom(
                  side: const BorderSide(color: QfColors.cyan),
                  shape: const CutCornerBorder(cut: 6),
                  padding: const EdgeInsets.symmetric(vertical: 12),
                ),
                child: Center(
                  child: Text(
                    l10n.nbaViewAllH2h,
                    style: const TextStyle(
                      fontFamily: qfDisplay,
                      fontSize: 12,
                      fontWeight: FontWeight.w700,
                      letterSpacing: 1.2,
                      color: QfColors.cyan,
                    ),
                  ),
                ),
              ),
            ],
          ],
        ],
      ),
    );
  }

  num? _extractLine(SportMarket m) {
    if (m.line != null) return m.line;
    final match = RegExp(r'([+-]?\d+(?:\.\d+)?)').firstMatch(m.selection);
    if (match != null) {
      return num.tryParse(match.group(1)!);
    }
    return null;
  }

  // ==========================================
  // SECCIÓN 5: MODELO QUANTFUT
  // ==========================================
  Widget _buildModeloCard(BuildContext context, String nameA, String nameB) {
    final l10n = context.l10n;
    final event = widget.event;
    final markets = event.markets;

    // 1. Sets totales (duración del partido)
    SportMarket? setsTotalMarket;
    for (final m in markets) {
      if (m.id.startsWith('sets_total') || m.market == 'sets_total') {
        setsTotalMarket = m;
        break;
      }
    }
    final s3 = setsTotalMarket != null ? (setsTotalMarket.probability * 100).round() : null;
    final s2 = s3 != null ? 100 - s3 : null;

    // 2. Ganador de set (favorito)
    final setWinnerMarkets = markets.where((m) => m.id.startsWith('set_winner') || m.market == 'set_winner').toList();
    final pSet1 = setWinnerMarkets.isNotEmpty ? (setWinnerMarkets[0].probability * 100).round() : null;
    final pSet2 = setWinnerMarkets.length > 1 ? (setWinnerMarkets[1].probability * 100).round() : null;
    final pSet3 = setWinnerMarkets.length > 2 ? (setWinnerMarkets[2].probability * 100).round() : null;

    // 3. Juegos totales
    final gamesTotalMarkets = markets.where((m) => m.id.startsWith('games_total') || m.market == 'games_total').toList()
      ..sort((a, b) => (_extractLine(a) ?? 0).compareTo(_extractLine(b) ?? 0));

    // Determinar cruce de 50%
    num? lineAbove50;
    num? lineBelow50;
    int? probAbove50;
    int? probBelow50;
    num? expectedLine;

    for (var i = 0; i < gamesTotalMarkets.length; i++) {
      final p = (gamesTotalMarkets[i].probability * 100).round();
      final line = _extractLine(gamesTotalMarkets[i]);
      if (p >= 50) {
        lineAbove50 = line;
        probAbove50 = p;
      } else if (lineBelow50 == null && p < 50) {
        lineBelow50 = line;
        probBelow50 = p;
        break;
      }
    }

    if (lineAbove50 != null && lineBelow50 != null) {
      expectedLine = ((lineAbove50 + lineBelow50) / 2.0).round();
    } else if (lineAbove50 != null) {
      expectedLine = lineAbove50.round();
    } else if (lineBelow50 != null) {
      expectedLine = lineBelow50.round();
    }

    // 4. Hándicap de juegos
    final handicapMarkets = markets
        .where((m) => (m.id.startsWith('games_handicap') || m.market == 'games_handicap') && _extractLine(m) != null)
        .toList()
      ..sort((a, b) => (_extractLine(a) ?? 0).compareTo(_extractLine(b) ?? 0));

    // Tomar solo líneas negativas o principales (-5.5, -3.5, -1.5)
    final principalHandicaps = handicapMarkets.where((m) => (_extractLine(m) ?? 0) < 0).toList();

    // 5. Tiebreak
    SportMarket? tbMarket;
    for (final m in markets) {
      if (m.id.startsWith('tiebreak') || m.market == 'tiebreak') {
        tbMarket = m;
        break;
      }
    }
    final tbProb = tbMarket != null ? (tbMarket.probability * 100).round() : null;

    return QfCard(
      key: _modeloKey,
      strong: true,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(
            l10n.tenModelKicker,
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
            l10n.tenModelTitle,
            style: const TextStyle(
              fontFamily: qfDisplay,
              fontSize: 22,
              fontWeight: FontWeight.w700,
              color: QfColors.text,
              letterSpacing: .4,
            ),
          ),
          const SizedBox(height: 12),
          // 1. Duración del partido
          if (s2 != null && s3 != null) ...[
            Container(
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
                      Text(
                        l10n.tenModelMatchDuration,
                        style: const TextStyle(fontFamily: qfDisplay, fontSize: 11, fontWeight: FontWeight.w700, letterSpacing: 1.4, color: QfColors.text2),
                      ),
                      Text(
                        l10n.tenModelSets,
                        style: const TextStyle(fontFamily: qfMono, fontSize: 10, color: QfColors.slate),
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  QfStackedBar(
                    height: 8,
                    parts: [
                      (l10n.tenModelIn2Sets(s2), s2.toDouble(), QfColors.cyan),
                      (l10n.tenModelIn3Sets(s3), s3.toDouble(), const Color(0xFFD1D4DE)),
                    ],
                  ),
                  const SizedBox(height: 8),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text(
                        l10n.tenModelIn2Sets(s2),
                        style: const TextStyle(fontFamily: qfMono, fontSize: 13, fontWeight: FontWeight.w700, color: QfColors.cyan),
                      ),
                      Text(
                        l10n.tenModelIn3Sets(s3),
                        style: const TextStyle(fontFamily: qfMono, fontSize: 13, fontWeight: FontWeight.w700, color: Color(0xFFD1D4DE)),
                      ),
                    ],
                  ),
                ],
              ),
            ),
            const SizedBox(height: 10),
          ],
          // 2. Gana cada set
          if (pSet1 != null) ...[
            Container(
              padding: const EdgeInsets.all(10),
              decoration: BoxDecoration(
                border: Border.all(color: QfColors.border),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Text(
                    l10n.tenModelWinsEachSet(_shortName(nameA)),
                    style: const TextStyle(fontFamily: qfDisplay, fontSize: 11, fontWeight: FontWeight.w700, letterSpacing: 1.4, color: QfColors.text2),
                  ),
                  const SizedBox(height: 10),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                    crossAxisAlignment: CrossAxisAlignment.end,
                    children: [
                      _buildSetBar(l10n.tenModelSet1, pSet1),
                      if (pSet2 != null) _buildSetBar(l10n.tenModelSet2, pSet2),
                      if (pSet3 != null) _buildSetBar(l10n.tenModelSet3, pSet3),
                    ],
                  ),
                  const SizedBox(height: 8),
                  Text(
                    l10n.tenModelSet3Footnote,
                    style: const TextStyle(fontSize: 11, color: QfColors.slate),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 10),
          ],
          // 3. Juegos totales (probabilidad de «Más de»)
          if (gamesTotalMarkets.isNotEmpty) ...[
            Container(
              padding: const EdgeInsets.all(10),
              decoration: BoxDecoration(
                border: Border.all(color: QfColors.border),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Text(
                    l10n.tenModelTotalGames,
                    style: const TextStyle(fontFamily: qfDisplay, fontSize: 11, fontWeight: FontWeight.w700, letterSpacing: 1.4, color: QfColors.text2),
                  ),
                  const SizedBox(height: 12),
                  SizedBox(
                    height: 105,
                    child: Row(
                      crossAxisAlignment: CrossAxisAlignment.end,
                      children: [
                        for (final m in gamesTotalMarkets.take(8)) ...[
                          Expanded(
                            child: _buildGameTotalBar(m),
                          ),
                          const SizedBox(width: 4),
                        ],
                      ],
                    ),
                  ),
                  const SizedBox(height: 8),
                  if (lineAbove50 != null && lineBelow50 != null && expectedLine != null)
                    Text(
                      l10n.tenModelGamesExpectedCaption(
                        lineText(lineAbove50),
                        probAbove50 ?? 50,
                        lineText(lineBelow50),
                        probBelow50 ?? 50,
                        '$expectedLine',
                      ),
                      style: const TextStyle(fontSize: 12, color: QfColors.text2, height: 1.4),
                    )
                  else if (expectedLine != null)
                    Text(
                      l10n.tenModelGamesExpectedSimple('$expectedLine'),
                      style: const TextStyle(fontSize: 12, color: QfColors.text2, height: 1.4),
                    ),
                ],
              ),
            ),
            const SizedBox(height: 10),
          ],
          // 4. Hándicap de juegos
          if (principalHandicaps.isNotEmpty) ...[
            Container(
              padding: const EdgeInsets.all(10),
              decoration: BoxDecoration(
                border: Border.all(color: QfColors.border),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Text(
                    l10n.tenModelHandicap(_shortName(nameA)),
                    style: const TextStyle(fontFamily: qfDisplay, fontSize: 11, fontWeight: FontWeight.w700, letterSpacing: 1.4, color: QfColors.text2),
                  ),
                  const SizedBox(height: 10),
                  Row(
                    children: [
                      for (final m in principalHandicaps.take(3)) ...[
                        Expanded(
                          child: Container(
                            margin: const EdgeInsets.symmetric(horizontal: 3),
                            padding: const EdgeInsets.symmetric(vertical: 8, horizontal: 4),
                            decoration: BoxDecoration(
                              border: Border.all(color: QfColors.border),
                            ),
                            child: Column(
                              children: [
                                Text(
                                  signedLine(_extractLine(m) ?? 0),
                                  style: const TextStyle(fontFamily: qfMono, fontSize: 12, fontWeight: FontWeight.w700, color: QfColors.text2),
                                ),
                                const SizedBox(height: 4),
                                Text(
                                  '${(m.probability * 100).round()}%',
                                  style: const TextStyle(fontFamily: qfMono, fontSize: 18, fontWeight: FontWeight.w700, color: QfColors.cyan),
                                ),
                              ],
                            ),
                          ),
                        ),
                      ],
                    ],
                  ),
                ],
              ),
            ),
            const SizedBox(height: 10),
          ],
          // 5. Habrá tie-break & Juegos esperados
          if (tbProb != null || expectedLine != null) ...[
            Row(
              children: [
                if (tbProb != null)
                  Expanded(
                    child: Container(
                      padding: const EdgeInsets.all(10),
                      decoration: BoxDecoration(
                        border: Border.all(color: QfColors.border),
                      ),
                      child: Column(
                        children: [
                          Text(
                            '$tbProb%',
                            style: const TextStyle(fontFamily: qfMono, fontSize: 20, fontWeight: FontWeight.w700, color: QfColors.cyan),
                          ),
                          const SizedBox(height: 4),
                          Text(
                            l10n.tenModelTiebreak,
                            style: const TextStyle(fontFamily: qfDisplay, fontSize: 10, fontWeight: FontWeight.w700, letterSpacing: 1.2, color: QfColors.text2),
                            textAlign: TextAlign.center,
                          ),
                        ],
                      ),
                    ),
                  ),
                if (tbProb != null && expectedLine != null) const SizedBox(width: 8),
                if (expectedLine != null)
                  Expanded(
                    child: Container(
                      padding: const EdgeInsets.all(10),
                      decoration: BoxDecoration(
                        border: Border.all(color: QfColors.border),
                      ),
                      child: Column(
                        children: [
                          Text(
                            l10n.tenModelGamesExpectedApprox('$expectedLine'),
                            style: const TextStyle(fontFamily: qfMono, fontSize: 20, fontWeight: FontWeight.w700, color: QfColors.cyan),
                          ),
                          const SizedBox(height: 4),
                          Text(
                            l10n.tenModelGamesExpectedLabel,
                            style: const TextStyle(fontFamily: qfDisplay, fontSize: 10, fontWeight: FontWeight.w700, letterSpacing: 1.2, color: QfColors.text2),
                            textAlign: TextAlign.center,
                          ),
                        ],
                      ),
                    ),
                  ),
              ],
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildSetBar(String label, int percent) {
    final height = (percent / 100.0 * 64.0).clamp(6.0, 64.0);
    final color = percent >= 50 ? QfColors.cyan : QfColors.slate;

    return Column(
      mainAxisAlignment: MainAxisAlignment.end,
      children: [
        Text(
          '$percent%',
          style: TextStyle(
            fontFamily: qfMono,
            fontSize: 13,
            fontWeight: FontWeight.w700,
            color: color,
          ),
        ),
        const SizedBox(height: 4),
        Container(
          width: 48,
          height: height,
          color: color,
        ),
        const SizedBox(height: 4),
        Text(
          label,
          style: const TextStyle(fontFamily: qfDisplay, fontSize: 10, fontWeight: FontWeight.w700, letterSpacing: 1.1, color: QfColors.text2),
        ),
      ],
    );
  }

  Widget _buildGameTotalBar(SportMarket market) {
    final prob = market.probability;
    final percent = (prob * 100).round();
    final height = (prob * 70.0).clamp(6.0, 70.0);
    final color = prob >= 0.5 ? QfColors.cyan : QfColors.slate;

    return Column(
      mainAxisAlignment: MainAxisAlignment.end,
      children: [
        Text(
          '$percent',
          style: TextStyle(
            fontFamily: qfMono,
            fontSize: 10,
            fontWeight: FontWeight.w700,
            color: color,
          ),
        ),
        const SizedBox(height: 2),
        Container(
          width: double.infinity,
          height: height,
          color: color,
        ),
        const SizedBox(height: 4),
        Text(
          lineText(_extractLine(market)),
          style: const TextStyle(fontFamily: qfMono, fontSize: 9, color: QfColors.text2),
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
        ),
      ],
    );
  }
}
