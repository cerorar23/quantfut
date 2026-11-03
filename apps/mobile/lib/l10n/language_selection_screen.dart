import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../product/qf_shapes.dart';
import '../product/qf_theme.dart';
import 'app_locale.dart';
import 'language_picker.dart';

// l10n-ignore-start (nombres propios de ligas y banderas: son datos, no textos traducibles)
const _flags = <String, String>{
  'es': '🇪🇸',
  'en': '🇬🇧',
  'pt': '🇧🇷',
  'fr': '🇫🇷',
  'it': '🇮🇹',
  'de': '🇩🇪',
};
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
/// flujo normal; después se cambia desde el botón de idioma de siempre.
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
    duration: const Duration(milliseconds: 1100),
  );
  late final AnimationController _orbit = AnimationController(
    vsync: this,
    duration: const Duration(seconds: 5),
  );
  late final AnimationController _pulse = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 2400),
  );
  late String _selected = AppLocale.instance.code;
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
    // Un instante para ver la tarjeta resaltada antes de pasar al siguiente paso.
    final still = MediaQuery.of(context).disableAnimations;
    await Future<void>.delayed(Duration(milliseconds: still ? 120 : 420));
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
                padding: const EdgeInsets.all(20),
                child: ConstrainedBox(
                  constraints: const BoxConstraints(maxWidth: 420),
                  child: _Card(
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        _Reveal(
                          animation: _entrance,
                          start: 0,
                          child: _OrbitIcon(orbit: _orbit, pulse: _pulse),
                        ),
                        const SizedBox(height: 18),
                        _Reveal(
                          animation: _entrance,
                          start: .12,
                          child: _Badge(label: l10n.languageFirstBadge),
                        ),
                        const SizedBox(height: 16),
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
                              fontSize: 28,
                              height: 1.1,
                            ),
                          ),
                        ),
                        const SizedBox(height: 8),
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
                        const SizedBox(height: 22),
                        GridView.count(
                          crossAxisCount: 2,
                          shrinkWrap: true,
                          physics: const NeverScrollableScrollPhysics(),
                          mainAxisSpacing: 10,
                          crossAxisSpacing: 10,
                          childAspectRatio: 1.9,
                          children: [
                            for (final (i, entry)
                                in appLanguages.entries.indexed)
                              _Reveal(
                                animation: _entrance,
                                start: .36 + i * .07,
                                child: _LanguageCard(
                                  code: entry.key,
                                  name: entry.value,
                                  selected: _selected == entry.key,
                                  onTap: () => _choose(entry.key),
                                ),
                              ),
                          ],
                        ),
                      ],
                    ),
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

/// Fondo oscuro con un resplandor azul tenue que sale de arriba (el único brillo de la pantalla).
class _Backdrop extends StatelessWidget {
  const _Backdrop();

  @override
  Widget build(BuildContext context) => DecoratedBox(
    decoration: BoxDecoration(
      gradient: RadialGradient(
        center: const Alignment(0, -.85),
        radius: 1.15,
        colors: [QfColors.primary.withValues(alpha: .14), QfColors.bg],
        stops: const [0, .75],
      ),
    ),
  );
}

class _Card extends StatelessWidget {
  const _Card({required this.child});

  final Widget child;

  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.fromLTRB(18, 26, 18, 20),
    decoration: const ShapeDecoration(
      color: QfColors.surface,
      shape: CutCornerBorder(side: BorderSide(color: QfColors.border)),
    ),
    child: child,
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
        math.min(1, start + .4),
        curve: Curves.easeOutCubic,
      ),
    );
    return FadeTransition(
      opacity: curved,
      child: SlideTransition(
        position: Tween(
          begin: const Offset(0, .12),
          end: Offset.zero,
        ).animate(curved),
        child: child,
      ),
    );
  }
}

/// Globo dentro de un disco, con un arco que gira y un brillo que respira.
class _OrbitIcon extends StatelessWidget {
  const _OrbitIcon({required this.orbit, required this.pulse});

  final Animation<double> orbit;
  final Animation<double> pulse;

  @override
  Widget build(BuildContext context) => ExcludeSemantics(
    child: SizedBox.square(
      dimension: 104,
      child: AnimatedBuilder(
        animation: Listenable.merge([orbit, pulse]),
        builder: (context, _) {
          final glow = Curves.easeInOut.transform(pulse.value);
          return Stack(
            alignment: Alignment.center,
            children: [
              Container(
                width: 74,
                height: 74,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  boxShadow: [
                    BoxShadow(
                      color: QfColors.primary.withValues(alpha: .10 + .10 * glow),
                      blurRadius: 18 + 10 * glow,
                      spreadRadius: 1 + 2 * glow,
                    ),
                  ],
                ),
              ),
              CustomPaint(
                size: const Size.square(104),
                painter: _OrbitPainter(orbit.value * 2 * math.pi),
              ),
              Container(
                width: 70,
                height: 70,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: QfColors.surface2,
                  border: Border.all(
                    color: QfColors.primary.withValues(alpha: .5),
                    width: 1.2,
                  ),
                ),
                child: const Icon(
                  Icons.language_rounded,
                  color: QfColors.primary,
                  size: 34,
                ),
              ),
            ],
          );
        },
      ),
    ),
  );
}

