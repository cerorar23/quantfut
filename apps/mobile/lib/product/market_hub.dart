import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../l10n/app_locale.dart';
import '../l10n/pick_labels.dart' show bookName;
import 'live_api.dart';
import 'market_catalog.dart';
import 'qf_charts.dart';
import 'qf_controls.dart';
import 'qf_shapes.dart';
import 'qf_theme.dart';

/// Piezas de la pestaña Mercados compartidas por fútbol, NBA y tenis: radar, tarjeta de familia,
/// tarjeta de pronóstico (escudos, cuota y casa) y cabecera de la pantalla de un mercado.
/// Fútbol fue el diseño de partida; NBA y tenis lo reutilizan tal cual.

/// Categorías de familias por deporte para las pestañas internas de Mercados (§4 y F3c).
const footballGoalsFamilies = <String>{'goals', 'team_goals', 'btts'};

const nbaPlayerFamilies = <String>{
  'player_points',
  'player_rebounds',
  'player_assists',
  'player_threes',
};

const tennisGamesFamilies = <String>{
  'games_total',
  'games_handicap',
  'tiebreak',
};

/// Color y símbolo de cada familia de mercado según la paleta CyberCore (§5.1).
const _look = <String, (Color, IconData)>{
  // Fútbol.
  'goals': (QfColors.cyan, Icons.sports_soccer),
  'btts': (QfColors.primary, Icons.compare_arrows),
  'team_goals': (QfColors.primary, Icons.sports_score),
  'corners': (Color(0xffffb020), Icons.flag_outlined),
  'corners_team': (Color(0xffff8a3d), Icons.flag_outlined),
  'handicap': (Color(0xffa78bfa), Icons.shield_outlined),
  'double_chance': (Color(0xffc6f432), Icons.alt_route_rounded),
  'winner': (Color(0xff4c9dff), Icons.emoji_events_outlined),
  'cards': (Color(0xffff2a6d), Icons.style_outlined),
  // NBA.
  'game_total': (QfColors.cyan, Icons.stacked_bar_chart),
  'team_points': (QfColors.primary, Icons.groups_outlined),
  'player_points': (Color(0xffc6f432), Icons.person_outline),
  'player_rebounds': (Color(0xffffb020), Icons.autorenew),
  'player_assists': (Color(0xffff8a3d), Icons.swap_horiz),
  'player_threes': (Color(0xffff2a6d), Icons.sports_basketball_outlined),
  // Tenis.
  'games_total': (QfColors.cyan, Icons.format_list_numbered),
  'games_handicap': (Color(0xffa78bfa), Icons.shield_outlined),
  'set_winner': (Color(0xffc6f432), Icons.looks_one_outlined),
  'sets_handicap': (Color(0xffff8a3d), Icons.exposure),
  'sets_total': (Color(0xffffb020), Icons.view_week_outlined),
  'tiebreak': (Color(0xffff2a6d), Icons.timelapse),
};

(Color, IconData) marketLook(String id) =>
    _look[id] ?? (QfColors.muted, Icons.circle_outlined);

/// Reloj del radar: una sola animación para el radar y las tarjetas. Sin animación continua si el
/// sistema pide reducir movimiento.
class RadarClock extends StatefulWidget {
  const RadarClock({super.key, required this.builder});
  final Widget Function(BuildContext context, Animation<double> clock) builder;
  @override
  State<RadarClock> createState() => _RadarClockState();
}

class _RadarClockState extends State<RadarClock>
    with SingleTickerProviderStateMixin {
  late final AnimationController _clock = AnimationController(
    vsync: this,
    duration: const Duration(seconds: 6),
  );

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (MediaQuery.maybeDisableAnimationsOf(context) ?? false) {
      _clock.stop();
    } else if (!_clock.isAnimating) {
      _clock.repeat();
    }
  }

  @override
  void dispose() {
    _clock.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => widget.builder(context, _clock);
}

/// Datos de una tarjeta de familia.
class MarketTileData {
  const MarketTileData({
    required this.id,
    required this.title,
    required this.detail,
    required this.color,
    required this.icon,
    required this.percent,
    required this.record,
    this.openCount = 0,
    this.resolvedCount = 0,
    this.todayAvatars = const [],
  });
  final String id, title, detail;
  final Color color;
  final IconData icon;

  /// Acierto (0–100) del anillo; null = sin línea ni resueltos.
  final double? percent;

  /// Publicados ya resueltos (acertados / total).
  final PublishedRecord record;

  final int openCount;
  final int resolvedCount;
  final List<Widget> todayAvatars;
}

/// Cuadrícula de dos columnas de tarjetas de familia.
class MarketTilesGrid extends StatelessWidget {
  const MarketTilesGrid({
    super.key,
    required this.clock,
    required this.tiles,
    required this.onOpen,
  });
  final Animation<double> clock;
  final List<MarketTileData> tiles;
  final ValueChanged<MarketTileData> onOpen;

