import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../l10n/app_locale.dart';
import 'live_api.dart';
import 'live_market_detail.dart';
import 'live_widgets.dart';
import 'market_catalog.dart';

/// Color y símbolo de cada familia de mercado. Una familia que no figure aquí
/// usa el gris neutro: añadir un mercado al catálogo nunca rompe la pantalla.
const _look = <String, (Color, String)>{
  'goals': (liveCyan, '⚽'),
  'team_goals': (liveGreen, '🥅'),
  'corners': (liveGold, '🚩'),
  'corners_team': (Color(0xffff8b3d), '🚩'),
  'handicap': (Color(0xff9a7bff), '⚖'),
  'double_chance': (Color(0xffbbf32a), '✌'),
  'winner': (Color(0xff4ea1ff), '🏆'),
  'cards': (Color(0xffe85667), '🟨'),
};
(Color, String) _lookOf(String id) => _look[id] ?? (liveMuted, '•');

/// Mercados del servidor que componen cada familia del catálogo.
const familyMarkets = <String, List<String>>{
  'goals': ['totals'],
  'team_goals': [
    'team_totals_home',
    'team_totals_away',
    'home_to_score',
    'away_to_score',
  ],
  'corners': ['corners'],
  'corners_team': ['corners_home', 'corners_away'],
  'handicap': ['spreads'],
  'double_chance': ['double_chance'],
  'winner': ['h2h'],
  'cards': ['cards'],
};

/// Resueltos de una familia según el servidor (historial vivo). Sin datos del
/// servidor devuelve null y la pantalla usa el catálogo empaquetado.
PublishedRecord? serverRecord(JsonMap historial, String familyId) {
  final byMarket = jsonMap(historial['por_mercado']);
  var cases = 0, won = 0;
  for (final key in familyMarkets[familyId] ?? const <String>[]) {
    final m = jsonMap(byMarket[key]);
    cases += (m['n'] as num?)?.toInt() ?? 0;
    won += (m['aciertos'] as num?)?.toInt() ?? 0;
  }
  return byMarket.isEmpty || won > cases ? null : PublishedRecord(cases, won);
}

/// Pestaña Mercados: radar animado + una tarjeta por familia de mercado.
///
/// Todo sale de [MarketCatalog] (evidencia validada y resultados publicados).
/// No hay alertas en vivo porque el modelo pronostica antes del partido; la
/// pantalla no insinúa lo contrario.
class MarketsDashboard extends StatefulWidget {
  const MarketsDashboard({
    super.key,
    required this.api,
    required this.alta,
    this.onVip,
  });

  /// Cliente para pedir el historial de cada mercado.
  final QuantFutApi api;

  /// Bloque `alta_probabilidad` de /home: próximos pronósticos e historial.
  final JsonMap alta;

  /// Abre la pantalla VIP desde un candado.
  final VoidCallback? onVip;
  @override
  State<MarketsDashboard> createState() => _MarketsDashboardState();
}

class _MarketsDashboardState extends State<MarketsDashboard>
    with SingleTickerProviderStateMixin {
  late final AnimationController _clock = AnimationController(
    vsync: this,
    duration: const Duration(seconds: 6),
  );

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    // Sin animación continua si el sistema pide reducir movimiento.
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
  Widget build(BuildContext context) => FutureBuilder<MarketCatalog>(
    future: MarketCatalog.load(),
    initialData: MarketCatalog.current,
    builder: (context, snapshot) {
      final catalog = snapshot.data;
      if (catalog == null) {
        return const Padding(
          padding: EdgeInsets.symmetric(vertical: 40),
          child: Center(child: CircularProgressIndicator()),
        );
      }
      final families = catalog.forSport(sportFootball);
      final historial = jsonMap(widget.alta['historial']);
      final upcoming = [
        for (final p in (widget.alta['proximos'] as List? ?? const []))
          jsonMap(p),
      ];
      final locked = [
        for (final p in (widget.alta['vip'] as List? ?? const [])) jsonMap(p),
      ];
      final liveOverall = (historial['n'] as num?) == null
          ? null
          : PublishedRecord(
              (historial['n'] as num).toInt(),
              (historial['aciertos'] as num?)?.toInt() ?? 0,
            );
      return Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _RadarHero(
            clock: _clock,
            catalog: catalog,
            families: families,
            overall: liveOverall ?? catalog.overall,
          ),
          const SizedBox(height: 12),
          LayoutBuilder(
            builder: (context, box) {
              final wide = (box.maxWidth - 10) / 2;
              return Wrap(
                spacing: 10,
                runSpacing: 10,
                children: [
                  for (var i = 0; i < families.length; i++)
                    SizedBox(
                      width: wide,
                      child: _FamilyCard(
                        clock: _clock,
                        family: families[i],
                        minimum: catalog.minimumCases,
                        phase: i / families.length,
                        record:
                            serverRecord(historial, families[i].id) ??
                            families[i].published,
                        onOpen: () => Navigator.of(context).push(
                          MaterialPageRoute<void>(
                            builder: (_) => MarketDetailScreen(
                              api: widget.api,
                              family: families[i],
                              minimum: catalog.minimumCases,
                              color: _lookOf(families[i].id).$1,
                              markets:
                                  familyMarkets[families[i].id] ?? const [],
                              onVip: widget.onVip,
                              locked: [
                                for (final p in locked)
                                  if ((familyMarkets[families[i].id] ??
                                          const [])
                                      .contains(p['market']))
                                    p,
                              ],
                              upcoming: [
                                for (final p in upcoming)
                                  if ((familyMarkets[families[i].id] ??
                                          const [])
                                      .contains(p['market']))
                                    p,
                              ],
                              record:
                                  serverRecord(historial, families[i].id) ??
                                  families[i].published,
                            ),
                          ),
                        ),
                      ),
                    ),
                ],
              );
            },
          ),
          const SizedBox(height: 12),
          liveText(context.l10n.marketsRadarNote, size: 10, color: liveMuted),
        ],
      );
    },
  );
}

