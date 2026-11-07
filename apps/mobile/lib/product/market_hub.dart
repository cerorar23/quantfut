import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../l10n/app_locale.dart';
import '../l10n/pick_labels.dart' show bookName;
import 'live_api.dart';
import 'live_widgets.dart';
import 'market_catalog.dart';
import 'qf_theme.dart';

/// Piezas de la pestaña Mercados compartidas por fútbol, NBA y tenis: radar, tarjeta de familia,
/// tarjeta de pronóstico (escudos, cuota y casa) y cabecera de la pantalla de un mercado.
/// Fútbol fue el diseño de partida; NBA y tenis lo reutilizan tal cual.

/// Color y símbolo de cada familia de mercado. Una familia que no figure aquí usa el gris neutro:
/// añadir un mercado nunca rompe la pantalla.
///
/// Iconos de Material y no emojis: un emoji depende de la fuente del teléfono y en Android antiguos
/// (🟨, ⚖, ✌) sale como cuadro vacío o en monocromo.
const _look = <String, (Color, IconData)>{
  // Fútbol.
  'goals': (liveCyan, Icons.sports_soccer),
  'btts': (liveGreen, Icons.compare_arrows),
  'team_goals': (liveGreen, Icons.sports_score),
  'corners': (liveGold, Icons.flag_outlined),
  'corners_team': (Color(0xffff8b3d), Icons.flag_outlined),
  'handicap': (Color(0xff9a7bff), Icons.shield_outlined),
  'double_chance': (Color(0xffbbf32a), Icons.alt_route_rounded),
  'winner': (Color(0xff4ea1ff), Icons.emoji_events_outlined),
  'cards': (Color(0xffe85667), Icons.style_outlined),
  // NBA.
  'game_total': (liveCyan, Icons.stacked_bar_chart),
  'team_points': (liveGreen, Icons.groups_outlined),
  'player_points': (liveGold, Icons.person_outline),
  'player_rebounds': (Color(0xffff8b3d), Icons.autorenew),
  'player_assists': (Color(0xffbbf32a), Icons.swap_horiz),
  'player_threes': (Color(0xffe85667), Icons.sports_basketball_outlined),
  // Tenis.
  'games_total': (liveCyan, Icons.format_list_numbered),
  'games_handicap': (Color(0xff9a7bff), Icons.shield_outlined),
  'set_winner': (Color(0xffbbf32a), Icons.looks_one_outlined),
  'sets_handicap': (Color(0xffff8b3d), Icons.exposure),
  'sets_total': (liveGold, Icons.view_week_outlined),
  'tiebreak': (Color(0xffe85667), Icons.timelapse),
};

(Color, IconData) marketLook(String id) =>
    _look[id] ?? (liveMuted, Icons.circle_outlined);

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
  });
  final String id, title, detail;
  final Color color;
  final IconData icon;

  /// Acierto (0–100) del anillo; null = sin línea ni resueltos.
  final double? percent;

  /// Publicados ya resueltos (acertados / total).
  final PublishedRecord record;
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