  @override
  Widget build(BuildContext context) => LayoutBuilder(
    builder: (context, box) {
      final wide = (box.maxWidth - 10) / 2;
      return Wrap(
        spacing: 10,
        runSpacing: 10,
        children: [
          for (var i = 0; i < tiles.length; i++)
            SizedBox(
              width: wide,
              child: MarketTile(
                clock: clock,
                data: tiles[i],
                phase: i / tiles.length,
                onOpen: () => onOpen(tiles[i]),
              ),
            ),
        ],
      );
    },
  );
}

/// Cabecera de la pestaña: «MODELO ACTIVO», número de familias, evidencia y radar (§5.1 y captura Mercados).
class MarketsHero extends StatelessWidget {
  const MarketsHero({
    super.key,
    required this.clock,
    required this.colors,
    required this.evidence,
    required this.overall,
    this.accent = QfColors.cyan,
  });
  final Animation<double> clock;

  /// Un color por familia: son los puntos del radar.
  final List<Color> colors;
  final String evidence;
  final PublishedRecord overall;
  final Color accent;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: accent.withValues(alpha: .22)),
        gradient: const LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [Color(0xff0f1c2b), Color(0xff0a121d)],
          stops: [0.0, 0.7],
        ),
      ),
      child: Row(
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    AnimatedBuilder(
                      animation: clock,
                      builder: (_, _) => Container(
                        width: 8,
                        height: 8,
                        decoration: BoxDecoration(
                          shape: BoxShape.circle,
                          color: QfColors.primary,
                          boxShadow: [
                            BoxShadow(
                              color: QfColors.primary.withValues(
                                alpha:
                                    .35 +
                                    .55 * math.sin(clock.value * 12.566).abs(),
                              ),
                              blurRadius: 8,
                              spreadRadius: 1,
                            ),
                          ],
                        ),
                      ),
                    ),
                    const SizedBox(width: 8),
                    Text(
                      context.l10n.marketsModelActive.toUpperCase(),
                      style: const TextStyle(
                        fontFamily: qfDisplay,
                        fontSize: 12,
                        fontWeight: FontWeight.w700,
                        letterSpacing: 1.4,
                        color: QfColors.primary,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                Row(
                  crossAxisAlignment: CrossAxisAlignment.baseline,
                  textBaseline: TextBaseline.alphabetic,
                  children: [
                    Text(
                      '${colors.length}',
                      style: const TextStyle(
                        fontFamily: qfDisplay,
                        fontSize: 54,
                        height: 1,
                        fontWeight: FontWeight.w700,
                        color: Colors.white,
                      ),
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Text(
                        context.l10n.marketsFamiliesRadar,
                        style: const TextStyle(
                          fontSize: 14,
                          fontWeight: FontWeight.w600,
                          height: 1.2,
                          color: Colors.white,
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 6),
                Text(
                  evidence,
                  style: const TextStyle(
                    fontSize: 12,
                    color: QfColors.muted,
                  ),
                ),
                const SizedBox(height: 10),
                Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 12,
                    vertical: 6,
                  ),
                  decoration: BoxDecoration(
                    color: Colors.white.withValues(alpha: .07),
                    borderRadius: BorderRadius.circular(999),
                  ),
                  child: Text(
                    overall.cases == 0
                        ? context.l10n.marketsNoResolved
                        : context.l10n.marketsPublishedWon(
                            overall.won,
                            overall.cases,
                            percent(overall.observed),
                          ),
                    style: const TextStyle(
                      fontSize: 12,
                      fontWeight: FontWeight.w600,
                      color: Colors.white,
                    ),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(width: 8),
          SizedBox(
            width: 110,
            height: 110,
            child: AnimatedBuilder(
              animation: clock,
              builder: (_, _) => CustomPaint(
                painter: _RadarPainter(clock.value, colors, accent),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _RadarPainter extends CustomPainter {
  _RadarPainter(this.t, this.blips, this.accent);
  final double t;
  final List<Color> blips;
  final Color accent;

  @override
  void paint(Canvas canvas, Size size) {
    final c = size.center(Offset.zero);
    final r = size.shortestSide / 2 - 2;
    final line = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1
      ..color = accent.withValues(alpha: .18);
    for (var k = 1; k <= 3; k++) {
      canvas.drawCircle(c, r * k / 3, line);
    }
    canvas.drawLine(c - Offset(r, 0), c + Offset(r, 0), line);
    canvas.drawLine(c - Offset(0, r), c + Offset(0, r), line);

    final head = t * 2 * math.pi;
    final rect = Rect.fromCircle(center: c, radius: r);
    canvas.drawCircle(
      c,
      r,
      Paint()
        ..shader = SweepGradient(
          colors: [Colors.transparent, accent.withValues(alpha: .5)],
          stops: const [.72, 1],
          transform: GradientRotation(head),
        ).createShader(rect),
    );
    canvas.drawLine(
      c,
      c + Offset(math.cos(head), math.sin(head)) * r,
      Paint()
        ..color = accent.withValues(alpha: .9)
        ..strokeWidth = 1.5,
    );

    for (var i = 0; i < blips.length; i++) {
      final angle = i * 2.399963; // ángulo áureo: reparto sin solaparse
      final dist = r * (.3 + .55 * ((i * .37) % 1));
      final behind = ((head - angle) % (2 * math.pi)) / (2 * math.pi);
      final glow = math.pow(1 - behind, 2).toDouble();
      final p = c + Offset(math.cos(angle), math.sin(angle)) * dist;
      canvas.drawCircle(
        p,
        3 + 4 * glow,
        Paint()..color = blips[i].withValues(alpha: .25 * glow),
      );
      canvas.drawCircle(
        p,
        2.6,
        Paint()..color = blips[i].withValues(alpha: .35 + .65 * glow),
      );
    }
  }

  @override
  bool shouldRepaint(_RadarPainter old) => old.t != t;
}

/// Tarjeta de una familia: anillo de acierto CyberCore, icono, nombre, detalle,
/// «Publicado n/m», fila de 10 puntos y fila «HOY» con avatares solapados (§5.1).
class MarketTile extends StatelessWidget {
  const MarketTile({
    super.key,
    required this.clock,
    required this.data,
    required this.phase,
    required this.onOpen,
  });
  final Animation<double> clock;
  final MarketTileData data;
  final double phase;
  final VoidCallback onOpen;

  @override
  Widget build(BuildContext context) {
    final color = data.color;
    final percentValue = data.percent;
    return Semantics(
      button: true,
      label:
          '${data.title}, '
          '${percentValue == null ? context.l10n.marketsNoLineLabel : context.l10n.marketsHistoricHit(percent(percentValue))}',
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          borderRadius: BorderRadius.circular(16),
          onTap: onOpen,
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: color.withValues(alpha: .38)),
              gradient: LinearGradient(
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
                colors: [
                  color.withValues(alpha: .30),
                  color.withValues(alpha: .07),
                  const Color(0xff10151f),
                ],
                stops: const [0.0, 0.6, 1.0],
              ),
            ),
            child: Stack(
              children: [
                Positioned.fill(
                  child: IgnorePointer(
                    child: AnimatedBuilder(
                      animation: clock,
                      builder: (_, _) => CustomPaint(
                        painter: _ScanPainter((clock.value + phase) % 1, color),
                      ),
                    ),
                  ),
                ),
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        QfRing(
                          size: 46,
                          stroke: 5,
                          value: percentValue != null ? percentValue / 100 : 0.0,
                          color: percentValue != null ? color : const Color(0xff262d3d),
                          trackColor: percentValue != null
                              ? Colors.white.withValues(alpha: .08)
                              : const Color(0xff262d3d),
                          centerText: percentValue == null ? '–' : null,
                        ),
                        Icon(data.icon, color: color, size: 22),
                      ],
                    ),
                    const SizedBox(height: 8),
                    Text(
                      data.title,
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(
                        fontSize: 15,
                        fontWeight: FontWeight.w700,
                        height: 1.2,
                        color: Colors.white,
                      ),
                    ),
                    const SizedBox(height: 3),
                    Text(
                      data.detail,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(fontSize: 11, color: QfColors.muted),
                    ),
                    const SizedBox(height: 3),
                    Text(
                      data.record.cases == 0
                          ? context.l10n.marketsNoPublications
                          : context.l10n.marketsPublished(data.record.won, data.record.cases),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(
                        fontSize: 11,
                        fontWeight: FontWeight.w600,
                        color: Colors.white,
                      ),
                    ),
                    const SizedBox(height: 6),
                    _TenDotsRow(
                      clock: clock,
                      record: data.record,
                      color: color,
                    ),
                    const SizedBox(height: 6),
                    Row(
                      children: [
                        Text(
                          'HOY',
                          style: const TextStyle(
                            fontFamily: qfDisplay,
                            fontSize: 10,
                            fontWeight: FontWeight.w700,
                            letterSpacing: 1.4,
                            color: QfColors.text2,
                          ),
                        ),
                        const SizedBox(width: 6),
                        if (data.todayAvatars.isEmpty)
                          const Text(
                            '—',
                            style: TextStyle(
                              fontSize: 11,
                              color: QfColors.muted,
                            ),
                          )
                        else
                          SizedBox(
                            height: 26,
                            width: 26.0 +
                                (math.min(data.todayAvatars.length, 4) - 1)
                                        .clamp(0, 3) *
                                    20.0,
                            child: Stack(
                              children: [
                                for (var j = 0;
                                    j < data.todayAvatars.length && j < 4;
                                    j++)
                                  Positioned(
                                    left: j * 20.0,
                                    top: 0,
                                    width: 26,
                                    height: 26,
                                    child: data.todayAvatars[j],
                                  ),
                              ],
                            ),
                          ),
                      ],
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

/// Fila de 10 puntos (círculo lleno = acierto, hueco = pendiente) con pulso en el último acierto.
class _TenDotsRow extends StatelessWidget {
  const _TenDotsRow({
    required this.clock,
    required this.record,
    required this.color,
  });
  final Animation<double> clock;
  final PublishedRecord record;
  final Color color;

  @override
  Widget build(BuildContext context) {
    const totalDots = 10;
    final hits = record.cases == 0
        ? 0
        : ((record.won * totalDots) / record.cases).round().clamp(0, totalDots);
    return AnimatedBuilder(
      animation: clock,
      builder: (_, _) => Row(
        children: [
          for (var i = 0; i < totalDots; i++) ...[
            if (i > 0) const SizedBox(width: 3),
            Container(
              width: 6,
              height: 6,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: i < hits
                    ? color.withValues(
                        alpha: i == hits - 1
                            ? .55 + .45 * math.sin(clock.value * 12.566).abs()
                            : 1,
                      )
                    : Colors.transparent,
                border: i < hits
                    ? null
                    : Border.all(
                        color: Colors.white.withValues(alpha: .22),
                        width: 1,
                      ),
              ),
            ),
          ],
        ],
      ),
    );
  }
}

/// Línea de barrido horizontal que baja por la tarjeta, desfasada por tarjeta.
class _ScanPainter extends CustomPainter {
  _ScanPainter(this.t, this.color);
  final double t;
  final Color color;

  @override
  void paint(Canvas canvas, Size size) {
    final y = size.height * t;
    final band = Rect.fromLTWH(0, y - 18, size.width, 36);
    canvas.drawRect(
      band,
      Paint()
        ..shader = LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [
            Colors.transparent,
            color.withValues(alpha: .10),
            Colors.transparent,
          ],
        ).createShader(band),
    );
  }

  @override
  bool shouldRepaint(_ScanPainter old) => old.t != t;
}

// ---- Pantalla de un mercado: cabecera, pronósticos y estados vacíos ----------------------

/// Tarjeta «Tasa de acierto»: acierto global y hoy (§5.1 y Mercado.dc.html).
class MarketRateCard extends StatelessWidget {
  const MarketRateCard({
    super.key,
    required this.color,
    required this.today,
    required this.overall,
    this.todayCount = 0,
    this.onLines,
  });
  final Color color;
  final PublishedRecord? today;
  final PublishedRecord overall;
  final int todayCount;
  final VoidCallback? onLines;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: ShapeDecoration(
        color: QfColors.surface,
        shape: CutCornerBorder(
          cut: 12,
          side: BorderSide(color: QfColors.borderStrong),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.show_chart, color: color, size: 18),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  l10n.mdHitRate,
                  style: const TextStyle(
                    fontFamily: qfDisplay,
                    fontSize: 14,
                    fontWeight: FontWeight.w700,
                    letterSpacing: 1.2,
                    color: Colors.white,
                  ),
                ),
              ),
              if (onLines != null)
                TextButton(
                  onPressed: onLines,
                  style: TextButton.styleFrom(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                    minimumSize: Size.zero,
                    tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                  ),
                  child: Text(
                    l10n.mdValidatedLines,
                    style: TextStyle(
                      fontFamily: qfDisplay,
                      fontSize: 12,
                      fontWeight: FontWeight.w700,
                      letterSpacing: 1.1,
                      color: color,
                    ),
                  ),
                ),
            ],
          ),
          const SizedBox(height: 10),
          Row(
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      l10n.mdOverall.toUpperCase(),
                      style: const TextStyle(
                        fontFamily: qfDisplay,
                        fontSize: 11,
                        fontWeight: FontWeight.w700,
                        letterSpacing: 1.4,
                        color: QfColors.text2,
                      ),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      percent(overall.observed),
                      style: TextStyle(
                        fontFamily: qfMono,
                        fontSize: 32,
                        height: 1.1,
                        fontWeight: FontWeight.w700,
                        color: QfColors.cyan,
                        shadows: [
                          Shadow(
                            color: QfColors.cyan.withValues(alpha: .45),
                            blurRadius: 18,
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      overall.cases == 0
                          ? l10n.marketsNoResolved
                          : '${overall.won}/${overall.cases}',
                      style: const TextStyle(
                        fontFamily: qfMono,
                        fontSize: 11,
                        fontWeight: FontWeight.w500,
                        color: QfColors.muted,
                      ),
                    ),
                  ],
                ),
              ),
              Container(width: 1, height: 48, color: QfColors.divider),
              const SizedBox(width: 16),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      l10n.commonToday.toUpperCase(),
                      style: const TextStyle(
                        fontFamily: qfDisplay,
                        fontSize: 11,
                        fontWeight: FontWeight.w700,
                        letterSpacing: 1.4,
                        color: QfColors.text2,
                      ),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      today == null || today!.cases == 0
                          ? '$todayCount'
                          : '${today!.won}/${today!.cases}',
                      style: const TextStyle(
                        fontFamily: qfMono,
                        fontSize: 32,
                        height: 1.1,
                        fontWeight: FontWeight.w700,
                        color: Colors.white,
                      ),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      today == null || today!.cases == 0
                          ? l10n.commonToday
                          : percent(today!.observed),
                      style: const TextStyle(
                        fontFamily: qfMono,
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

Widget marketEmptyState(String message) => Center(
  child: Padding(
    padding: const EdgeInsets.all(28),
    child: Text(
      message,
      textAlign: TextAlign.center,
      style: const TextStyle(fontSize: 13, color: QfColors.muted),
    ),
  ),
);

/// Etiqueta de día de un historial: Hoy, Ayer o la fecha corta.
String marketDayLabel(DateTime d) {
  final now = DateTime.now();
  final diff = DateTime(
    now.year,
    now.month,
    now.day,
  ).difference(DateTime(d.year, d.month, d.day)).inDays;
  final l10n = AppLocale.instance.l10n;
  return diff == 0
      ? l10n.commonToday
      : diff == 1
      ? l10n.commonYesterday
      : localDate(DateFormat.yMd, d);
}

/// Separador de día de un historial.
Widget marketDayChip(String label) => Padding(
  padding: const EdgeInsets.only(top: 10, bottom: 10),
  child: Center(
    child: Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 5),
      decoration: ShapeDecoration(
        color: Colors.white.withValues(alpha: .06),
        shape: const CutCornerBorder(cut: 6),
      ),
      child: Text(
        label,
        style: const TextStyle(
          fontFamily: qfDisplay,
          fontSize: 11,
          fontWeight: FontWeight.w700,
          letterSpacing: 1.2,
          color: QfColors.muted,
        ),
      ),
    ),
  ),
);

/// Pantalla de un mercado: cabecera con insignia, tarjeta de acierto global + hoy,
/// QfTabs «HOY (n) · ANTERIORES», filas de pronósticos y barra fija de desbloqueo (§5.1).
class MarketScaffold extends StatefulWidget {
  const MarketScaffold({
    super.key,
    required this.title,
    required this.color,
    required this.today,
    required this.overall,
    required this.todayCount,
    required this.todayTab,
    required this.historyTab,
    this.subtitle,
    this.badge,
    this.onLines,
    this.onUnlock,
    this.unlockCost = 40,
    this.onVip,
    this.initialTab = 0,
  });

  final String title;
  final Color color;
  final PublishedRecord? today;
  final PublishedRecord overall;
  final int todayCount;
  final Widget todayTab, historyTab;
  final String? subtitle, badge;
  final VoidCallback? onLines;
  final VoidCallback? onUnlock;
  final int unlockCost;
  final VoidCallback? onVip;
  final int initialTab;

  @override
  State<MarketScaffold> createState() => _MarketScaffoldState();
}

class _MarketScaffoldState extends State<MarketScaffold> {
  late int _tabIndex;

  @override
  void initState() {
    super.initState();
    _tabIndex = widget.initialTab;
  }

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    return Scaffold(
      backgroundColor: QfColors.bg,
      appBar: PreferredSize(
        preferredSize: const Size.fromHeight(56),
        child: Container(
          decoration: const BoxDecoration(
            color: QfColors.surface,
            border: Border(bottom: BorderSide(color: QfColors.border)),
          ),
          child: SafeArea(
            bottom: false,
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 8),
              child: Row(
                children: [
                  IconButton(
                    icon: const Icon(Icons.arrow_back, color: QfColors.muted),
                    onPressed: () => Navigator.of(context).pop(),
                  ),
                  Expanded(
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          widget.title.toUpperCase(),
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: const TextStyle(
                            fontFamily: qfDisplay,
                            fontSize: 18,
                            fontWeight: FontWeight.w700,
                            letterSpacing: 1.2,
                            color: Colors.white,
                          ),
                        ),
                        if (widget.subtitle != null && widget.subtitle!.isNotEmpty)
                          Text(
                            widget.subtitle!,
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: const TextStyle(
                              fontFamily: qfMono,
                              fontSize: 11,
                              fontWeight: FontWeight.w500,
                              color: QfColors.text2,
                            ),
                          ),
                      ],
                    ),
                  ),
                  if (widget.badge != null || widget.onLines != null) ...[
                    const SizedBox(width: 8),
                    InkWell(
                      onTap: widget.onLines,
                      borderRadius: BorderRadius.circular(4),
                      child: Container(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 8,
                          vertical: 4,
                        ),
                        decoration: BoxDecoration(
                          color: QfColors.primary.withValues(alpha: .09),
                          border: Border.all(
                            color: QfColors.primary.withValues(alpha: .4),
                          ),
                          borderRadius: BorderRadius.circular(4),
                        ),
                        child: Text(
                          widget.badge ?? l10n.mdLineConfirmed.toUpperCase(),
                          style: const TextStyle(
                            fontFamily: qfDisplay,
                            fontSize: 11,
                            fontWeight: FontWeight.w700,
                            letterSpacing: 1.2,
                            color: QfColors.primary,
                          ),
                        ),
                      ),
                    ),
                  ],
                ],
              ),
            ),
          ),
        ),
      ),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 12, 16, 8),
            child: MarketRateCard(
              color: widget.color,
              today: widget.today,
              overall: widget.overall,
              todayCount: widget.todayCount,
              onLines: widget.onLines,
            ),
          ),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
            child: QfTabs(
              labels: [
                l10n.mdTabToday(widget.todayCount),
                l10n.mdTabPrevious,
              ],
              index: _tabIndex,
              onChanged: (i) => setState(() => _tabIndex = i),
            ),
          ),
          Expanded(
            child: _tabIndex == 0 ? widget.todayTab : widget.historyTab,
          ),
          _MarketBottomBar(
            cost: widget.unlockCost,
            onUnlock: widget.onUnlock,
            onVip: widget.onVip,
          ),
        ],
      ),
    );
  }
}

