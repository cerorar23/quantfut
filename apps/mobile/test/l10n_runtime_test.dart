// La app se pinta en los 6 idiomas sin errores (incluidos desbordes de texto) y el
// cambio de idioma en caliente actualiza la pantalla sin perder la navegación.
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gobet/l10n/app_locale.dart';
import 'package:gobet/product/live_api.dart';
import 'package:gobet/product/live_profile.dart';
import 'package:gobet/product/live_shell.dart';
import 'package:gobet/product/live_widgets.dart';

const languages = ['es', 'en', 'pt', 'fr', 'it', 'de'];

class _Api extends QuantFutApi {
  @override
  Future<JsonMap> home(DateTime date) async => {
    'config': {
      'features': {
        for (final k in ['agenda', 'alta_probabilidad', 'escalera', 'vip'])
          k: {'enabled': true, 'message': 'x'},
      },
    },
    'rewards': {'enabled': true, 'unlock_cost': 100},
    'plans': [],
    'agenda': [
      {
        'match_id': 'm1',
        'kickoff_utc': DateTime.now()
            .add(const Duration(hours: 2))
            .toUtc()
            .toIso8601String(),
        'local': {'nombre': 'Equipo A'},
        'visitante': {'nombre': 'Equipo B'},
        'liga': {'nombre': 'Liga'},
        'probabilities': {'home': .6, 'draw': .25, 'away': .15},
      },
    ],
    'alta_probabilidad': {
      'estado': 'activa',
      'proximos': [
        {
          'match_id': 'm1',
          'pick_key': 'm1',
          'local': 'Equipo A',
          'visitante': 'Equipo B',
          'market': 'totals',
          'selection': 'over',
          'line': 2.5,
          'prob': .8,
          'ref_price': 1.5,
          'ref_book': 'Casa',
          'free': true,
        },
      ],
      'vip': [],
    },
    'escalera': {'activo': true, 'actuales': []},
  };

  @override
  Future<dynamic> request(
    String path, {
    JsonMap? query,
    JsonMap? body,
    bool retry = true,
  }) async {
    if (path == '/mobile/v1/rewards') {
      return {
        'settings': {
          'enabled': true,
          'unlock_cost': 100,
          'attendance_coins': [30, 35, 35, 40, 40, 45, 50],
          'message': '',
        },
        'signed_in': false,
        'providers': [
          {'provider': 'tapjoy', 'name': 'Tapjoy', 'available': true},
        ],
        'wallet': null,
        'ledger': [],
        'referrals': null,
        'terms': '',
      };
    }
    return {};
  }
}

Future<void> pumpShell(WidgetTester tester) async {
  tester.view.physicalSize = const Size(390, 844);
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);
  await tester.pumpWidget(
    ListenableBuilder(
      listenable: AppLocale.instance,
      builder: (context, _) => MaterialApp(
        localizationsDelegates: AppLocalizations.localizationsDelegates,
        supportedLocales: AppLocalizations.supportedLocales,
        locale: AppLocale.instance.locale,
        theme: liveTheme(),
        debugShowCheckedModeBanner: false,
        home: ProductShell(api: _Api()),
      ),
    ),
  );
  await tester.pumpAndSettle();
}

/// Etiqueta de la barra inferior (hay textos iguales fuera de ella, p. ej. «Home»).
Finder navLabel(String label) => find.descendant(
  of: find.byType(BottomNavigationBar),
  matching: find.text(label),
);

void main() {
  // Fuentes reales de la app: con la fuente de prueba (Ahem) todo desborda.
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

  for (final code in languages) {
    testWidgets('las 5 pestañas se pintan en $code sin errores', (
      tester,
    ) async {
      AppLocale.instance.reset();
      await AppLocale.instance.select(code);
      final l10n = lookupAppLocalizations(Locale(code));
      await pumpShell(tester);

      expect(navLabel(l10n.navHome), findsOneWidget);
      expect(find.text(l10n.homeTicketsTitle), findsOneWidget);

      await tester.tap(navLabel(l10n.navPredictions));
      await tester.pumpAndSettle();
      expect(find.text(l10n.streamLadder), findsOneWidget);
      // El texto del pronóstico se genera en el idioma actual desde market/selection/line.
      expect(
        find.text(l10n.selGoals('over', code == 'en' ? '2.5' : '2,5')),
        findsWidgets,
      );

      await tester.tap(navLabel(l10n.navMarkets));
      // La pestaña Mercados tiene una animación en bucle: no «se asienta».
      await tester.pump(const Duration(seconds: 1));
      await tester.pump(const Duration(seconds: 1));
      expect(find.text(l10n.marketsAndResults), findsOneWidget);

      await tester.tap(navLabel(l10n.navCoins));
      await tester.pumpAndSettle();
      expect(find.text(l10n.rewardsMyCoins), findsOneWidget);
      expect(find.text(l10n.rewardsOffersTitle), findsOneWidget);

      await tester.tap(navLabel(l10n.navProfile));
      await tester.pumpAndSettle();
      expect(find.text(l10n.profileTitle), findsOneWidget);

      // Un desborde de texto o cualquier excepción de render falla la prueba.
      expect(tester.takeException(), isNull);
    });
  }

  testWidgets('cambiar de idioma en caliente actualiza la pantalla', (
    tester,
  ) async {
    await pumpShell(tester);
    expect(navLabel('Inicio'), findsOneWidget);

    await tester.tap(navLabel('Perfil'));
    await tester.pumpAndSettle();
    expect(find.text('Perfil y configuración'), findsOneWidget);

    await AppLocale.instance.select('en');
    await tester.pumpAndSettle();
    // Sigue en la misma pestaña (Perfil) pero ya en inglés.
    expect(find.text('Profile and settings'), findsOneWidget);
    expect(navLabel('Home'), findsOneWidget);
    expect(navLabel('Inicio'), findsNothing);

    await AppLocale.instance.select('de');
    await tester.pumpAndSettle();
    expect(find.text('Profil und Einstellungen'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets('el selector de idioma del perfil cambia el idioma', (
    tester,
  ) async {
    await pumpShell(tester);
    await tester.tap(navLabel('Perfil'));
    await tester.pumpAndSettle();

    final tile = find.byKey(const ValueKey('profile-idiomas'));
    await tester.scrollUntilVisible(
      tile,
      200,
      scrollable: find
          .descendant(
            of: find.byType(LiveProfileScreen),
            matching: find.byType(Scrollable),
          )
          .first,
    );
    await tester.tap(tile);
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const ValueKey('language-fr')));
    await tester.pumpAndSettle();

    expect(AppLocale.instance.code, 'fr');
    expect(navLabel('Accueil'), findsOneWidget);
  });
}
