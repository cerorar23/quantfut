import 'package:flutter/material.dart';

import '../l10n/app_locale.dart';
import 'live_api.dart' show realPercent;
import 'qf_theme.dart';

/// Rectángulo con esquinas cortadas arriba-derecha y abajo-izquierda (hexágono
/// de 6 puntos), la silueta de la piel v3.
class CutCornerBorder extends OutlinedBorder {
  const CutCornerBorder({this.cut = 12, super.side = BorderSide.none});

  final double cut;

  Path _path(Rect r) {
    final c = cut.clamp(0.0, r.shortestSide / 2).toDouble();
    return Path()
      ..moveTo(r.left, r.top)
      ..lineTo(r.right - c, r.top)
      ..lineTo(r.right, r.top + c)
      ..lineTo(r.right, r.bottom)
      ..lineTo(r.left + c, r.bottom)
      ..lineTo(r.left, r.bottom - c)
      ..close();
  }

  @override
  EdgeInsetsGeometry get dimensions => EdgeInsets.all(side.width);

  @override
  Path getInnerPath(Rect rect, {TextDirection? textDirection}) =>
      _path(rect.deflate(side.width));

  @override
  Path getOuterPath(Rect rect, {TextDirection? textDirection}) => _path(rect);

  @override
  void paint(Canvas canvas, Rect rect, {TextDirection? textDirection}) {
    if (side.style == BorderStyle.none || side.width == 0) return;
    canvas.drawPath(
      _path(rect.deflate(side.width / 2)),
      side.toPaint()..strokeJoin = StrokeJoin.miter,
    );
  }

  @override
  CutCornerBorder copyWith({BorderSide? side, double? cut}) =>
      CutCornerBorder(cut: cut ?? this.cut, side: side ?? this.side);

  @override
  ShapeBorder scale(double t) => CutCornerBorder(cut: cut * t, side: side.scale(t));
}

/// Tarjeta con corte de 12 dp; con `accent`, corchetes de 16×2 dp en las
/// esquinas intactas. Pulsable (mínimo 44 dp) si recibe `onTap`.
class QfCard extends StatelessWidget {
  const QfCard({
    super.key,
    required this.child,
    this.accent,
    this.onTap,
    this.padding = const EdgeInsets.all(12),
  });

  final Widget child;
  final Color? accent;
  final VoidCallback? onTap;
  final EdgeInsets padding;

  @override
  Widget build(BuildContext context) {
    const shape = CutCornerBorder(side: BorderSide(color: QfColors.border));
    Widget body = Padding(
      padding: padding,
      child: ConstrainedBox(
        constraints: const BoxConstraints(minHeight: 44),
        child: child,
      ),
    );
    if (onTap != null) {
      body = InkWell(customBorder: shape, onTap: onTap, child: body);
    }
    return Stack(
      children: [
        Material(
          color: QfColors.surface,
          shape: shape,
          clipBehavior: Clip.antiAlias,
          child: SizedBox(width: double.infinity, child: body),
        ),
        if (accent != null)
          Positioned.fill(
            child: IgnorePointer(child: CustomPaint(painter: _BracketPainter(accent!))),
          ),
      ],
    );
  }
}

/// Corchetes en las esquinas arriba-izquierda y abajo-derecha.
class _BracketPainter extends CustomPainter {
  const _BracketPainter(this.color);
  final Color color;

  @override
  void paint(Canvas canvas, Size size) {
    const len = 16.0, w = 2.0, h = w / 2;
    final p = Paint()
      ..color = color
      ..strokeWidth = w
      ..style = PaintingStyle.stroke;
    canvas.drawPath(
      Path()
        ..moveTo(h, len)
        ..lineTo(h, h)
        ..lineTo(len, h),
      p,
    );
    canvas.drawPath(
      Path()
        ..moveTo(size.width - h, size.height - len)
        ..lineTo(size.width - h, size.height - h)
        ..lineTo(size.width - len, size.height - h),
      p,
    );
  }

  @override
  bool shouldRepaint(_BracketPainter old) => old.color != color;
}

/// Insignia en mayúsculas (Rajdhani), borde de 1 dp y relleno al 13 %.
class QfBadge extends StatelessWidget {
  const QfBadge(this.label, {super.key, required this.color, this.icon});