class _MarketBottomBar extends StatelessWidget {
  const _MarketBottomBar({
    this.cost = 40,
    this.onUnlock,
    this.onVip,
  });
  final int cost;
  final VoidCallback? onUnlock;
  final VoidCallback? onVip;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    return Container(
      decoration: const BoxDecoration(
        color: QfColors.surface,
        border: Border(top: BorderSide(color: QfColors.border)),
      ),
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
      child: SafeArea(
        top: false,
        child: Row(
          children: [
            Expanded(
              child: SizedBox(
                height: 48,
                child: Material(
                  color: Colors.transparent,
                  shape: const CutCornerBorder(cut: 8),
                  clipBehavior: Clip.antiAlias,
                  child: Ink(
                    decoration: const BoxDecoration(
                      gradient: qfGreenGradient,
                    ),
                    child: InkWell(
                      onTap: onUnlock ?? onVip,
                      child: Center(
                        child: Row(
                          mainAxisSize: MainAxisSize.min,
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            const Icon(
                              Icons.lock_open,
                              size: 16,
                              color: Color(0xFF03110F),
                            ),
                            const SizedBox(width: 6),
                            Flexible(
                              child: Text(
                                l10n.shellUnlockAction(cost).toUpperCase(),
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                                style: const TextStyle(
                                  fontFamily: qfDisplay,
                                  fontWeight: FontWeight.w700,
                                  fontSize: 14,
                                  letterSpacing: 1.0,
                                  color: Color(0xFF03110F),
                                ),
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ),
                ),
              ),
            ),
            const SizedBox(width: 8),
            SizedBox(
              width: 88,
              height: 48,
              child: Material(
                color: Colors.transparent,
                shape: const CutCornerBorder(cut: 8),
                clipBehavior: Clip.antiAlias,
                child: Ink(
                  decoration: BoxDecoration(
                    color: QfColors.yellow.withValues(alpha: 0.08),
                    border: Border.all(
                      color: QfColors.yellow.withValues(alpha: 0.5),
                    ),
                  ),
                  child: InkWell(
                    onTap: onVip,
                    child: const Center(
                      child: Text(
                        'VIP',
                        style: TextStyle(
                          fontFamily: qfDisplay,
                          fontWeight: FontWeight.w700,
                          fontSize: 15,
                          letterSpacing: 1.2,
                          color: QfColors.yellow,
                        ),
                      ),
                    ),
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// ---- Tarjeta de pronóstico ---------------------------------------------------------------

/// Un pronóstico listo para pintar. Los avatares los construye cada deporte (escudo, logo o foto);
/// aquí solo se colocan. Nada se inventa: sin cuota se pinta «—» y sin casa solo el precio.
class MarketPick {
  const MarketPick({
    required this.home,
    required this.away,
    required this.homeAvatar,
    required this.awayAvatar,
    required this.pick,
    this.kickoff,
    this.league,
    this.probability,
    this.price,
    this.book,
    this.quoteAt,
    this.outcome,
    this.score,
    this.scoreNote,
    this.onTap,
  });
  final String home, away;
  final Widget Function(double size) homeAvatar, awayAvatar;

  /// El pronóstico en palabras («Más de 2,5 goles», «Nikola Jokic · Más de 24,5»).
  final String pick;
  final Object? kickoff;
  final String? league;

  /// 0–1, del modelo.
  final double? probability;
  final double? price;
  final String? book;
  final DateTime? quoteAt;

  /// `win`, `loss`, `push` o null mientras no haya resultado.
  final String? outcome;

  /// Resultado del partido («2-1») y una nota bajo él («córners · total 9»).
  final String? score, scoreNote;
  final VoidCallback? onTap;
}

class MarketPickCard extends StatelessWidget {
  const MarketPickCard({super.key, required this.data, required this.color});
  final MarketPick data;
  final Color color;

  Widget _side(Widget avatar, String name) => Row(
    children: [
      avatar,
      const SizedBox(width: 10),
      Expanded(
        child: Text(
          name,
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
          style: const TextStyle(
            fontSize: 14,
            fontWeight: FontWeight.w700,
            color: Colors.white,
          ),
        ),
      ),
    ],
  );

  Widget _outcomeBadge(BuildContext context) {
    final l10n = context.l10n;
    final won = data.outcome == 'win', lost = data.outcome == 'loss';
    final (label, tone) = won
        ? (l10n.parleyOutcomeWin, QfColors.primary)
        : lost
        ? (l10n.parleyOutcomeLoss, QfColors.danger)
        : (l10n.parleyOutcomeVoid, QfColors.muted);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: tone.withValues(alpha: .12),
        border: Border.all(color: tone.withValues(alpha: .6)),
        borderRadius: BorderRadius.circular(4),
      ),
      child: Text(
        label,
        style: TextStyle(
          fontFamily: qfDisplay,
          fontSize: 11,
          fontWeight: FontWeight.w700,
          letterSpacing: 1.2,
          color: tone,
        ),
      ),
    );
  }

  Widget _quote(BuildContext context) {
    final l10n = context.l10n;
    final price = data.price;
    if (price == null) {
      return Semantics(
        label: l10n.quoteNone,
        excludeSemantics: true,
        child: const Text(
          '—',
          key: ValueKey('pick-quote-none'),
          style: TextStyle(fontFamily: qfMono, fontSize: 15, color: QfColors.muted),
        ),
      );
    }
    final book = data.book == null ? null : bookName(data.book);
    final at = data.quoteAt;
    final caption = book == null
        ? null
        : at == null
        ? book
        : l10n.quoteBookAt(book, localDate(DateFormat.Hm, at.toLocal()));
    return ConstrainedBox(
      key: const ValueKey('pick-quote'),
      constraints: const BoxConstraints(maxWidth: 124),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.end,
        children: [
          Text(
            '@${decimalText(price)}',
            style: const TextStyle(
              fontFamily: qfMono,
              fontSize: 16,
              fontWeight: FontWeight.w700,
              color: QfColors.yellow,
            ),
          ),
          if (caption != null)
            Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Icon(
                  Icons.storefront_outlined,
                  size: 11,
                  color: QfColors.muted,
                ),
                const SizedBox(width: 3),
                Flexible(
                  child: Text(
                    caption,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(fontSize: 10, color: QfColors.muted),
                  ),
                ),
              ],
            ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final won = data.outcome == 'win', lost = data.outcome == 'loss';
    final tone = data.outcome == null || (!won && !lost)
        ? color
        : (won ? QfColors.primary : QfColors.danger);
    final prob = data.probability;
    final score = data.score;
    final header = [
      if (data.kickoff != null) kickoffText(data.kickoff),
      if (data.league != null && data.league!.isNotEmpty) data.league!,
    ].join(' · ');
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      decoration: ShapeDecoration(
        color: QfColors.surface,
        shape: CutCornerBorder(
          cut: 8,
          side: BorderSide(color: tone.withValues(alpha: .28)),
        ),
      ),
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          customBorder: const CutCornerBorder(cut: 8),
          onTap: data.onTap,
          child: Padding(
            padding: const EdgeInsets.all(14),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Expanded(
                      child: Text(
                        header,
                        style: const TextStyle(
                          fontFamily: qfMono,
                          fontSize: 11,
                          fontWeight: FontWeight.w500,
                          color: QfColors.text2,
                        ),
                      ),
                    ),
                    if (data.outcome != null) _outcomeBadge(context),
                  ],
                ),
                const SizedBox(height: 10),
                Row(
                  children: [
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.stretch,
                        children: [
                          _side(data.homeAvatar(32), data.home),
                          const SizedBox(height: 8),
                          _side(data.awayAvatar(32), data.away),
                        ],
                      ),
                    ),
                    if (score != null) ...[
                      const SizedBox(width: 10),
                      Column(
                        crossAxisAlignment: CrossAxisAlignment.end,
                        children: [
                          Text(
                            score,
                            style: const TextStyle(
                              fontFamily: qfMono,
                              fontSize: 22,
                              fontWeight: FontWeight.w700,
                              color: QfColors.cyan,
                            ),
                          ),
                          if (data.scoreNote != null)
                            Text(
                              data.scoreNote!,
                              style: const TextStyle(
                                fontSize: 10,
                                color: QfColors.muted,
                              ),
                            ),
                        ],
                      ),
                    ],
                    if (prob != null) ...[
                      const SizedBox(width: 12),
                      Column(
                        crossAxisAlignment: CrossAxisAlignment.end,
                        children: [
                          Text(
                            realPercent(prob),
                            style: const TextStyle(
                              fontFamily: qfMono,
                              fontSize: 20,
                              fontWeight: FontWeight.w700,
                              color: QfColors.primary,
                            ),
                          ),
                          Text(
                            l10n.mdModel.toUpperCase(),
                            style: const TextStyle(
                              fontFamily: qfDisplay,
                              fontSize: 10,
                              fontWeight: FontWeight.w700,
                              letterSpacing: 1.2,
                              color: QfColors.muted,
                            ),
                          ),
                        ],
                      ),
                    ],
                  ],
                ),
                const SizedBox(height: 12),
                Row(
                  children: [
                    Expanded(child: _pickChip(data.pick, color)),
                    const SizedBox(width: 10),
                    _quote(context),
                  ],
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

Widget _pickChip(String text, Color color) => Container(
  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
  decoration: ShapeDecoration(
    color: color.withValues(alpha: .12),
    shape: CutCornerBorder(
      cut: 6,
      side: BorderSide(color: color.withValues(alpha: .35)),
    ),
  ),
  child: Text(
    text,
    maxLines: 2,
    overflow: TextOverflow.ellipsis,
    style: TextStyle(
      fontSize: 12,
      fontWeight: FontWeight.w700,
      color: color,
    ),
  ),
);

/// Pronóstico bloqueado (VIP): solo partido y hora, con el candado (§5.1).
class MarketLockedCard extends StatelessWidget {
  const MarketLockedCard({
    super.key,
    required this.kickoff,
    required this.home,
    required this.away,
    required this.homeAvatar,
    required this.awayAvatar,
    this.onTap,
  });
  final Object? kickoff;
  final String home, away;
  final Widget Function(double size) homeAvatar, awayAvatar;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) => Container(
    margin: const EdgeInsets.only(bottom: 8),
    decoration: const ShapeDecoration(
      color: QfColors.surface,
      shape: CutCornerBorder(
        cut: 8,
        side: BorderSide(color: QfColors.border),
      ),
    ),
    child: Material(
      color: Colors.transparent,
      child: InkWell(
        customBorder: const CutCornerBorder(cut: 8),
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.all(14),
          child: Row(
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      kickoffText(kickoff),
                      style: const TextStyle(
                        fontFamily: qfMono,
                        fontSize: 11,
                        fontWeight: FontWeight.w500,
                        color: QfColors.text2,
                      ),
                    ),
                    const SizedBox(height: 8),
                    for (final (avatar, name) in [
                      (homeAvatar, home),
                      (awayAvatar, away),
                    ])
                      Padding(
                        padding: const EdgeInsets.only(bottom: 6),
                        child: Row(
                          children: [
                            avatar(28),
                            const SizedBox(width: 10),
                            Expanded(
                              child: Text(
                                name,
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                                style: const TextStyle(
                                  fontSize: 14,
                                  fontWeight: FontWeight.w700,
                                  color: Colors.white,
                                ),
                              ),
                            ),
                          ],
                        ),
                      ),
                  ],
                ),
              ),
              const SizedBox(width: 10),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
                decoration: ShapeDecoration(
                  color: QfColors.yellow.withValues(alpha: .08),
                  shape: CutCornerBorder(
                    cut: 6,
                    side: BorderSide(color: QfColors.yellow.withValues(alpha: .5)),
                  ),
                ),
                child: const Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(Icons.lock_outline, color: QfColors.yellow, size: 20),
                    SizedBox(height: 2),
                    Text(
                      'VIP',
                      style: TextStyle(
                        fontFamily: qfDisplay,
                        fontSize: 11,
                        fontWeight: FontWeight.w700,
                        letterSpacing: 1.2,
                        color: QfColors.yellow,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    ),
  );
}
