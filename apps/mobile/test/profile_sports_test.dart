// Perfil → «Mis deportes»: orden con flechas, interruptor por deporte y deporte por defecto.
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gobet/core/app_update.dart';
import 'package:gobet/l10n/app_locale.dart';
import 'package:gobet/product/live_api.dart';
import 'package:gobet/product/live_detail.dart';
import 'package:gobet/product/live_profile.dart';
import 'package:gobet/product/live_widgets.dart';
import 'package:gobet/product/qf_theme.dart';
import 'package:gobet/product/my_sports.dart';
import 'package:gobet/product/sports.dart';

class _SignedIn extends QuantFutApi {
  @override
  bool get signedIn => true;
}

class _DetailFails extends QuantFutApi {
  @override
  Future<JsonMap> detail(String id) async => throw const ApiFailure('Sin conexión');
}

SportPrefs prefsOn(Map<String, String> store) => SportPrefs(
  read: (key) async => store[key],
  write: (key, value) async => store[key] = value,
);

Future<int Function()> pump(
  WidgetTester tester,
  Map<String, String> store, {
  SportPrefs? prefs,
  bool shellFails = false,
}) async {
  var changes = 0;
  await AppLocale.instance.select('es');
  await tester.pumpWidget(
    MaterialApp(
      localizationsDelegates: AppLocalizations.localizationsDelegates,
      supportedLocales: AppLocalizations.supportedLocales,
      locale: AppLocale.instance.locale,
      theme: liveTheme(),
      home: Scaffold(
        body: ListView(
          children: [
            MySportsSection(
              prefs: prefs ?? prefsOn(store),
              onChanged: () async {
                changes++;
                if (shellFails) throw StateError('refresco');
              },
            ),
          ],
        ),
      ),
    ),
  );
  await tester.pumpAndSettle();
  return () => changes;
}

Finder row(String id) => find.byKey(ValueKey('my-sport-$id'));

bool switchOn(WidgetTester tester, String id) =>
    tester.widget<Switch>(find.byKey(ValueKey('my-sport-switch-$id'))).value;

