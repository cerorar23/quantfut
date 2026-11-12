// Catálogo en pantalla: Beta en «Mis deportes», deporte nuevo con icono genérico, NBA apagada y avisos.
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gobet/core/firebase_preferences.dart';
import 'package:gobet/l10n/app_locale.dart';
import 'package:gobet/product/live_api.dart';
import 'package:gobet/product/live_widgets.dart';
import 'package:gobet/product/my_sports.dart';
import 'package:gobet/product/sport_selector.dart';
import 'package:gobet/product/sports.dart';

Map<String, Object?> sport(String id, int orden, {String estado = 'on', String icono = 'generico', String? es}) => {
  'id': id,
  'orden': orden,
  'estado': estado,
  'nombre': {'es': es ?? id, 'en': '${es ?? id} EN'},
  'icono': icono,
  'color': '#336699',
  'secciones': ['high'],
};

void install(List<Map<String, Object?>> sports) =>
    sportCatalogNotifier.value = SportCatalog.fromJson({'deportes': sports})!;

class _Api extends QuantFutApi {
  @override
  Future<dynamic> request(String path, {JsonMap? query, JsonMap? body, bool retry = true}) async => {
    'notifications': [
      {'notification_id': 1, 'title': 'Aviso NBA', 'body': 'b', 'sport': 'nba'},
      {'notification_id': 2, 'title': 'Aviso golf', 'body': 'b', 'sport': 'golf'},
      {'notification_id': 3, 'title': 'Aviso raro', 'body': 'b', 'sport': 'curling'},
    ],
  };
}

Widget host(Widget child) => MaterialApp(
  localizationsDelegates: AppLocalizations.localizationsDelegates,
  supportedLocales: AppLocalizations.supportedLocales,
  locale: AppLocale.instance.locale,
  theme: liveTheme(),
  home: Scaffold(body: ListView(children: [child])),
);

SportPrefs prefsOn(Map<String, String> store) => SportPrefs(
  read: (key) async => store[key],
  write: (key, value) async => store[key] = value,
);

