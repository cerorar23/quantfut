// Pantalla de acceso: carrusel de presentación + tarjeta con Google y consentimiento.
import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gobet/core/access_screen.dart';
import 'package:gobet/l10n/app_locale.dart';
import 'package:gobet/product/live_widgets.dart';

const languages = ['es', 'en', 'pt', 'fr', 'it', 'de'];

class _Host extends StatefulWidget {
  const _Host({this.busy = false, this.docs = true, this.error, this.linking = false, this.onGoogle, this.onTerms, this.onPrivacy});
  final bool busy, docs, linking;
  final String? error;
  final VoidCallback? onGoogle, onTerms, onPrivacy;
  @override
  State<_Host> createState() => _HostState();
}

class _HostState extends State<_Host> {
  bool consent = false;
  @override
  Widget build(BuildContext context) => AccessScreen(
    busy: widget.busy,
    consent: consent,
    docsReady: widget.docs,
    onConsent: (v) => setState(() => consent = v),
    onGoogle: widget.onGoogle ?? () {},
    onTerms: widget.onTerms ?? () {},
    onPrivacy: widget.onPrivacy ?? () {},
    error: widget.error,
    linkingForm: widget.linking ? const TextField(key: ValueKey('link-email')) : null,
    actions: const [Text('acciones')],
  );
}

Future<void> pump(
  WidgetTester tester,
  Widget body, {
  Size size = const Size(390, 844),
  String code = 'es',
}) async {
  tester.view.physicalSize = size;
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);
  await AppLocale.instance.select(code);
  await tester.pumpWidget(
    MaterialApp(
      localizationsDelegates: AppLocalizations.localizationsDelegates,
      supportedLocales: AppLocalizations.supportedLocales,
      locale: AppLocale.instance.locale,
      theme: liveTheme(),
      home: body,
    ),
  );
  await tester.pump(const Duration(milliseconds: 500));
}

