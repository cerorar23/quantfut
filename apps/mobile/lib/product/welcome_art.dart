import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../l10n/app_locale.dart';
import 'qf_shapes.dart';
import 'qf_theme.dart';

/// Ilustraciones de la pantalla de bienvenida (CyberCore v3).
/// Basadas en pantallas/Bienvenida.dc.html y capturas/Bienvenida.png.
class WelcomeArt extends StatelessWidget {
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
  Widget build(BuildContext context) {
    return Center(
      child: FittedBox(
        fit: BoxFit.contain,
        child: SizedBox(
          width: 340,
          height: 280,
          child: _buildArt(context),
        ),
      ),
    );
  }

  Widget _buildArt(BuildContext context) {
    switch (index) {
      case 0:
        return const _Slide0Art();
      case 1:
        return const _Slide1Art();
      case 2:
        return const _Slide2Art();
      case 3:
        return const _Slide3Art();
      case 4:
      default:
        return const _Slide4Art();
    }
  }
}

// ---------------------------------------------------------------------------
// Diapositiva 0: Tres tarjetas con deportes (Fútbol, NBA elevada, Tenis) + barra
// ---------------------------------------------------------------------------
class _Slide0Art extends StatelessWidget {
  const _Slide0Art();

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    return Stack(
      alignment: Alignment.center,
      children: [
        // Tarjeta izquierda (Fútbol): rotada -6 grados
        Positioned(
          left: 10,
          top: 36,
          child: Transform.rotate(
            angle: -6 * math.pi / 180,
            child: Container(
              width: 104,
              height: 150,
              decoration: const ShapeDecoration(
                color: QfColors.surface,
                shape: CutCornerBorder(
                  cut: 10,
                  side: BorderSide(color: QfColors.border),
                ),
              ),
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  const Icon(Icons.sports_soccer, size: 52, color: QfColors.text),
                  const SizedBox(height: 10),
                  Text(
                    l10n.artFootball.toUpperCase(),
                    style: const TextStyle(
                      fontFamily: qfDisplay,
                      fontWeight: FontWeight.w700,
                      fontSize: 12,
                      letterSpacing: 1.4,
                      color: QfColors.muted,
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
        // Tarjeta derecha (Tenis): rotada +6 grados
        Positioned(
          right: 10,
          top: 36,
          child: Transform.rotate(
            angle: 6 * math.pi / 180,
            child: Container(
              width: 104,
              height: 150,
              decoration: const ShapeDecoration(
                color: QfColors.surface,
                shape: CutCornerBorder(
                  cut: 10,
                  side: BorderSide(color: QfColors.border),
                ),
              ),
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  const Icon(Icons.sports_tennis, size: 52, color: QfColors.text),
                  const SizedBox(height: 10),
                  Text(
                    l10n.artTennis.toUpperCase(),
                    style: const TextStyle(
                      fontFamily: qfDisplay,
                      fontWeight: FontWeight.w700,
                      fontSize: 12,
                      letterSpacing: 1.4,
                      color: QfColors.muted,
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
        // Tarjeta central (NBA): elevada, sombra cian, cian brillante
        Positioned(
          top: 14,
          child: Container(
            width: 118,
            height: 174,
            decoration: ShapeDecoration(
              color: QfColors.surface2,
              shadows: [
                BoxShadow(
                  color: QfColors.cyan.withValues(alpha: 0.32),
                  blurRadius: 36,
                  spreadRadius: 2,
                ),
              ],
              shape: const CutCornerBorder(
                cut: 10,
                side: BorderSide(color: QfColors.cyan, width: 1.2),
              ),
            ),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                const Icon(Icons.sports_basketball, size: 62, color: QfColors.cyan),
                const SizedBox(height: 10),
                Text(
                  l10n.artNba.toUpperCase(),
                  style: const TextStyle(
                    fontFamily: qfDisplay,
                    fontWeight: FontWeight.w700,
                    fontSize: 14,
                    letterSpacing: 1.4,
                    color: QfColors.cyan,
                  ),
                ),
              ],
            ),
          ),
        ),
        // Barra inferior de tres segmentos (58 cian, 24 pizarra, 18 atenuado)
        Positioned(
          left: 30,
          right: 30,
          bottom: 24,
          child: SizedBox(
            height: 8,
            child: Row(
              children: [
                Expanded(
                  flex: 58,
                  child: Container(color: QfColors.cyan),
                ),
                const SizedBox(width: 3),
                Expanded(
                  flex: 24,
                  child: Container(color: QfColors.slate),
                ),
                const SizedBox(width: 3),
                Expanded(
                  flex: 18,
                  child: Container(color: QfColors.chrome),
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }
}

// ---------------------------------------------------------------------------
// Diapositiva 1: Mini radar pentagonal de 5 ejes + pestañas (Forma, Cara a cara, Estadísticas)
// ---------------------------------------------------------------------------
class _Slide1Art extends StatelessWidget {
  const _Slide1Art();

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    return Column(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        SizedBox(
          width: 320,
          height: 190,
          child: CustomPaint(
            painter: _RadarPainter(
              labels: [
                l10n.radarAttack.toUpperCase(),
                l10n.radarCreation.toUpperCase(),
                l10n.radarFinishing.toUpperCase(),
                l10n.artCorners.toUpperCase(),
                l10n.radarDefense.toUpperCase(),
              ],
            ),
          ),
        ),
        const SizedBox(height: 10),
        Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
              decoration: const ShapeDecoration(
                color: QfColors.chipActiveBg,
                shape: CutCornerBorder(
                  cut: 6,
                  side: BorderSide(color: QfColors.borderStrong),
                ),
              ),
              child: Text(
                l10n.artForm.toUpperCase(),
                style: const TextStyle(
                  fontFamily: qfDisplay,
                  fontWeight: FontWeight.w700,
                  fontSize: 11,
                  letterSpacing: 1.1,
                  color: QfColors.cyan,
                ),
              ),
            ),
            const SizedBox(width: 6),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
              decoration: const ShapeDecoration(
                color: QfColors.surface,
                shape: CutCornerBorder(
                  cut: 6,
                  side: BorderSide(color: QfColors.border),
                ),
              ),
              child: Text(
                l10n.artHeadToHead.toUpperCase(),
                style: const TextStyle(
                  fontFamily: qfDisplay,
                  fontWeight: FontWeight.w700,
                  fontSize: 11,
                  letterSpacing: 1.1,
                  color: QfColors.muted,
                ),
              ),
            ),
            const SizedBox(width: 6),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
              decoration: const ShapeDecoration(
                color: QfColors.surface,
                shape: CutCornerBorder(
                  cut: 6,
                  side: BorderSide(color: QfColors.border),
                ),
              ),
              child: Text(
                l10n.artStats.toUpperCase(),
                style: const TextStyle(
                  fontFamily: qfDisplay,
                  fontWeight: FontWeight.w700,
                  fontSize: 11,
                  letterSpacing: 1.1,
                  color: QfColors.muted,
                ),
              ),
            ),
          ],
        ),
      ],
    );
  }
}

class _RadarPainter extends CustomPainter {
  const _RadarPainter({required this.labels});

  final List<String> labels;

  static const _valsA = [0.78, 0.70, 0.62, 0.58, 0.82];
  static const _valsB = [0.62, 0.74, 0.72, 0.70, 0.45];

  Offset _point(Offset center, double r, int k) {
    final angle = (-90 + 72 * k) * math.pi / 180;
    return Offset(center.dx + r * math.cos(angle), center.dy + r * math.sin(angle));
  }

  Path _poly(Offset center, double maxR, List<double> vals) {
    final path = Path();
    for (var k = 0; k < 5; k++) {
      final p = _point(center, maxR * vals[k], k);
      if (k == 0) {
        path.moveTo(p.dx, p.dy);
      } else {
        path.lineTo(p.dx, p.dy);
      }
    }
    path.close();
    return path;
  }

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2 + 4);
    const maxR = 64.0;

    // 4 anillos concéntricos
    final ringPaint = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1
      ..color = QfColors.cyan.withValues(alpha: 0.16);
    for (final fraction in [0.25, 0.5, 0.75, 1.0]) {
      canvas.drawPath(_poly(center, maxR, List.filled(5, fraction)), ringPaint);
    }

    // 5 radios desde el centro
    final axisPaint = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1
      ..color = QfColors.cyan.withValues(alpha: 0.2);
    for (var k = 0; k < 5; k++) {
      canvas.drawLine(center, _point(center, maxR, k), axisPaint);
    }

    // Polígono Equipo B (pizarra suave con trazo discontinuo simulado)
    final pathB = _poly(center, maxR, _valsB);
    canvas.drawPath(
      pathB,
      Paint()
        ..style = PaintingStyle.fill
        ..color = QfColors.chrome.withValues(alpha: 0.14),
    );
    canvas.drawPath(
      pathB,
      Paint()
        ..style = PaintingStyle.stroke
        ..strokeWidth = 1.6
        ..color = QfColors.chrome.withValues(alpha: 0.8),
    );

    // Polígono Equipo A (cian brillante)
    final pathA = _poly(center, maxR, _valsA);
    canvas.drawPath(
      pathA,
      Paint()
        ..style = PaintingStyle.fill
        ..color = QfColors.cyan.withValues(alpha: 0.28),
    );
    canvas.drawPath(
      pathA,
      Paint()
        ..style = PaintingStyle.stroke
        ..strokeWidth = 2.0
        ..color = QfColors.cyan,
    );

    // Etiquetas en los vértices
    for (var k = 0; k < 5; k++) {
      final p = _point(center, maxR + 14, k);
      final textSpan = TextSpan(
        text: labels[k],
        style: const TextStyle(
          fontFamily: qfDisplay,
          fontWeight: FontWeight.w700,
          fontSize: 9.5,
          letterSpacing: 1.0,
          color: QfColors.muted,
        ),
      );
      final tp = TextPainter(
        text: textSpan,
        textAlign: k == 0
            ? TextAlign.center
            : (k == 1 || k == 2 ? TextAlign.left : TextAlign.right),
        textDirection: TextDirection.ltr,
      )..layout();

      Offset textOffset;
      if (k == 0) {
        textOffset = Offset(p.dx - tp.width / 2, p.dy - tp.height - 2);
      } else if (k == 1) {
        textOffset = Offset(p.dx + 2, p.dy - tp.height / 2);
      } else if (k == 2) {
        textOffset = Offset(p.dx + 2, p.dy - 2);
      } else if (k == 3) {
        textOffset = Offset(p.dx - tp.width - 2, p.dy - 2);
      } else {
        textOffset = Offset(p.dx - tp.width - 2, p.dy - tp.height / 2);
      }
      tp.paint(canvas, textOffset);
    }
  }

  @override
  bool shouldRepaint(covariant _RadarPainter oldDelegate) => false;
}

// ---------------------------------------------------------------------------
// Diapositiva 2: 6 fichas de mercado con anillo de porcentaje cónico
// ---------------------------------------------------------------------------
class _Slide2Art extends StatelessWidget {
  const _Slide2Art();

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final items = [
      (l10n.welcomeMarket1, 61, const Color(0xFFFF8A3D)),
      (l10n.welcomeMarket2, 82, const Color(0xFFA78BFA)),
      (l10n.welcomeMarket3, 79, const Color(0xFFC6F432)),
      (l10n.welcomeMarket4, 58, const Color(0xFF4C9DFF)),
      (l10n.welcomeMarket5, 54, const Color(0xFF2BD99F)),
      (l10n.welcomeMarket6, 59, const Color(0xFFFFB020)),
    ];

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 10),
      child: GridView.count(
        shrinkWrap: true,
        physics: const NeverScrollableScrollPhysics(),
        crossAxisCount: 2,
        mainAxisSpacing: 8,
        crossAxisSpacing: 8,
        childAspectRatio: 2.4,
        children: items.map((item) {
          final label = item.$1;
          final pct = item.$2;
          final color = item.$3;
          return Container(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 6),
            decoration: BoxDecoration(
              color: const Color(0xFF10151F),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: color.withValues(alpha: 0.4), width: 1),
            ),
            child: Row(
              children: [
                // Anillo de porcentaje cónico
                SizedBox(
                  width: 36,
                  height: 36,
                  child: CustomPaint(
                    painter: _ConicRingPainter(pct: pct, color: color),
                    child: Center(
                      child: Text(
                        '$pct',
                        style: const TextStyle(
                          fontFamily: qfMono,
                          fontWeight: FontWeight.w700,
                          fontSize: 10,
                          color: QfColors.text,
                        ),
                      ),
                    ),
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    label.toUpperCase(),
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                      fontFamily: qfDisplay,
                      fontWeight: FontWeight.w700,
                      fontSize: 10.5,
                      height: 1.15,
                      letterSpacing: 0.6,
                      color: QfColors.text,
                    ),
                  ),
                ),
              ],
            ),
          );
        }).toList(),
      ),
    );
  }
}

