import 'package:flutter/material.dart';

import '../l10n/app_locale.dart';
import 'live_api.dart' show realPercent;
import 'qf_theme.dart';

/// Rectángulo con esquinas cortadas arriba-derecha y abajo-izquierda (hexágono
/// de 6 puntos), silueta del sistema CyberCore (10 dp o 16 dp).
class CutCornerBorder extends OutlinedBorder {
  const CutCornerBorder({
    this.cut = 10,
    BorderSide? border,
    BorderSide side = BorderSide.none,
  }) : super(side: border ?? side);

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

/// Forma para hojas inferiores CyberCore: esquinas cortadas arriba-izquierda y arriba-derecha.
class BottomSheetCutShape extends ShapeBorder {
  const BottomSheetCutShape({this.cut = 18, this.side = BorderSide.none});

  final double cut;
  final BorderSide side;

  @override
  EdgeInsetsGeometry get dimensions => EdgeInsets.only(top: side.width);

  @override
  Path getInnerPath(Rect rect, {TextDirection? textDirection}) =>
      getOuterPath(rect.deflate(side.width));

  @override
  Path getOuterPath(Rect rect, {TextDirection? textDirection}) {
    final c = cut.clamp(0.0, rect.shortestSide / 2).toDouble();
    return Path()
      ..moveTo(rect.left, rect.bottom)
      ..lineTo(rect.left, rect.top + c)
      ..lineTo(rect.left + c, rect.top)
      ..lineTo(rect.right - c, rect.top)
      ..lineTo(rect.right, rect.top + c)
      ..lineTo(rect.right, rect.bottom)
      ..close();
  }

  @override
  void paint(Canvas canvas, Rect rect, {TextDirection? textDirection}) {
    if (side.style == BorderStyle.none || side.width == 0) return;
    final paint = side.toPaint()..style = PaintingStyle.stroke;
    final c = cut.clamp(0.0, rect.shortestSide / 2).toDouble();
    final path = Path()
      ..moveTo(rect.left, rect.top + c)
      ..lineTo(rect.left + c, rect.top)
      ..lineTo(rect.right - c, rect.top)
      ..lineTo(rect.right, rect.top + c);
    canvas.drawPath(path, paint);
  }

  @override
  ShapeBorder scale(double t) => BottomSheetCutShape(cut: cut * t, side: side.scale(t));
}

/// Líneas de barrido estáticas (scanlines) CyberCore (1 línea cada 4 dp en cyan al 3 %).
class ScanlinesPainter extends CustomPainter {
  const ScanlinesPainter({this.lineColor});
  final Color? lineColor;

  @override
  void paint(Canvas canvas, Size size) {
    final p = Paint()
      ..color = lineColor ?? QfColors.cyan.withValues(alpha: .03)
      ..strokeWidth = 1.0;
    for (double y = 0; y < size.height; y += 4.0) {
      canvas.drawLine(Offset(0, y), Offset(size.width, y), p);
    }
  }

  @override
  bool shouldRepaint(ScanlinesPainter old) => old.lineColor != lineColor;
}

/// Tarjeta CyberCore con corte 10 o 16 dp; con `strong`, activa borde fuerte (48 %)
/// y líneas de barrido; con `glow`, añade brillo exterior cian.
class QfCard extends StatelessWidget {
  const QfCard({
    super.key,
    required this.child,
    this.cut = 10,
    this.strong = false,
    this.glow = false,
    this.accent,
    this.borderColor,
    this.backgroundColor,
    this.onTap,
    this.padding = const EdgeInsets.all(14),
  });

  final Widget child;
  final double cut;
  final bool strong;
  final bool glow;
  final Color? accent;
  final Color? borderColor;
  final Color? backgroundColor;
  final VoidCallback? onTap;
  final EdgeInsets padding;

