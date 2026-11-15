import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../bottombar.dart';
import '../l10n/app_locale.dart';
import '../product/qf_shapes.dart';
import '../product/qf_theme.dart';
import '../product/welcome_art.dart';

class WelcomePage {
  const WelcomePage(this.title, this.description, this.color);
  final String Function(AppLocalizations l10n) title;
  final String Function(AppLocalizations l10n) description;
  final Color color;
}

final welcomePages = [
  WelcomePage(
    (l10n) => l10n.welcome1Title,
    (l10n) => l10n.welcome1Body,
    QfColors.cyan,
  ),
  WelcomePage(
    (l10n) => l10n.welcome2Title,
    (l10n) => l10n.welcome2Body,
    QfColors.green,
  ),
  WelcomePage(
    (l10n) => l10n.welcome3Title,
    (l10n) => l10n.welcome3Body,
    QfColors.yellow,
  ),
  WelcomePage(
    (l10n) => l10n.welcome4Title,
    (l10n) => l10n.welcome4Body,
    QfColors.cyan,
  ),
  WelcomePage(
    (l10n) => l10n.welcome5Title,
    (l10n) => l10n.welcome5Body,
    QfColors.green,
  ),
];

class SecondScreen extends StatefulWidget {
  const SecondScreen({super.key, this.onFinished});
  final VoidCallback? onFinished;

  @override
  State<SecondScreen> createState() => _SecondScreenState();
}

class _SecondScreenState extends State<SecondScreen> {
  final _controller = PageController();
  int _page = 0;
  bool _leaving = false;

  void _finish() {
    if (_leaving) return;
    _leaving = true;
    if (widget.onFinished != null) {
      widget.onFinished!();
      return;
    }
    Navigator.of(context).pushReplacement(
      MaterialPageRoute<void>(builder: (_) => const MainScreen()),
    );
  }

