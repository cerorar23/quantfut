import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../l10n/app_locale.dart';
import 'qf_shapes.dart';
import 'qf_theme.dart';

/// Anillo de porcentaje CyberCore con cifra al centro (§4).
class QfRing extends StatelessWidget {
  const QfRing({
    super.key,
    required this.value,
    this.color = QfColors.cyan,
    this.trackColor,
    this.size = 54,
    this.stroke = 5,
    this.centerText,
    this.showPercent = true,
  });

  final double value; // 0.0 a 1.0
  final Color color;
  final Color? trackColor;
  final double size;
  final double stroke;
  final String? centerText;
  final bool showPercent;

  @override
  Widget build(BuildContext context) {
    final v = value.clamp(0.0, 1.0);
    final text = centerText ?? (showPercent ? '${(v * 100).round()}%' : '');

    return SizedBox(
      width: size,
      height: size,
      child: Stack(
        alignment: Alignment.center,
        children: [
          CustomPaint(
            size: Size(size, size),
            painter: _RingPainter(
              value: v,
              color: color,
              trackColor: trackColor ?? QfColors.track,
              stroke: stroke,
            ),
          ),
          if (text.isNotEmpty)
            Text(
              text,
              style: TextStyle(
                fontFamily: qfMono,
                fontWeight: FontWeight.w700,
                fontSize: size * 0.28,
                color: QfColors.text,
              ),
            ),
        ],
      ),
    );
  }
}

class _RingPainter extends CustomPainter {
  const _RingPainter({
    required this.value,
    required this.color,
    required this.trackColor,
    required this.stroke,
  });

  final double value;
  final Color color;
  final Color trackColor;
  final double stroke;

  @override
  void paint(Canvas canvas, Size size) {
    final rect = Rect.fromLTWH(
      stroke / 2,
      stroke / 2,
      size.width - stroke,
      size.height - stroke,
    );

    final trackPaint = Paint()
      ..color = trackColor
      ..style = PaintingStyle.stroke
      ..strokeWidth = stroke;

    final progressPaint = Paint()
      ..color = color
      ..style = PaintingStyle.stroke
      ..strokeWidth = stroke
      ..strokeCap = StrokeCap.round;

    canvas.drawOval(rect, trackPaint);
    if (value > 0) {
      canvas.drawArc(
        rect,
        -math.pi / 2,
        2 * math.pi * value,
        false,
        progressPaint,
      );
    }
  }

  @override
  bool shouldRepaint(_RingPainter old) =>
      old.value != value ||
      old.color != color ||
      old.trackColor != trackColor ||
      old.stroke != stroke;
}

/// Gráfico de Radar de 5 ejes CyberCore con 2 polígonos y 4 anillos concéntricos (§4 y §5.9).
class QfRadar extends StatelessWidget {
  const QfRadar({
    super.key,
    required this.labels,
    required this.a,
    required this.b,
    this.size = 180,
    this.colorA = QfColors.cyan,
    this.colorB = QfColors.chrome,
  }) : assert(labels.length == 5, 'QfRadar requiere exactamente 5 etiquetas');

  final List<String> labels;
  final List<double> a; // Valores normalizados 0.0 a 1.0 (equipo local)
  final List<double> b; // Valores normalizados 0.0 a 1.0 (equipo rival)
  final double size;
  final Color colorA;
  final Color colorB;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: size,
      height: size,
      child: CustomPaint(
        size: Size(size, size),
        painter: _RadarPainter(
          labels: labels,
          a: a,
          b: b,
          colorA: colorA,
          colorB: colorB,
        ),
      ),
    );
  }
}

class _RadarPainter extends CustomPainter {
  const _RadarPainter({
    required this.labels,
    required this.a,
    required this.b,
    required this.colorA,
    required this.colorB,
  });