/// Cabecera de la pestaña: «MODELO ACTIVO», número de familias, evidencia y radar.
class MarketsHero extends StatelessWidget {
  const MarketsHero({
    super.key,
    required this.clock,
    required this.colors,
    required this.evidence,
    required this.overall,
    this.accent = liveCyan,
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
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(22),
        border: Border.all(color: accent.withValues(alpha: .25)),
        gradient: const LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [Color(0xff0f2a3a), Color(0xff0a1220)],
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
                          color: liveGreen,
                          boxShadow: [
                            BoxShadow(
                              color: liveGreen.withValues(
                                alpha:
                                    .25 +
                                    .45 * math.sin(clock.value * 12.566).abs(),
                              ),
                              blurRadius: 8,
                            ),
                          ],
                        ),
                      ),
                    ),
                    const SizedBox(width: 8),
                    liveText(
                      context.l10n.marketsModelActive,
                      size: 11,
                      color: liveGreen,
                      bold: true,
                    ),
                  ],
                ),
                const SizedBox(height: 10),
                Row(
                  crossAxisAlignment: CrossAxisAlignment.end,
                  children: [
                    Text(
                      '${colors.length}',
                      style: const TextStyle(
                        fontSize: 48,
                        height: 1,
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: liveText(
                        context.l10n.marketsFamiliesRadar,
                        size: 14,
                        bold: true,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                liveText(evidence, size: 12, color: liveMuted),
                const SizedBox(height: 12),
                Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 12,
                    vertical: 7,
                  ),
                  decoration: BoxDecoration(
                    color: Colors.white.withValues(alpha: .06),
                    borderRadius: BorderRadius.circular(20),
                  ),
                  child: liveText(
                    overall.cases == 0
                        ? context.l10n.marketsNoResolved
                        : context.l10n.marketsPublishedWon(
                            overall.won,
                            overall.cases,
                            percent(overall.observed),
                          ),
                    size: 11,
                    bold: true,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(width: 12),
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

/// Tarjeta de una familia: anillo de acierto, icono, nombre, detalle y «Publicado n/m» con puntos.
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
          borderRadius: BorderRadius.circular(18),
          onTap: onOpen,
          child: Container(
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(18),
              border: Border.all(color: color.withValues(alpha: .35)),
              gradient: LinearGradient(
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
                colors: [color.withValues(alpha: .12), const Color(0xff0d1522)],
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
                      children: [
                        SizedBox(
                          width: 54,
                          height: 54,
                          child: TweenAnimationBuilder<double>(
                            tween: Tween(end: (percentValue ?? 0) / 100),
                            duration: const Duration(milliseconds: 1100),
                            curve: Curves.easeOutCubic,
                            builder: (_, v, _) => CustomPaint(
                              painter: _RingPainter(v, color),
                              child: Center(
                                child: Text(
                                  percentValue == null
                                      ? '—'
                                      : '${percentValue.round()}%',
                                  style: const TextStyle(
                                    fontSize: 14,
                                    fontWeight: FontWeight.w800,
                                  ),
                                ),
                              ),
                            ),
                          ),
                        ),
                        const Spacer(),
                        Icon(data.icon, color: color, size: 24),
                      ],
                    ),
                    const SizedBox(height: 10),
                    Text(
                      data.title,
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(
                        fontSize: 14,
                        fontWeight: FontWeight.w800,
                        height: 1.15,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      data.detail,
                      maxLines: 3,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(fontSize: 11, color: liveMuted),
                    ),
                    const SizedBox(height: 10),
                    _PublishedRow(
                      clock: clock,
                      record: data.record,
                      color: color,
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

/// «Publicado 15/21» con puntos. Los puntos reflejan la proporción de aciertos,
/// no el orden en que ocurrieron; el último acertado late.
class _PublishedRow extends StatelessWidget {
  const _PublishedRow({
    required this.clock,
    required this.record,
    required this.color,
  });
  final Animation<double> clock;
  final PublishedRecord record;
  final Color color;

  @override
  Widget build(BuildContext context) {
    if (record.cases == 0) {
      return liveText(
        context.l10n.marketsNoPublications,
        size: 10,
        color: liveMuted,
      );
    }
    final dots = math.min(record.cases, 10);
    final hits = (record.won * dots / record.cases).round();
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        liveText(
          context.l10n.marketsPublished(record.won, record.cases),
          size: 10,
          color: liveMuted,
          bold: true,
        ),
        const SizedBox(height: 6),
        AnimatedBuilder(
          animation: clock,
          builder: (_, _) => Wrap(
            spacing: 4,
            runSpacing: 4,
            children: [
              for (var i = 0; i < dots; i++)
                Container(
                  width: 7,
                  height: 7,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: i < hits
                        ? color.withValues(
                            alpha: i == hits - 1
                                ? .55 +
                                      .45 * math.sin(clock.value * 12.566).abs()
                                : 1,
                          )
                        : Colors.transparent,
                    border: i < hits
                        ? null
                        : Border.all(color: Colors.white24, width: 1),
                  ),
                ),
            ],
          ),
        ),
      ],
    );
  }
}

class _RingPainter extends CustomPainter {
  _RingPainter(this.progress, this.color);
  final double progress;
  final Color color;

  @override
  void paint(Canvas canvas, Size size) {
    final rect = Offset.zero & size;
    final box = rect.deflate(4);
    canvas.drawArc(
      box,
      0,
      2 * math.pi,
      false,
      Paint()
        ..style = PaintingStyle.stroke
        ..strokeWidth = 5
        ..color = Colors.white.withValues(alpha: .08),
    );
    canvas.drawArc(
      box,
      -math.pi / 2,
      2 * math.pi * progress.clamp(0, 1),
      false,
      Paint()
        ..style = PaintingStyle.stroke
        ..strokeWidth = 5
        ..strokeCap = StrokeCap.round
        ..color = color,
    );
  }

  @override
  bool shouldRepaint(_RingPainter old) =>
      old.progress != progress || old.color != color;
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

/// Tarjeta «Tasa de acierto»: hoy y general. `onLines` (solo fútbol) abre las líneas validadas.
class MarketRateCard extends StatelessWidget {
  const MarketRateCard({
    super.key,
    required this.color,
    required this.today,
    required this.overall,
    this.onLines,
  });
  final Color color;
  final PublishedRecord? today;
  final PublishedRecord overall;
  final VoidCallback? onLines;

  Widget _stat(String label, PublishedRecord? r) => Expanded(
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        liveText(label, size: 11, color: liveMuted),
        const SizedBox(height: 4),
        Wrap(
          spacing: 8,
          crossAxisAlignment: WrapCrossAlignment.end,
          children: [
            liveText(
              r == null ? '—' : '${r.won}/${r.cases}',
              size: 17,
              bold: true,
            ),
            if (r != null && r.cases > 0)
              liveText(percent(r.observed), size: 15, bold: true, color: color),
          ],
        ),
      ],
    ),
  );

  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.all(14),
    decoration: BoxDecoration(
      color: livePanel,
      borderRadius: BorderRadius.circular(16),
      border: Border.all(color: color.withValues(alpha: .3)),
    ),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Icon(Icons.show_chart, color: color, size: 20),
            const SizedBox(width: 8),
            Expanded(
              child: liveText(context.l10n.mdHitRate, size: 14, bold: true),
            ),
            if (onLines != null)
              TextButton(
                onPressed: onLines,
                child: Text(
                  context.l10n.mdValidatedLines,
                  style: const TextStyle(fontSize: 11),
                ),
              ),
          ],
        ),
        const SizedBox(height: 6),
        Row(
          children: [
            _stat(context.l10n.commonToday, today),
            Container(width: 1, height: 36, color: Colors.white12),
            const SizedBox(width: 14),
            _stat(context.l10n.mdOverall, overall),
          ],
        ),
      ],
    ),
  );
}

