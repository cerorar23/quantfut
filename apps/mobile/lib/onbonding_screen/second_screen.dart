import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../bottombar.dart';
import '../l10n/app_locale.dart';
import '../l10n/language_picker.dart';
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
    QfColors.football,
  ),
  WelcomePage(
    (l10n) => l10n.welcome2Title,
    (l10n) => l10n.welcome2Body,
    QfColors.primary,
  ),
  WelcomePage(
    (l10n) => l10n.welcome3Title,
    (l10n) => l10n.welcome3Body,
    QfColors.success,
  ),
  WelcomePage(
    (l10n) => l10n.welcome4Title,
    (l10n) => l10n.welcome4Body,
    QfColors.nba,
  ),
  WelcomePage(
    (l10n) => l10n.welcome5Title,
    (l10n) => l10n.welcome5Body,
    QfColors.tennis,
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
                    Padding(
                      padding: const EdgeInsets.fromLTRB(24, 8, 12, 0),
                      child: Row(
                        children: [
                          const Text(
                            '// ', // l10n-ignore (marca)
                            style: TextStyle(
                              fontFamily: qfDisplay,
                              fontWeight: FontWeight.w700,
                              fontSize: 20,
                              color: QfColors.primary,
                            ),
                          ),
                          const Text(
                            'QUANTFUT', // l10n-ignore (marca)
                            style: TextStyle(
                              fontFamily: qfDisplay,
                              fontWeight: FontWeight.w700,
                              fontSize: 18,
                              letterSpacing: 1.2,
                              color: QfColors.text,
                            ),
                          ),
                          const Spacer(),
                          const LanguageButton(color: QfColors.text2),
                          TextButton(
                            onPressed: _finish,
                            style: TextButton.styleFrom(
                              foregroundColor: QfColors.primary,
                              minimumSize: const Size(64, 48),
                            ),
                            child: Text(l10n.welcomeSkip),
                          ),
                        ],
                      ),
                    ),
                    Expanded(
                      child: PageView.builder(
                        controller: _controller,
                        itemCount: welcomePages.length,
                        onPageChanged: (index) => setState(() => _page = index),
                        itemBuilder: (context, index) => LayoutBuilder(
                          builder: (context, box) {
                            final page = welcomePages[index];
                            final artSize = (box.maxHeight * .46).clamp(
                              135.0,
                              265.0,
                            );
                            return SingleChildScrollView(
                              key: ValueKey('welcome-scroll-$index'),
                              child: ConstrainedBox(
                                constraints: BoxConstraints(
                                  minHeight: box.maxHeight,
                                ),
                                child: Padding(
                                  padding: const EdgeInsets.symmetric(
                                    horizontal: 22,
                                    vertical: 18,
                                  ),
                                  child: Column(
                                    mainAxisAlignment: MainAxisAlignment.center,
                                    children: [
                                      ExcludeSemantics(
                                        child: SizedBox(
                                          width: artSize,
                                          height: artSize,
                                          child: WelcomeArt(
                                            index: index,
                                            accent: page.color,
                                            active: index == _page,
                                          ),
                                        ),
                                      ),
                                      const SizedBox(height: 30),
                                      Text(
                                        page.title(l10n),
                                        key: ValueKey('welcome-title-$index'),
                                        textAlign: TextAlign.center,
                                        style: const TextStyle(
                                          color: QfColors.text,
                                          fontFamily: qfDisplay,
                                          fontWeight: FontWeight.w700,
                                          fontSize: 30,
                                          height: 1.08,
                                        ),
                                      ),
                                      const SizedBox(height: 16),
                                      Text(
                                        page.description(l10n),
                                        textAlign: TextAlign.center,
                                        style: const TextStyle(
                                          color: QfColors.text2,
                                          fontFamily: 'Gilroy Medium',
                                          fontSize: 15,
                                          height: 1.55,
                                        ),
                                      ),
                                    ],
                                  ),
                                ),
                              ),
                            );
                          },
                        ),
                      ),
                    ),
                    Padding(
                      padding: const EdgeInsets.fromLTRB(20, 0, 20, 16),
                      child: Column(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Semantics(
                            label: l10n.welcomeScreenOf(_page + 1, welcomePages.length),
                            child: Row(
                              mainAxisAlignment: MainAxisAlignment.center,
                              children: List.generate(
                                5,
                                (index) => SizedBox(
                                  width: 44,
                                  height: 44,
                                  child: IconButton(
                                    tooltip: l10n.welcomeGoTo(index + 1),
                                    onPressed: () => _goTo(index),
                                    padding: EdgeInsets.zero,
                                    icon: AnimatedContainer(
                                      duration:
                                          MediaQuery.disableAnimationsOf(
                                            context,
                                          )
                                          ? Duration.zero
                                          : const Duration(milliseconds: 200),
                                      height: 6,
                                      width: _page == index ? 24 : 6,
                                      color: _page == index
                                          ? QfColors.primary
                                          : QfColors.border,
                                    ),
                                  ),
                                ),
                              ),
                            ),
                          ),
                          SizedBox(
                            width: double.infinity,
                            height: 52,
                            child: FilledButton(
                              onPressed: () =>
                                  _page == 4 ? _finish() : _goTo(_page + 1),
                              style: qfFilled(QfColors.primary),
                              child: Text(_page == 4 ? l10n.welcomeStart : l10n.welcomeNext),
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