  @override
  Widget build(BuildContext context) {
    final border = borderColor ?? (strong ? QfColors.borderStrong : QfColors.border);
    final shape = CutCornerBorder(cut: cut, side: BorderSide(color: border));

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

    Widget content = Stack(
      children: [
        if (strong)
          const Positioned.fill(
            child: IgnorePointer(
              child: RepaintBoundary(child: CustomPaint(painter: ScanlinesPainter())),
            ),
          ),
        body,
        if (accent != null)
          Positioned.fill(
            child: IgnorePointer(
              child: CustomPaint(painter: _BracketPainter(accent!)),
            ),
          ),
      ],
    );

    Widget card = Material(
      color: backgroundColor ?? QfColors.surface,
      shape: shape,
      clipBehavior: Clip.antiAlias,
      child: SizedBox(width: double.infinity, child: content),
    );

    if (glow) {
      return Container(
        decoration: BoxDecoration(
          boxShadow: [
            BoxShadow(
              color: QfColors.cyan.withValues(alpha: .14),
              blurRadius: 22,
              spreadRadius: 0,
            ),
          ],
        ),
        child: card,
      );
    }

    return card;
  }
}

/// Corchetes en las esquinas intactas (arriba-izquierda y abajo-derecha).
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

/// Tipos de insignia semántica CyberCore (§4 y §3.1).
enum QfBadgeKind {
  free,
  won,
  vip,
  lost,
  live,
  review,
  voided,
  doubt,
}

/// Insignia en mayúsculas (Rajdhani 700), corte 8 dp, borde de 1 dp y fondo tenue (9-13 %).
class QfBadge extends StatelessWidget {
  const QfBadge(
    this.label, {
    super.key,
    required this.color,
    this.icon,
  }) : kind = null;

  const QfBadge.kind(
    this.kind, {
    super.key,
    this.label = '',
    this.icon,
  }) : color = null;

  final String label;
  final Color? color;
  final IconData? icon;
  final QfBadgeKind? kind;

