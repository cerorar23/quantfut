import 'dart:math' as math;

import 'package:flutter/material.dart';

/// Original offline illustrations. Shapes are decorative, not real statistics.
class WelcomeArt extends StatefulWidget {
  const WelcomeArt({
    super.key,
    required this.index,
    required this.accent,
    required this.active,
  });
  final int index;
  final Color accent;
  final bool active;
  @override
  State<WelcomeArt> createState() => _WelcomeArtState();
}

class _WelcomeArtState extends State<WelcomeArt>
    with SingleTickerProviderStateMixin, WidgetsBindingObserver {
  late final _animation = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 2800),
  );
  bool _resumed = true;
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _resumed =
        WidgetsBinding.instance.lifecycleState == null ||
        WidgetsBinding.instance.lifecycleState == AppLifecycleState.resumed;
  }

  void _sync() {
    if (widget.active && _resumed && !MediaQuery.disableAnimationsOf(context)) {
      if (!_animation.isAnimating) _animation.repeat(reverse: true);
    } else {
      _animation.stop();
    }
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    _sync();
  }

  @override
  void didUpdateWidget(WelcomeArt oldWidget) {
    super.didUpdateWidget(oldWidget);
    _sync();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    _resumed = state == AppLifecycleState.resumed;
    _sync();
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _animation.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => RepaintBoundary(
    child: AnimatedBuilder(
      animation: _animation,
      builder: (context, _) => CustomPaint(
        painter: _ArtPainter(
          widget.index,
          widget.accent,
          MediaQuery.disableAnimationsOf(context) ? .5 : _animation.value,
        ),
      ),
    ),
  );
}

class _ArtPainter extends CustomPainter {
  _ArtPainter(this.index, this.accent, this.phase);
  final int index;
  final Color accent;
  final double phase;
  static const ink = Color(0xffe9edf5),
      track = Color(0xff293a4b),
      muted = Color(0xff8496aa);
  void text(
    Canvas c,
    String value,
    Offset at, {
    double size = 9,
    Color color = ink,
  }) {
    final p = TextPainter(
      text: TextSpan(
        text: value,
        style: TextStyle(
          fontFamily: 'Gilroy Bold',
          fontSize: size,
          color: color,
          letterSpacing: .7,
        ),
      ),
      textDirection: TextDirection.ltr,
    )..layout();
    p.paint(c, at);
  }

  void line(Canvas c, Offset a, Offset b, Color color, [double width = 4]) =>
      c.drawLine(
        a,
        b,
        Paint()
          ..color = color
          ..strokeWidth = width
          ..strokeCap = StrokeCap.round,
      );
  void icon(Canvas c, IconData value, Offset at, Color color, double size) {
    final p = TextPainter(
      text: TextSpan(
        text: String.fromCharCode(value.codePoint),
        style: TextStyle(
          fontFamily: value.fontFamily,
          package: value.fontPackage,
          fontSize: size,
          color: color,
        ),
      ),
      textDirection: TextDirection.ltr,
    )..layout();
    p.paint(c, at);
  }

