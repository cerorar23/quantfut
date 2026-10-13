import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../product/live_widgets.dart';
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
      backgroundColor: liveBg,
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
                              color: Colors.white,
                              fontFamily: 'Gilroy ExtraBold',
                              fontSize: 25,
                              height: 1.15,
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
                              color: liveMuted,
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

/// Fondo oscuro con un resplandor verde que sale de arriba.
class _Backdrop extends StatelessWidget {
  const _Backdrop();

  @override
  Widget build(BuildContext context) => DecoratedBox(
    decoration: BoxDecoration(
      gradient: RadialGradient(
        center: const Alignment(0, -.85),
        radius: 1.15,
        colors: [liveGreen.withValues(alpha: .20), liveBg],
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
    decoration: BoxDecoration(
      color: Colors.white.withValues(alpha: .045),
      borderRadius: BorderRadius.circular(28),
      border: Border.all(color: Colors.white.withValues(alpha: .09)),
      boxShadow: [
        BoxShadow(
          color: Colors.black.withValues(alpha: .45),
          blurRadius: 40,
          offset: const Offset(0, 18),
        ),
      ],
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
                      color: liveGreen.withValues(alpha: .22 + .20 * glow),
                      blurRadius: 26 + 18 * glow,
                      spreadRadius: 2 + 4 * glow,
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
                  color: const Color(0xff0a1b1a),
                  border: Border.all(
                    color: liveGreen.withValues(alpha: .35),
                    width: 1.2,
                  ),
                ),
                child: const Icon(
                  Icons.language_rounded,
                  color: liveGreen,
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
        ..color = liveGreen.withValues(alpha: .14),
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
            colors: [liveGreen.withValues(alpha: 0), liveGreen],
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
    decoration: BoxDecoration(
      color: liveGreen.withValues(alpha: .09),
      borderRadius: BorderRadius.circular(99),
      border: Border.all(color: liveGreen.withValues(alpha: .38)),
    ),
    child: Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          width: 6,
          height: 6,
          decoration: const BoxDecoration(
            color: liveGreen,
            shape: BoxShape.circle,
          ),
        ),
        const SizedBox(width: 8),
        Flexible(
          child: Text(
            label.toUpperCase(),
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: const TextStyle(
              color: liveGreen,
              fontFamily: 'Gilroy Bold',
              fontSize: 11,
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
        duration: const Duration(milliseconds: 220),
        curve: Curves.easeOut,
        decoration: BoxDecoration(
          color: selected
              ? liveGreen.withValues(alpha: .12)
              : Colors.white.withValues(alpha: .035),
          borderRadius: BorderRadius.circular(16),
          border: Border.all(
            color: selected
                ? liveGreen
                : Colors.white.withValues(alpha: .09),
            width: selected ? 1.6 : 1,
          ),
          boxShadow: selected
              ? [
                  BoxShadow(
                    color: liveGreen.withValues(alpha: .28),
                    blurRadius: 18,
                  ),
                ]
              : null,
        ),
        child: Material(
          type: MaterialType.transparency,
          child: InkWell(
            borderRadius: BorderRadius.circular(16),
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
                            color: Colors.white,
                            fontFamily: 'Gilroy Bold',
                            fontSize: 15,
                          ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 5),
                  FittedBox(
                    fit: BoxFit.scaleDown,
                    child: Text(
                      _leagues[code] ?? '',
                      style: TextStyle(
                        color: selected
                            ? liveGreen
                            : liveMuted.withValues(alpha: .85),
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