class _ConicRingPainter extends CustomPainter {
  const _ConicRingPainter({required this.pct, required this.color});

  final int pct;
  final Color color;

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);
    final radius = size.width / 2;
    const strokeWidth = 3.6;

    // Fondo gris del anillo
    final trackPaint = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = strokeWidth
      ..color = Colors.white.withValues(alpha: 0.12);
    canvas.drawCircle(center, radius - strokeWidth / 2, trackPaint);

    // Arco activo
    final sweepAngle = (pct / 100) * 2 * math.pi;
    final arcPaint = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = strokeWidth
      ..strokeCap = StrokeCap.round
      ..color = color;
    canvas.drawArc(
      Rect.fromCircle(center: center, radius: radius - strokeWidth / 2),
      -math.pi / 2,
      sweepAngle,
      false,
      arcPaint,
    );
  }

  @override
  bool shouldRepaint(covariant _ConicRingPainter oldDelegate) =>
      oldDelegate.pct != pct || oldDelegate.color != color;
}

// ---------------------------------------------------------------------------
// Diapositiva 3: Anillo de acierto 76% + Historial con 3 partidos (✓ / ✗)
// ---------------------------------------------------------------------------
class _Slide3Art extends StatelessWidget {
  const _Slide3Art();

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 14),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          // Tarjeta superior: Anillo de acierto + números
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
            decoration: const ShapeDecoration(
              color: QfColors.surface,
              shape: CutCornerBorder(
                cut: 10,
                side: BorderSide(color: QfColors.borderStrong),
              ),
            ),
            child: Row(
              children: [
                // Anillo de acierto 76% (verde y magenta)
                SizedBox(
                  width: 58,
                  height: 58,
                  child: CustomPaint(
                    painter: const _HitRatePainter(pct: 76),
                    child: const Center(
                      child: Text(
                        '76%',
                        style: TextStyle(
                          fontFamily: qfMono,
                          fontWeight: FontWeight.w700,
                          fontSize: 14,
                          color: QfColors.text,
                        ),
                      ),
                    ),
                  ),
                ),
                const SizedBox(width: 14),
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      l10n.artRegisteredRate.toUpperCase(),
                      style: const TextStyle(
                        fontFamily: qfDisplay,
                        fontWeight: FontWeight.w700,
                        fontSize: 10.5,
                        letterSpacing: 1.2,
                        color: Color(0xFF939AB0),
                      ),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      '16 ${l10n.artWon}',
                      style: const TextStyle(
                        fontFamily: qfMono,
                        fontWeight: FontWeight.w700,
                        fontSize: 12,
                        color: QfColors.green,
                      ),
                    ),
                    Text(
                      '5 ${l10n.artLost}',
                      style: const TextStyle(
                        fontFamily: qfMono,
                        fontWeight: FontWeight.w700,
                        fontSize: 12,
                        color: QfColors.danger,
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
          const SizedBox(height: 8),
          // Tarjeta inferior: Historial con 3 partidos
          Container(
            decoration: const ShapeDecoration(
              color: QfColors.surface,
              shape: CutCornerBorder(
                cut: 8,
                side: BorderSide(color: QfColors.border),
              ),
            ),
            child: Column(
              children: [
                _historyRow(
                  match: l10n.welcomeHistoryMatch1,
                  status: l10n.artWon.toUpperCase(),
                  won: true,
                  borderBottom: true,
                ),
                _historyRow(
                  match: l10n.welcomeHistoryMatch2,
                  status: l10n.artWon.toUpperCase(),
                  won: true,
                  borderBottom: true,
                ),
                _historyRow(
                  match: l10n.welcomeHistoryMatch3,
                  status: l10n.artLost.toUpperCase(),
                  won: false,
                  borderBottom: false,
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _historyRow({
    required String match,
    required String status,
    required bool won,
    required bool borderBottom,
  }) {
    final color = won ? QfColors.green : QfColors.danger;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 7),
      decoration: BoxDecoration(
        border: borderBottom
            ? const Border(bottom: BorderSide(color: QfColors.divider))
            : null,
      ),
      child: Row(
        children: [
          Container(
            width: 22,
            height: 22,
            decoration: BoxDecoration(
              border: Border.all(color: color, width: 1.2),
              borderRadius: BorderRadius.circular(3),
            ),
            child: Icon(
              won ? Icons.check : Icons.close,
              size: 14,
              color: color,
            ),
          ),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              match,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(
                fontFamily: 'Exo 2',
                fontSize: 11.5,
                color: QfColors.text,
              ),
            ),
          ),
          const SizedBox(width: 6),
          Text(
            status,
            style: TextStyle(
              fontFamily: qfMono,
              fontWeight: FontWeight.w700,
              fontSize: 10.5,
              color: color,
            ),
          ),
        ],
      ),
    );
  }
}

class _HitRatePainter extends CustomPainter {
  const _HitRatePainter({required this.pct});

  final int pct;

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);
    final radius = size.width / 2;
    const strokeWidth = 5.0;

    // Porción fallada (magenta)
    final failPaint = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = strokeWidth
      ..color = QfColors.danger;
    canvas.drawCircle(center, radius - strokeWidth / 2, failPaint);

    // Porción ganada (verde)
    final sweepAngle = (pct / 100) * 2 * math.pi;
    final winPaint = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = strokeWidth
      ..color = QfColors.green;
    canvas.drawArc(
      Rect.fromCircle(center: center, radius: radius - strokeWidth / 2),
      -math.pi / 2,
      sweepAngle,
      false,
      winPaint,
    );
  }

  @override
  bool shouldRepaint(covariant _HitRatePainter oldDelegate) => oldDelegate.pct != pct;
}