  @override
  void paint(Canvas c, Size size) {
    c.save();
    c.scale(size.width / 260, size.height / 260);
    c.drawCircle(
      const Offset(130, 130),
      120,
      Paint()
        ..shader = RadialGradient(
          colors: [accent.withValues(alpha: .13), accent.withValues(alpha: 0)],
        ).createShader(const Rect.fromLTWH(10, 10, 240, 240)),
    );
    c.translate(0, -math.sin(phase * math.pi) * 5);
    final card = RRect.fromRectAndRadius(
      const Rect.fromLTWH(28, 28, 204, 204),
      const Radius.circular(16),
    );
    c.drawRRect(card, Paint()..color = const Color(0xff132333));
    c.drawRRect(
      card,
      Paint()
        ..color = const Color(0xff2b506a)
        ..style = PaintingStyle.stroke,
    );
    const headings = [
      'FÚTBOL + NBA',
      'EL CONTEXTO IMPORTA',
      'EXPLORA LOS MERCADOS',
      'HISTORIAL A LA VISTA',
      'DATOS + TU CRITERIO',
    ];
    text(c, headings[index], const Offset(48, 47), color: accent);
    if (index == 0) {
      final bounce = math.sin(phase * math.pi) * 13;
      for (var i = 0; i < 3; i++) {
        c.drawOval(
          Rect.fromCenter(
            center: const Offset(130, 151),
            width: 160 - i * 24,
            height: 58 - i * 12,
          ),
          Paint()
            ..color = track
            ..style = PaintingStyle.stroke,
        );
      }
      ball(c, Offset(91, 111 - bounce), false);
      ball(c, Offset(170, 115 + bounce * .3), true);
      text(c, 'FÚTBOL', const Offset(67, 186), color: accent);
      text(c, 'NBA', const Offset(160, 186), color: const Color(0xffffb600));
    } else if (index == 1) {
      final rect = Rect.fromCircle(center: const Offset(130, 116), radius: 40);
      final p = Paint()
        ..style = PaintingStyle.stroke
        ..strokeWidth = 8
        ..strokeCap = StrokeCap.round;
      c.drawArc(rect, math.pi * .75, math.pi * 1.5, false, p..color = track);
      c.drawArc(
        rect,
        math.pi * .75,
        math.pi * (1 + phase * .3),
        false,
        p..color = accent,
      );
      icon(c, Icons.insights_rounded, const Offset(111, 98), ink, 38);
      const labels = ['FORMA', 'CARA A CARA', 'ESTADÍSTICAS'];
      for (var i = 0; i < 3; i++) {
        final y = 176.0 + i * 18;
        text(c, labels[i], Offset(48, y - 5), size: 7, color: muted);
        line(c, Offset(140, y), Offset(209, y), track, 3);
        line(c, Offset(140, y), Offset(163 + i * 8 + phase * 10, y), accent, 3);
      }
    } else if (index == 2 || index == 3) {
      const markets = [
        Icons.sports_soccer,
        Icons.flag_rounded,
        Icons.sports_basketball,
      ];
      const results = [
        Icons.check_rounded,
        Icons.close_rounded,
        Icons.schedule_rounded,
      ];
      const labels = ['GOLES', 'CÓRNERS', 'NBA'];
      const colors = [Color(0xff00d5ee), Color(0xff00d58b), Color(0xffffb600)];
      for (var i = 0; i < 3; i++) {
        final y = 90.0 + i * 39;
        c.drawRRect(
          RRect.fromRectAndRadius(
            Rect.fromLTWH(41, y - 5, 178, 33),
            const Radius.circular(9),
          ),
          Paint()..color = track.withValues(alpha: .45),
        );
        icon(
          c,
          index == 2 ? markets[i] : results[i],
          Offset(49, y),
          colors[i],
          21,
        );
        if (index == 2) {
          text(c, labels[i], Offset(79, y + 4));
        } else {
          line(c, Offset(80, y + 8), Offset(119 + phase * 15, y + 8), muted, 4);
        }
        line(c, Offset(146, y + 10), Offset(203, y + 10), track, 3);
        line(
          c,
          Offset(146, y + 10),
          Offset(164 + phase * 14 + i * 5, y + 10),
          colors[i],
          3,
        );
      }
      text(
        c,
        index == 2 ? 'ANALIZA CADA SELECCIÓN' : 'TRANSPARENCIA',
        const Offset(49, 210),
        size: 7.5,
        color: muted,
      );
    } else {
      c.drawCircle(
        const Offset(130, 132),
        47,
        Paint()..color = accent.withValues(alpha: .08),
      );
      c.drawCircle(
        const Offset(130, 132),
        47,
        Paint()
          ..color = accent.withValues(alpha: .3)
          ..style = PaintingStyle.stroke,
      );
      icon(c, Icons.menu_book_rounded, const Offset(104, 106), accent, 52);
      for (var i = 0; i < 3; i++) {
        final a = -math.pi / 2 + i * math.pi * 2 / 3 + (phase - .5) * .5;
        c.drawCircle(
          Offset(130 + math.cos(a) * 57, 132 + math.sin(a) * 57),
          4,
          Paint()..color = i == 1 ? const Color(0xffffb600) : accent,
        );
      }
      text(
        c,
        'ANALIZA. COMPARA. EXPLORA.',
        const Offset(47, 205),
        size: 8,
        color: muted,
      );
    }
    c.restore();
  }

  void ball(Canvas c, Offset center, bool basketball) {
    c.save();
    c.translate(center.dx, center.dy);
    c.rotate((phase - .5) * .2);
    c.drawCircle(
      Offset.zero,
      29,
      Paint()..color = basketball ? const Color(0xffffb600) : ink,
    );
    if (basketball) {
      line(c, const Offset(-28, 0), const Offset(28, 0), track, 2);
      line(c, const Offset(0, -28), const Offset(0, 28), track, 2);
      c.drawOval(
        const Rect.fromLTWH(-12, -28, 24, 56),
        Paint()
          ..color = track
          ..style = PaintingStyle.stroke
          ..strokeWidth = 2,
      );
    } else {
      final p = Path();
      for (var i = 0; i < 5; i++) {
        final a = -math.pi / 2 + i * math.pi * 2 / 5;
        final at = Offset(math.cos(a) * 11, math.sin(a) * 11);
        if (i == 0) {
          p.moveTo(at.dx, at.dy);
        } else {
          p.lineTo(at.dx, at.dy);
        }
        line(c, at, at * 2.5, track, 2);
      }
      c.drawPath(p..close(), Paint()..color = track);
    }
    c.restore();
  }

  @override
  bool shouldRepaint(_ArtPainter old) =>
      old.index != index || old.phase != phase || old.accent != accent;
}
