import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gobet/l10n/app_locale.dart';
import 'package:gobet/product/live_guide.dart';
import 'package:gobet/product/live_more.dart';
import 'package:gobet/product/live_widgets.dart';

void main() {
  tearDown(() => AppLocale.instance.reset());

  Widget buildHost(Widget child, {Size size = const Size(390, 844)}) => MaterialApp(
        localizationsDelegates: AppLocalizations.localizationsDelegates,
        supportedLocales: AppLocalizations.supportedLocales,
        locale: AppLocale.instance.locale,
        theme: liveTheme(),
        home: MediaQuery(
          data: MediaQueryData(size: size),
          child: child,
        ),
      );

  group('Guía de pronósticos (GuideScreen)', () {
    testWidgets('renderiza los 6 temas y permite navegar con chips y botones', (tester) async {
      await AppLocale.instance.select('es');
      await tester.pumpWidget(buildHost(const GuideScreen()));
      await tester.pumpAndSettle();

      // Cabecera y contador inicial
      expect(find.text('GUÍA DE PRONÓSTICOS'), findsOneWidget);
      expect(find.text('1 / 6'), findsOneWidget);

      // 6 chips de temas
      for (var i = 0; i < 6; i++) {
        expect(find.byKey(ValueKey('guide-topic-$i')), findsOneWidget);
      }

      // Diagrama de probabilidad visible
      expect(find.text('75 % = 3 DE CADA 4'), findsOneWidget);

      // Botón Anterior deshabilitado al inicio
      final prevFinder = find.byKey(const ValueKey('guide-prev'));
      expect(prevFinder, findsOneWidget);

      // Botón Siguiente avanza al tema 2
      final nextFinder = find.byKey(const ValueKey('guide-next'));
      await tester.tap(nextFinder);
      await tester.pumpAndSettle();

      expect(find.text('2 / 6'), findsOneWidget);
      expect(find.text('PROBABILIDAD DEL MODELO'), findsOneWidget);

      // Tocar directamente el chip del tema 5 (Escalera)
      await tester.tap(find.byKey(const ValueKey('guide-topic-4')));
      await tester.pumpAndSettle();

      expect(find.text('5 / 6'), findsOneWidget);
      expect(find.text('4 EN JUEGO'), findsOneWidget);

      // Botón Anterior retrocede al tema 4 (Parley)
      await tester.tap(prevFinder);
      await tester.pumpAndSettle();

      expect(find.text('4 / 6'), findsOneWidget);
      expect(find.text('42%'), findsOneWidget);
    });

    testWidgets('renderiza limpiamente a 320 px de ancho sin desbordes', (tester) async {
      tester.view.physicalSize = const Size(320, 700);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);

      await AppLocale.instance.select('es');
      await tester.pumpWidget(buildHost(const GuideScreen(), size: const Size(320, 700)));
      await tester.pumpAndSettle();

      // Recorrer los 6 temas a 320 px con el botón siguiente
      for (var i = 0; i < 5; i++) {
        await tester.tap(find.byKey(const ValueKey('guide-next')));
        await tester.pumpAndSettle();
        expect(tester.takeException(), isNull);
      }
    });
  });

  group('Menú Más (showMoreSheet)', () {
    testWidgets('despliega secciones VIP, Aprende, App, Legal y botones funcionales', (tester) async {
      await AppLocale.instance.select('es');
      var vipCalled = false;
      var sportsCalled = false;

      await tester.pumpWidget(
        buildHost(
          Builder(
            builder: (context) => Scaffold(
              body: Center(
                child: ElevatedButton(
                  onPressed: () => showMoreSheet(
                    context,
                    onMySports: () => sportsCalled = true,
                    onVip: () => vipCalled = true,
                  ),
                  child: const Text('Abrir'),
                ),
              ),
            ),
          ),
        ),
      );
      await tester.pumpAndSettle();

      // Abrir hoja
      await tester.tap(find.text('Abrir'));
      await tester.pumpAndSettle();

      // Ver secciones
      expect(find.text('QUANT'), findsOneWidget);
      expect(find.text('FUT'), findsOneWidget);
      expect(find.text('// APRENDE'), findsOneWidget);
      expect(find.text('// APP'), findsOneWidget);
      expect(find.text('// LEGAL'), findsOneWidget);

      // Acceso VIP
      final vipTile = find.text('Todos los pronósticos, sin monedas');
      expect(vipTile, findsOneWidget);
      await tester.tap(vipTile);
      await tester.pumpAndSettle();
      expect(vipCalled, isTrue);

      // Reabrir para probar Mis deportes y cerrar
      await tester.tap(find.text('Abrir'));
      await tester.pumpAndSettle();

      final sportsTile = find.byKey(const ValueKey('more-sports'));
      expect(sportsTile, findsOneWidget);
      await tester.tap(sportsTile);
      await tester.pumpAndSettle();
      expect(sportsCalled, isTrue);
    });
  });
}
