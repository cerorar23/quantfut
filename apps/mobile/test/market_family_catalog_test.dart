// Nombres de familias de mercado: catálogo del servidor → texto de la app → título del archivo.
import 'package:flutter_test/flutter_test.dart';
import 'package:gobet/l10n/app_locale.dart';
import 'package:gobet/product/market_catalog.dart';
import 'package:gobet/product/sport_catalog_store.dart';
import 'package:gobet/product/sports.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  late MarketCatalog evidence;

  setUpAll(() async {
    evidence = await MarketCatalog.load();
  });

  tearDown(() {
    sportCatalogNotifier.value = SportCatalog.builtIn;
    AppLocale.instance.reset();
  });

  SportCatalog withFamilies(List<Map<String, Object?>> familias, {String sport = 'futbol'}) => SportCatalog.fromJson({
    'deportes': [
      {
        'id': sport,
        'orden': 1,
        'estado': 'on',
        'nombre': {'es': 'x'},
        'icono': 'generico',
        'color': '#112233',
        'secciones': ['high'],
        'familias': familias,
      },
    ],
  })!;

  test('con la copia de fábrica los textos son los de siempre en los 6 idiomas', () async {
    final factory = (await loadFactorySportCatalog())!;
    for (final code in ['es', 'en', 'pt', 'fr', 'it', 'de']) {
      await AppLocale.instance.select(code);
      sportCatalogNotifier.value = SportCatalog.builtIn; // sin nombres de catálogo: el `switch` de la app
      final before = [for (final f in evidence.families) (f.localTitle, f.localSubtitle)];
      sportCatalogNotifier.value = factory;
      final after = [for (final f in evidence.families) (f.localTitle, f.localSubtitle)];
      expect(after, before, reason: code);
    }
  });

  test('el nombre del catálogo manda, en el idioma actual y cayendo a español', () async {
    sportCatalogNotifier.value = withFamilies([
      {
        'id': 'handicap',
        'orden': 1,
        'nombre': {'es': 'Hándicap del servidor', 'en': 'Server handicap'},
        'subtitulo': {'es': 'Sub del servidor'},
      },
    ]);
    final handicap = evidence.byId('handicap');
    expect(handicap.localTitle, 'Hándicap del servidor');
    await AppLocale.instance.select('en');
    expect(handicap.localTitle, 'Server handicap');
    expect(handicap.localSubtitle, 'Sub del servidor', reason: 'sin inglés cae a español');
    await AppLocale.instance.select('de');
    expect(handicap.localTitle, 'Hándicap del servidor', reason: 'alemán ausente: español');
  });

  test('sin entrada en el catálogo usa el texto de la app; sin texto de la app, el título del archivo', () {
    sportCatalogNotifier.value = withFamilies([
      {'id': 'otra', 'orden': 1, 'nombre': {'es': 'Otra'}},
    ]);
    final l10n = AppLocale.instance.l10n;
    expect(evidence.byId('cards').localTitle, l10n.famCardsTitle);
    expect(evidence.byId('cards').localSubtitle, l10n.famCardsSubtitle);
    final unknown = MarketFamily.publishedOnly(id: 'btts', title: 'Ambos marcan');
    expect(unknown.localTitle, 'Ambos marcan');
    expect(unknown.localSubtitle, 'Ambos marcan');
  });

  test('un nombre vacío del servidor no tapa el texto de la app', () {
    sportCatalogNotifier.value = withFamilies([
      {'id': 'cards', 'orden': 1, 'nombre': {'es': '  '}, 'subtitulo': <String, Object?>{}},
    ]);
    expect(evidence.byId('cards').localTitle, AppLocale.instance.l10n.famCardsTitle);
  });

  test('las familias de NBA se buscan en el deporte nba y las de fútbol en el de fútbol', () {
    sportCatalogNotifier.value = withFamilies([
      {'id': 'nba_winner', 'orden': 1, 'nombre': {'es': 'Ganador NBA del servidor'}},
    ], sport: 'nba');
    expect(evidence.byId('nba_winner').localTitle, 'Ganador NBA del servidor');
    expect(evidence.byId('winner').localTitle, AppLocale.instance.l10n.famWinnerTitle, reason: 'fútbol: nba no lo gobierna');
  });

  test('con el deporte apagado (fuera del catálogo) vuelve al texto de la app', () async {
    final factory = (await loadFactorySportCatalog())!;
    sportCatalogNotifier.value = withFamilies([
      {'id': 'cards', 'orden': 1, 'nombre': {'es': 'Del servidor'}},
    ], sport: 'tenis');
    expect(evidence.byId('cards').localTitle, AppLocale.instance.l10n.famCardsTitle);
    expect(factory.contains(kFootball), isTrue);
  });
}
