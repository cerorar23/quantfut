import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../bottombar.dart';
import '../product/welcome_art.dart';

class WelcomePage {
  const WelcomePage(this.title, this.description, this.color);
  final String title;
  final String description;
  final Color color;
}

const welcomePages = [
  WelcomePage(
    'Fútbol y NBA,\ncon otra perspectiva',
    'Descubre el lado estadístico del deporte: partidos, análisis y '
        'pronósticos del proyecto que ya conoces en la web.',
    Color(0xff00d5ee),
  ),
  WelcomePage(
    'Cada partido,\ncon más contexto',
    'La forma reciente, el cara a cara y las estadísticas ayudan a '
        'entender lo que puede pasar. Empieza por los datos.',
    Color(0xffffb600),
  ),
  WelcomePage(
    'Más mercados.\nMás información.',
    'Goles, córners, hándicap y estadísticas de la NBA. '
        'Conoce qué mide cada análisis antes de interpretar una selección.',
    Color(0xff00d58b),
  ),
  WelcomePage(
    'Los resultados,\na la vista',
    'Un pronóstico también se entiende después del partido. '
        'El historial permite comparar estimaciones con resultados.',
    Color(0xffbd81ff),
  ),
  WelcomePage(
    'Todo empieza\npor informarte',
    'Una probabilidad no es una certeza. Explora el contenido, '
        'revisa el contexto y forma tu propio criterio.',
    Color(0xff00d5ee),
  ),
];

class SecondScreen extends StatefulWidget {
  const SecondScreen({super.key});
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
    final accent = welcomePages[_page].color;
    return AnnotatedRegion<SystemUiOverlayStyle>(
      value: SystemUiOverlayStyle.light.copyWith(
        statusBarColor: Colors.transparent,
        systemNavigationBarColor: const Color(0xff0c1926),
      ),
      child: Scaffold(
        backgroundColor: const Color(0xff090f1a),
        body: Container(
          decoration: const BoxDecoration(
            gradient: LinearGradient(
              begin: Alignment.topCenter,
              end: Alignment.bottomCenter,
              colors: [Color(0xff090f1a), Color(0xff0c1926)],
            ),
          ),
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
                            'Q.',
                            style: TextStyle(
                              fontFamily: 'Gilroy ExtraBold',
                              fontSize: 25,
                              color: Color(0xff00d58b),
                            ),
                          ),
                          const SizedBox(width: 8),
                          const Text(
                            'QuantFut',
                            style: TextStyle(
                              color: Color(0xffc0cad7),
                              fontSize: 13,
                              fontFamily: 'Gilroy Bold',
                            ),
                          ),
                          const Spacer(),
                          TextButton(
                            onPressed: _finish,
                            style: TextButton.styleFrom(
                              foregroundColor: const Color(0xffb4bfce),
                              minimumSize: const Size(64, 48),
                            ),
                            child: const Text('Saltar'),
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
                                        page.title,
                                        key: ValueKey('welcome-title-$index'),
                                        textAlign: TextAlign.center,
                                        style: const TextStyle(
                                          color: Color(0xffe9edf5),
                                          fontFamily: 'Gilroy ExtraBold',
                                          fontSize: 27,
                                          height: 1.12,
                                        ),
                                      ),
                                      const SizedBox(height: 16),
                                      Text(
                                        page.description,
                                        textAlign: TextAlign.center,
                                        style: const TextStyle(
                                          color: Color(0xffa0adbd),
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
                            label: 'Pantalla ${_page + 1} de 5',
                            child: Row(
                              mainAxisAlignment: MainAxisAlignment.center,
                              children: List.generate(
                                5,
                                (index) => SizedBox(
                                  width: 40,
                                  height: 44,
                                  child: IconButton(
                                    tooltip: 'Ir a bienvenida ${index + 1}',
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
                                      width: _page == index ? 22 : 6,
                                      decoration: BoxDecoration(
                                        color: _page == index
                                            ? accent
                                            : const Color(0xff425060),
                                        borderRadius: BorderRadius.circular(8),
                                      ),
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
                              style: FilledButton.styleFrom(
                                backgroundColor: accent,
                                foregroundColor: const Color(0xff07121a),
                                shape: RoundedRectangleBorder(
                                  borderRadius: BorderRadius.circular(14),
                                ),
                                textStyle: const TextStyle(
                                  fontFamily: 'Gilroy ExtraBold',
                                  fontSize: 16,
                                ),
                              ),
                              child: Text(_page == 4 ? 'Empezar' : 'Siguiente'),
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
