import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../core/meta_events.dart';
import '../l10n/app_locale.dart';
import 'qf_shapes.dart';
import 'qf_theme.dart';

/// Guía de pronósticos CyberCore: 6 temas interactivos con chips superiores,
/// gráficos ilustrativos dedicados (§5.7), textos explicativos y navegación anterior/siguiente.
class GuideScreen extends StatefulWidget {
  const GuideScreen({super.key});

  @override
  State<GuideScreen> createState() => _GuideScreenState();
}

class _GuideScreenState extends State<GuideScreen> {
  int currentTopic = 0;
  bool completed = false;

  void complete() {
    if (completed) return;
    completed = true;
    MetaEvents.current?.completeTutorial();
  }

  void _next() {
    if (currentTopic < 5) {
      setState(() => currentTopic++);
      if (currentTopic == 5) complete();
    } else {
      complete();
      Navigator.of(context).maybePop();
    }
  }

  void _prev() {
    if (currentTopic > 0) {
      setState(() => currentTopic--);
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final topics = [
      (l10n.guideTopic1, l10n.guideHead1, l10n.guideBody1),
      (l10n.guideTopic2, l10n.guideHead2, l10n.guideBody2),
      (l10n.guideTopic3, l10n.guideHead3, l10n.guideBody3),
      (l10n.guideTopic4, l10n.guideHead4, l10n.guideBody4),
      (l10n.guideTopic5, l10n.guideHead5, l10n.guideBody5),
      (l10n.guideTopic6, l10n.guideHead6, l10n.guideBody6),
    ];

    final (topicLabel, head, body) = topics[currentTopic];
    final isTopic6 = currentTopic == 5;

    return Scaffold(
      backgroundColor: QfColors.bg,
      appBar: PreferredSize(
        preferredSize: const Size.fromHeight(56),
        child: Container(
          height: 56,
          padding: const EdgeInsets.only(left: 6, right: 14),
          decoration: const BoxDecoration(
            color: QfColors.bg,
            border: Border(bottom: BorderSide(color: QfColors.border)),
          ),
          child: Row(
            children: [
              IconButton(
                tooltip: MaterialLocalizations.of(context).backButtonTooltip,
                constraints: const BoxConstraints(minWidth: 44, minHeight: 44),
                icon: const Icon(Icons.chevron_left, color: QfColors.text2, size: 24),
                onPressed: () => Navigator.of(context).maybePop(),
              ),
              Expanded(
                child: Text(
                  l10n.guideTitle.toUpperCase(),
                  style: const TextStyle(
                    fontFamily: qfDisplay,
                    fontSize: 18,
                    fontWeight: FontWeight.w700,
                    letterSpacing: 1.0,
                    color: QfColors.text,
                  ),
                ),
              ),
              Text(
                '${currentTopic + 1} / 6',
                style: const TextStyle(
                  fontFamily: qfMono,
                  fontSize: 12,
                  fontWeight: FontWeight.w700,
                  color: QfColors.muted,
                ),
              ),
            ],
          ),
        ),
      ),
      body: Column(
        children: [
          Expanded(
            child: ListView(
              key: const ValueKey('guide-list'),
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
              children: [
                Text(
                  l10n.guideSubtitle,
                  style: const TextStyle(fontSize: 13, color: QfColors.text2),
                ),
                const SizedBox(height: 12),

                // Selector de temas (chips)
                SingleChildScrollView(
                  scrollDirection: Axis.horizontal,
                  child: Row(
                    children: [
                      for (final (i, t) in topics.indexed)
                        Padding(
                          padding: const EdgeInsets.only(right: 6),
                          child: InkWell(
                            key: ValueKey('guide-topic-$i'),
                            onTap: () {
                              setState(() => currentTopic = i);
                              if (i == 5) complete();
                            },
                            child: Container(
                              constraints: const BoxConstraints(minHeight: 40),
                              padding: const EdgeInsets.symmetric(horizontal: 12),
                              alignment: Alignment.center,
                              decoration: ShapeDecoration(
                                color: currentTopic == i
                                    ? QfColors.cyan.withValues(alpha: .1)
                                    : Colors.transparent,
                                shape: CutCornerBorder(
                                  cut: 8,
                                  side: BorderSide(
                                    color: currentTopic == i ? QfColors.cyan : QfColors.border,
                                  ),
                                ),
                              ),
                              child: Text(
                                t.$1.toUpperCase(),
                                style: TextStyle(
                                  fontFamily: qfDisplay,
                                  fontSize: 12,
                                  fontWeight: FontWeight.w700,
                                  letterSpacing: 0.8,
                                  color: currentTopic == i ? QfColors.cyan : QfColors.text2,
                                ),
                              ),
                            ),
                          ),
                        ),
                    ],
                  ),
                ),
                const SizedBox(height: 14),

                // Tarjeta de contenido CyberCore
                Container(
                  decoration: ShapeDecoration(
                    color: QfColors.surface,
                    shape: CutCornerBorder(
                      cut: 16,
                      side: BorderSide(
                        color: isTopic6
                            ? QfColors.yellow.withValues(alpha: .45)
                            : QfColors.borderStrong,
                      ),
                    ),
                  ),
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      Text(
                        '// $topicLabel'.toUpperCase(),
                        style: TextStyle(
                          fontFamily: qfDisplay,
                          fontWeight: FontWeight.w700,
                          fontSize: 11,
                          letterSpacing: 1.6,
                          color: isTopic6 ? QfColors.yellow : QfColors.cyan,
                        ),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        head.toUpperCase(),
                        style: const TextStyle(
                          fontFamily: qfDisplay,
                          fontWeight: FontWeight.w700,
                          fontSize: 22,
                          height: 1.1,
                          letterSpacing: 0.3,
                          color: QfColors.text,
                        ),
                      ),
                      const SizedBox(height: 14),

                      // Gráfico según tema
                      _buildDiagram(currentTopic, l10n),
                      const SizedBox(height: 14),

                      // Texto explicativo largo
                      Text(
                        body,
                        style: const TextStyle(
                          fontSize: 14,
                          height: 1.45,
                          color: QfColors.text2,
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 14),
              ],
            ),
          ),

          // Botones inferiores ANTERIOR / SIGUIENTE
          Container(
            padding: const EdgeInsets.fromLTRB(14, 10, 14, 14),
            decoration: const BoxDecoration(
              color: QfColors.surface,
              border: Border(top: BorderSide(color: QfColors.border)),
            ),
            child: Row(
              children: [
                Expanded(
                  child: Opacity(
                    opacity: currentTopic > 0 ? 1.0 : 0.4,
                    child: InkWell(
                      key: const ValueKey('guide-prev'),
                      onTap: currentTopic > 0 ? _prev : null,
                      child: Container(
                        constraints: const BoxConstraints(minHeight: 48),
                        alignment: Alignment.center,
                        decoration: ShapeDecoration(
                          color: QfColors.cyan.withValues(alpha: .05),
                          shape: const CutCornerBorder(
                            cut: 10,
                            side: BorderSide(color: QfColors.borderStrong),
                          ),
                        ),
                        child: Text(
                          l10n.guidePrevious.toUpperCase(),
                          style: const TextStyle(
                            fontFamily: qfDisplay,
                            fontWeight: FontWeight.w700,
                            fontSize: 14,
                            letterSpacing: 1.0,
                            color: QfColors.cyan,
                          ),
                        ),
                      ),
                    ),
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: InkWell(
                    key: const ValueKey('guide-next'),
                    onTap: _next,
                    child: Container(
                      constraints: const BoxConstraints(minHeight: 48),
                      alignment: Alignment.center,
                      decoration: const ShapeDecoration(
                        gradient: LinearGradient(
                          colors: [QfColors.green, Color(0xFF8AFFDF)],
                          begin: Alignment.topLeft,
                          end: Alignment.bottomRight,
                        ),
                        shape: CutCornerBorder(
                          cut: 10,
                          side: BorderSide(color: QfColors.green),
                        ),
                      ),
                      child: Text(
                        l10n.guideNext.toUpperCase(),
                        style: const TextStyle(
                          fontFamily: qfDisplay,
                          fontWeight: FontWeight.w700,
                          fontSize: 14,
                          letterSpacing: 1.0,
                          color: Color(0xFF03110F),
                        ),
                      ),
                    ),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildDiagram(int topic, AppLocalizations l10n) => switch (topic) {
    0 => _diagramProbability(),
    1 => _diagramOdds(),
    2 => _diagramSealing(),
    3 => _diagramParley(),
    4 => _diagramLadder(),
    _ => _diagramResponsibility(l10n),
  };

  Widget _diagramContainer({required Widget child}) => Container(
    padding: const EdgeInsets.all(14),
    decoration: BoxDecoration(
      color: Colors.white.withValues(alpha: .02),
      border: Border.all(color: QfColors.divider),
    ),
    child: child,
  );

  // Tema 1: Probabilidad (3 de 4 casillas verdes, 1 gris)
  Widget _diagramProbability() => _diagramContainer(
    child: LayoutBuilder(
      builder: (context, constraints) {
        final boxSize = math.min(54.0, (constraints.maxWidth - 24) / 4);
        return Column(
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                for (var i = 0; i < 3; i++)
                  Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 3),
                    child: Container(
                      width: boxSize,
                      height: boxSize,
                      alignment: Alignment.center,
                      decoration: ShapeDecoration(
                        color: QfColors.green.withValues(alpha: .1),
                        shape: const CutCornerBorder(
                          cut: 10,
                          side: BorderSide(color: QfColors.green),
                        ),
                      ),
                      child: const Icon(Icons.check, size: 24, color: QfColors.green),
                    ),
                  ),
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 3),
                  child: Container(
                    width: boxSize,
                    height: boxSize,
                    alignment: Alignment.center,
                    decoration: ShapeDecoration(
                      color: Colors.transparent,
                      shape: const CutCornerBorder(
                        cut: 10,
                        side: BorderSide(color: QfColors.muted),
                      ),
                    ),
                    child: const Icon(Icons.close, size: 24, color: QfColors.muted),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            const Text(
              '75 % = 3 DE CADA 4',
              style: TextStyle(
                fontFamily: qfMono,
                fontSize: 20,
                fontWeight: FontWeight.w700,
                color: QfColors.cyan,
              ),
            ),
          ],
        );
      },
    ),
  );

  // Tema 2: Cuota vs probabilidad implícita
  Widget _diagramOdds() => _diagramContainer(
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const Row(
              children: [
                Expanded(
                  child: Text(
                    'PROBABILIDAD DEL MODELO',
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(
                      fontFamily: qfDisplay,
                      fontSize: 11,
                      fontWeight: FontWeight.w700,
                      letterSpacing: 1.2,
                      color: QfColors.muted,
                    ),
                  ),
                ),
                SizedBox(width: 8),
                Text(
                  '62%',
                  style: TextStyle(
                    fontFamily: qfMono,
                    fontSize: 14,
                    fontWeight: FontWeight.w700,
                    color: QfColors.cyan,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 4),
            Container(
              height: 10,
              color: Colors.white.withValues(alpha: .06),
              alignment: Alignment.centerLeft,
              child: FractionallySizedBox(
                widthFactor: 0.62,
                child: Container(color: QfColors.cyan),
              ),
            ),
          ],
        ),
        const SizedBox(height: 10),
        Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const Row(
              children: [
                Expanded(
                  child: Text(
                    'LA QUE IMPLICA LA CUOTA 1.80',
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(
                      fontFamily: qfDisplay,
                      fontSize: 11,
                      fontWeight: FontWeight.w700,
                      letterSpacing: 1.2,
                      color: QfColors.muted,
                    ),
                  ),
                ),
                SizedBox(width: 8),
                Text(
                  '56%',
                  style: TextStyle(
                    fontFamily: qfMono,
                    fontSize: 14,
                    fontWeight: FontWeight.w700,
                    color: QfColors.chrome,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 4),
            Container(
              height: 10,
              color: Colors.white.withValues(alpha: .06),
              alignment: Alignment.centerLeft,
              child: FractionallySizedBox(
                widthFactor: 0.56,
                child: Container(color: QfColors.chrome),
              ),
            ),
          ],
        ),
        const SizedBox(height: 8),
        const Text(
          'Comparar ambas ayuda a ver si el precio es razonable.',
          style: TextStyle(fontSize: 12, color: QfColors.text2),
        ),
      ],
    ),
  );

  // Tema 3: Sello previo al partido
  Widget _diagramSealing() => _diagramContainer(
    child: Stack(
      alignment: Alignment.center,
      children: [
        Positioned(
          top: 22,
          left: 40,
          right: 40,
          child: Container(
            height: 2,
            decoration: const BoxDecoration(
              gradient: LinearGradient(
                colors: [QfColors.green, QfColors.slate],
              ),
            ),
          ),
        ),
        Row(
          children: [
            Expanded(child: _timelineNode(Icons.lock_outline, 'PUBLICADO', 'con su cuota', QfColors.green)),
            Expanded(child: _timelineNode(Icons.schedule, 'PARTIDO', 'sin cambios', QfColors.slate)),
            Expanded(child: _timelineNode(Icons.check, 'RESULTADO', 'al historial', QfColors.slate)),
          ],
        ),
      ],
    ),
  );

  Widget _timelineNode(IconData icon, String title, String sub, Color color) => Column(
    children: [
      Container(
        width: 44,
        height: 44,
        alignment: Alignment.center,
        decoration: BoxDecoration(
          color: QfColors.surface,
          border: Border.all(color: color),
        ),
        child: Icon(icon, size: 22, color: color),
      ),
      const SizedBox(height: 6),
      Text(
        title,
        textAlign: TextAlign.center,
        maxLines: 1,
        overflow: TextOverflow.ellipsis,
        style: const TextStyle(
          fontFamily: qfDisplay,
          fontSize: 11,
          fontWeight: FontWeight.w700,
          letterSpacing: 1.0,
          color: QfColors.text,
        ),
      ),
      Text(
        sub,
        textAlign: TextAlign.center,
        maxLines: 1,
        overflow: TextOverflow.ellipsis,
        style: const TextStyle(
          fontFamily: qfMono,
          fontSize: 10,
          fontWeight: FontWeight.w500,
          color: QfColors.muted,
        ),
      ),
    ],
  );

  // Tema 4: Parley (producto de probabilidades)
  Widget _diagramParley() => _diagramContainer(
    child: Column(
      children: [
        const SingleChildScrollView(
          scrollDirection: Axis.horizontal,
          child: Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Text('80% ', style: TextStyle(fontFamily: qfMono, fontSize: 16, fontWeight: FontWeight.w700, color: QfColors.text2)),
              Text('× ', style: TextStyle(fontFamily: qfMono, fontSize: 16, fontWeight: FontWeight.w700, color: QfColors.slate)),
              Text('75% ', style: TextStyle(fontFamily: qfMono, fontSize: 16, fontWeight: FontWeight.w700, color: QfColors.text2)),
              Text('× ', style: TextStyle(fontFamily: qfMono, fontSize: 16, fontWeight: FontWeight.w700, color: QfColors.slate)),
              Text('70% ', style: TextStyle(fontFamily: qfMono, fontSize: 16, fontWeight: FontWeight.w700, color: QfColors.text2)),
              Text('= ', style: TextStyle(fontFamily: qfMono, fontSize: 16, fontWeight: FontWeight.w700, color: QfColors.slate)),
              Text(
                '42%',
                style: TextStyle(
                  fontFamily: qfMono,
                  fontSize: 16,
                  fontWeight: FontWeight.w700,
                  color: QfColors.cyan,
                  shadows: [Shadow(color: QfColors.cyan, blurRadius: 14)],
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 12),
        Column(
          children: [
            _barLine(0.80, QfColors.slate),
            const SizedBox(height: 4),
            _barLine(0.60, QfColors.slate),
            const SizedBox(height: 4),
            _barLine(0.42, QfColors.cyan),
          ],
        ),
      ],
    ),
  );

  Widget _barLine(double factor, Color color) => Container(
    height: 8,
    color: Colors.white.withValues(alpha: .06),
    alignment: Alignment.centerLeft,
    child: FractionallySizedBox(
      widthFactor: factor,
      child: Container(color: color),
    ),
  );

  // Tema 5: Reto Escalera (5 peldaños)
  Widget _diagramLadder() => _diagramContainer(
    child: Column(
      children: [
        SizedBox(
          height: 96,
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              _ladderStep(0.20, QfColors.green),
              const SizedBox(width: 6),
              _ladderStep(0.38, QfColors.green),
              const SizedBox(width: 6),
              _ladderStep(0.56, QfColors.green),
              const SizedBox(width: 6),
              _ladderStep(0.74, QfColors.cyan, glow: true),
              const SizedBox(width: 6),
              _ladderStep(0.92, Colors.transparent, isDashed: true),
            ],
          ),
        ),
        const SizedBox(height: 6),
        const Row(
          children: [
            Expanded(child: Text('1 ✓', textAlign: TextAlign.center, style: _stepStyle)),
            SizedBox(width: 6),
            Expanded(child: Text('2 ✓', textAlign: TextAlign.center, style: _stepStyle)),
            SizedBox(width: 6),
            Expanded(child: Text('3 ✓', textAlign: TextAlign.center, style: _stepStyle)),
            SizedBox(width: 6),
            Expanded(
              child: Text(
                '4 EN JUEGO',
                textAlign: TextAlign.center,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: TextStyle(
                  fontFamily: qfDisplay,
                  fontSize: 10,
                  fontWeight: FontWeight.w700,
                  letterSpacing: 0.8,
                  color: QfColors.cyan,
                ),
              ),
            ),
            SizedBox(width: 6),
            Expanded(child: Text('5', textAlign: TextAlign.center, style: _stepStyle)),
          ],
        ),
      ],
    ),
  );

  static const _stepStyle = TextStyle(
    fontFamily: qfDisplay,
    fontSize: 10,
    fontWeight: FontWeight.w700,
    letterSpacing: 1.0,
    color: QfColors.muted,
  );

  Widget _ladderStep(double factor, Color color, {bool glow = false, bool isDashed = false}) =>
      Expanded(
        child: FractionallySizedBox(
          heightFactor: factor,
          child: Container(
            decoration: BoxDecoration(
              color: color,
              border: isDashed ? Border.all(color: QfColors.slate) : null,
              boxShadow: glow
                  ? const [BoxShadow(color: Color(0x8000F0FF), blurRadius: 16)]
                  : null,
            ),
          ),
        ),
      );

  // Tema 6: Responsabilidad (18+)
  Widget _diagramResponsibility(AppLocalizations l10n) => _diagramContainer(
    child: Row(
      children: [
        Container(
          width: 64,
          height: 64,
          alignment: Alignment.center,
          decoration: ShapeDecoration(
            shape: const CutCornerBorder(
              cut: 10,
              side: BorderSide(color: QfColors.yellow, width: 2),
            ),
          ),
          child: const Text(
            '18+', // l10n-ignore (insignia universal)
            style: TextStyle(
              fontFamily: qfMono,
              fontSize: 22,
              fontWeight: FontWeight.w700,
              color: QfColors.yellow,
            ),
          ),
        ),
        const SizedBox(width: 14),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(l10n.guideRespRule1, style: const TextStyle(fontSize: 13, color: QfColors.text)),
              const SizedBox(height: 4),
              Text(l10n.guideRespRule2, style: const TextStyle(fontSize: 13, color: QfColors.text)),
              const SizedBox(height: 4),
              Text(l10n.guideRespRule3, style: const TextStyle(fontSize: 13, color: QfColors.text)),
            ],
          ),
        ),
      ],
    ),
  );
}