  final List<String> labels;
  final List<double> a;
  final List<double> b;
  final Color colorA;
  final Color colorB;

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);
    final radius = size.width / 2 - 24.0;
    const count = 5;
    const angleStep = 2 * math.pi / count;
    const startAngle = -math.pi / 2;

    // 4 anillos concéntricos
    final gridPaint = Paint()
      ..color = QfColors.slate.withValues(alpha: .22)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1.0;

    for (var ring = 1; ring <= 4; ring++) {
      final r = radius * (ring / 4);
      final ringPath = Path();
      for (var i = 0; i < count; i++) {
        final angle = startAngle + i * angleStep;
        final point = center + Offset(math.cos(angle) * r, math.sin(angle) * r);
        if (i == 0) {
          ringPath.moveTo(point.dx, point.dy);
        } else {
          ringPath.lineTo(point.dx, point.dy);
        }
      }
      ringPath.close();
      canvas.drawPath(ringPath, gridPaint);
    }

    // Ejes radiales
    for (var i = 0; i < count; i++) {
      final angle = startAngle + i * angleStep;
      final point = center + Offset(math.cos(angle) * radius, math.sin(angle) * radius);
      canvas.drawLine(center, point, gridPaint);
    }

    // Polígono B (rival - chrome)
    if (b.isNotEmpty) {
      final pathB = Path();
      for (var i = 0; i < count; i++) {
        final val = i < b.length ? b[i].clamp(0.08, 1.0) : 0.08;
        final r = radius * val;
        final angle = startAngle + i * angleStep;
        final p = center + Offset(math.cos(angle) * r, math.sin(angle) * r);
        if (i == 0) {
          pathB.moveTo(p.dx, p.dy);
        } else {
          pathB.lineTo(p.dx, p.dy);
        }
      }
      pathB.close();
      canvas.drawPath(
        pathB,
        Paint()
          ..color = colorB.withValues(alpha: .10)
          ..style = PaintingStyle.fill,
      );
      canvas.drawPath(
        pathB,
        Paint()
          ..color = colorB.withValues(alpha: .70)
          ..style = PaintingStyle.stroke
          ..strokeWidth = 1.5,
      );
    }

    // Polígono A (local - cyan relleno 26%)
    if (a.isNotEmpty) {
      final pathA = Path();
      for (var i = 0; i < count; i++) {
        final val = i < a.length ? a[i].clamp(0.08, 1.0) : 0.08;
        final r = radius * val;
        final angle = startAngle + i * angleStep;
        final p = center + Offset(math.cos(angle) * r, math.sin(angle) * r);
        if (i == 0) {
          pathA.moveTo(p.dx, p.dy);
        } else {
          pathA.lineTo(p.dx, p.dy);
        }
      }
      pathA.close();
      canvas.drawPath(
        pathA,
        Paint()
          ..color = colorA.withValues(alpha: .26)
          ..style = PaintingStyle.fill,
      );
      canvas.drawPath(
        pathA,
        Paint()
          ..color = colorA
          ..style = PaintingStyle.stroke
          ..strokeWidth = 2.0,
      );
    }

    // Etiquetas de los ejes
    final textPainter = TextPainter(textDirection: TextDirection.ltr);
    for (var i = 0; i < count; i++) {
      final angle = startAngle + i * angleStep;
      final labelPoint = center + Offset(math.cos(angle) * (radius + 14), math.sin(angle) * (radius + 14));
      textPainter.text = TextSpan(
        text: labels[i].toUpperCase(),
        style: const TextStyle(
          fontFamily: qfDisplay,
          fontWeight: FontWeight.w700,
          fontSize: 9.5,
          color: QfColors.muted,
          letterSpacing: .6,
        ),
      );
      textPainter.layout();
      textPainter.paint(
        canvas,
        labelPoint - Offset(textPainter.width / 2, textPainter.height / 2),
      );
    }
  }

  @override
  bool shouldRepaint(_RadarPainter old) => true;
}

/// Fila comparativa divergente: valor A (izq), etiqueta (centro), valor B (der) con barras centrales (§4).
class QfDivergingRow extends StatelessWidget {
  const QfDivergingRow({
    super.key,
    required this.label,
    required this.a,
    required this.b,
    this.lowerIsBetter = false,
    this.formatA,
    this.formatB,
    this.highlightA,
    this.highlightB,
  });