  @override
  Widget build(BuildContext context) {
    Color effectiveColor;
    String effectiveLabel;
    IconData? effectiveIcon = icon;

    if (kind != null) {
      switch (kind!) {
        case QfBadgeKind.free:
          effectiveColor = QfColors.green;
          effectiveLabel = label.isNotEmpty ? label : 'GRATIS';
        case QfBadgeKind.won:
          effectiveColor = QfColors.green;
          effectiveLabel = label.isNotEmpty ? label : 'ACERTADO';
          effectiveIcon ??= Icons.check_rounded;
        case QfBadgeKind.vip:
          effectiveColor = QfColors.yellow;
          effectiveLabel = label.isNotEmpty ? label : 'VIP';
          effectiveIcon ??= Icons.lock_outline_rounded;
        case QfBadgeKind.lost:
          effectiveColor = QfColors.magenta;
          effectiveLabel = label.isNotEmpty ? label : 'FALLADO';
          effectiveIcon ??= Icons.close_rounded;
        case QfBadgeKind.live:
          effectiveColor = QfColors.magenta;
          effectiveLabel = label.isNotEmpty ? label : 'EN VIVO';
          effectiveIcon ??= Icons.circle;
        case QfBadgeKind.review:
          effectiveColor = QfColors.slate;
          effectiveLabel = label.isNotEmpty ? label : 'REVISION';
        case QfBadgeKind.voided:
          effectiveColor = QfColors.slate;
          effectiveLabel = label.isNotEmpty ? label : 'ANULADO';
        case QfBadgeKind.doubt:
          effectiveColor = QfColors.yellow;
          effectiveLabel = label.isNotEmpty ? label : 'DUDA';
      }
    } else {
      effectiveColor = color ?? QfColors.cyan;
      effectiveLabel = label;
    }

    return DecoratedBox(
      decoration: ShapeDecoration(
        color: effectiveColor.withValues(alpha: .09),
        shape: CutCornerBorder(
          cut: 8,
          side: BorderSide(color: effectiveColor.withValues(alpha: .40)),
        ),
      ),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            if (effectiveIcon != null) ...[
              Icon(effectiveIcon, size: 12, color: effectiveColor),
              const SizedBox(width: 4),
            ],
            Text(
              effectiveLabel.toUpperCase(),
              style: TextStyle(
                fontFamily: qfDisplay,
                fontWeight: FontWeight.w700,
                fontSize: 11,
                letterSpacing: 1.32,
                color: effectiveColor,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// Título de sección (Rajdhani 700 en mayúsculas).
Widget qfTitle(String text, {double size = 15, Color color = QfColors.text}) => Padding(
  padding: const EdgeInsets.only(top: 16, bottom: 4),
  child: Text(
    text.toUpperCase(),
    style: TextStyle(
      fontFamily: qfDisplay,
      fontWeight: FontWeight.w700,
      fontSize: size,
      letterSpacing: .9,
      color: color,
    ),
  ),
);

/// Diálogo con corte de esquinas y estilo CyberCore.
Widget qfAlert({
  required String title,
  required Widget content,
  required List<Widget> actions,
  IconData? icon,
  Color iconColor = QfColors.cyan,
}) => AlertDialog(
  backgroundColor: QfColors.surface2,
  shape: const CutCornerBorder(side: BorderSide(color: QfColors.border)),
  icon: icon == null ? null : Icon(icon, color: iconColor),
  title: Text(
    title.toUpperCase(),
    style: const TextStyle(
      fontFamily: qfDisplay,
      fontWeight: FontWeight.w700,
      fontSize: 20,
      letterSpacing: .6,
      color: QfColors.text,
    ),
  ),
  content: DefaultTextStyle.merge(
    style: const TextStyle(color: QfColors.text2, height: 1.4),
    child: content,
  ),
  actions: actions,
);

/// Botón relleno de compatibilidad durante la migración progresiva.
ButtonStyle qfFilled(Color color) => FilledButton.styleFrom(
  backgroundColor: color,
  foregroundColor: color == QfColors.yellow ? QfColors.onYellow : (color == QfColors.green ? QfColors.onGreen : Colors.white),
  minimumSize: const Size(64, 44),
  shape: const CutCornerBorder(cut: 8),
  textStyle: const TextStyle(fontFamily: qfDisplay, fontWeight: FontWeight.w700, fontSize: 15, letterSpacing: .6),
);

/// Botón de texto cian con 44 dp de alto.
ButtonStyle qfText() => TextButton.styleFrom(
  foregroundColor: QfColors.cyan,
  minimumSize: const Size(64, 44),
);

/// Barra superior (fondo `bg`, título en Rajdhani).
AppBar qfAppBar(String title) => AppBar(
  backgroundColor: QfColors.bg,
  foregroundColor: QfColors.text,
  title: Text(
    title,
    style: const TextStyle(fontFamily: qfDisplay, fontWeight: FontWeight.w700, fontSize: 21),
  ),
);

/// Etiqueta de sección CyberCore con prefijo "// " (Rajdhani 11 / 700 / color cian).
Widget qfSectionTag(String text) {
  final clean = text.startsWith('//') ? text : '// $text';
  return Text(
    clean.toUpperCase(),
    style: QfText.sectionTag,
  );
}

/// Mensaje de error: icono y texto en magenta (el color nunca va solo).
Widget qfError(String message) => Row(
  crossAxisAlignment: CrossAxisAlignment.start,
  children: [
    const Icon(Icons.error_outline, size: 16, color: QfColors.magenta),
    const SizedBox(width: 6),
    Expanded(
      child: Text(
        message,
        style: const TextStyle(
          fontFamily: qfBody,
          fontSize: 13,
          color: QfColors.magentaText,
        ),
      ),
    ),
  ],
);

/// `total` segmentos, los `filled` primeros en `color`; `current` (opcional)
/// marca el segmento en curso con borde.
class SegmentedBar extends StatelessWidget {
  const SegmentedBar({
    super.key,
    required this.total,
    required this.filled,
    this.color = QfColors.cyan,
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
                  border: i == current ? Border.all(color: color, width: 1.5) : null,
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

/// Barra de 2 o 3 partes (la mayor en `cyan`, el resto en `chrome`/`slate`)
/// con leyenda mono «ETIQ nn %».
class ProbabilityBar extends StatelessWidget {
  // ignore: prefer_const_constructors_in_immutables
  ProbabilityBar({super.key, required this.parts})
    : assert(parts.length == 2 || parts.length == 3, 'ProbabilityBar admite 2 o 3 partes');

  final List<(String label, double value)> parts;

  @override
  Widget build(BuildContext context) {
    var top = 0;
    for (var i = 1; i < parts.length; i++) {
      if (parts[i].$2 > parts[top].$2) top = i;
    }
    const neutral = [QfColors.chrome, QfColors.slate];
    var n = 0;
    final colors = [
      for (var i = 0; i < parts.length; i++) i == top ? QfColors.cyan : neutral[n++ % 2],
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
                  fontWeight: FontWeight.w700,
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