  void _goTo(int index) {
    if (MediaQuery.disableAnimationsOf(context)) {
      _controller.jumpToPage(index);
    } else {
      _controller.animateToPage(
        index,
        duration: const Duration(milliseconds: 320),
        curve: Curves.easeInOutCubic,
      );
    }
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    return AnnotatedRegion<SystemUiOverlayStyle>(
      value: SystemUiOverlayStyle.light.copyWith(
        statusBarColor: Colors.transparent,
        systemNavigationBarColor: QfColors.bg,
      ),
      child: Scaffold(
        backgroundColor: QfColors.bg,
        body: ColoredBox(
          color: QfColors.bg,
          child: SafeArea(
            child: Center(
              child: ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 480),
                child: Column(
                  children: [
                    // Header: contador de páginas (ej. 1 / 5) y botón SALTAR
                    Container(
                      height: 56,
                      padding: const EdgeInsets.only(left: 20, right: 8),
                      child: Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Text(
                            '${_page + 1} / ${welcomePages.length}',
                            style: const TextStyle(
                              fontFamily: qfMono,
                              fontWeight: FontWeight.w700,
                              fontSize: 12,
                              color: Color(0xFF939AB0),
                            ),
                          ),
                          TextButton(
                            onPressed: _finish,
                            style: TextButton.styleFrom(
                              foregroundColor: QfColors.muted,
                              minimumSize: const Size(64, 44),
                              padding: const EdgeInsets.symmetric(horizontal: 14),
                            ),
                            child: Text(
                              l10n.welcomeSkip.toUpperCase(),
                              style: const TextStyle(
                                fontFamily: qfDisplay,
                                fontWeight: FontWeight.w700,
                                fontSize: 13,
                                letterSpacing: 1.4,
                                color: QfColors.muted,
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                    // Contenido en carrusel
                    Expanded(
                      child: PageView.builder(
                        controller: _controller,
                        itemCount: welcomePages.length,
                        onPageChanged: (index) => setState(() => _page = index),
                        itemBuilder: (context, index) {
                          final page = welcomePages[index];
                          return Padding(
                            padding: const EdgeInsets.symmetric(horizontal: 24),
                            child: Column(
                              children: [
                                // Área de ilustración con resplandor radial
                                Expanded(
                                  flex: 5,
                                  child: Stack(
                                    alignment: Alignment.center,
                                    children: [
                                      Positioned.fill(
                                        child: DecoratedBox(
                                          decoration: BoxDecoration(
                                            gradient: RadialGradient(
                                              center: const Alignment(0, -0.1),
                                              radius: 0.65,
                                              colors: [
                                                QfColors.cyan.withValues(alpha: 0.16),
                                                Colors.transparent,
                                              ],
                                            ),
                                          ),
                                        ),
                                      ),
                                      WelcomeArt(
                                        index: index,
                                        accent: page.color,
                                        active: index == _page,
                                      ),
                                    ],
                                  ),
                                ),
                                const SizedBox(height: 12),
                                // Textos principales
                                Expanded(
                                  flex: 3,
                                  child: Column(
                                    crossAxisAlignment: CrossAxisAlignment.stretch,
                                    children: [
                                      Text(
                                        page.title(l10n),
                                        key: ValueKey('welcome-title-$index'),
                                        style: const TextStyle(
                                          color: QfColors.text,
                                          fontFamily: qfDisplay,
                                          fontWeight: FontWeight.w700,
                                          fontSize: 32,
                                          height: 1.05,
                                          letterSpacing: 0.3,
                                        ),
                                      ),
                                      const SizedBox(height: 10),
                                      Text(
                                        page.description(l10n),
                                        style: const TextStyle(
                                          color: QfColors.muted,
                                          fontFamily: 'Exo 2',
                                          fontSize: 14,
                                          height: 1.4,
                                        ),
                                      ),
                                    ],
                                  ),
                                ),
                              ],
                            ),
                          );
                        },
                      ),
                    ),
                    // Pie: puntos indicadores y botón de acción principal
                    Padding(
                      padding: const EdgeInsets.fromLTRB(24, 8, 24, 22),
                      child: Column(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Semantics(
                            label: l10n.welcomeScreenOf(_page + 1, welcomePages.length),
                            child: Row(
                              mainAxisAlignment: MainAxisAlignment.center,
                              children: List.generate(
                                welcomePages.length,
                                (index) => Semantics(
                                  button: true,
                                  selected: _page == index,
                                  label: l10n.welcomeGoTo(index + 1),
                                  child: GestureDetector(
                                    onTap: () => _goTo(index),
                                    behavior: HitTestBehavior.opaque,
                                    child: SizedBox(
                                      width: 44,
                                      height: 44,
                                      child: Center(
                                        child: AnimatedContainer(
                                          duration: MediaQuery.disableAnimationsOf(context)
                                              ? Duration.zero
                                              : const Duration(milliseconds: 200),
                                          height: 6,
                                          width: _page == index ? 26 : 6,
                                          decoration: BoxDecoration(
                                            color: _page == index
                                                ? QfColors.cyan
                                                : const Color(0xFF3A3F55),
                                            borderRadius: BorderRadius.circular(1),
                                          ),
                                        ),
                                      ),
                                    ),
                                  ),
                                ),
                              ),
                            ),
                          ),
                          const SizedBox(height: 10),
                          // Botón SIGUIENTE / EMPEZAR en gradiente verde CyberCore
                          SizedBox(
                            width: double.infinity,
                            height: 54,
                            child: Container(
                              decoration: ShapeDecoration(
                                gradient: const LinearGradient(
                                  colors: [Color(0xFF05FFA1), Color(0xFF8AFFDF)],
                                  begin: Alignment.topLeft,
                                  end: Alignment.bottomRight,
                                ),
                                shadows: [
                                  BoxShadow(
                                    color: const Color(0xFF05FFA1).withValues(alpha: 0.18),
                                    blurRadius: 28,
                                    offset: const Offset(0, 8),
                                  ),
                                ],
                                shape: const CutCornerBorder(cut: 10),
                              ),
                              child: Material(
                                color: Colors.transparent,
                                child: InkWell(
                                  customBorder: const CutCornerBorder(cut: 10),
                                  onTap: () =>
                                      _page == 4 ? _finish() : _goTo(_page + 1),
                                  child: Center(
                                    child: Text(
                                      (_page == 4 ? l10n.welcomeStart : l10n.welcomeNext).toUpperCase(),
                                      style: const TextStyle(
                                        fontFamily: qfDisplay,
                                        fontWeight: FontWeight.w700,
                                        fontSize: 17,
                                        letterSpacing: 1.5,
                                        color: Color(0xFF03110F),
                                      ),
                                    ),
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
              ),
            ),
          ),
        ),
      ),
    );
  }
}