void main() {
  setUpAll(() async {
    for (final f in {
      'Gilroy Medium': 'fonts/Gilroy-Medium.ttf',
      'Gilroy Bold': 'fonts/Gilroy-Bold.otf',
      'Gilroy ExtraBold': 'fonts/Gilroy-ExtraBold.otf',
      'MaterialIcons': 'fonts/MaterialIcons-Regular.otf',
    }.entries) {
      await (FontLoader(f.key)..addFont(rootBundle.load(f.value))).load();
    }
  });
  tearDown(() => AppLocale.instance.reset());

  testWidgets('muestra la primera diapositiva, la tarjeta de acceso y el aviso', (tester) async {
    await pump(tester, const _Host());
    expect(find.text('Entiende cada partido con datos.'), findsOneWidget);
    expect(find.text('PROBABILIDADES REALES'), findsOneWidget);
    expect(find.text('Inicia sesión para continuar'), findsOneWidget);
    expect(find.text('Continuar con Google'), findsOneWidget);
    expect(find.textContaining('Solo con fines informativos'), findsOneWidget);
    expect(find.byKey(const ValueKey('language-button')), findsOneWidget);
  });

  testWidgets('desliza entre las cinco diapositivas y los puntos las siguen', (tester) async {
    await pump(tester, const _Host());
    for (final title in [
      'Pronósticos con su acierto a la vista.',
      'Sube escalón a escalón.',
      'Un boleto sellado antes de los partidos.',
      'Gana monedas y desbloquea.',
    ]) {
      await tester.fling(find.byKey(const ValueKey('access-carousel')), const Offset(-300, 0), 1200);
      await tester.pump(const Duration(milliseconds: 600));
      expect(find.text(title), findsOneWidget);
    }
    // Un punto lleva de vuelta a la primera.
    await tester.tap(find.byKey(const ValueKey('access-dot-0')));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 800));
    expect(find.text('Entiende cada partido con datos.'), findsOneWidget);
  });

  testWidgets('Google sin casilla avisa y no inicia sesión; con casilla sí', (tester) async {
    var google = 0;
    await pump(tester, _Host(onGoogle: () => google++));
    await tester.tap(find.byKey(const ValueKey('google-button')));
    await tester.pump(const Duration(milliseconds: 500));
    expect(google, 0);
    expect(find.text('Marca la casilla para continuar.'), findsOneWidget);
    await tester.tap(find.byKey(const ValueKey('consent')));
    await tester.pump();
    expect(find.text('Marca la casilla para continuar.'), findsNothing);
    await tester.tap(find.byKey(const ValueKey('google-button')));
    await tester.pump();
    expect(google, 1);
  });

  testWidgets('los enlaces legales de la frase abren cada documento', (tester) async {
    var terms = 0, privacy = 0;
    await pump(tester, _Host(onTerms: () => terms++, onPrivacy: () => privacy++));
    Future<void> tapSpan(String label) async {
      final rich = find.byWidgetPredicate(
        (w) => w is RichText && w.text.toPlainText().contains(label) && w.text.toPlainText().contains('18'),
      );
      expect(rich, findsOneWidget);
      final box = tester.renderObject<RenderParagraph>(rich);
      final text = box.text.toPlainText();
      final i = text.indexOf(label);
      final rects = box.getBoxesForSelection(TextSelection(baseOffset: i, extentOffset: i + 4));
      await tester.tapAt(box.localToGlobal(rects.first.toRect().center));
      await tester.pump();
    }

    await tapSpan('Términos de uso');
    await tapSpan('Política de privacidad');
    expect(terms, 1);
    expect(privacy, 1);
  });

  testWidgets('conectando: botón con aviso y sin acción; sin documentos: botón apagado', (tester) async {
    await pump(tester, const _Host(busy: true));
    expect(find.text('Conectando…'), findsOneWidget);
    expect(tester.widget<OutlinedButton>(find.byKey(const ValueKey('google-button'))).onPressed, isNull);
    await pump(tester, const _Host(docs: false));
    expect(tester.widget<OutlinedButton>(find.byKey(const ValueKey('google-button'))).onPressed, isNull);
  });

  testWidgets('muestra el error y las acciones secundarias', (tester) async {
    await pump(tester, const _Host(error: 'Algo falló'));
    expect(find.text('Algo falló'), findsOneWidget);
    expect(find.text('acciones'), findsOneWidget);
  });

  testWidgets('vincular cuenta: el formulario sustituye al carrusel y al botón de Google', (tester) async {
    await pump(tester, const _Host(linking: true));
    expect(find.byKey(const ValueKey('link-email')), findsOneWidget);
    expect(find.byKey(const ValueKey('access-carousel')), findsNothing);
    expect(find.byKey(const ValueKey('google-button')), findsNothing);
  });

  for (final code in languages) {
    testWidgets('se pinta en $code sin desbordes, también en 320 px y con aviso', (tester) async {
      for (final size in const [Size(390, 844), Size(320, 568)]) {
        await pump(tester, const _Host(error: 'Error'), size: size, code: code);
        await tester.tap(find.byKey(const ValueKey('google-button')));
        await tester.pump(const Duration(milliseconds: 500));
        for (var i = 0; i < 4; i++) {
          await tester.fling(find.byKey(const ValueKey('access-carousel')), const Offset(-300, 0), 1200);
          await tester.pump(const Duration(milliseconds: 600));
          expect(tester.takeException(), isNull, reason: '$code $size diapositiva ${i + 2}');
        }
      }
    });
  }

  testWidgets('con animaciones desactivadas no deja controladores en marcha', (tester) async {
    tester.view.physicalSize = const Size(390, 844);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    await AppLocale.instance.select('es');
    await tester.pumpWidget(
      MediaQuery(
        data: const MediaQueryData(disableAnimations: true, size: Size(390, 844)),
        child: MaterialApp(
          localizationsDelegates: AppLocalizations.localizationsDelegates,
          supportedLocales: AppLocalizations.supportedLocales,
          locale: AppLocale.instance.locale,
          theme: liveTheme(),
          home: const _Host(),
        ),
      ),
    );
    await tester.pumpAndSettle();
    expect(find.text('Entiende cada partido con datos.'), findsOneWidget);
  });
}