void main() {
  tearDown(() => AppLocale.instance.reset());

  testWidgets('Mis deportes ordena con flechas y marca el primero por defecto', (tester) async {
    final store = <String, String>{};
    final changes = await pump(tester, store);
    expect(find.descendant(of: row('futbol'), matching: find.text('por defecto')), findsOneWidget);
    await tester.tap(find.byKey(const ValueKey('my-sport-down-futbol')));
    await tester.pumpAndSettle();
    expect(store['sports_order'], 'nba,futbol,tenis');
    expect(changes(), 1);
    expect(find.descendant(of: row('nba'), matching: find.text('por defecto')), findsOneWidget);
    expect(find.text('por defecto'), findsOneWidget);
    // La fila de NBA queda arriba.
    expect(tester.getTopLeft(row('nba')).dy, lessThan(tester.getTopLeft(row('futbol')).dy));
    await tester.tap(find.byKey(const ValueKey('my-sport-up-tenis')));
    await tester.pumpAndSettle();
    expect(store['sports_order'], 'nba,tenis,futbol');
  });

  testWidgets('las flechas de los extremos están apagadas y todo mide al menos 44 dp', (tester) async {
    await pump(tester, {});
    IconButton arrow(String key) => tester.widget<IconButton>(find.byKey(ValueKey(key)));
    expect(arrow('my-sport-up-futbol').onPressed, isNull);
    expect(arrow('my-sport-down-tenis').onPressed, isNull);
    expect(arrow('my-sport-down-futbol').onPressed, isNotNull);
    for (final key in ['my-sport-up-nba', 'my-sport-down-nba', 'my-sport-switch-nba']) {
      final size = tester.getSize(find.byKey(ValueKey(key)));
      expect(size.height, greaterThanOrEqualTo(44), reason: key);
      expect(size.width, greaterThanOrEqualTo(44), reason: key);
    }
  });

  testWidgets('Mis deportes no permite apagar el último visible', (tester) async {
    final store = {'sports_hidden': 'nba,tenis'};
    final changes = await pump(tester, store);
    expect(switchOn(tester, 'futbol'), isTrue);
    expect(switchOn(tester, 'nba'), isFalse);
    await tester.tap(find.byKey(const ValueKey('my-sport-switch-futbol')));
    await tester.pumpAndSettle();
    expect(switchOn(tester, 'futbol'), isTrue);
    expect(store['sports_hidden'], 'nba,tenis');
    expect(changes(), 0);
    expect(find.text('Deja al menos un deporte visible.'), findsOneWidget);
  });

  testWidgets('Versión de la app comprueba la actualización con el flujo de AppUpdate', (tester) async {
    tester.view.physicalSize = const Size(390, 2400);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    await AppLocale.instance.select('es');
    final api = QuantFutApi();
    addTearDown(api.dispose);
    AppUpdate? next;
    await tester.pumpWidget(
      MaterialApp(
        localizationsDelegates: AppLocalizations.localizationsDelegates,
        supportedLocales: AppLocalizations.supportedLocales,
        locale: AppLocale.instance.locale,
        theme: liveTheme(),
        home: Scaffold(
          body: LiveProfileScreen(
            api: api,
            data: const {},
            onVip: () {},
            onChanged: () async {},
            sportPrefs: prefsOn({}),
            checkUpdate: () async => next,
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();
    final row = find.byKey(const ValueKey('profile-version'));
    expect(tester.getSize(row).height, greaterThanOrEqualTo(44));
    await tester.tap(row);
    await tester.pumpAndSettle();
    expect(find.text('Ya tienes la última versión.'), findsOneWidget);
    next = AppUpdate('1.1.0+4', Uri.parse('https://play.google.com/store/apps/details?id=x'), false);
    await tester.tap(row);
    await tester.pumpAndSettle();
    expect(find.byType(AppUpdateDialog), findsOneWidget);
  });

  testWidgets('si falla el refresco del shell, lo guardado se queda y no hay aviso de error', (tester) async {
    final store = <String, String>{};
    final changes = await pump(tester, store, shellFails: true);
    await tester.tap(find.byKey(const ValueKey('my-sport-switch-nba')));
    await tester.pumpAndSettle();
    expect(changes(), 1);
    expect(store['sports_hidden'], 'nba');
    expect(switchOn(tester, 'nba'), isFalse);
    expect(find.text('No se pudo guardar el cambio. Inténtalo de nuevo.'), findsNothing);
    // Sigue operativo: se puede volver a cambiar.
    await tester.tap(find.byKey(const ValueKey('my-sport-switch-nba')));
    await tester.pumpAndSettle();
    expect(store['sports_hidden'], '');
  });

  testWidgets('si falla el guardado, se revierte, se avisa y el shell no se entera', (tester) async {
    final store = <String, String>{};
    final failing = SportPrefs(
      read: (key) async => store[key],
      write: (key, value) async => throw StateError('disco'),
    );
    final changes = await pump(tester, store, prefs: failing);
    await tester.tap(find.byKey(const ValueKey('my-sport-down-futbol')));
    await tester.pumpAndSettle();
    expect(changes(), 0);
    expect(find.text('No se pudo guardar el cambio. Inténtalo de nuevo.'), findsOneWidget);
    expect(tester.getTopLeft(row('futbol')).dy, lessThan(tester.getTopLeft(row('nba')).dy));
    expect(find.descendant(of: row('futbol'), matching: find.text('por defecto')), findsOneWidget);
  });

  testWidgets('ocultar el primero pasa «por defecto» al siguiente visible y avisa al shell', (tester) async {
    final store = <String, String>{};
    final changes = await pump(tester, store);
    await tester.tap(find.byKey(const ValueKey('my-sport-switch-futbol')));
    await tester.pumpAndSettle();
    expect(store['sports_hidden'], 'futbol');
    expect(switchOn(tester, 'futbol'), isFalse);
    expect(changes(), 1);
    expect(find.descendant(of: row('nba'), matching: find.text('por defecto')), findsOneWidget);
    // Volver a mostrarlo lo devuelve a su sitio de por defecto.
    await tester.tap(find.byKey(const ValueKey('my-sport-switch-futbol')));
    await tester.pumpAndSettle();
    expect(store['sports_hidden'], '');
    expect(find.descendant(of: row('futbol'), matching: find.text('por defecto')), findsOneWidget);
  });

  testWidgets('Actualizar mi acceso es una acción primary, no ámbar', (tester) async {
    tester.view.physicalSize = const Size(390, 2400);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    await AppLocale.instance.select('es');
    final api = _SignedIn()..account = {'email': 'a@b.c', 'email_verified': true};
    addTearDown(api.dispose);
    await tester.pumpWidget(
      MaterialApp(
        localizationsDelegates: AppLocalizations.localizationsDelegates,
        supportedLocales: AppLocalizations.supportedLocales,
        locale: AppLocale.instance.locale,
        theme: liveTheme(),
        home: Scaffold(
          body: LiveProfileScreen(
            api: api,
            data: const {},
            onVip: () {},
            onChanged: () async {},
            sportPrefs: prefsOn({}),
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();
    final button = tester.widget<FilledButton>(
      find.ancestor(of: find.text('Actualizar mi acceso'), matching: find.byType(FilledButton)),
    );
    expect(button.style?.backgroundColor?.resolve(<WidgetState>{}), QfColors.primary);
  });

  testWidgets('Reintentar del detalle del partido es primary, no ámbar', (tester) async {
    await AppLocale.instance.select('es');
    final api = _DetailFails();
    addTearDown(api.dispose);
    await tester.pumpWidget(
      MaterialApp(
        localizationsDelegates: AppLocalizations.localizationsDelegates,
        supportedLocales: AppLocalizations.supportedLocales,
        locale: AppLocale.instance.locale,
        theme: liveTheme(),
        home: Scaffold(body: LiveMatchDetail(api: api, id: 'x', onVip: () {})),
      ),
    );
    await tester.pumpAndSettle();
    final button = tester.widget<FilledButton>(
      find.ancestor(of: find.text('Reintentar'), matching: find.byType(FilledButton)),
    );
    expect(button.style?.backgroundColor?.resolve(<WidgetState>{}), QfColors.primary);
  });
}
