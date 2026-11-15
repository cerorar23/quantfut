import 'package:flutter/material.dart';

import '../l10n/app_locale.dart';
import 'qf_shapes.dart';
import 'qf_theme.dart';
import 'sports.dart';

/// Tarjeta «Destacado del día» CyberCore:
/// - Tarjeta fuerte: `QfCard(cut: 16, strong: true, glow: true)`
/// - Encabezado: etiqueta verde «DESTACADO DEL DÍA» + meta «liga · día hora» (o título)
/// - Fila de equipos: dos escudos/fotos de 58 dp con nombre, probabilidad central (42 px mono cian con brillo) y texto del pick
/// - Barra de 2–3 partes (cian / slate / chrome) y leyenda
/// - Botón verde: «VER PRONÓSTICO GRATIS» con icono chevron
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
    this.meta,
    this.homeName,
    this.awayName,
    this.probabilities,
    this.onTap,
  });

  final SportId sport;

  /// Avatares de 58–66 dp (local y visitante).
  final Widget left, right;
  final String probability, pick, kicker;

  /// Enfrentamiento o meta, por ejemplo «Knicks · Heat» o «LALIGA 2 · SÁB 17:30».
  final String? title;
  final String? meta;
  final String? homeName;
  final String? awayName;

  /// Probabilidades 1X2 o 2 vías para la barra y leyenda.
  final List<(String, double)>? probabilities;

  final VoidCallback? onTap;

  int _parseProb(String prob) {
    final match = RegExp(r'(\d+)').firstMatch(prob);
    if (match != null) {
      return int.tryParse(match.group(1)!) ?? 50;
    }
    return 50;
  }

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final subtitle = meta ?? title;

    // Equipos/jugadores a partir de homeName/awayName o title
    String? local = homeName;
    String? visitor = awayName;
    if ((local == null || visitor == null) && title != null) {
      final parts = title!.split(RegExp(r'\s*·\s*|\s*@\s*|\s*–\s*|\s*-\s*'));
      if (parts.length >= 2) {
        local ??= parts[0].trim();
        visitor ??= parts[1].trim();
      }
    }

    final pVal = _parseProb(probability);
    final hasMultiProb = probabilities != null && probabilities!.isNotEmpty;

    return Semantics(
      button: onTap != null,
      label: '$kicker. ${title ?? ''}. $pick $probability',
      excludeSemantics: true,
      child: QfCard(
        cut: 16,
        strong: true,
        glow: true,
        padding: const EdgeInsets.all(14),
        onTap: onTap,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          mainAxisSize: MainAxisSize.min,
          children: [
            // Encabezado: Kicker verde + Meta/Título
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Expanded(
                  child: Text(
                    kicker.toUpperCase(),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                      fontFamily: qfDisplay,
                      fontWeight: FontWeight.w700,
                      fontSize: 12,
                      letterSpacing: 1.6,
                      color: QfColors.green,
                    ),
                  ),
                ),
                if (subtitle != null) ...[
                  const SizedBox(width: 8),
                  Flexible(
                    child: Text(
                      subtitle.toUpperCase(),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      textAlign: TextAlign.end,
                      style: const TextStyle(
                        fontFamily: qfMono,
                        fontWeight: FontWeight.w500,
                        fontSize: 11,
                        color: QfColors.muted,
                      ),
                    ),
                  ),
                ],
              ],
            ),
            const SizedBox(height: 12),

            // Fila central: Avatar local + Probabilidad/Pick al centro + Avatar visitante
            Row(
              children: [
                Expanded(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      SizedBox(
                        width: 58,
                        height: 58,
                        child: FittedBox(
                          fit: BoxFit.contain,
                          child: left,
                        ),
                      ),
                      if (local != null && local.isNotEmpty) ...[
                        const SizedBox(height: 6),
                        Text(
                          local,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          textAlign: TextAlign.center,
                          style: const TextStyle(
                            fontWeight: FontWeight.w700,
                            fontSize: 14,
                            color: QfColors.text,
                          ),
                        ),
                      ],
                    ],
                  ),
                ),
                Expanded(
                  flex: 2,
                  child: Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 6),
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
                              fontWeight: FontWeight.w700,
                              fontSize: 40,
                              height: 1.0,
                              color: QfColors.cyan,
                              shadows: [
                                Shadow(
                                  color: Color(0x7300F0FF),
                                  blurRadius: 18,
                                ),
                              ],
                            ),
                          ),
                        ),
                        const SizedBox(height: 6),
                        Text(
                          pick.toUpperCase(),
                          maxLines: 2,
                          textAlign: TextAlign.center,
                          overflow: TextOverflow.ellipsis,
                          style: const TextStyle(
                            fontFamily: qfDisplay,
                            fontWeight: FontWeight.w700,
                            fontSize: 12,
                            letterSpacing: 1.2,
                            color: QfColors.muted,
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
                Expanded(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      SizedBox(
                        width: 58,
                        height: 58,
                        child: FittedBox(
                          fit: BoxFit.contain,
                          child: right,
                        ),
                      ),
                      if (visitor != null && visitor.isNotEmpty) ...[
                        const SizedBox(height: 6),
                        Text(
                          visitor,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          textAlign: TextAlign.center,
                          style: const TextStyle(
                            fontWeight: FontWeight.w700,
                            fontSize: 14,
                            color: QfColors.text,
                          ),
                        ),
                      ],
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),

            // Barra de probabilidad de 2 o 3 partes
            if (hasMultiProb) ...[
              Row(
                children: [
                  for (var i = 0; i < probabilities!.length; i++) ...[
                    if (i > 0) const SizedBox(width: 3),
                    Expanded(
                      flex: (probabilities![i].$2 * 100).round().clamp(1, 100),
                      child: Container(
                        height: 6,
                        color: i == 0
                            ? QfColors.cyan
                            : (i == 1 && probabilities!.length == 3
                                ? QfColors.slate
                                : QfColors.chrome),
                      ),
                    ),
                  ],
                ],
              ),
              const SizedBox(height: 4),
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  for (final p in probabilities!)
                    Text(
                      '${p.$1} · ${(p.$2 * 100).round()}%',
                      style: const TextStyle(
                        fontFamily: qfMono,
                        fontWeight: FontWeight.w500,
                        fontSize: 11,
                        color: QfColors.muted,
                      ),
                    ),
                ],
              ),
            ] else ...[
              Row(
                children: [
                  Expanded(
                    flex: pVal.clamp(1, 99),
                    child: Container(height: 6, color: QfColors.cyan),
                  ),
                  const SizedBox(width: 3),
                  Expanded(
                    flex: (100 - pVal).clamp(1, 99),
                    child: Container(height: 6, color: QfColors.slate),
                  ),
                ],
              ),
              const SizedBox(height: 4),
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text(
                    '1 · $pVal%',
                    style: const TextStyle(
                      fontFamily: qfMono,
                      fontWeight: FontWeight.w500,
                      fontSize: 11,
                      color: QfColors.muted,
                    ),
                  ),
                  Text(
                    '2 · ${100 - pVal}%',
                    style: const TextStyle(
                      fontFamily: qfMono,
                      fontWeight: FontWeight.w500,
                      fontSize: 11,
                      color: QfColors.muted,
                    ),
                  ),
                ],
              ),
            ],
            const SizedBox(height: 12),

            // Botón verde «VER PRONÓSTICO GRATIS»
            Material(
              color: Colors.transparent,
              child: Ink(
                height: 48,
                decoration: const ShapeDecoration(
                  gradient: qfGreenGradient,
                  shape: CutCornerBorder(cut: 8),
                ),
                child: InkWell(
                  customBorder: const CutCornerBorder(cut: 8),
                  onTap: onTap,
                  child: Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 10),
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Flexible(
                          child: FittedBox(
                            fit: BoxFit.scaleDown,
                            child: Text(
                              l10n.homeViewFreePick.toUpperCase(),
                              maxLines: 1,
                              style: const TextStyle(
                                fontFamily: qfDisplay,
                                fontWeight: FontWeight.w700,
                                fontSize: 15,
                                letterSpacing: 1.0,
                                color: QfColors.onGreen,
                              ),
                            ),
                          ),
                        ),
                        const SizedBox(width: 6),
                        const Icon(
                          Icons.chevron_right,
                          size: 18,
                          color: QfColors.onGreen,
                        ),
                      ],
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

/// Líneas de la cancha (conservado por compatibilidad).
class CourtPainter extends CustomPainter {
  const CourtPainter(this.sport, this.color);

  final SportId sport;
  final Color color;

  @override
  void paint(Canvas canvas, Size size) {}

  @override
  bool shouldRepaint(CourtPainter old) =>
      old.sport != sport || old.color != color;
}