  final String label;
  final num? a;
  final num? b;
  final bool lowerIsBetter;
  final String? formatA;
  final String? formatB;
  final bool? highlightA;
  final bool? highlightB;

  @override
  Widget build(BuildContext context) {
    final valA = a?.toDouble() ?? 0.0;
    final valB = b?.toDouble() ?? 0.0;

    bool aWins;
    bool bWins;

    if (highlightA != null && highlightB != null) {
      aWins = highlightA!;
      bWins = highlightB!;
    } else if (a == null || b == null || a == b) {
      aWins = false;
      bWins = false;
    } else if (lowerIsBetter) {
      aWins = valA < valB;
      bWins = valB < valA;
    } else {
      aWins = valA > valB;
      bWins = valB > valA;
    }

    final maxVal = math.max(valA, valB);
    final normA = maxVal > 0 ? (valA / maxVal).clamp(0.0, 1.0) : 0.0;
    final normB = maxVal > 0 ? (valB / maxVal).clamp(0.0, 1.0) : 0.0;

    final strA = formatA ?? (a == null ? '—' : (a is int ? '$a' : a!.toStringAsFixed(1)));
    final strB = formatB ?? (b == null ? '—' : (b is int ? '$b' : b!.toStringAsFixed(1)));

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 5),
      child: Column(
        children: [
          Row(
            children: [
              SizedBox(
                width: 52,
                child: Text(
                  strA,
                  textAlign: TextAlign.left,
                  style: TextStyle(
                    fontFamily: qfMono,
                    fontSize: 13,
                    fontWeight: aWins ? FontWeight.w700 : FontWeight.w500,
                    color: aWins ? QfColors.cyan : (bWins ? QfColors.muted : QfColors.text),
                  ),
                ),
              ),
              Expanded(
                child: Text(
                  label.toUpperCase(),
                  textAlign: TextAlign.center,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    fontFamily: qfDisplay,
                    fontSize: 11,
                    fontWeight: FontWeight.w700,
                    letterSpacing: .6,
                    color: QfColors.muted,
                  ),
                ),
              ),
              SizedBox(
                width: 52,
                child: Text(
                  strB,
                  textAlign: TextAlign.right,
                  style: TextStyle(
                    fontFamily: qfMono,
                    fontSize: 13,
                    fontWeight: bWins ? FontWeight.w700 : FontWeight.w500,
                    color: bWins ? QfColors.chrome : (aWins ? QfColors.muted : QfColors.text),
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 3),
          Row(
            children: [
              Expanded(
                child: Directionality(
                  textDirection: TextDirection.rtl,
                  child: ClipRRect(
                    borderRadius: BorderRadius.circular(2),
                    child: Container(
                      height: 5,
                      color: QfColors.track,
                      child: FractionallySizedBox(
                        alignment: Alignment.centerRight,
                        widthFactor: normA,
                        child: Container(
                          color: aWins ? QfColors.cyan : QfColors.cyan.withValues(alpha: .35),
                        ),
                      ),
                    ),
                  ),
                ),
              ),
              Container(
                width: 2,
                height: 7,
                color: QfColors.slate,
                margin: const EdgeInsets.symmetric(horizontal: 4),
              ),
              Expanded(
                child: ClipRRect(
                  borderRadius: BorderRadius.circular(2),
                  child: Container(
                    height: 5,
                    color: QfColors.track,
                    child: FractionallySizedBox(
                      alignment: Alignment.centerLeft,
                      widthFactor: normB,
                      child: Container(
                        color: bWins ? QfColors.chrome : QfColors.chrome.withValues(alpha: .35),
                      ),
                    ),
                  ),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

/// N rombos comparativos y resumen de dominio («X mejor en N de M») (§4 y §5.9).
class QfDominanceDots extends StatelessWidget {
  const QfDominanceDots({
    super.key,
    required this.winners,
    required this.homeName,
    required this.awayName,
  });

  /// Lista donde 1 = gana local, -1 = gana rival, 0 = empate.
  final List<int> winners;
  final String homeName;
  final String awayName;

  @override
  Widget build(BuildContext context) {
    var homeWins = 0;
    var awayWins = 0;
    for (final w in winners) {
      if (w > 0) homeWins++;
      if (w < 0) awayWins++;
    }

    String summary;
    Color summaryColor;
    if (homeWins > awayWins) {
      summary = '$homeName mejor en $homeWins de ${winners.length}';
      summaryColor = QfColors.cyan;
    } else if (awayWins > homeWins) {
      summary = '$awayName mejor en $awayWins de ${winners.length}';
      summaryColor = QfColors.chrome;
    } else {
      summary = 'Equilibrio ($homeWins – $awayWins)';
      summaryColor = QfColors.text2;
    }

    return Column(
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            for (var i = 0; i < winners.length; i++) ...[
              if (i > 0) const SizedBox(width: 5),
              _Diamond(winner: winners[i]),
            ],
          ],
        ),
        const SizedBox(height: 6),
        Text(
          summary,
          style: TextStyle(
            fontFamily: qfDisplay,
            fontSize: 12,
            fontWeight: FontWeight.w700,
            letterSpacing: .5,
            color: summaryColor,
          ),
        ),
      ],
    );
  }
}

class _Diamond extends StatelessWidget {
  const _Diamond({required this.winner});
  final int winner;

  @override
  Widget build(BuildContext context) {
    Color c;
    if (winner > 0) {
      c = QfColors.cyan;
    } else if (winner < 0) {
      c = QfColors.chrome;
    } else {
      c = QfColors.slate.withValues(alpha: .4);
    }

    return Transform.rotate(
      angle: math.pi / 4,
      child: Container(
        width: 8,
        height: 8,
        color: c,
      ),
    );
  }
}

/// Resultado individual para píldoras de forma.
class QfFormResult {
  const QfFormResult({
    required this.result, // 'G', 'W', 'E', 'D', 'P', 'L'
    required this.score,
    required this.opponent,
    required this.isHome,
    this.isLast = false,
    this.opponentCrestUrl,
    this.venueLabel,
    this.tag,
  });

  final String result;
  final String score;
  final String opponent;
  final bool isHome;
  final bool isLast;
  final String? opponentCrestUrl;
  final String? venueLabel;
  final String? tag;
}

/// Fila de 5-6 píldoras de forma (G/E/P) con el último partido resaltado (§4).
class QfFormPills extends StatelessWidget {
  const QfFormPills({
    super.key,
    required this.results,
    this.expanded = false,
  });

  final List<QfFormResult> results;
  final bool expanded;

  @override
  Widget build(BuildContext context) {
    if (expanded) {
      return Row(
        children: [
          for (var i = 0; i < results.length; i++) ...[
            if (i > 0) const SizedBox(width: 6),
            Expanded(child: _FormPillWidget(result: results[i])),
          ],
        ],
      );
    }
    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          for (var i = 0; i < results.length; i++) ...[
            if (i > 0) const SizedBox(width: 6),
            _FormPillWidget(result: results[i]),
          ],
        ],
      ),
    );
  }
}

class _FormPillWidget extends StatelessWidget {
  const _FormPillWidget({required this.result});
  final QfFormResult result;

  @override
  Widget build(BuildContext context) {
    final letter = result.result.toUpperCase();
    Color color;
    if (letter == 'G' || letter == 'W') {
      color = QfColors.green;
    } else if (letter == 'E' || letter == 'D') {
      color = QfColors.slate;
    } else {
      color = QfColors.magenta;
    }

    final isDetailed = result.opponentCrestUrl != null || result.venueLabel != null;

    if (isDetailed) {
      final ln = context.l10n;
      final tagText = result.tag ?? (result.isLast ? ln.anLastMatch : '');
      return Container(
        padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 6),
        decoration: ShapeDecoration(
          color: color.withValues(alpha: .12),
          shape: CutCornerBorder(
            cut: 6,
            side: BorderSide(
              color: result.isLast ? QfColors.cyan : color.withValues(alpha: .35),
              width: result.isLast ? 2 : 1,
            ),
          ),
          shadows: result.isLast
              ? [
                  BoxShadow(
                    color: color.withValues(alpha: .3),
                    blurRadius: 10,
                  ),
                ]
              : null,
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            SizedBox(
              height: 12,
              child: tagText.isNotEmpty
                  ? Text(
                      tagText,
                      style: const TextStyle(
                        fontFamily: qfDisplay,
                        fontSize: 9,
                        fontWeight: FontWeight.w700,
                        color: QfColors.cyan,
                        letterSpacing: .8,
                      ),
                    )
                  : const SizedBox.shrink(),
            ),
            const SizedBox(height: 3),
            if (result.opponentCrestUrl != null && result.opponentCrestUrl!.isNotEmpty)
              Image.network(
                result.opponentCrestUrl!,
                width: 22,
                height: 22,
                fit: BoxFit.contain,
                errorBuilder: (_, _, _) => SizedBox(
                  width: 22,
                  height: 22,
                  child: Center(
                    child: Text(
                      result.opponent.isNotEmpty ? result.opponent.substring(0, 1) : '',
                      style: const TextStyle(
                        fontFamily: qfDisplay,
                        fontSize: 10,
                        fontWeight: FontWeight.w700,
                        color: QfColors.muted,
                      ),
                    ),
                  ),
                ),
              )
            else
              SizedBox(
                width: 22,
                height: 22,
                child: Center(
                  child: Text(
                    result.opponent.isNotEmpty ? result.opponent.substring(0, 1) : '',
                    style: const TextStyle(
                      fontFamily: qfDisplay,
                      fontSize: 10,
                      fontWeight: FontWeight.w700,
                      color: QfColors.muted,
                    ),
                  ),
                ),
              ),
            const SizedBox(height: 3),
            Text(
              letter,
              style: TextStyle(
                fontFamily: qfDisplay,
                fontSize: 12,
                fontWeight: FontWeight.w700,
                color: color,
              ),
            ),
            const SizedBox(height: 1),
            Text(
              result.score,
              style: const TextStyle(
                fontFamily: qfMono,
                fontSize: 12,
                fontWeight: FontWeight.w700,
                color: QfColors.text,
              ),
            ),
            const SizedBox(height: 1),
            Text(
              result.venueLabel ?? (result.isHome ? 'CASA' : 'FUERA'),
              style: const TextStyle(
                fontFamily: qfMono,
                fontSize: 10,
                fontWeight: FontWeight.w500,
                color: QfColors.muted,
              ),
            ),
          ],
        ),
      );
    }

    Widget pill = Container(
      width: 44,
      padding: const EdgeInsets.symmetric(vertical: 4),
      decoration: ShapeDecoration(
        color: color.withValues(alpha: .12),
        shape: CutCornerBorder(
          cut: 6,
          side: BorderSide(
            color: result.isLast ? QfColors.cyan : color.withValues(alpha: .4),
            width: result.isLast ? 2 : 1,
          ),
        ),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            letter,
            style: TextStyle(
              fontFamily: qfDisplay,
              fontSize: 13,
              fontWeight: FontWeight.w700,
              color: color,
            ),
          ),
          Text(
            result.score,
            style: const TextStyle(
              fontFamily: qfMono,
              fontSize: 9,
              color: QfColors.text2,
            ),
          ),
        ],
      ),
    );

    if (result.isLast) {
      return Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 1),
            decoration: BoxDecoration(
              color: QfColors.cyan.withValues(alpha: .18),
              borderRadius: BorderRadius.circular(3),
            ),
            child: const Text(
              'ULT',
              style: TextStyle(
                fontFamily: qfDisplay,
                fontSize: 8,
                fontWeight: FontWeight.w700,
                color: QfColors.cyan,
                letterSpacing: .5,
              ),
            ),
          ),
          const SizedBox(height: 2),
          pill,
        ],
      );
    }

    return pill;
  }
}