class _OrbitPainter extends CustomPainter {
  const _OrbitPainter(this.angle);

  final double angle;

  @override
  void paint(Canvas canvas, Size size) {
    final rect = (Offset.zero & size).deflate(3);
    canvas.drawArc(
      rect,
      0,
      2 * math.pi,
      false,
      Paint()
        ..style = PaintingStyle.stroke
        ..strokeWidth = 1.5
        ..color = QfColors.border,
    );
    // El arco se dibuja siempre desde 0° y es el lienzo el que gira: así el degradado
    // no se parte al cruzar los 360°.
    const sweep = 1.45 * math.pi;
    final local = Rect.fromCircle(center: Offset.zero, radius: rect.width / 2);
    canvas
      ..save()
      ..translate(rect.center.dx, rect.center.dy)
      ..rotate(angle)
      ..drawArc(
        local,
        0,
        sweep,
        false,
        Paint()
          ..style = PaintingStyle.stroke
          ..strokeWidth = 3.2
          ..strokeCap = StrokeCap.round
          ..shader = SweepGradient(
            endAngle: sweep,
            colors: [QfColors.primary.withValues(alpha: 0), QfColors.primary],
          ).createShader(local),
      )
      ..restore();
  }

  @override
  bool shouldRepaint(_OrbitPainter oldDelegate) => oldDelegate.angle != angle;
}

class _Badge extends StatelessWidget {
  const _Badge({required this.label});

  final String label;

  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 7),
    decoration: ShapeDecoration(
      color: QfColors.primary.withValues(alpha: .13),
      shape: const CutCornerBorder(cut: 8, side: BorderSide(color: QfColors.primary)),
    ),
    child: Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(width: 6, height: 6, color: QfColors.primary),
        const SizedBox(width: 8),
        Flexible(
          child: Text(
            label.toUpperCase(),
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: const TextStyle(
              color: QfColors.primary,
              fontFamily: qfDisplay,
              fontWeight: FontWeight.w700,
              fontSize: 12,
              letterSpacing: 1.3,
            ),
          ),
        ),
      ],
    ),
  );
}

class _LanguageCard extends StatelessWidget {
  const _LanguageCard({
    required this.code,
    required this.name,
    required this.selected,
    required this.onTap,
  });

  final String code;
  final String name;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => Semantics(
    button: true,
    selected: selected,
    label: name,
    onTap: onTap,
    child: ExcludeSemantics(
      child: AnimatedContainer(
        key: ValueKey('first-language-$code'),
        duration: MediaQuery.of(context).disableAnimations
            ? Duration.zero
            : const Duration(milliseconds: 220),
        curve: Curves.easeOut,
        decoration: ShapeDecoration(
          color: selected ? QfColors.surface2 : QfColors.bg,
          shape: CutCornerBorder(
            cut: 8,
            side: BorderSide(
              color: selected ? QfColors.primary : QfColors.border,
              width: selected ? 2 : 1,
            ),
          ),
        ),
        child: Material(
          type: MaterialType.transparency,
          child: InkWell(
            customBorder: const CutCornerBorder(cut: 8),
            onTap: onTap,
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 10),
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  FittedBox(
                    fit: BoxFit.scaleDown,
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Text(
                          _flags[code] ?? '',
                          style: const TextStyle(fontSize: 18),
                        ),
                        const SizedBox(width: 8),
                        Text(
                          name,
                          style: const TextStyle(
                            color: QfColors.text,
                            fontFamily: 'Gilroy Bold',
                            fontSize: 15,
                          ),
                        ),
                        // ✓ además del borde: el color no es la única señal.
                        if (selected) ...[
                          const SizedBox(width: 6),
                          const Icon(Icons.check, size: 16, color: QfColors.primary),
                        ],
                      ],
                    ),
                  ),
                  const SizedBox(height: 5),
                  FittedBox(
                    fit: BoxFit.scaleDown,
                    child: Text(
                      _leagues[code] ?? '',
                      style: TextStyle(
                        color: selected ? QfColors.primary : QfColors.text2,
                        fontFamily: 'Gilroy Bold',
                        fontSize: 10,
                        letterSpacing: .3,
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    ),
  );
}
