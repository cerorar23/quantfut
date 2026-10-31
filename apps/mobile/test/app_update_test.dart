import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gobet/core/app_update.dart';
import 'package:gobet/l10n/app_localizations.dart';
import 'package:gobet/product/qf_theme.dart';

Map<String, dynamic> policy() => {
  'app_version_android': '13.0.0+71',
  'app_version_ios': '13.0.3+81',
  'min_build_android': 65,
  'min_build_ios': 75,
  'force_update_app': false,
  'app_link': 'https://play.google.com/store/apps/details?id=pro.quantfut',
  'ios_app_link': 'https://apps.apple.com/app/id123456',
};

void main() {
  testWidgets(
    'Startup and resume preserve mandatory dialog until policy clears',
    (tester) async {
      final key = GlobalKey<NavigatorState>();
      AppUpdate? next = AppUpdate(
        '1.0.0+71',
        Uri.parse('https://play.google.com/store/apps/details?id=test'),
        true,
      );
      var offline = false;
      await tester.pumpWidget(
        MaterialApp(
          navigatorKey: key,
          locale: const Locale('es'),
          localizationsDelegates: AppLocalizations.localizationsDelegates,
          supportedLocales: AppLocalizations.supportedLocales,
          builder: (_, child) => AppUpdateGate(
            navigatorKey: key,
            checkForUpdate: () async {
              if (offline) throw Exception('offline');
              return next;
            },
            child: child!,
          ),
          home: const Scaffold(body: Text('Inicio')),
        ),
      );
      await tester.pumpAndSettle();
      expect(find.byType(AlertDialog), findsOneWidget);
      tester.binding.handleAppLifecycleStateChanged(
        AppLifecycleState.paused,
      );
      tester.binding.handleAppLifecycleStateChanged(
        AppLifecycleState.resumed,
      );
      await tester.pumpAndSettle();
      expect(find.byType(AlertDialog), findsOneWidget);
      offline = true;
      tester.binding.handleAppLifecycleStateChanged(
        AppLifecycleState.paused,
      );
      tester.binding.handleAppLifecycleStateChanged(
        AppLifecycleState.resumed,
      );
      await tester.pumpAndSettle();
      expect(find.byType(AlertDialog), findsOneWidget);
      offline = false;
      next = null;
      tester.binding.handleAppLifecycleStateChanged(
        AppLifecycleState.paused,
      );
      tester.binding.handleAppLifecycleStateChanged(
        AppLifecycleState.resumed,
      );
      await tester.pumpAndSettle();
      expect(find.byType(AlertDialog), findsNothing);
      expect(find.text('Inicio'), findsOneWidget);
    },
  );

  testWidgets('Unavailable configuration allows startup', (tester) async {
    final key = GlobalKey<NavigatorState>();
    await tester.pumpWidget(
      MaterialApp(
        navigatorKey: key,
        builder: (_, child) => AppUpdateGate(
          navigatorKey: key,
          checkForUpdate: () async => throw Exception('offline'),
          child: child!,
        ),
        home: const Scaffold(body: Text('Inicio')),
      ),
    );
    await tester.pumpAndSettle();
    expect(find.byType(CircularProgressIndicator), findsNothing);
    expect(find.text('Inicio'), findsOneWidget);
  });

  test('Compares integer builds separately per platform', () {
    expect(AppUpdate.evaluate(policy(), 'android', '71'), isNull);
    expect(AppUpdate.evaluate(policy(), 'android', '72'), isNull);
    expect(AppUpdate.evaluate(policy(), 'android', '70')!.required, isFalse);
    expect(AppUpdate.evaluate(policy(), 'android', '64')!.required, isTrue);
    expect(
      AppUpdate.evaluate(policy(), 'ios', '80')!.store.host,
      'apps.apple.com',
    );
    expect(AppUpdate.evaluate(policy(), 'ios', '74')!.required, isTrue);
    expect(AppUpdate.evaluate(policy(), 'windows', '1'), isNull);
    expect(AppUpdate.evaluate(policy(), 'android', 'invalid'), isNull);
    expect(
      AppUpdate.evaluate(
        policy()..['app_version_android'] = '1.0.0+100',
        'android',
        '99',
      ),
      isNotNull,
    );
  });

  test('Supports force indicators and ignores broken policy', () {
    for (final force in [true, 1, '1', 'true']) {
      expect(
        AppUpdate.evaluate(
          policy()..['force_update_app'] = force,
          'android',
          '70',
        )!.required,
        isTrue,
      );
    }
    expect(
      AppUpdate.evaluate(
        policy()..['app_version_android'] = 'broken',
        'android',
        '1',
      ),
      isNull,
    );
    expect(
      AppUpdate.evaluate(
        policy()..['app_link'] = 'https://evil.example/app',
        'android',
        '1',
      ),
      isNull,
    );
    expect(
      AppUpdate.evaluate(policy()..['min_build_android'] = 90, 'android', '1'),
      isNull,
    );
  });

  for (final required in [true, false]) {
    testWidgets('Dialog blocking=$required and store failure can retry', (
      tester,
    ) async {
      var opens = 0;
      await tester.pumpWidget(
        MaterialApp(
          locale: const Locale('es'),
          localizationsDelegates: AppLocalizations.localizationsDelegates,
          supportedLocales: AppLocalizations.supportedLocales,
          home: Builder(
            builder: (context) => Scaffold(
              body: TextButton(
                onPressed: () => showDialog<void>(
                  context: context,
                  barrierDismissible: false,
                  builder: (_) => AppUpdateDialog(
                    update: AppUpdate(
                      '1.0.0+71',
                      Uri.parse(
                        'https://play.google.com/store/apps/details?id=test',
                      ),
                      required,
                    ),
                    openStore: (_) async {
                      opens++;
                      return false;
                    },
                  ),
                ),
                child: const Text('Abrir'),
              ),
            ),
          ),
        ),
      );
      await tester.tap(find.text('Abrir'));
      await tester.pumpAndSettle();
      await tester.tapAt(const Offset(5, 5));
      await tester.pumpAndSettle();
      expect(find.byType(AlertDialog), findsOneWidget);
      expect(find.text('Más tarde'), required ? findsNothing : findsOneWidget);
      // Piel v3: actualizar es una acción azul (el ámbar queda para VIP y monedas), de 44 dp.
      final now = find.byKey(const ValueKey('update-now'));
      expect(
        tester.widget<FilledButton>(now).style?.backgroundColor?.resolve(<WidgetState>{}),
        QfColors.primary,
      );
      expect(tester.getSize(now).height, greaterThanOrEqualTo(44));
      expect(find.text('1.0.0+71'), findsOneWidget);
      await tester.tap(find.text('Actualizar ahora'));
      await tester.pumpAndSettle();
      expect(opens, 1);
      expect(
        find.text('No se pudo abrir la tienda. Inténtalo de nuevo.'),
        findsOneWidget,
      );
      await tester.tap(find.text('Actualizar ahora'));
      await tester.pumpAndSettle();
      expect(opens, 2);
      await tester.binding.handlePopRoute();
      await tester.pumpAndSettle();
      expect(
        find.byType(AlertDialog),
        required ? findsOneWidget : findsNothing,
      );
    });
  }
}