/// Barras de margen por partido para NBA (arriba verde = victoria, abajo magenta = derrota) (§4).
class QfMarginBars extends StatelessWidget {
  const QfMarginBars({
    super.key,
    required this.margins,
    this.height = 70,
  });

  final List<int> margins;
  final double height;

  @override
  Widget build(BuildContext context) {
    if (margins.isEmpty) return const SizedBox.shrink();

    final maxMargin = margins.map((m) => m.abs()).fold<int>(1, math.max);

    return SizedBox(
      height: height,
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [
          for (var i = 0; i < margins.length; i++) ...[
            if (i > 0) const SizedBox(width: 8),
            Expanded(
              child: _SingleMarginBar(
                margin: margins[i],
                maxMargin: maxMargin,
              ),
            ),
          ],
        ],
      ),
    );
  }
}

class _SingleMarginBar extends StatelessWidget {
  const _SingleMarginBar({
    required this.margin,
    required this.maxMargin,
  });

  final int margin;
  final int maxMargin;

  @override
  Widget build(BuildContext context) {
    final isWin = margin > 0;
    final color = isWin ? QfColors.green : QfColors.magenta;
    final ratio = (margin.abs() / maxMargin).clamp(0.1, 1.0);

    return Column(
      children: [
        Expanded(
          child: Align(
            alignment: Alignment.bottomCenter,
            child: isWin
                ? FractionallySizedBox(
                    heightFactor: ratio,
                    child: Container(
                      width: 12,
                      decoration: ShapeDecoration(
                        color: color,
                        shape: const CutCornerBorder(cut: 3),
                      ),
                    ),
                  )
                : const SizedBox.shrink(),
          ),
        ),
        Container(
          height: 1,
          color: QfColors.slate,
        ),
        Expanded(
          child: Align(
            alignment: Alignment.topCenter,
            child: !isWin
                ? FractionallySizedBox(
                    heightFactor: ratio,
                    child: Container(
                      width: 12,
                      decoration: ShapeDecoration(
                        color: color,
                        shape: const CutCornerBorder(cut: 3),
                      ),
                    ),
                  )
                : const SizedBox.shrink(),
          ),
        ),
        Text(
          '${margin > 0 ? "+" : ""}$margin',
          style: TextStyle(
            fontFamily: qfMono,
            fontSize: 9,
            fontWeight: FontWeight.w700,
            color: color,
          ),
        ),
      ],
    );
  }
}