  final String label;
  final Color color;
  final IconData? icon;

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: ShapeDecoration(
        color: color.withValues(alpha: .13),
        shape: CutCornerBorder(cut: 8, side: BorderSide(color: color)),
      ),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            if (icon != null) ...[Icon(icon, size: 14, color: color), const SizedBox(width: 4)],
            Text(
              label.toUpperCase(),
              style: TextStyle(
                fontFamily: qfDisplay,
                fontWeight: FontWeight.w700,
                fontSize: 12,
                letterSpacing: .8,
                color: color,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// `total` segmentos, los `filled` primeros en `color`; `current` (opcional)
/// marca el segmento en curso con borde.
class SegmentedBar extends StatelessWidget {
  const SegmentedBar({
    super.key,
    required this.total,
    required this.filled,
    this.color = QfColors.primary,
    this.current,
  });

  final int total, filled;
  final Color color;
  final int? current;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      label: '$filled/$total',
      excludeSemantics: true,
      child: Row(
        children: [
          for (var i = 0; i < total; i++) ...[
            if (i > 0) const SizedBox(width: 3),
            Expanded(
              child: DecoratedBox(
                key: const ValueKey('qf-segment'),
                decoration: BoxDecoration(
                  color: i < filled ? color : QfColors.surface2,
                  border: i == current ? Border.all(color: color) : null,
                ),
                child: const SizedBox(height: 8),
              ),
            ),
          ],
        ],
      ),
    );
  }
}

/// Barra de 2 o 3 partes (la mayor en `primary`, el resto en tonos neutros)
/// con leyenda mono «ETIQ nn %».
class ProbabilityBar extends StatelessWidget {
  // ignore: prefer_const_constructors_in_immutables  (el assert mira la longitud: no es const)
  ProbabilityBar({super.key, required this.parts})
    : assert(parts.length == 2 || parts.length == 3, 'ProbabilityBar admite 2 o 3 partes');

  final List<(String label, double value)> parts;

  @override
  Widget build(BuildContext context) {
    var top = 0;
    for (var i = 1; i < parts.length; i++) {
      if (parts[i].$2 > parts[top].$2) top = i;
    }
    const neutral = [QfColors.text2, QfColors.muted];
    var n = 0;
    final colors = [
      for (var i = 0; i < parts.length; i++) i == top ? QfColors.primary : neutral[n++ % 2],
    ];
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            for (var i = 0; i < parts.length; i++) ...[
              if (i > 0) const SizedBox(width: 2),
              Expanded(
                flex: (parts[i].$2 * 1000).round().clamp(1, 1000),
                child: DecoratedBox(
                  decoration: BoxDecoration(color: colors[i]),
                  child: const SizedBox(height: 8),
                ),
              ),
            ],
          ],
        ),
        const SizedBox(height: 4),
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            for (var i = 0; i < parts.length; i++)
              Text(
                '${parts[i].$1} ${realPercent(parts[i].$2)}',
                style: TextStyle(
                  fontFamily: qfMono,
                  fontSize: 12,
                  color: i == top ? QfColors.text : QfColors.text2,
                ),
              ),
          ],
        ),
      ],
    );
  }
}

/// Dos líneas de protocolo: sello acortado y hora de publicación (UTC).
class SealLine extends StatelessWidget {
  const SealLine({super.key, required this.seal, required this.publishedAt});

  final String seal;
  final DateTime publishedAt;

  String get _short =>
      seal.length <= 9 ? seal : '${seal.substring(0, 4)}…${seal.substring(seal.length - 4)}';

  @override
  Widget build(BuildContext context) {
    final l = context.l10n;
    final u = publishedAt.toUtc();
    String two(int v) => v.toString().padLeft(2, '0');
    const style = TextStyle(fontFamily: qfMono, fontSize: 11, color: QfColors.muted);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text('> ${l.sealLabel} $_short', style: style),
        Text(
          '> ${l.sealPublished} ${two(u.hour)}:${two(u.minute)} UTC · ${l.sealVerified}',
          style: style,
        ),
      ],
    );
  }
}