// ---------------------------------------------------------------------------
// Diapositiva 4: Escudo con «NO ES UNA CERTEZA» y barra segmentada
// ---------------------------------------------------------------------------
class _Slide4Art extends StatelessWidget {
  const _Slide4Art();

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 20),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          // Icono escudo en caja de esquinas cortadas con resplandor cian
          Container(
            width: 74,
            height: 74,
            decoration: ShapeDecoration(
              color: QfColors.cyan.withValues(alpha: 0.08),
              shadows: [
                BoxShadow(
                  color: QfColors.cyan.withValues(alpha: 0.28),
                  blurRadius: 32,
                  spreadRadius: 2,
                ),
              ],
              shape: const CutCornerBorder(
                cut: 10,
                side: BorderSide(color: QfColors.borderStrong, width: 1.2),
              ),
            ),
            child: const Center(
              child: Icon(Icons.shield_outlined, size: 40, color: QfColors.cyan),
            ),
          ),
          const SizedBox(height: 14),
          // Tarjeta con probabilidad 62% y advertencia
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
            decoration: const ShapeDecoration(
              color: QfColors.surface,
              shape: CutCornerBorder(
                cut: 12,
                side: BorderSide(color: QfColors.border),
              ),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  crossAxisAlignment: CrossAxisAlignment.baseline,
                  textBaseline: TextBaseline.alphabetic,
                  children: [
                    const Text(
                      '62%',
                      style: TextStyle(
                        fontFamily: qfMono,
                        fontWeight: FontWeight.w700,
                        fontSize: 28,
                        color: QfColors.cyan,
                      ),
                    ),
                    Text(
                      l10n.artProbability.toUpperCase(),
                      style: const TextStyle(
                        fontFamily: qfDisplay,
                        fontWeight: FontWeight.w700,
                        fontSize: 10.5,
                        letterSpacing: 1.4,
                        color: Color(0xFF939AB0),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                // 10 segmentos (6 llenos, 4 contorno)
                SizedBox(
                  height: 9,
                  child: Row(
                    children: List.generate(10, (i) {
                      final filled = i < 6;
                      return Expanded(
                        child: Container(
                          margin: EdgeInsets.only(right: i < 9 ? 3 : 0),
                          decoration: BoxDecoration(
                            color: filled ? QfColors.cyan : Colors.transparent,
                            border: filled
                                ? null
                                : Border.all(color: QfColors.slate, width: 1),
                            borderRadius: BorderRadius.circular(1),
                          ),
                        ),
                      );
                    }),
                  ),
                ),
                const SizedBox(height: 10),
                Text(
                  l10n.artNotCertainty.toUpperCase(),
                  style: const TextStyle(
                    fontFamily: qfDisplay,
                    fontWeight: FontWeight.w700,
                    fontSize: 11.5,
                    letterSpacing: 1.2,
                    color: QfColors.yellow,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