/// Barra apilada proporcional de 2 o 3 partes CyberCore (§4).
class QfStackedBar extends StatelessWidget {
  const QfStackedBar({
    super.key,
    required this.parts,
    this.height = 8,
  });

  final List<(String label, double value, Color color)> parts;
  final double height;

  @override
  Widget build(BuildContext context) {
    final total = parts.fold<double>(0.0, (acc, p) => acc + p.$2);
    if (total <= 0) return const SizedBox.shrink();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        ClipRRect(
          borderRadius: BorderRadius.circular(height / 2),
          child: SizedBox(
            height: height,
            child: Row(
              children: [
                for (var i = 0; i < parts.length; i++)
                  Expanded(
                    flex: ((parts[i].$2 / total) * 1000).round().clamp(1, 1000),
                    child: Container(color: parts[i].$3),
                  ),
              ],
            ),
          ),
        ),
        const SizedBox(height: 4),
        Wrap(
          spacing: 12,
          runSpacing: 4,
          children: [
            for (final p in parts)
              Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Container(
                    width: 6,
                    height: 6,
                    decoration: BoxDecoration(color: p.$3, shape: BoxShape.circle),
                  ),
                  const SizedBox(width: 4),
                  Text(
                    '${p.$1} (${p.$2 is int ? p.$2.toInt() : p.$2.toStringAsFixed(0)})',
                    style: const TextStyle(
                      fontFamily: qfMono,
                      fontSize: 10,
                      color: QfColors.text2,
                    ),
                  ),
                ],
              ),
          ],
        ),
      ],
    );
  }
}

