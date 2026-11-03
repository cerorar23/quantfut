import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter_svg/flutter_svg.dart';

import '../product/live_widgets.dart';
import '../product/qf_theme.dart';

const _track = QfColors.border;
const _panel = QfColors.surface2;

/// Logotipo de Google con sus cuatro colores (trazado oficial de las guías de marca).
class GoogleLogo extends StatelessWidget {
  const GoogleLogo({super.key, this.size = 22});

  final double size;

  static const _svg =
      '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48">'
      '<path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"/>'
      '<path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"/>'
      '<path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"/>'
      '<path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"/>'
      '</svg>';

  @override
  Widget build(BuildContext context) =>
      SvgPicture.string(_svg, width: size, height: size);
}

/// Ilustración animada de una diapositiva de la pantalla de acceso. `t` es una vuelta de 0 a 1.
/// Son esquemas: no llevan textos ni cifras de ejemplo, para no prometer ningún resultado.
class AccessIllustration extends StatelessWidget {
  const AccessIllustration({super.key, required this.index, required this.t});

  final int index;
  final Animation<double> t;

  @override
  Widget build(BuildContext context) => AnimatedBuilder(
    animation: t,
    builder: (context, _) => CustomPaint(
      painter: _Painter(index, t.value),
      size: Size.infinite,
    ),
  );
}

class _Painter extends CustomPainter {
  const _Painter(this.index, this.t);

  final int index;
  final double t;

  /// Oscilación suave 0–1.
  double _wave(double phase) => .5 + .5 * math.sin(2 * math.pi * (t + phase));

  /// Avance de 0 a 1 que se queda un rato lleno y vuelve a empezar.
  double _fill(double phase) {
    final v = ((t + phase) % 1.0) / .7;
    return Curves.easeOutCubic.transform(v.clamp(0, 1).toDouble());
  }

  void _round(Canvas c, Rect r, Color color, [double radius = 6]) =>
      c.drawRRect(RRect.fromRectAndRadius(r, Radius.circular(radius)), Paint()..color = color);

  @override
  void paint(Canvas canvas, Size size) {
    canvas.save();
    // Se dibuja en un lienzo lógico de 280 × 170 centrado y escalado.
    final scale = math.min(size.width / 280, size.height / 170);
    canvas.translate((size.width - 280 * scale) / 2, (size.height - 170 * scale) / 2);
    canvas.scale(scale);
    switch (index) {
      case 0:
        _probabilities(canvas);
      case 1:
        _pick(canvas);
      case 2:
        _ladder(canvas);
      case 3:
        _ticket(canvas);
      default:
        _coins(canvas);
    }
    canvas.restore();
  }

  void _probabilities(Canvas c) {
    const center = Offset(78, 85);
    final ring = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = 12
      ..color = _track;
    c.drawCircle(center, 50, ring);
    c.drawArc(
      Rect.fromCircle(center: center, radius: 50),
      -math.pi / 2,
      2 * math.pi * (.45 + .3 * _fill(0)),
      false,
      ring
        ..strokeCap = StrokeCap.round
        ..color = liveGreen,
    );
    final values = [.35 + .35 * _wave(0), .15 + .1 * _wave(.3), .3 + .25 * _wave(.6)];
    final colors = [liveGreen, liveMuted, liveCyan];
    for (var i = 0; i < 3; i++) {
      final y = 52.0 + i * 28;
      _round(c, Rect.fromLTWH(150, y, 112, 12), _track, 6);
      _round(c, Rect.fromLTWH(150, y, 112 * values[i], 12), colors[i], 6);
    }
  }

  void _pick(Canvas c) {
    final card = Rect.fromLTWH(20, 14, 240, 142);
    _round(c, card, _panel, 18);
    c.drawRRect(
      RRect.fromRectAndRadius(card, const Radius.circular(18)),
      Paint()
        ..style = PaintingStyle.stroke
        ..color = liveGreen.withValues(alpha: .35),
    );
    _round(c, const Rect.fromLTWH(36, 30, 70, 8), _track, 4);
    _round(c, const Rect.fromLTWH(36, 48, 130, 12), Colors.white24, 6);
    _round(c, const Rect.fromLTWH(36, 74, 108, 24), liveGreen.withValues(alpha: .2), 12);
    _round(c, const Rect.fromLTWH(46, 82, 66, 8), liveGreen, 4);
    final pulse = 1 + .06 * _wave(0);
    c.save();
    c.translate(206, 86);
    c.scale(pulse);
    _round(c, const Rect.fromLTWH(-30, -13, 60, 26), liveGold.withValues(alpha: .2), 13);
    _round(c, const Rect.fromLTWH(-18, -4, 36, 8), liveGold, 4);
    c.restore();
    _round(c, const Rect.fromLTWH(36, 120, 190, 10), _track, 5);
    _round(c, Rect.fromLTWH(36, 120, 190 * (.45 + .4 * _fill(0)), 10), liveGreen, 5);
  }

