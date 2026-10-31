import 'dart:math' as math;

import 'package:flutter/material.dart';

import 'live_widgets.dart';
import 'qf_theme.dart';

/// Lluvia breve de monedas con un «+N monedas» que sube y se desvanece. Se reproduce una vez al
/// montarse; con «reducir animaciones» activado no se dibuja nada.
class CoinBurst extends StatefulWidget {
  const CoinBurst({super.key, required this.label});

  final String label;

  @override
  State<CoinBurst> createState() => _CoinBurstState();
}

class _CoinBurstState extends State<CoinBurst>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 1400),
  );
  bool _started = false;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (_started) return;
    _started = true;
    if (!MediaQuery.of(context).disableAnimations) _controller.forward();
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (MediaQuery.of(context).disableAnimations) return const SizedBox.shrink();
    return IgnorePointer(
      child: AnimatedBuilder(
        animation: _controller,
        builder: (context, _) {
          final t = _controller.value;
          if (t >= 1) return const SizedBox.shrink();
          return Stack(
            children: [
              Positioned.fill(child: CustomPaint(painter: _BurstPainter(t))),
              Align(
                alignment: Alignment(0, .1 - .5 * Curves.easeOut.transform(t)),
                child: Opacity(
                  opacity: (1 - Curves.easeIn.transform(t)).clamp(0, 1).toDouble(),
                  child: Text(
                    widget.label,
                    style: const TextStyle(
                      color: liveGold,
                      fontFamily: 'Gilroy ExtraBold',
                      fontSize: 34,
                      shadows: [Shadow(blurRadius: 14, color: Colors.black54)],
                    ),
                  ),
                ),
              ),
            ],
          );
        },
      ),
    );
  }
}

class _BurstPainter extends CustomPainter {
  const _BurstPainter(this.t);

  final double t;
  static const _count = 18;

  @override
  void paint(Canvas canvas, Size size) {
    final origin = Offset(size.width / 2, size.height * .55);
    for (var i = 0; i < _count; i++) {
      // Abanico hacia arriba; velocidad y tamaño repartidos de forma fija (sin azar).
      final angle = -math.pi / 2 + (i / (_count - 1) - .5) * math.pi * 1.2;
      final speed = 230 + (i * 53 % 120);
      final x = origin.dx + math.cos(angle) * speed * t;
      final y = origin.dy + math.sin(angle) * speed * t + 520 * t * t;
      final alpha = (1 - t * t).clamp(0, 1).toDouble();
      final radius = 6.0 + (i * 7 % 5);
      canvas.drawCircle(
        Offset(x, y),
        radius,
        Paint()..color = liveGold.withValues(alpha: alpha),
      );
      canvas.drawCircle(
        Offset(x, y),
        radius * .55,
        Paint()..color = QfColors.text.withValues(alpha: alpha),
      );
    }
  }

  @override
  bool shouldRepaint(_BurstPainter oldDelegate) => oldDelegate.t != t;
}