/// Cinta de 15 casillas por zonas para clasificación NBA (§4 y §5.9).
class QfSeasonTrack extends StatelessWidget {
  const QfSeasonTrack({
    super.key,
    this.size = 15,
    required this.homeRank,
    required this.awayRank,
    required this.homeCode,
    required this.awayCode,
  });

  final int size;
  final int homeRank;
  final int awayRank;
  final String homeCode;
  final String awayCode;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SizedBox(
          height: 38,
          child: Row(
            children: [
              for (var i = 1; i <= size; i++)
                Expanded(
                  child: _TrackCell(
                    rank: i,
                    isHome: i == homeRank,
                    isAway: i == awayRank,
                    homeCode: homeCode,
                    awayCode: awayCode,
                  ),
                ),
            ],
          ),
        ),
        const SizedBox(height: 6),
        const Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(
              '1-6 PLAYOFFS',
              style: TextStyle(
                fontFamily: qfDisplay,
                fontSize: 9,
                fontWeight: FontWeight.w700,
                color: QfColors.cyan,
              ),
            ),
            Text(
              '7-10 PLAY-IN',
              style: TextStyle(
                fontFamily: qfDisplay,
                fontSize: 9,
                fontWeight: FontWeight.w700,
                color: QfColors.slate,
              ),
            ),
            Text(
              '11-15 FUERA',
              style: TextStyle(
                fontFamily: qfDisplay,
                fontSize: 9,
                fontWeight: FontWeight.w700,
                color: QfColors.muted,
              ),
            ),
          ],
        ),
      ],
    );
  }
}