Widget marketEmptyState(String message) => Center(
  child: Padding(
    padding: const EdgeInsets.all(28),
    child: liveText(message, size: 13, color: liveMuted),
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
  padding: const EdgeInsets.only(top: 8, bottom: 10),
  child: Center(
    child: Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 5),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: .06),
        borderRadius: BorderRadius.circular(14),
      ),
      child: liveText(label, size: 11, color: liveMuted, bold: true),
    ),
  ),
);

/// Pantalla de un mercado: tarjeta de acierto, pestañas Hoy / Anteriores y su contenido.
/// El contenido de cada pestaña lo pone cada deporte; el marco es el mismo.
class MarketScaffold extends StatelessWidget {
  const MarketScaffold({
    super.key,
    required this.title,
    required this.color,
    required this.today,
    required this.overall,
    required this.todayCount,
    required this.todayTab,
    required this.historyTab,
    this.onLines,
  });
  final String title;
  final Color color;
  final PublishedRecord? today;
  final PublishedRecord overall;
  final int todayCount;
  final Widget todayTab, historyTab;
  final VoidCallback? onLines;

  @override
  Widget build(BuildContext context) => Theme(
    data: liveTheme(),
    child: DefaultTabController(
      length: 2,
      child: Scaffold(
        appBar: AppBar(
          backgroundColor: liveBg,
          title: liveText(title, size: 18, bold: true),
        ),
        body: Column(
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 4, 16, 8),
              child: MarketRateCard(
                color: color,
                today: today,
                overall: overall,
                onLines: onLines,
              ),
            ),
            TabBar(
              indicatorColor: color,
              labelColor: Colors.white,
              unselectedLabelColor: liveMuted,
              tabs: [
                Tab(text: context.l10n.mdTabToday(todayCount)),
                Tab(text: context.l10n.mdTabPrevious),
              ],
            ),
            Expanded(child: TabBarView(children: [todayTab, historyTab])),
          ],
        ),
      ),
    ),
  );
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
          style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w700),
        ),
      ),
    ],
  );

  Widget _outcomeBadge(BuildContext context) {
    final l10n = context.l10n;
    final won = data.outcome == 'win', lost = data.outcome == 'loss';
    final (label, bg, icon) = won
        ? (l10n.parleyOutcomeWin, const Color(0xff1f7a3d), Icons.check_rounded)
        : lost
        ? (l10n.parleyOutcomeLoss, const Color(0xffc23b4d), Icons.close_rounded)
        : (l10n.parleyOutcomeVoid, const Color(0xff4a5568), Icons.remove);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: bg,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 14, color: Colors.white),
          const SizedBox(width: 3),
          liveText(label, size: 11, bold: true),
        ],
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
          style: TextStyle(fontFamily: qfMono, fontSize: 15, color: liveMuted),
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
          liveText(
            '@${decimalText(price)}',
            size: 17,
            bold: true,
            color: liveGold,
          ),
          if (caption != null)
            Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Icon(
                  Icons.storefront_outlined,
                  size: 11,
                  color: liveMuted,
                ),
                const SizedBox(width: 3),
                Flexible(
                  child: Text(
                    caption,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(fontSize: 10, color: liveMuted),
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
        : (won ? liveGreen : QfColors.danger);
    final prob = data.probability;
    final score = data.score;
    final header = [
      if (data.kickoff != null) kickoffText(data.kickoff),
      if (data.league != null && data.league!.isNotEmpty) data.league!,
    ].join(' · ');
    return liveCard(
      border: tone.withValues(alpha: .28),
      padding: EdgeInsets.zero,
      child: InkWell(
        borderRadius: BorderRadius.circular(16),
        onTap: data.onTap,
        child: Padding(
          padding: const EdgeInsets.all(14),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Expanded(child: liveText(header, size: 11, color: liveMuted)),
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
                        liveText(score, size: 22, bold: true, color: liveCyan),
                        if (data.scoreNote != null)
                          liveText(data.scoreNote!, size: 9, color: liveMuted),
                      ],
                    ),
                  ],
                  if (prob != null) ...[
                    const SizedBox(width: 12),
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.end,
                      children: [
                        liveText(
                          realPercent(prob),
                          size: 20,
                          bold: true,
                          color: liveGreen,
                        ),
                        liveText(l10n.mdModel, size: 9, color: liveMuted),
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
    );
  }
}

Widget _pickChip(String text, Color color) => Container(
  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
  decoration: BoxDecoration(
    color: color.withValues(alpha: .16),
    borderRadius: BorderRadius.circular(8),
  ),
  child: Text(
    text,
    maxLines: 2,
    overflow: TextOverflow.ellipsis,
    style: TextStyle(fontSize: 12, fontWeight: FontWeight.w800, color: color),
  ),
);

/// Pronóstico bloqueado (VIP): solo partido y hora, con el candado.
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
  Widget build(BuildContext context) => InkWell(
    borderRadius: BorderRadius.circular(16),
    onTap: onTap,
    child: liveCard(
      border: Colors.white12,
      child: Row(
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                liveText(kickoffText(kickoff), size: 11, color: liveMuted),
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
          Column(
            children: [
              const Icon(Icons.lock_outline, color: liveGold, size: 22),
              const SizedBox(height: 4),
              liveText('VIP', size: 11, color: liveGold, bold: true),
            ],
          ),
        ],
      ),
    ),
  );
}