void main() {
  tearDown(() {
    sportCatalogNotifier.value = SportCatalog.builtIn;
    AppLocale.instance.reset();
  });

  testWidgets('un preview sale en «Mis deportes» con la etiqueta Beta, oculto, y se puede activar', (tester) async {
    await AppLocale.instance.select('es');
    install([sport('futbol', 1, icono: 'futbol'), sport('golf', 2, estado: 'preview', icono: 'golf'), sport('nba', 3)]);
    final store = <String, String>{};
    await tester.pumpWidget(host(MySportsSection(prefs: prefsOn(store), onChanged: () async {})));
    await tester.pumpAndSettle();

    expect(find.byKey(const ValueKey('my-sport-golf')), findsOneWidget);
    expect(find.descendant(of: find.byKey(const ValueKey('my-sport-golf')), matching: find.text('BETA')), findsOneWidget);
    expect(find.text('BETA'), findsOneWidget, reason: 'solo el preview lleva la etiqueta');
    Switch golf() => tester.widget<Switch>(find.byKey(const ValueKey('my-sport-switch-golf')));
    expect(golf().value, isFalse);
    expect(tester.widget<Switch>(find.byKey(const ValueKey('my-sport-switch-futbol'))).value, isTrue);

    await tester.tap(find.byKey(const ValueKey('my-sport-switch-golf')));
    await tester.pumpAndSettle();
    expect(golf().value, isTrue);
    expect(store['sports_hidden'], '');
    expect(await prefsOn(store).hidden(), isEmpty);
  });

  testWidgets('la etiqueta Beta está traducida en los 6 idiomas', (tester) async {
    install([sport('futbol', 1), sport('golf', 2, estado: 'preview')]);
    for (final (code, text) in [('es', 'BETA'), ('en', 'BETA'), ('pt', 'BETA'), ('fr', 'BÊTA'), ('it', 'BETA'), ('de', 'BETA')]) {
      await AppLocale.instance.select(code);
      await tester.pumpWidget(host(MySportsSection(prefs: prefsOn({}), onChanged: () async {})));
      await tester.pumpAndSettle();
      expect(find.text(text), findsOneWidget, reason: code);
    }
  });

  testWidgets('un deporte nuevo (golf) con icono desconocido: genérico en el selector y en «Mis deportes»', (tester) async {
    await AppLocale.instance.select('en');
    install([sport('futbol', 1, icono: 'futbol'), sport('golf', 2, icono: 'icono_del_futuro', es: 'Golf')]);
    await tester.pumpWidget(
      MaterialApp(
        localizationsDelegates: AppLocalizations.localizationsDelegates,
        supportedLocales: AppLocalizations.supportedLocales,
        locale: AppLocale.instance.locale,
        home: Scaffold(
          body: Column(
            children: [
              SportSelector(sports: sportCatalog.ids, value: 'golf', onChanged: (_) {}),
              Expanded(child: MySportsSection(prefs: prefsOn({}), onChanged: () async {})),
            ],
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();
    expect(tester.takeException(), isNull);
    final chip = find.byKey(const ValueKey('sport-golf'));
    expect(find.descendant(of: chip, matching: find.byIcon(sportIcons['generico']!)), findsOneWidget);
    expect(find.descendant(of: chip, matching: find.text('GOLF EN')), findsOneWidget, reason: 'nombre del catálogo en inglés');
    expect(find.descendant(of: find.byKey(const ValueKey('my-sport-golf')), matching: find.byIcon(sportIcons['generico']!)), findsOneWidget);
    expect(find.descendant(of: find.byKey(const ValueKey('sport-futbol')), matching: find.byIcon(Icons.sports_soccer)), findsOneWidget);
  });

  testWidgets('NBA apagada en el catálogo: no sale en el selector ni en «Mis deportes»', (tester) async {
    await AppLocale.instance.select('es');
    install([sport('futbol', 1, icono: 'futbol'), sport('tenis', 2, icono: 'tenis')]);
    await tester.pumpWidget(
      host(
        Column(
          children: [
            SportSelector(sports: sportCatalog.ids, value: 'futbol', onChanged: (_) {}),
            MySportsSection(prefs: prefsOn({'sports_order': 'nba,futbol,tenis'}), onChanged: () async {}),
          ],
        ),
      ),
    );
    await tester.pumpAndSettle();
    expect(find.byKey(const ValueKey('sport-nba')), findsNothing);
    expect(find.byKey(const ValueKey('my-sport-nba')), findsNothing);
    expect(find.byKey(const ValueKey('sport-tenis')), findsOneWidget);
  });

  testWidgets('avisos de Firebase: etiqueta solo para deportes del catálogo; uno desconocido no rompe nada', (tester) async {
    await AppLocale.instance.select('es');
    // NBA apagada y golf nuevo con icono desconocido.
    install([sport('futbol', 1), sport('golf', 2, icono: 'raro', es: 'Golf')]);
    final api = _Api();
    addTearDown(api.dispose);
    await tester.pumpWidget(
      MaterialApp(
        localizationsDelegates: AppLocalizations.localizationsDelegates,
        supportedLocales: AppLocalizations.supportedLocales,
        locale: AppLocale.instance.locale,
        theme: liveTheme(),
        home: FirebaseInbox(api: api),
      ),
    );
    await tester.pumpAndSettle();
    expect(tester.takeException(), isNull);
    expect(find.byKey(const ValueKey('inbox-sport-golf')), findsOneWidget);
    expect(find.descendant(of: find.byKey(const ValueKey('inbox-2')), matching: find.text('GOLF')), findsOneWidget);
    expect(find.descendant(of: find.byKey(const ValueKey('inbox-2')), matching: find.byIcon(sportIcons['generico']!)), findsOneWidget);
    for (final id in [1, 3]) {
      expect(
        find.descendant(of: find.byKey(ValueKey('inbox-$id')), matching: find.byWidgetPredicate((w) => '${w.key}'.contains('inbox-sport'))),
        findsNothing,
        reason: 'aviso $id: NBA apagada y curling desconocido no llevan etiqueta',
      );
      expect(find.byKey(ValueKey('inbox-$id')), findsOneWidget, reason: 'el aviso se sigue mostrando');
    }
  });
}