class _TrackCell extends StatelessWidget {
  const _TrackCell({
    required this.rank,
    required this.isHome,
    required this.isAway,
    required this.homeCode,
    required this.awayCode,
  });

  final int rank;
  final bool isHome;
  final bool isAway;
  final String homeCode;
  final String awayCode;

  @override
  Widget build(BuildContext context) {
    Color zoneColor;
    if (rank <= 6) {
      zoneColor = QfColors.cyan.withValues(alpha: .2);
    } else if (rank <= 10) {
      zoneColor = QfColors.slate.withValues(alpha: .2);
    } else {
      zoneColor = QfColors.track;
    }

    return Column(
      children: [
        if (isHome)
          Text(
            homeCode,
            style: const TextStyle(
              fontFamily: qfDisplay,
              fontSize: 8,
              fontWeight: FontWeight.w700,
              color: QfColors.cyan,
            ),
          )
        else if (isAway)
          Text(
            awayCode,
            style: const TextStyle(
              fontFamily: qfDisplay,
              fontSize: 8,
              fontWeight: FontWeight.w700,
              color: QfColors.chrome,
            ),
          )
        else
          const SizedBox(height: 10),
        Container(
          height: 18,
          margin: const EdgeInsets.symmetric(horizontal: 1),
          alignment: Alignment.center,
          decoration: BoxDecoration(
            color: (isHome || isAway)
                ? (isHome ? QfColors.cyan : QfColors.chrome)
                : zoneColor,
            border: Border.all(
              color: rank <= 6 ? QfColors.cyan.withValues(alpha: .4) : QfColors.track,
              width: 0.5,
            ),
          ),
          child: Text(
            '$rank',
            style: TextStyle(
              fontFamily: qfMono,
              fontSize: 8,
              fontWeight: FontWeight.w700,
              color: (isHome || isAway) ? QfColors.onGreen : QfColors.text2,
            ),
          ),
        ),
      ],
    );
  }
}

/// Barra de 12 casillas (pips) CyberCore para Coins / Desbloqueos (§4).
class QfPips extends StatelessWidget {
  const QfPips({
    super.key,
    this.total = 12,
    required this.filled,
    this.spend = 0,
    this.missing = 0,
    this.filledColor = QfColors.yellow,
    this.height = 10,
    this.spacing = 3,
  });