class _RadarHero extends StatelessWidget {
  const _RadarHero({
    required this.clock,
    required this.catalog,
    required this.families,
    required this.overall,
  });
  final Animation<double> clock;
  final MarketCatalog catalog;
  final List<MarketFamily> families;
  final PublishedRecord overall;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(22),
        border: Border.all(color: liveCyan.withValues(alpha: .25)),
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
                      '${families.length}',
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
                liveText(
                  context.l10n.marketsEvidenceAt(catalog.cutoff),
                  size: 12,
                  color: liveMuted,
                ),
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
                painter: _RadarPainter(clock.value, [
                  for (final f in families) _lookOf(f.id).$1,
                ]),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _RadarPainter extends CustomPainter {
  _RadarPainter(this.t, this.blips);
  final double t;
  final List<Color> blips;

  @override
  void paint(Canvas canvas, Size size) {
    final c = size.center(Offset.zero);
    final r = size.shortestSide / 2 - 2;
    final line = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1
      ..color = liveCyan.withValues(alpha: .18);
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
          colors: [Colors.transparent, liveCyan.withValues(alpha: .5)],
          stops: const [.72, 1],
          transform: GradientRotation(head),
        ).createShader(rect),
    );
    canvas.drawLine(
      c,
      c + Offset(math.cos(head), math.sin(head)) * r,
      Paint()
        ..color = liveCyan.withValues(alpha: .9)
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

class _FamilyCard extends StatelessWidget {
  const _FamilyCard({
    required this.clock,
    required this.family,
    required this.minimum,
    required this.phase,
    required this.record,
    required this.onOpen,
  });
  final Animation<double> clock;
  final MarketFamily family;
  final int minimum;
  final double phase;
  final PublishedRecord record;
  final VoidCallback onOpen;

  @override
  Widget build(BuildContext context) {
    final (color, icon) = _lookOf(family.id);
    final best = family.bestSupported(minimum);
    return Semantics(
      button: true,
      label:
          '${family.localTitle}, '
          '${best == null ? context.l10n.marketsNoLineLabel : context.l10n.marketsHistoricHit(percent(best.observed))}',
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
                            tween: Tween(end: (best?.observed ?? 0) / 100),
                            duration: const Duration(milliseconds: 1100),
                            curve: Curves.easeOutCubic,
                            builder: (_, v, _) => CustomPaint(
                              painter: _RingPainter(v, color),
                              child: Center(
                                child: Text(
                                  best == null
                                      ? '—'
                                      : '${best.observed.round()}%',
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
                        Text(icon, style: const TextStyle(fontSize: 22)),
                      ],
                    ),
                    const SizedBox(height: 10),
                    Text(
                      family.localTitle,
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
                      best == null
                          ? context.l10n.marketsInReview
                          : '${best.localLabel} · ${casesLabel(best.cases)}',
                      maxLines: 3,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(fontSize: 11, color: liveMuted),
                    ),
                    const SizedBox(height: 10),
                    _PublishedRow(clock: clock, record: record, color: color),
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
