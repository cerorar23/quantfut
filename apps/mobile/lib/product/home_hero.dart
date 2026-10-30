import 'package:flutter/material.dart';

import 'qf_shapes.dart';
import 'qf_theme.dart';
import 'sports.dart';

/// Tarjeta «Destacado del día»: cancha del deporte dibujada en su acento, los dos avatares
/// grandes y en el centro la probabilidad (azul) y el pick (verde). Sin imágenes con derechos:
/// la cancha se pinta en la app, como `welcome_art.dart`.
class HomeHero extends StatelessWidget {
  const HomeHero({
    super.key,
    required this.sport,
    required this.left,
    required this.right,
    required this.probability,
    required this.pick,
    required this.kicker,
    this.title,
    this.onTap,
  });

  final SportKind sport;

  /// Avatares de 66 dp (local y visitante).
  final Widget left, right;
  final String probability, pick, kicker;

  /// Enfrentamiento, por ejemplo «Knicks · Heat».
  final String? title;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final accent = sportSpecs[sport]!.accent;
    return Semantics(
      button: onTap != null,
      label: '$kicker. ${title ?? ''}. $pick $probability',
      excludeSemantics: true,
      child: QfCard(
        accent: accent,
        onTap: onTap,
        padding: EdgeInsets.zero,
        child: SizedBox(
          height: 176,
          child: Stack(
            children: [
              Positioned.fill(
                child: CustomPaint(
                  painter: CourtPainter(sport, accent.withValues(alpha: .22)),
                ),
              ),
              Padding(
                padding: const EdgeInsets.fromLTRB(16, 14, 16, 14),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    Text(
                      kicker.toUpperCase(),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(
                        fontFamily: qfDisplay,
                        fontWeight: FontWeight.w700,
                        fontSize: 13,
                        letterSpacing: 1.2,
                        color: accent,
                      ),
                    ),
                    if (title != null)
                      Text(
                        title!,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(color: QfColors.text2, fontSize: 12),
                      ),
                    const Spacer(),
                    Row(
                      children: [
                        left,
                        const SizedBox(width: 10),
                        Expanded(
                          child: Column(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              FittedBox(
                                fit: BoxFit.scaleDown,
                                child: Text(
                                  probability,
                                  maxLines: 1,
                                  style: const TextStyle(
                                    fontFamily: qfMono,
                                    fontWeight: FontWeight.w500,
                                    fontSize: 30,
                                    color: QfColors.primary,
                                  ),
                                ),
                              ),
                              const SizedBox(height: 4),
                              Text(
                                pick,
                                maxLines: 2,
                                textAlign: TextAlign.center,
                                overflow: TextOverflow.ellipsis,
                                style: const TextStyle(
                                  fontFamily: 'Gilroy Bold',
                                  fontSize: 13,
                                  color: QfColors.success,
                                ),
                              ),
                            ],
                          ),
                        ),
                        const SizedBox(width: 10),
                        right,
                      ],
                    ),
                    const Spacer(),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

/// Líneas de la cancha (vista cenital horizontal): campo, pista NBA o pista de tenis.
class CourtPainter extends CustomPainter {
  const CourtPainter(this.sport, this.color);

  final SportKind sport;
  final Color color;

  @override
  void paint(Canvas canvas, Size size) {
    final p = Paint()
      ..color = color
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1.5;
    final r = Rect.fromLTWH(10, 10, size.width - 20, size.height - 20);
    if (r.width <= 0 || r.height <= 0) return;
    canvas.drawRect(r, p);
    final c = r.center;
    switch (sport) {
      case SportKind.football:
        canvas.drawLine(Offset(c.dx, r.top), Offset(c.dx, r.bottom), p);
        canvas.drawCircle(c, r.height * .2, p);
        for (final left in [true, false]) {
          final x = left ? r.left : r.right;
          final dir = left ? 1.0 : -1.0;
          final box = r.height * .6, small = r.height * .28;
          canvas.drawRect(
            Rect.fromLTWH(left ? x : x - r.width * .13, c.dy - box / 2, r.width * .13, box),
            p,
          );
          canvas.drawRect(
            Rect.fromLTWH(left ? x : x - r.width * .05, c.dy - small / 2, r.width * .05, small),
            p,
          );
          canvas.drawCircle(Offset(x + dir * r.width * .1, c.dy), 1.5, p);
        }
      case SportKind.nba:
        canvas.drawLine(Offset(c.dx, r.top), Offset(c.dx, r.bottom), p);
        canvas.drawCircle(c, r.height * .16, p);
        for (final left in [true, false]) {
          final x = left ? r.left : r.right;
          final lane = r.height * .34, depth = r.width * .18;
          canvas.drawRect(
            Rect.fromLTWH(left ? x : x - depth, c.dy - lane / 2, depth, lane),
            p,
          );
          final arc = Rect.fromCircle(
            center: Offset(x, c.dy),
            radius: r.height * .44,
          );
          canvas.drawArc(arc, left ? -1.4 : 1.74, 2.8, false, p);
        }
      case SportKind.tennis:
        final alley = r.height * .12;
        canvas.drawLine(Offset(r.left, r.top + alley), Offset(r.right, r.top + alley), p);
        canvas.drawLine(Offset(r.left, r.bottom - alley), Offset(r.right, r.bottom - alley), p);
        canvas.drawLine(Offset(c.dx, r.top), Offset(c.dx, r.bottom), p..strokeWidth = 2.5);
        p.strokeWidth = 1.5;
        final service = r.width * .27;
        for (final x in [c.dx - service, c.dx + service]) {
          canvas.drawLine(Offset(x, r.top + alley), Offset(x, r.bottom - alley), p);
        }
        canvas.drawLine(Offset(c.dx - service, c.dy), Offset(c.dx + service, c.dy), p);
    }
  }

  @override
  bool shouldRepaint(CourtPainter old) => old.sport != sport || old.color != color;
}