  final int total;
  final int filled;
  final int spend;
  final int missing;
  final Color filledColor;
  final double height;
  final double spacing;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        for (var i = 0; i < total; i++) ...[
          if (i > 0) SizedBox(width: spacing),
          Expanded(
            child: _PipCell(
              index: i,
              filled: filled,
              spend: spend,
              missing: missing,
              filledColor: filledColor,
              height: height,
            ),
          ),
        ],
      ],
    );
  }
}

class _PipCell extends StatelessWidget {
  const _PipCell({
    required this.index,
    required this.filled,
    required this.spend,
    required this.missing,
    required this.filledColor,
    required this.height,
  });

  final int index;
  final int filled;
  final int spend;
  final int missing;
  final Color filledColor;
  final double height;

  @override
  Widget build(BuildContext context) {
    BoxDecoration decoration;

    if (missing > 0) {
      if (index < filled) {
        // Casillas que se tienen
        decoration = BoxDecoration(
          color: filledColor,
          borderRadius: BorderRadius.circular(1.5),
        );
      } else if (index < (filled + missing)) {
        // Casillas que faltan
        decoration = BoxDecoration(
          color: QfColors.magenta.withValues(alpha: .15),
          borderRadius: BorderRadius.circular(1.5),
          border: Border.all(color: QfColors.magenta, width: 1),
        );
      } else {
        // Vacías
        decoration = BoxDecoration(
          color: Colors.white.withValues(alpha: .06),
          borderRadius: BorderRadius.circular(1.5),
        );
      }
    } else {
      if (index < (filled - spend)) {
        // Casillas llenas conservadas
        decoration = BoxDecoration(
          color: filledColor,
          borderRadius: BorderRadius.circular(1.5),
        );
      } else if (index < filled) {
        // Casillas que se gastan
        decoration = BoxDecoration(
          color: QfColors.cyan.withValues(alpha: .18),
          borderRadius: BorderRadius.circular(1.5),
          border: Border.all(color: QfColors.cyan, width: 1),
        );
      } else {
        // Vacías
        decoration = BoxDecoration(
          color: Colors.white.withValues(alpha: .06),
          borderRadius: BorderRadius.circular(1.5),
        );
      }
    }

    return Container(
      height: height,
      decoration: decoration,
    );
  }
}

/// Utilidad de barras verticales para Tenis (Modelo / Juegos totales) (§4).
class QfSegmentedChart extends StatelessWidget {
  const QfSegmentedChart({
    super.key,
    required this.bars,
    this.height = 100,
  });

  final List<(String label, double value, String displayValue)> bars;
  final double height;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: height,
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.end,
        children: [
          for (var i = 0; i < bars.length; i++) ...[
            if (i > 0) const SizedBox(width: 8),
            Expanded(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.end,
                children: [
                  Text(
                    bars[i].$3,
                    style: const TextStyle(
                      fontFamily: qfMono,
                      fontSize: 10,
                      fontWeight: FontWeight.w700,
                      color: QfColors.cyan,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Expanded(
                    child: Align(
                      alignment: Alignment.bottomCenter,
                      child: FractionallySizedBox(
                        heightFactor: bars[i].$2.clamp(0.05, 1.0),
                        widthFactor: 0.8,
                        child: Container(
                          decoration: ShapeDecoration(
                            color: QfColors.cyan.withValues(alpha: .3 + 0.7 * bars[i].$2.clamp(0.0, 1.0)),
                            shape: const CutCornerBorder(cut: 4),
                          ),
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    bars[i].$1,
                    style: const TextStyle(
                      fontFamily: qfDisplay,
                      fontSize: 10,
                      fontWeight: FontWeight.w700,
                      color: QfColors.muted,
                    ),
                  ),
                ],
              ),
            ),
          ],
        ],
      ),
    );
  }
}