  void _ladder(Canvas c) {
    const steps = 5;
    final active = (t * (steps + 2)).floor();
    for (var i = 0; i < steps; i++) {
      final h = 34.0 + i * 20;
      final rect = Rect.fromLTWH(24 + i * 48, 156 - h, 40, h);
      final lit = i < active;
      _round(c, rect, lit ? liveGreen : _track, 8);
      if (lit) {
        _round(c, Rect.fromLTWH(rect.left + 10, rect.top + 10, 20, 6), Colors.white24, 3);
      }
    }
    final i = (active - 1).clamp(0, steps - 1);
    final h = 34.0 + i * 20;
    c.drawCircle(
      Offset(24 + i * 48 + 20, 156 - h - 14 - 4 * _wave(0)),
      9,
      Paint()..color = liveGold,
    );
  }

  void _ticket(Canvas c) {
    const card = Rect.fromLTWH(30, 10, 220, 150);
    _round(c, card, _panel, 18);
    _round(c, const Rect.fromLTWH(46, 26, 60, 12), liveCyan.withValues(alpha: .3), 6);
    _round(c, const Rect.fromLTWH(176, 24, 56, 18), liveGold, 9);
    // Línea punteada con muescas.
    for (var x = 44.0; x < 236; x += 12) {
      c.drawLine(const Offset(0, 0).translate(x, 58), Offset(x + 6, 58), Paint()..color = _track..strokeWidth = 2);
    }
    c.drawCircle(const Offset(30, 58), 8, Paint()..color = QfColors.bg);
    c.drawCircle(const Offset(250, 58), 8, Paint()..color = QfColors.bg);
    final lit = (t * 4).floor();
    for (var i = 0; i < 3; i++) {
      final y = 80.0 + i * 24;
      final done = i < lit;
      c.drawCircle(Offset(54, y), 6, Paint()..color = done ? liveGreen : _track);
      _round(c, Rect.fromLTWH(70, y - 5, 110 - i * 14, 10), Colors.white24, 5);
      _round(c, Rect.fromLTWH(200, y - 5, 32, 10), liveGold.withValues(alpha: done ? 1 : .35), 5);
      if (i < 2) c.drawLine(Offset(54, y + 6), Offset(54, y + 18), Paint()..color = _track..strokeWidth = 2);
    }
  }

  void _coins(Canvas c) {
    final claimed = (t * 8).floor().clamp(0, 7);
    for (var i = 0; i < 7; i++) {
      final done = i < claimed;
      final today = i == claimed && claimed < 7;
      final rect = Rect.fromLTWH(14 + i * 37, 92, 31, 48);
      _round(c, rect, done ? liveGreen.withValues(alpha: .25) : (today ? liveGold : _track), 10);
      c.drawCircle(
        rect.center.translate(0, -8),
        7,
        Paint()..color = done ? liveGreen : (today ? QfColors.bg : liveGold),
      );
      _round(c, Rect.fromCenter(center: rect.center.translate(0, 12), width: 18, height: 6), done ? liveGreen : Colors.white24, 3);
    }
    // Monedas que suben desde el día de hoy.
    final p = (t * 8) % 1.0;
    for (var k = 0; k < 4; k++) {
      final dx = (k - 1.5) * 16;
      final dy = -70 * p - k * 6;
      c.drawCircle(
        Offset(14 + (claimed.clamp(0, 6)) * 37 + 15 + dx * p, 84 + dy),
        6 - 2 * p,
        Paint()..color = liveGold.withValues(alpha: (1 - p).clamp(0, 1).toDouble()),
      );
    }
  }

  @override
  bool shouldRepaint(_Painter old) => old.t != t || old.index != index;
}
