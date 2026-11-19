import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../product/qf_shapes.dart';
import '../product/qf_theme.dart';
import 'app_locale.dart';
import 'language_picker.dart';

// l10n-ignore-start (nombres propios de ligas y códigos: son datos, no textos traducibles)
const _leagues = <String, String>{
  'es': 'LaLiga / Liga MX',
  'en': 'Premier League',
  'pt': 'Brasileirão',
  'fr': 'Ligue 1',
  'it': 'Serie A',
  'de': 'Bundesliga',
};
// l10n-ignore-end

/// Primera pantalla de la app: elección de idioma, antes de la bienvenida y del acceso.
///
/// Sale solo mientras la persona no haya elegido un idioma (`AppLocale.chosen`). Al tocar
/// un idioma se guarda con [selectLanguage] y `AppLocale` avisa a la app, que pasa sola al
/// flujo normal; después se cambia desde el botón de idioma en Perfil.
class LanguageSelectionScreen extends StatefulWidget {
  const LanguageSelectionScreen({super.key});

  @override
  State<LanguageSelectionScreen> createState() =>
      _LanguageSelectionScreenState();
}

class _LanguageSelectionScreenState extends State<LanguageSelectionScreen>
    with TickerProviderStateMixin {
  late final AnimationController _entrance = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 900),
  );
  late final AnimationController _orbit = AnimationController(
    vsync: this,
    duration: const Duration(seconds: 6),
  );
  late final AnimationController _pulse = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 2400),
  );
  late String _selected = AppLocale.instance.code;
  late final String _detected = AppLocale.instance.code;
  bool _leaving = false;
  bool _started = false;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (_started) return;
    _started = true;
    if (MediaQuery.of(context).disableAnimations) {
      _entrance.value = 1;
    } else {
      _entrance.forward();
      _orbit.repeat();
      _pulse.repeat(reverse: true);
    }
  }

  @override
  void dispose() {
    _entrance.dispose();
    _orbit.dispose();
    _pulse.dispose();
    super.dispose();
  }

  Future<void> _choose(String code) async {
    if (_leaving) return;
    setState(() {
      _selected = code;
      _leaving = true;
    });
    final still = MediaQuery.of(context).disableAnimations;
    await Future<void>.delayed(Duration(milliseconds: still ? 80 : 350));
    await selectLanguage(code);
  }

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    return Scaffold(
      backgroundColor: QfColors.bg,
      body: Stack(
        children: [
          const Positioned.fill(child: _Backdrop()),
          SafeArea(
            child: Center(
              child: SingleChildScrollView(
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                child: ConstrainedBox(
                  constraints: const BoxConstraints(maxWidth: 420),
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      // Cabecera superior con órbitas y globo
                      _Reveal(
                        animation: _entrance,
                        start: 0,
                        child: _OrbitHeader(
                          orbit: _orbit,
                          pulse: _pulse,
                        ),
                      ),
                      const SizedBox(height: 12),
                      // Insignia con FittedBox para pantallas estrechas
                      _Reveal(
                        animation: _entrance,
                        start: .12,
                        child: FittedBox(
                          fit: BoxFit.scaleDown,
                          child: QfBadge(
                            l10n.languageFirstBadge.toUpperCase(),
                            color: QfColors.cyan,
                          ),
                        ),
                      ),
                      const SizedBox(height: 10),
                      // Título
                      _Reveal(
                        animation: _entrance,
                        start: .2,
                        child: Text(
                          l10n.languageFirstTitle,
                          key: const ValueKey('first-language-title'),
                          textAlign: TextAlign.center,
                          style: const TextStyle(
                            color: QfColors.text,
                            fontFamily: qfDisplay,
                            fontWeight: FontWeight.w700,
                            fontSize: 30,
                            height: 1.05,
                            letterSpacing: .8,
                          ),
                        ),
                      ),
                      const SizedBox(height: 6),
                      // Subtítulo
                      _Reveal(
                        animation: _entrance,
                        start: .28,
                        child: Text(
                          l10n.languageFirstHint,
                          textAlign: TextAlign.center,
                          style: const TextStyle(
                            color: QfColors.text2,
                            fontSize: 13,
                            height: 1.35,
                          ),
                        ),
                      ),
                      const SizedBox(height: 16),
                      // Lista de 6 filas de idiomas
                      for (final (i, entry) in appLanguages.entries.indexed) ...[
                        _Reveal(
                          animation: _entrance,
                          start: .34 + i * .06,
                          child: _LanguageRow(
                            code: entry.key,
                            name: entry.value,
                            league: _leagues[entry.key] ?? '',
                            selected: _selected == entry.key,
                            isDetected: _detected == entry.key,
                            detectedLabel: l10n.languageDetected,
                            onTap: () => _choose(entry.key),
                          ),
                        ),
                        if (i < appLanguages.length - 1)
                          const SizedBox(height: 8),
                      ],
                      const SizedBox(height: 14),
                      // Nota al pie
                      _Reveal(
                        animation: _entrance,
                        start: .76,
                        child: Text(
                          l10n.languageChangeLater,
                          textAlign: TextAlign.center,
                          style: const TextStyle(
                            fontSize: 11,
                            color: QfColors.muted,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

/// Fondo oscuro con resplandor radial en la parte superior.
class _Backdrop extends StatelessWidget {
  const _Backdrop();

  @override
  Widget build(BuildContext context) => const DecoratedBox(
    decoration: BoxDecoration(
      gradient: RadialGradient(
        center: Alignment(0, -.85),
        radius: 1.2,
        colors: [Color(0x2200f0ff), QfColors.bg],
        stops: [0, .7],
      ),
    ),
  );
}

/// Aparece con fundido y un ligero ascenso, escalonado según [start] (0 a 1).
class _Reveal extends StatelessWidget {
  const _Reveal({
    required this.animation,
    required this.start,
    required this.child,
  });

  final Animation<double> animation;
  final double start;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    final curved = CurvedAnimation(
      parent: animation,
      curve: Interval(
        start.clamp(0, .95),
        math.min(1, start + .35),
        curve: Curves.easeOutCubic,
      ),
    );
    return FadeTransition(
      opacity: curved,
      child: SlideTransition(
        position: Tween(
          begin: const Offset(0, .08),
          end: Offset.zero,
        ).animate(curved),
        child: child,
      ),
    );
  }
}

/// Cabecera de 180 dp con marca QUANTFUT, órbitas animadas y globo en corte angular.
class _OrbitHeader extends StatelessWidget {
  const _OrbitHeader({required this.orbit, required this.pulse});

  final Animation<double> orbit;
  final Animation<double> pulse;

  @override
  Widget build(BuildContext context) => ExcludeSemantics(
    child: SizedBox(
      height: 180,
      width: double.infinity,
      child: Stack(
        alignment: Alignment.center,
        children: [
          // Órbitas concéntricas con partículas giratorias
          Positioned.fill(
            child: AnimatedBuilder(
              animation: Listenable.merge([orbit, pulse]),
              builder: (context, _) => CustomPaint(
                painter: _OrbitsPainter(
                  angle: orbit.value * 2 * math.pi,
                  pulse: pulse.value,
                ),
              ),
            ),
          ),
          // Contenido central: Marca y caja con globo
          Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              // QUANTFUT
              const Text.rich(
                TextSpan(
                  children: [
                    TextSpan(
                      text: 'QUANT', // l10n-ignore (marca)
                      style: TextStyle(color: QfColors.text),
                    ),
                    TextSpan(
                      text: 'FUT', // l10n-ignore (marca)
                      style: TextStyle(color: QfColors.cyan),
                    ),
                  ],
                ),
                style: TextStyle(
                  fontFamily: qfDisplay,
                  fontWeight: FontWeight.w700,
                  fontSize: 21,
                  letterSpacing: 3.0,
                ),
              ),
              const SizedBox(height: 14),
              // Contenedor 68x68 con globo
              Container(
                width: 68,
                height: 68,
                decoration: ShapeDecoration(
                  color: const Color(0x1400f0ff),
                  shape: const CutCornerBorder(
                    cut: 10,
                    side: BorderSide(color: Color(0x7a00f0ff)),
                  ),
                  shadows: const [
                    BoxShadow(
                      color: Color(0x4000f0ff),
                      blurRadius: 28,
                      spreadRadius: 1,
                    ),
                  ],
                ),
                child: const Center(
                  child: Icon(
                    Icons.language_rounded,
                    color: QfColors.cyan,
                    size: 34,
                  ),
                ),
              ),
            ],
          ),
        ],
      ),
    ),
  );
}

class _OrbitsPainter extends CustomPainter {
  const _OrbitsPainter({required this.angle, required this.pulse});

  final double angle;
  final double pulse;

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2 + 10);

    // 3 anillos concéntricos
    final strokePaint = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1.0;

    // Anillo 1 (r = 52)
    strokePaint.color = const Color(0x3800f0ff);
    canvas.drawCircle(center, 52, strokePaint);

    // Anillo 2 (r = 82)
    strokePaint.color = const Color(0x2400f0ff);
    canvas.drawCircle(center, 82, strokePaint);

    // Anillo 3 (r = 112)
    strokePaint.color = const Color(0x1400f0ff);
    canvas.drawCircle(center, 112, strokePaint);

    // Partículas orbitales
    final dotPaint = Paint()..style = PaintingStyle.fill;

    // Dot 1 en anillo 1 (cyan)
    final a1 = angle;
    dotPaint.color = QfColors.cyan;
    canvas.drawCircle(
      center + Offset(52 * math.cos(a1), 52 * math.sin(a1)),
      3.5,
      dotPaint,
    );

    // Dot 2 en anillo 2 (verde)
    final a2 = -angle * 0.7 + 1.2;
    dotPaint.color = QfColors.green;
    canvas.drawCircle(
      center + Offset(82 * math.cos(a2), 82 * math.sin(a2)),
      3.0,
      dotPaint,
    );

    // Dot 3 en anillo 2 (amarillo)
    final a3 = -angle * 0.7 + 3.8;
    dotPaint.color = QfColors.yellow;
    canvas.drawCircle(
      center + Offset(82 * math.cos(a3), 82 * math.sin(a3)),
      2.8,
      dotPaint,
    );

    // Dot 4 en anillo 3 (cyan tenue)
    final a4 = angle * 0.5 + 2.5;
    dotPaint.color = const Color(0xb000f0ff);
    canvas.drawCircle(
      center + Offset(112 * math.cos(a4), 112 * math.sin(a4)),
      2.6,
      dotPaint,
    );
  }

  @override
  bool shouldRepaint(_OrbitsPainter oldDelegate) =>
      oldDelegate.angle != angle || oldDelegate.pulse != pulse;
}

/// Fila horizontal de 58 dp para cada idioma conforme a Idioma.dc.html.
class _LanguageRow extends StatelessWidget {
  const _LanguageRow({
    required this.code,
    required this.name,
    required this.league,
    required this.selected,
    required this.isDetected,
    required this.detectedLabel,
    required this.onTap,
  });

  final String code;
  final String name;
  final String league;
  final bool selected;
  final bool isDetected;
  final String detectedLabel;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final isHighlighted = selected || isDetected;

    final borderColor = isHighlighted ? QfColors.cyan : QfColors.border;
    final bgColor = isHighlighted ? const Color(0x1a00f0ff) : QfColors.surface;

    return Semantics(
      button: true,
      selected: selected,
      label: '$name $league',
      onTap: onTap,
      child: Material(
        key: ValueKey('first-language-$code'),
        color: Colors.transparent,
        child: InkWell(
          customBorder: const CutCornerBorder(cut: 10),
          onTap: onTap,
          child: Container(
            constraints: const BoxConstraints(minHeight: 58),
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
            decoration: ShapeDecoration(
              color: bgColor,
              shape: CutCornerBorder(
                cut: 10,
                side: BorderSide(
                  color: borderColor,
                  width: isHighlighted ? 1.5 : 1.0,
                ),
              ),
              shadows: isHighlighted
                  ? const [
                      BoxShadow(
                        color: Color(0x2400f0ff),
                        blurRadius: 18,
                        spreadRadius: 1,
                      ),
                    ]
                  : null,
            ),
            child: Row(
              children: [
                // Casilla de código (40x40 dp)
                Container(
                  width: 40,
                  height: 40,
                  decoration: ShapeDecoration(
                    color: isHighlighted
                        ? const Color(0x2400f0ff)
                        : Colors.transparent,
                    shape: CutCornerBorder(
                      cut: 6,
                      side: BorderSide(
                        color: isHighlighted
                            ? const Color(0x8a00f0ff)
                            : QfColors.border,
                      ),
                    ),
                  ),
                  child: Center(
                    child: Text(
                      code.toUpperCase(),
                      style: TextStyle(
                        fontFamily: qfMono,
                        fontWeight: FontWeight.w700,
                        fontSize: 15,
                        color: isHighlighted ? QfColors.cyan : QfColors.muted,
                      ),
                    ),
                  ),
                ),
                const SizedBox(width: 12),
                // Textos: Nombre nativo (con ✓ para selected) y Liga
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Flexible(
                            child: Text(
                              name,
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                              style: const TextStyle(
                                fontSize: 16,
                                fontWeight: FontWeight.w700,
                                color: QfColors.text,
                              ),
                            ),
                          ),
                          if (selected) ...[
                            const SizedBox(width: 6),
                            const Icon(
                              Icons.check,
                              size: 16,
                              color: QfColors.cyan,
                            ),
                          ],
                        ],
                      ),
                      const SizedBox(height: 2),
                      Text(
                        league,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: TextStyle(
                          fontFamily: qfMono,
                          fontSize: 11,
                          fontWeight: FontWeight.w500,
                          color: isHighlighted
                              ? QfColors.text2
                              : QfColors.muted,
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(width: 8),
                // Trailing: DETECTADO o Chevron
                if (isDetected)
                  Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 8,
                      vertical: 3,
                    ),
                    color: QfColors.cyan,
                    child: Text(
                      detectedLabel,
                      style: const TextStyle(
                        fontFamily: qfDisplay,
                        fontWeight: FontWeight.w700,
                        fontSize: 10,
                        letterSpacing: 1.2,
                        color: Color(0xff03110f),
                      ),
                    ),
                  )
                else
                  const Icon(
                    Icons.chevron_right_rounded,
                    size: 20,
                    color: QfColors.muted,
                  ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
